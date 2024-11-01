import json
from collections import deque

from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     message_handler, type_subscription)
from autogen_core.components.models import SystemMessage
from autogen_ext.models import AzureOpenAIChatCompletionClient

from ..data_types import EndUserMessage, HandoffMessage, TravelPlan
from ..intent import IntentClassifier
from ..otlp_tracing import logger
from ..registry import AgentRegistry
from ..session_state import SessionStateManager


@type_subscription(topic_type="router")
class SemanticRouterAgent(RoutedAgent):
    def __init__(
        self,
        name: str,
        model_client: AzureOpenAIChatCompletionClient,
        agent_registry: AgentRegistry,
        intent_classifier: IntentClassifier,
        session_manager: SessionStateManager,
    ) -> None:
        super().__init__("SemanticRouterAgent")
        self._name = name
        self._model_client = model_client
        self._registry = agent_registry
        self._classifier = intent_classifier
        self._session_manager = session_manager

    @message_handler
    async def route_message(self, message: EndUserMessage, ctx: MessageContext) -> None:
        session_id = ctx.topic_id.source

        # Add the current message to session history
        self._session_manager.add_to_history(session_id, message)

        # Analyze conversation history for better context
        history = self._session_manager.get_history(session_id)
        logger.info("Analyzing conversation history for context")

        travel_plan: TravelPlan = await self._get_agents_to_route(message, history)
        logger.info(f"Routing message to agents: {travel_plan}")

        if not travel_plan.subtasks:
            logger.info("No agents selected for routing")
            return

        # If only one agent is involved, send the message directly
        if len(travel_plan.subtasks) == 1:
            assigned_agent = travel_plan.subtasks[0].assigned_agent
            logger.info(f"Routing message to agent: {assigned_agent}")
            await self.publish_message(
                EndUserMessage(content=message.content, source=message.source),
                DefaultTopicId(type=assigned_agent, source=session_id),
            )
        else:
            # If more than one agent is involved, send the message to GroupChatManager for coordination
            logger.info(
                f"Routing message to GroupChatManager for coordination: {[subtask.assigned_agent for subtask in travel_plan.subtasks]}"
            )
            await self.publish_message(
                travel_plan,
                DefaultTopicId(type="group_chat_manager", source=session_id),
            )

    @message_handler
    async def handle_handoff(
        self, message: HandoffMessage, ctx: MessageContext
    ) -> None:
        session_id = ctx.topic_id.source
        logger.info(f"Received handoff message from {message.source}")

        # Clear session if conversation is complete, otherwise continue routing
        if message.complete:
            self._session_manager.clear_session(session_id)
        else:
            await self.route_message(
                EndUserMessage(content=message.content, source=message.source), ctx
            )

    async def _get_agents_to_route(
        self, message: EndUserMessage, history: deque
    ) -> TravelPlan:
        # System prompt to determine the appropriate agents to handle the message
        system_message = f"""
        You are an orchestration agent.
        Your job is to decide which agents to run based on the user's request and the conversation history.
        Below are the available agents:

        * hotel_booking - Helps in booking hotels.
        * activities_booking - Helps in providing activities information.
        * flight_booking - Helps in providing flight information.
        * car_rental - Helps in booking car rentals.
        * group_chat_manager - Coordinates messages between agents to create a travel plan.
        * destination_info - Provides information about a destination city.
        * default_agent - Default agent to handle any other requests that do not match the above agents.

        The current user message: {message.content}
        Conversation history so far: {[msg.content for msg in history]}

        Note: You should try and address the current user message. coversation history is provided for context.

        Output one or more of the agent identifiers and the sub task with details they need to act up on. Include information regarding the travel plan in the sub tasks.Do not provide any other information.
        """
        try:
            response = await self._model_client.create(
                [SystemMessage(system_message)],
                extra_create_args={"response_format": TravelPlan},
            )
            my_travel_plan: TravelPlan = TravelPlan.model_validate(
                json.loads(response.content)
            )
            logger.info(f"Received travel plan: {my_travel_plan}")
            return my_travel_plan
        except Exception as e:
            logger.error(f"Failed to parse activities response: {str(e)}")
            return TravelPlan(subtasks=[])
