from dataclasses import dataclass
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
    requirements: dict


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
