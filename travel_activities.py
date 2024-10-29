from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     default_subscription, message_handler,
                                     type_subscription)

from data_types import (AgentResponse, GroupChatMessage, HandoffMessage,
                        TravelRequest, UserMessage)
from otlp_tracing import logger


# Activities Agent
@default_subscription
@type_subscription("activities")
class ActivitiesAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("ActivitiesAgent")

    @message_handler
    async def handle_message(self, message: UserMessage, ctx: MessageContext) -> None:
        logger.info(f"ActivitiesAgent received message: {message.content}")
        if "travel plan" in message.content.lower():
            # Cannot handle complex travel plans, hand off back to router
            await self.publish_message(
                HandoffMessage(content=message.content, source=self.id.type),
                DefaultTopicId(type="router", source=ctx.topic_id.source),
            )
            return
        # Provide activities booking
        requirements = self.extract_requirements(message.content)
        response = await self.process_request(requirements)
        await self.publish_message(
            AgentResponse(
                source=self.id.type,
                content=f"Activities booked: {response['activities_details']}",
            ),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
        )

    @message_handler
    async def handle_travel_request(
        self, message: TravelRequest, ctx: MessageContext
    ) -> None:
        logger.info(f"ActivitiesAgent received travel request: {message.content}")
        # Provide activities booking
        response = await self.process_request(message.requirements)
        await self.publish_message(
            GroupChatMessage(
                source=self.id.type,
                content=f"Activities booked: {response['activities_details']}",
            ),
            DefaultTopicId(type="group_chat_manager", source=ctx.topic_id.source),
        )

    async def process_request(self, requirements: dict) -> dict:
        # Simulate activities booking logic
        activities_details = "Booked activities in {}: {}".format(
            requirements.get("destination_city", "Unknown"),
            "Eiffel Tower tour, Seine River cruise",
        )
        return {"activities_details": activities_details}

    def extract_requirements(self, user_input: str) -> dict:
        # Simple keyword-based extraction
        requirements = {}
        if "paris" in user_input.lower():
            requirements["destination_city"] = "Paris"
        return requirements
