from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     default_subscription, message_handler,
                                     type_subscription)

from data_types import (AgentResponse, EndUserMessage, GroupChatMessage,
                        HandoffMessage, TravelRequest)
from otlp_tracing import logger


# Flight Agent with Handoff Logic
@default_subscription
@type_subscription("flight")
class FlightAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("FlightAgent")

    @message_handler
    async def handle_message(
        self, message: EndUserMessage, ctx: MessageContext
    ) -> None:
        logger.info(f"FlightAgent received message: {message.content}")
        if "travel plan" in message.content.lower():
            # Cannot handle complex travel plans, hand off back to router
            await self.publish_message(
                HandoffMessage(content=message.content, source=self.id.type),
                DefaultTopicId(type="router", source=ctx.topic_id.source),
            )
            return
        # Process flight booking
        requirements = self.extract_requirements(message.content)
        response = await self.process_request(requirements)
        await self.publish_message(
            AgentResponse(
                source=self.id.type,
                content=f"Flight booked: {response['flight_details']}",
            ),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
        )

    @message_handler
    async def handle_travel_request(
        self, message: TravelRequest, ctx: MessageContext
    ) -> None:
        logger.info(f"FlightAgent received travel request: {message.content}")
        # Process flight booking
        response = await self.process_request(message.requirements)
        await self.publish_message(
            GroupChatMessage(
                source=self.id.type,
                content=f"Flight booked: {response['flight_details']}",
            ),
            DefaultTopicId(type="group_chat_manager", source=ctx.topic_id.source),
        )

    async def process_request(self, requirements: dict) -> dict:
        # Simulate flight booking logic
        flight_details = "Flight from {} to {} on {}".format(
            requirements.get("departure_city", "Unknown"),
            requirements.get("destination_city", "Unknown"),
            requirements.get("departure_date", "Unknown"),
        )
        return {"flight_details": flight_details}

    def extract_requirements(self, user_input: str) -> dict:
        # Simple keyword-based extraction
        requirements = {}
        words = user_input.lower().split()
        if "paris" in words:
            requirements["destination_city"] = "Paris"
        if "new york" in user_input.lower():
            requirements["departure_city"] = "New York"
        # Add more keyword-based extractions as needed
        requirements["departure_date"] = "2023-12-20"
        return requirements
