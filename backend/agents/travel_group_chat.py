import asyncio
from collections import defaultdict
from typing import List

from autogen_core import AgentId, MessageContext
from autogen_core import (
    DefaultTopicId,
    RoutedAgent,
    message_handler,
    type_subscription,
)

from ..data_types import (
    AgentStructuredResponse,
    EndUserMessage,
    GroupChatMessage,
    TravelPlan,
    TravelRequest,
    GroupChatResponse,
)
from ..otlp_tracing import logger


@type_subscription("group_chat_manager")
class GroupChatManager(RoutedAgent):
    """
    Manages communication between multiple agents involved in creating a travel plan.

    Attributes:
        _chat_history (List[GroupChatMessage]): Stores messages exchanged during the chat.
        _conversation_complete (bool): Indicates if the conversation is complete.
        _session_id (str): Stores the current session ID.
        _responses (defaultdict): Stores agent responses for compiling the final travel plan.
    """

    def __init__(self) -> None:
        super().__init__("GroupChatManager")
        self._chat_history: List[GroupChatMessage] = []
        self._conversation_complete = False
        self._session_id = None
        self._responses = defaultdict(list)

    @message_handler
    async def handle_travel_request(
        self, message: EndUserMessage, ctx: MessageContext
    ) -> None:
        """
        Handles incoming travel requests from the user and initiates communication with relevant agents.

        Args:
            message (EndUserMessage): The incoming user message.
            ctx (MessageContext): The context of the current message.
        """
        self._session_id = ctx.topic_id.source
        await self.request_relevant_agents(ctx.topic_id.type)

    @message_handler
    async def handle_complex_travel_request(
        self, message: TravelPlan, ctx: MessageContext
    ) -> None:
        """
        Handles complex travel requests that require coordination between multiple agents.

        Args:
            message (TravelPlan): The incoming travel plan request containing multiple tasks.
            ctx (MessageContext): The context of the current message.
        """
        try:
            self._session_id = ctx.topic_id.source
            tasks = []
            
            for task in message.subtasks:
                try:
                    if isinstance(task, dict):
                        task_details = task.get('task_details')
                        assigned_agent = task.get('assigned_agent')
                    else:
                        task_details = task.task_details
                        assigned_agent = task.assigned_agent
                        
                    travel_request = TravelRequest(
                        source="GroupChatManager",
                        content=task_details,
                        original_task=message.main_task,
                    )
                    agent_id = AgentId(type=assigned_agent, key=self._session_id)
                    
                    tasks.append(
                        self.send_message(travel_request, agent_id)
                    )
                    
                except Exception as e:
                    logger.error(f"Error creating task")
                    logger.error(f"Task data: {task}")
                    logger.error(f"Error type: {type(e)}")
                    logger.error(f"Error message: {str(e)}")
                    logger.error("Error details:", exc_info=True)
                    continue

            group_results: List[GroupChatMessage] = await asyncio.gather(*tasks)
            final_plan = "\n".join([response.content for response in group_results])

            await self.publish_message(
                AgentStructuredResponse(
                    agent_type=self.id.type,
                    data=GroupChatMessage(
                        source=self.id.type,
                        content=final_plan,
                    ),
                    message=f"Here is your comprehensive travel plan:\n{final_plan}",
                ),
                DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
            )
            
        except Exception as e:
            logger.error("Error in handle_complex_travel_request")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error message: {str(e)}")
            logger.error("Error details:", exc_info=True)

    async def request_relevant_agents(self, relevant_agents: List[str]) -> None:
        """
        Sends requests to the relevant agents to provide details needed for the travel plan.

        Args:
            relevant_agents (List[str]): The list of agent types involved in the travel plan.
        """
        for agent_type in relevant_agents:
            await self.publish_message(
                TravelRequest(
                    source="GroupChatManager",
                    content="Provide details for the travel plan",
                    original_task="General travel plan",
                ),
                DefaultTopicId(type=agent_type, source=self._session_id),
            )

    @message_handler
    async def handle_handoff(self, message: TravelRequest, ctx: MessageContext) -> None:
        """
        Handles handoff requests from other agents, either continuing or concluding the conversation.

        Args:
            message (TravelRequest): The handoff message from another agent.
            ctx (MessageContext): Context information for the message.
        """
        session_id = ctx.topic_id.source
        if message.original_task and "complete" in message.content.lower():
            self._conversation_complete = True
        else:
            await self.compile_final_plan()

    async def compile_final_plan(self) -> None:
        """
        Compiles the final travel plan based on collected responses from agents.
        """
        final_plan = "\n".join(
            response.content for response in self._responses[self._session_id]
        )
        await self.publish_message(
            AgentStructuredResponse(
                agent_type=self.id.type,
                data=GroupChatResponse(
                    source=self.id.type,
                    content=final_plan,
                ),
                message=f"Here is your comprehensive travel plan:\n{final_plan}",
            ),
            DefaultTopicId(type="user_proxy", source=self._session_id),
        )
