from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     default_subscription, message_handler,
                                     type_subscription)

from data_types import (AgentResponse, EndUserMessage, GroupChatMessage,
                        HandoffMessage, TravelRequest)
from otlp_tracing import logger


# Car Rental Agent
@default_subscription
@type_subscription("car_rental")
class CarRentalAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("CarRentalAgent")

    @message_handler
    async def handle_message(
        self, message: EndUserMessage, ctx: MessageContext
    ) -> None:
        logger.info(f"CarRentalAgent received message: {message.content}")
        if "travel plan" in message.content.lower():
            # Cannot handle complex travel plans, hand off back to router
            await self.publish_message(
                HandoffMessage(content=message.content, source=self.id.type),
                DefaultTopicId(type="router", source=ctx.topic_id.source),
            )
            return
        # Process car rental booking
        requirements = self.extract_requirements(message.content)
        response = await self.process_request(requirements)
        await self.publish_message(
            AgentResponse(
                source=self.id.type,
                content=f"Car rented: {response['car_rental_details']}",
            ),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
        )

    @message_handler
    async def handle_travel_request(
        self, message: TravelRequest, ctx: MessageContext
    ) -> None:
        logger.info(f"CarRentalAgent received travel request: {message.content}")
        # Process car rental booking
        response = await self.process_request(message.requirements)
        await self.publish_message(
            GroupChatMessage(
                source=self.id.type,
                content=f"Car rented: {response['car_rental_details']}",
            ),
            DefaultTopicId(type="group_chat_manager", source=ctx.topic_id.source),
        )

    async def process_request(self, requirements: dict) -> dict:
        # Simulate car rental booking logic
        car_rental_details = "Car rented in {} from {} to {}".format(
            requirements.get("rental_city", "Unknown"),
            requirements.get("rental_start_date", "Unknown"),
            requirements.get("rental_end_date", "Unknown"),
        )
        return {"car_rental_details": car_rental_details}

    def extract_requirements(self, user_input: str) -> dict:
        # Simple keyword-based extraction
        requirements = {}
        if "paris" in user_input.lower():
            requirements["rental_city"] = "Paris"
        requirements["rental_start_date"] = "2023-12-21"
        requirements["rental_end_date"] = "2023-12-26"
        return requirements
