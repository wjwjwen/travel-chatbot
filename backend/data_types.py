from dataclasses import dataclass
from enum import Enum
from typing import List

from pydantic import BaseModel


# Message Protocol Definitions
@dataclass
class BaseMessage:
    source: str


@dataclass
class EndUserMessage(BaseMessage):
    content: str


@dataclass
class AgentResponse(BaseMessage):
    content: str


@dataclass
class GroupChatMessage(BaseMessage):
    content: str


@dataclass
class RequestToSpeak(BaseMessage):
    pass


@dataclass
class TravelRequest(BaseMessage):
    content: str
    original_task: str


@dataclass
class HandoffMessage(BaseMessage):
    content: str


class ActivitiesDetail(BaseModel):
    activity_name: str
    activity_type: str
    activity_description: str


class Activities(BaseModel):
    destination_city: str
    activities: List[ActivitiesDetail]


class DestinationInfo(BaseModel):
    city: str
    country: str
    destination_info: str
    best_time_to_visit: str
    average_temp: str
    currency: str
    language: str
    similar_destinations: List[str]


class AgentEnum(str, Enum):
    FlightBooking = "flight_booking"
    HotelBooking = "hotel_booking"
    CarRental = "car_rental"
    ActivitiesBooking = "activities_booking"
    DestinationInfo = "destination_info"


class TravelSubTask(BaseModel):
    task_details: str
    assigned_agent: AgentEnum

    class Config:
        use_enum_values = True  # To serialize enums as their values


class TravelPlan(BaseModel):
    main_task: str
    subtasks: List[TravelSubTask]
