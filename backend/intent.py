# Intent Classifier
from .otlp_tracing import logger


class IntentClassifier:
    def __init__(self):

        self.intents = {
            "flight_booking": ["flight", "plane", "ticket", "airline"],
            "hotel_booking": ["hotel", "accommodation", "room", "stay"],
            "car_rental": ["car rental", "rent a car", "rental car", "car hire"],
            "activities_booking": ["activities", "tours", "sightseeing", "events"],
            "travel_plan": ["travel plan", "itinerary", "trip", "vacation", "holiday"],
            "destination_info": ["destination", "city", "country", "place"],
            # Add more intents as needed
        }

    async def classify_intent(self, message: str) -> str:
        message_lower = message.lower()
        for intent, keywords in self.intents.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return intent
        logger.info(f"Unknown intent for message: {message}")
        return "unknown_intent"
