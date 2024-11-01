from typing import Optional

from .otlp_tracing import logger


# Agent Registry
class AgentRegistry:
    def __init__(self):
        self.agents = {
            "flight_booking": "flight_booking",
            "hotel_booking": "hotel_booking",
            "car_rental": "car_rental",
            "activities_booking": "activities_booking",
            "travel_plan": "group_chat_manager",
            "destination_info": "destination_info",
            # Map more intents to agent types as needed
        }

    async def get_agent(self, intent: str) -> Optional[str]:
        logger.info(f"AgentRegistry: Getting agent for intent: {intent}")
        return self.agents.get(intent)
