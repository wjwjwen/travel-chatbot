from pydantic import BaseModel
from enum import Enum
from typing import List, Optional, Union
from datetime import date


# Message Protocol Definitions
class BaseMessage(BaseModel):
    source: str


class EndUserMessage(BaseMessage):
    content: str


class AgentResponse(BaseMessage):
    content: str


class GroupChatMessage(BaseMessage):
    content: str


class GroupChatResponse(BaseMessage):
    content: str


class RequestToSpeak(BaseMessage):
    pass


class TravelRequest(BaseMessage):
    content: str
    original_task: str


class HandoffMessage(BaseMessage):
    content: str


class ActivitiesDetail(BaseModel):
    activity_name: str
    activity_type: str
    activity_description: str


class Activities(BaseModel):
    destination_city: str
    activities: List[ActivitiesDetail]


class Greeter(BaseModel):
    greeting: str


# Destination Information Data Model
class DestinationInfo(BaseModel):
    city: str
    country: str
    description: str
    best_time_to_visit: str
    average_temperature: str
    currency: str
    language: str
    similar_destinations: List[str]


# Flight Booking Data Model
class FlightBooking(BaseModel):
    departure_city: str
    destination_city: str
    departure_date: date
    return_date: date
    airline: str
    flight_number: str
    total_price: float
    booking_reference: str
    number_of_passengers: int


# Hotel Booking Data Model
class HotelBooking(BaseModel):
    city: str
    check_in_date: str
    check_out_date: str
    hotel_name: str
    room_type: str
    total_price: float
    booking_reference: str


class CarRental(BaseModel):
    rental_city: str
    rental_start_date: str
    rental_end_date: str
    car_type: str
    company: str
    total_price: float
    booking_reference: str


class AgentEnum(str, Enum):
    FlightBooking = "flight_booking"
    HotelBooking = "hotel_booking"
    CarRental = "car_rental"
    ActivitiesBooking = "activities_booking"
    DestinationInfo = "destination_info"
    DefaultAgent = "default_agent"
    GroupChatManager = "group_chat_manager"


class TravelSubTask(BaseModel):
    task_details: str
    assigned_agent: AgentEnum

    class Config:
        use_enum_values = True  # To serialize enums as their values


class TravelPlan(BaseModel):
    main_task: str
    subtasks: List[TravelSubTask]
    is_greeting: bool


# Generic Response Wrapper
class AgentStructuredResponse(BaseModel):
    agent_type: AgentEnum
    data: Union[
        Activities,
        DestinationInfo,
        FlightBooking,
        HotelBooking,
        CarRental,
        Greeter,
        GroupChatResponse,
    ]
    message: Optional[str] = None  # Additional message or notes from the agent


class Resource(BaseModel):
    """
    Represents a resource node retrieved during chat interactions.

    Attributes:
        content (str): The textual content of the resource.
        node_id (str): The identifier of the node.
        score (Optional[float]): Score representing the relevance of the resource.
    """

    content: str
    node_id: str
    score: Optional[float] = None
