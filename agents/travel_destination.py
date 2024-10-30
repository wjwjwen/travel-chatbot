from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     default_subscription, message_handler,
                                     type_subscription)

from data_types import GroupChatMessage, TravelRequest
from otlp_tracing import logger


# Destination Agent
@default_subscription
@type_subscription("destination")
class DestinationAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("DestinationAgent")

    @message_handler
    async def handle_message(self, message: TravelRequest, ctx: MessageContext) -> None:
        logger.info(f"DestinationAgent received travel request: {message.content}")
        # Provide destination information
        response = await self.process_request(message.requirements)
        await self.publish_message(
            GroupChatMessage(
                source=self.id.type,
                content=f"Destination info: {response['destination_info']}",
            ),
            DefaultTopicId(type="group_chat_manager", source=ctx.topic_id.source),
        )

    async def process_request(self, requirements: dict) -> dict:
        # Simulate destination information retrieval
        destination_info = "Top attractions in {}".format(
            requirements.get("destination_city", "Unknown")
        )
        return {"destination_info": destination_info}
