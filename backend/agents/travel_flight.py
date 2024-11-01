import random
from typing import Dict

from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     message_handler, type_subscription)
from typing_extensions import Annotated

from ..data_types import (AgentResponse, EndUserMessage, HandoffMessage,
                          TravelRequest)
from ..otlp_tracing import logger


async def simulate_flight_booking(
    departure_city: Annotated[str, "The city from which the flight will depart."],
    destination_city: Annotated[str, "The city to which the flight will arrive."],
    departure_date: Annotated[
        str, "The departure date of the flight in the format 'YYYY-MM-DD'."
    ],
    return_date: Annotated[
        str, "The return date of the flight in the format 'YYYY-MM-DD'."
    ],
) -> Dict[str, str | int]:
    """
    Simulate a flight booking process.

    This function simulates the process of booking a flight by randomly selecting a flight option,
    calculating the total price for a round trip, and generating a booking reference number.

    Args:
        departure_city (str): The city from which the flight will depart.
        destination_city (str): The city to which the flight will arrive.
        departure_date (str): The departure date of the flight in the format 'YYYY-MM-DD'.
        return_date (str): The return date of the flight in the format 'YYYY-MM-DD'.

    Returns:
        Dict[str, str | int]: A dictionary containing the flight booking details, including the departure city,
                              destination city, departure and return dates, airline, flight number, total price,
                              and booking reference.
                              Example:
                              {
                                  "departure_city": "New York",
                                  "destination_city": "Paris",
                                  "departure_date": "2023-10-01",
                                  "return_date": "2023-10-07",
                                  "airline": "Delta",
                                  "flight_number": "DL456",
                                  "total_price": 500,
                                  "booking_reference": "FL-1234-PAR"
                              }
    """
    # Simulate available flight options
    flight_options = [
        {"airline": "Air France", "flight_number": "AF123", "price_per_ticket": 200},
        {"airline": "Delta", "flight_number": "DL456", "price_per_ticket": 250},
        {
            "airline": "British Airways",
            "flight_number": "BA789",
            "price_per_ticket": 300,
        },
        {"airline": "Lufthansa", "flight_number": "LH101", "price_per_ticket": 220},
        {"airline": "Emirates", "flight_number": "EK202", "price_per_ticket": 400},
        {"airline": "Qatar Airways", "flight_number": "QR303", "price_per_ticket": 350},
        {
            "airline": "Singapore Airlines",
            "flight_number": "SQ404",
            "price_per_ticket": 450,
        },
        {
            "airline": "United Airlines",
            "flight_number": "UA505",
            "price_per_ticket": 280,
        },
        {
            "airline": "American Airlines",
            "flight_number": "AA606",
            "price_per_ticket": 260,
        },
        {"airline": "KLM", "flight_number": "KL707", "price_per_ticket": 240},
    ]

    # Randomly select a flight option
    selected_flight = random.choice(flight_options)

    # Calculate total price for a round trip
    total_price = 2 * selected_flight["price_per_ticket"]

    # Create a booking reference number
    booking_reference = (
        f"FL-{random.randint(1000, 9999)}-{destination_city[:3].upper()}"
    )

    # Simulate flight booking details
    flight_booking_details = {
        "departure_city": departure_city,
        "destination_city": destination_city,
        "departure_date": departure_date,
        "return_date": return_date,
        "airline": selected_flight["airline"],
        "flight_number": selected_flight["flight_number"],
        "total_price": total_price,
        "booking_reference": booking_reference,
    }

    return flight_booking_details


# Flight Agent with Handoff Logic
@type_subscription(topic_type="flight_booking")
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
        logger.info(f"FlightAgent processing flight booking: {message.content}")
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
        logger.info(f"FlightAgent received travel request sub-task: {message.content}")
        # Process flight booking
        await self.publish_message(
            AgentResponse(
                source=self.id.type,
                content="Flight booking processed as requested and confirmation will be sent by email",
            ),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
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
