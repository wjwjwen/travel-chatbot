from typing import Optional

from otlp_tracing import logger


# Agent Registry
class AgentRegistry:
    def __init__(self):
        self.agents = {
            "flight_booking": "flight",
            "hotel_booking": "hotel",
            "car_rental": "car_rental",
            "activities_booking": "activities",
            "travel_plan": "group_chat_manager",
            # Map more intents to agent types as needed
        }

    async def get_agent(self, intent: str) -> Optional[str]:
        logger.info(f"AgentRegistry: Getting agent for intent: {intent}")
        return self.agents.get(intent)
