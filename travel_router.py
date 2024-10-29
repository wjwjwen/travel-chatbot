from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     default_subscription, message_handler)

from data_types import HandoffMessage, UserMessage
from intent import IntentClassifier
from otlp_tracing import logger
from registry import AgentRegistry


# Semantic Router Agent
@default_subscription
class SemanticRouterAgent(RoutedAgent):
    def __init__(
        self,
        name: str,
        agent_registry: AgentRegistry,
        intent_classifier: IntentClassifier,
    ) -> None:
        super().__init__("SemanticRouterAgent")
        self._name = name
        self._registry = agent_registry
        self._classifier = intent_classifier

    @message_handler
    async def route_message(self, message: UserMessage, ctx: MessageContext) -> None:
        session_id = ctx.topic_id.source
        intent = await self._classifier.classify_intent(message.content)
        agent_type = await self._registry.get_agent(intent)
        logger.info(f"Intent: {intent}, Agent: {agent_type}")
        if not agent_type:
            # Unknown intent, route to DefaultAgent
            agent_type = "default_agent"
            logger.info("Unknown intent, routing to DefaultAgent")
        await self.publish_message(
            UserMessage(content=message.content, source=message.source),
            DefaultTopicId(type=agent_type, source=session_id),
        )

    @message_handler
    async def handle_handoff(
        self, message: HandoffMessage, ctx: MessageContext
    ) -> None:
        logger.info(
            f"SemanticRouterAgent received handoff message from {message.source}"
        )
        await self.route_message(
            UserMessage(content=message.content, source=message.source), ctx
        )
