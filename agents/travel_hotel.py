from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     default_subscription, message_handler,
                                     type_subscription)

from data_types import (AgentResponse, EndUserMessage, GroupChatMessage,
                        HandoffMessage, TravelRequest)
from otlp_tracing import logger


# Hotel Agent with Handoff Logic
@default_subscription
@type_subscription("hotel")
class HotelAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("HotelAgent")

    @message_handler
    async def handle_message(
        self, message: EndUserMessage, ctx: MessageContext
    ) -> None:
        logger.info(f"HotelAgent received message: {message.content}")
        if "travel plan" in message.content.lower():
            # Cannot handle complex travel plans, hand off back to router
            await self.publish_message(
                HandoffMessage(content=message.content, source=self.id.type),
                DefaultTopicId(type="router", source=ctx.topic_id.source),
            )
            return
        # Process hotel booking
        requirements = self.extract_requirements(message.content)
        response = await self.process_request(requirements)
        await self.publish_message(
            AgentResponse(
                source=self.id.type,
                content=f"Hotel booked: {response['hotel_details']}",
            ),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
        )

    @message_handler
    async def handle_travel_request(
        self, message: TravelRequest, ctx: MessageContext
    ) -> None:
        logger.info(f"HotelAgent received travel request: {message.content}")
        # Process hotel booking
        response = await self.process_request(message.requirements)
        await self.publish_message(
            GroupChatMessage(
                source=self.id.type,
                content=f"Hotel booked: {response['hotel_details']}",
            ),
            DefaultTopicId(type="group_chat_manager", source=ctx.topic_id.source),
        )

    async def process_request(self, requirements: dict) -> dict:
        # Simulate hotel booking logic
        hotel_details = "Hotel in {} from {} to {}".format(
            requirements.get("destination_city", "Unknown"),
            requirements.get("check_in_date", "Unknown"),
            requirements.get("check_out_date", "Unknown"),
        )
        return {"hotel_details": hotel_details}

    def extract_requirements(self, user_input: str) -> dict:
        # Simple keyword-based extraction
        requirements = {}
        words = user_input.lower().split()
        if "paris" in words:
            requirements["destination_city"] = "Paris"
        # Add more keyword-based extractions as needed
        requirements["check_in_date"] = "2023-12-20"
        requirements["check_out_date"] = "2023-12-27"
        return requirements
