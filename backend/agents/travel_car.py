import asyncio
import datetime
import random
from typing import Dict, List

from autogen_core.base import MessageContext
from autogen_core.components import (
    DefaultTopicId,
    RoutedAgent,
    message_handler,
    type_subscription,
)
from autogen_core.components.models import LLMMessage, SystemMessage
from typing_extensions import Annotated

from ..data_types import (
    AgentResponse,
    EndUserMessage,
    GroupChatMessage,
    HandoffMessage,
    TravelRequest,
)
from ..otlp_tracing import logger


async def simulate_car_rental_booking(
    rental_city: Annotated[str, "The city where the car rental will take place."],
    rental_start_date: Annotated[
        str, "The start date of the car rental in the format 'YYYY-MM-DD'."
    ],
    rental_end_date: Annotated[
        str, "The end date of the car rental in the format 'YYYY-MM-DD'."
    ],
) -> Dict[str, str | int]:
    """
    Simulate a car rental booking process.

    This function simulates the process of booking a car rental by randomly selecting a car option,
    calculating the rental duration and total price, and generating a booking reference number.

    Args:
        rental_city (str): The city where the car rental will take place.
        rental_start_date (str): The start date of the car rental in the format 'YYYY-MM-DD'.
        rental_end_date (str): The end date of the car rental in the format 'YYYY-MM-DD'.

    Returns:
        Dict[str, str | int]: A dictionary containing the car rental details, including the rental city,
                              start and end dates, car type, company, total price, and booking reference.
                              Example:
                              {
                                  "rental_city": "New York",
                                  "rental_start_date": "2023-10-01",
                                  "rental_end_date": "2023-10-07",
                                  "car_type": "SUV",
                                  "company": "Hertz",
                                  "total_price": 560,
                                  "booking_reference": "CR-1234-NYC"
                              }
    """
    # Simulate available car options
    car_options = [
        {"car_type": "Sedan", "company": "Avis", "price_per_day": 50},
        {"car_type": "SUV", "company": "Hertz", "price_per_day": 80},
        {"car_type": "Convertible", "company": "Budget", "price_per_day": 100},
        {"car_type": "Minivan", "company": "Enterprise", "price_per_day": 70},
        {"car_type": "Compact", "company": "Thrifty", "price_per_day": 40},
        {"car_type": "Luxury", "company": "Alamo", "price_per_day": 150},
        {"car_type": "Pickup Truck", "company": "National", "price_per_day": 90},
        {"car_type": "Electric", "company": "Tesla Rentals", "price_per_day": 120},
        {"car_type": "Hybrid", "company": "Green Wheels", "price_per_day": 60},
        {"car_type": "Sports Car", "company": "Exotic Rentals", "price_per_day": 200},
        {"car_type": "Station Wagon", "company": "Family Rentals", "price_per_day": 75},
        {"car_type": "Van", "company": "Van Rentals Inc.", "price_per_day": 85},
        {"car_type": "Crossover", "company": "Cross Rentals", "price_per_day": 65},
        {"car_type": "Coupe", "company": "Luxury Line", "price_per_day": 110},
        {"car_type": "Hatchback", "company": "City Rentals", "price_per_day": 45},
    ]

    # Randomly select a car option
    selected_car = random.choice(car_options)

    # Calculate rental duration
    start_date = datetime.datetime.strptime(rental_start_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(rental_end_date, "%Y-%m-%d")
    rental_days = (end_date - start_date).days

    # Calculate total price
    total_price = rental_days * selected_car["price_per_day"]

    # Create a booking reference number
    booking_reference = f"CR-{random.randint(1000, 9999)}-{rental_city[:3].upper()}"

    # Simulate car rental details
    car_rental_details = {
        "rental_city": rental_city,
        "rental_start_date": rental_start_date,
        "rental_end_date": rental_end_date,
        "car_type": selected_car["car_type"],
        "company": selected_car["company"],
        "total_price": total_price,
        "booking_reference": booking_reference,
    }
    # Induce an artificial delay to simulate network latency
    await asyncio.sleep(3)
    return car_rental_details


# Car Rental Agent
@type_subscription("car_rental")
class CarRentalAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("CarRentalAgent")
        logger.info("CarRentalAgent initialized")
        self._system_messages: List[LLMMessage] = [
            SystemMessage(
                "You are a helpful AI assistant that can advise on car rental bookings based on user preferences."
            )
        ]

    async def _process_request(self, requirements: dict) -> dict:
        # Simulate car rental booking logic
        return await simulate_car_rental_booking(
            requirements.get("rental_city", "Unknown"),
            requirements.get("rental_start_date", "Unknown"),
            requirements.get("rental_end_date", "Unknown"),
        )

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
        # Extract requirements and process the car rental request
        requirements = self.extract_requirements(message.content)
        response = await self._process_request(requirements)
        await self.publish_message(
            AgentResponse(
                source=self.id.type,
                content=f"Car rented: {response}",
            ),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
        )

    @message_handler
    async def handle_travel_request(
        self, message: TravelRequest, ctx: MessageContext
    ) -> GroupChatMessage:
        logger.info(
            f"CarRentalAgent received travel request: TravelRequest - {message.content}"
        )
        requirements = self.extract_requirements(message.content)
        response = await self._process_request(requirements)
        return GroupChatMessage(
            source=self.id.type,
            content=f"Car rented: {response}",
        )

    def extract_requirements(self, user_input: str) -> dict:
        # Simple keyword-based extraction
        requirements = {}
        if "new york" in user_input.lower():
            requirements["rental_city"] = "New York"
        requirements["rental_start_date"] = "2023-12-21"
        requirements["rental_end_date"] = "2023-12-26"
        return requirements
