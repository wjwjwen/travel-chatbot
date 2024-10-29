from dataclasses import dataclass


# Message Protocol Definitions
@dataclass
class BaseMessage:
    source: str


@dataclass
class UserMessage(BaseMessage):
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
