import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import List, Optional

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentRuntime, MessageContext
from autogen_core.components import (
    DefaultSubscription,
    DefaultTopicId,
    RoutedAgent,
    default_subscription,
    message_handler,
    type_subscription,
)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, WebSocketException

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("travel_chatbot")

# Define FastAPI app
app = FastAPI()


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


# Intent Classifier
class IntentClassifier:
    def __init__(self):
        self.intents = {
            "flight_booking": ["flight", "plane", "ticket", "airline"],
            "hotel_booking": ["hotel", "accommodation", "room", "stay"],
            "car_rental": ["car rental", "rent a car", "rental car", "car hire"],
            "activities_booking": ["activities", "tours", "sightseeing", "events"],
            "travel_plan": ["travel plan", "itinerary", "trip", "vacation", "holiday"],
            # Add more intents as needed
        }

    async def classify_intent(self, message: str) -> str:
        message_lower = message.lower()
        for intent, keywords in self.intents.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return intent
        return "unknown_intent"


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
        return self.agents.get(intent)


# Semantic Router Agent
@default_subscription
class SemanticRouterAgent(RoutedAgent):
    def __init__(
        self,
        name: str,
        agent_registry: AgentRegistry,
        intent_classifier: IntentClassifier,
    ) -> None:
        super().__init__("SemanticRouterAgent")
        self._name = name
        self._registry = agent_registry
        self._classifier = intent_classifier

    @message_handler
    async def route_message(self, message: UserMessage, ctx: MessageContext) -> None:
        session_id = ctx.topic_id.source
        intent = await self._classifier.classify_intent(message.content)
        agent_type = await self._registry.get_agent(intent)
        if not agent_type:
            # Unknown intent, route to DefaultAgent
            agent_type = "default_agent"
        await self.publish_message(
            UserMessage(content=message.content, source=message.source),
            DefaultTopicId(type=agent_type, source=session_id),
        )

    @message_handler
    async def handle_handoff(
        self, message: HandoffMessage, ctx: MessageContext
    ) -> None:
        logger.info(
            f"SemanticRouterAgent received handoff message from {message.source}"
        )
        await self.route_message(
            UserMessage(content=message.content, source=message.source), ctx
        )


# Default Agent
@default_subscription
class DefaultAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("DefaultAgent")

    @message_handler
    async def handle_unknown_intent(
        self, message: UserMessage, ctx: MessageContext
    ) -> None:
        logger.info(f"DefaultAgent received message: {message.content}")
        content = "I'm sorry, I couldn't understand your request. Could you please provide more details?"
        await self.publish_message(
            AgentResponse(source="DefaultAgent", content=content),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
        )


# Flight Agent with Handoff Logic
@default_subscription
@type_subscription("flight")
class FlightAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("FlightAgent")

    @message_handler
    async def handle_message(self, message: UserMessage, ctx: MessageContext) -> None:
        logger.info(f"FlightAgent received message: {message.content}")
        if "travel plan" in message.content.lower():
            # Cannot handle complex travel plans, hand off back to router
            await self.publish_message(
                HandoffMessage(content=message.content, source=self.id.type),
                DefaultTopicId(type="router", source=ctx.topic_id.source),
            )
            return
        # Process flight booking
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
        logger.info(f"FlightAgent received travel request: {message.content}")
        # Process flight booking
        response = await self.process_request(message.requirements)
        await self.publish_message(
            GroupChatMessage(
                source=self.id.type,
                content=f"Flight booked: {response['flight_details']}",
            ),
            DefaultTopicId(type="group_chat_manager", source=ctx.topic_id.source),
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


# Hotel Agent with Handoff Logic
@default_subscription
@type_subscription("hotel")
class HotelAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("HotelAgent")

    @message_handler
    async def handle_message(self, message: UserMessage, ctx: MessageContext) -> None:
        logger.info(f"HotelAgent received message: {message.content}")
        if "travel plan" in message.content.lower():
            # Cannot handle complex travel plans, hand off back to router
            await self.publish_message(
                HandoffMessage(content=message.content, source=self.id.type),
                DefaultTopicId(type="router", source=ctx.topic_id.source),
            )
            return
        # Process hotel booking
        requirements = self.extract_requirements(message.content)
        response = await self.process_request(requirements)
        await self.publish_message(
            AgentResponse(
                source=self.id.type,
                content=f"Hotel booked: {response['hotel_details']}",
            ),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
        )

    @message_handler
    async def handle_travel_request(
        self, message: TravelRequest, ctx: MessageContext
    ) -> None:
        logger.info(f"HotelAgent received travel request: {message.content}")
        # Process hotel booking
        response = await self.process_request(message.requirements)
        await self.publish_message(
            GroupChatMessage(
                source=self.id.type,
                content=f"Hotel booked: {response['hotel_details']}",
            ),
            DefaultTopicId(type="group_chat_manager", source=ctx.topic_id.source),
        )

    async def process_request(self, requirements: dict) -> dict:
        # Simulate hotel booking logic
        hotel_details = "Hotel in {} from {} to {}".format(
            requirements.get("destination_city", "Unknown"),
            requirements.get("check_in_date", "Unknown"),
            requirements.get("check_out_date", "Unknown"),
        )
        return {"hotel_details": hotel_details}

    def extract_requirements(self, user_input: str) -> dict:
        # Simple keyword-based extraction
        requirements = {}
        words = user_input.lower().split()
        if "paris" in words:
            requirements["destination_city"] = "Paris"
        # Add more keyword-based extractions as needed
        requirements["check_in_date"] = "2023-12-20"
        requirements["check_out_date"] = "2023-12-27"
        return requirements


# Car Rental Agent
@default_subscription
@type_subscription("car_rental")
class CarRentalAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("CarRentalAgent")

    @message_handler
    async def handle_message(self, message: UserMessage, ctx: MessageContext) -> None:
        logger.info(f"CarRentalAgent received message: {message.content}")
        if "travel plan" in message.content.lower():
            # Cannot handle complex travel plans, hand off back to router
            await self.publish_message(
                HandoffMessage(content=message.content, source=self.id.type),
                DefaultTopicId(type="router", source=ctx.topic_id.source),
            )
            return
        # Process car rental booking
        requirements = self.extract_requirements(message.content)
        response = await self.process_request(requirements)
        await self.publish_message(
            AgentResponse(
                source=self.id.type,
                content=f"Car rented: {response['car_rental_details']}",
            ),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
        )

    @message_handler
    async def handle_travel_request(
        self, message: TravelRequest, ctx: MessageContext
    ) -> None:
        logger.info(f"CarRentalAgent received travel request: {message.content}")
        # Process car rental booking
        response = await self.process_request(message.requirements)
        await self.publish_message(
            GroupChatMessage(
                source=self.id.type,
                content=f"Car rented: {response['car_rental_details']}",
            ),
            DefaultTopicId(type="group_chat_manager", source=ctx.topic_id.source),
        )

    async def process_request(self, requirements: dict) -> dict:
        # Simulate car rental booking logic
        car_rental_details = "Car rented in {} from {} to {}".format(
            requirements.get("rental_city", "Unknown"),
            requirements.get("rental_start_date", "Unknown"),
            requirements.get("rental_end_date", "Unknown"),
        )
        return {"car_rental_details": car_rental_details}

    def extract_requirements(self, user_input: str) -> dict:
        # Simple keyword-based extraction
        requirements = {}
        if "paris" in user_input.lower():
            requirements["rental_city"] = "Paris"
        requirements["rental_start_date"] = "2023-12-21"
        requirements["rental_end_date"] = "2023-12-26"
        return requirements


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


# Destination Agent
@default_subscription
@type_subscription("destination")
class DestinationAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("DestinationAgent")

    @message_handler
    async def handle_message(self, message: TravelRequest, ctx: MessageContext) -> None:
        logger.info(f"DestinationAgent received travel request: {message.content}")
        # Provide destination information
        response = await self.process_request(message.requirements)
        await self.publish_message(
            GroupChatMessage(
                source=self.id.type,
                content=f"Destination info: {response['destination_info']}",
            ),
            DefaultTopicId(type="group_chat_manager", source=ctx.topic_id.source),
        )

    async def process_request(self, requirements: dict) -> dict:
        # Simulate destination information retrieval
        destination_info = "Top attractions in {}".format(
            requirements.get("destination_city", "Unknown")
        )
        return {"destination_info": destination_info}


# Group Chat Manager
@default_subscription
class GroupChatManager(RoutedAgent):
    def __init__(self, participant_topic_types: List[str]) -> None:
        super().__init__("GroupChatManager")
        self._participant_topic_types = participant_topic_types
        self._current_speaker_index = 0
        self._chat_history: List[GroupChatMessage] = []
        self._conversation_complete = False
        self._session_id = None

    @message_handler
    async def handle_travel_request(
        self, message: UserMessage, ctx: MessageContext
    ) -> None:
        logger.info(f"GroupChatManager received travel request: {message.content}")
        self._session_id = ctx.topic_id.source
        # Start the group chat
        await self.next_speaker()

    @message_handler
    async def handle_message(
        self, message: GroupChatMessage, ctx: MessageContext
    ) -> None:
        logger.info(
            f"GroupChatManager received message from {message.source}: {message.content}"
        )
        self._chat_history.append(message)
        if self._current_speaker_index >= len(self._participant_topic_types):
            self._conversation_complete = True
            await self.compile_final_plan()
            return
        await self.next_speaker()

    async def next_speaker(self) -> None:
        if self._conversation_complete:
            return
        if self._current_speaker_index >= len(self._participant_topic_types):
            # Conversation complete
            self._conversation_complete = True
            await self.compile_final_plan()
            return

        next_agent_type = self._participant_topic_types[self._current_speaker_index]
        self._current_speaker_index += 1
        logger.info(f"GroupChatManager requesting {next_agent_type} to speak")
        await self.publish_message(
            TravelRequest(
                source="GroupChatManager",
                content="Start group chat",
                requirements={"destination_city": "Paris"},
            ),
            DefaultTopicId(type=next_agent_type, source=self._session_id),
        )

    async def compile_final_plan(self) -> None:
        # Combine all messages to create a comprehensive plan
        plan = "\n".join([msg.content for msg in self._chat_history])
        logger.info(f"Final travel plan:\n{plan}")
        # Send the final plan to the user
        await self.publish_message(
            AgentResponse(
                source="GroupChatManager",
                content=f"Here is your comprehensive travel plan:\n{plan}",
            ),
            DefaultTopicId(type="user_proxy", source=self._session_id),
        )


# User Proxy Agent
@default_subscription
class UserProxyAgent(RoutedAgent):
    def __init__(self, websocket: WebSocket) -> None:
        super().__init__("UserProxyAgent")
        self.websocket = websocket

    @message_handler
    async def handle_agent_response(
        self, message: AgentResponse, ctx: MessageContext
    ) -> None:
        logger.info(f"UserProxyAgent received agent response: {message.content}")
        await self.websocket.send_text(f"{message.content}")

    @message_handler
    async def handle_user_message(
        self, message: UserMessage, ctx: MessageContext
    ) -> None:
        logger.info(f"UserProxyAgent received user message: {message.content}")
        # Forward the message to the router
        await self.publish_message(
            UserMessage(content=message.content, source=message.source),
            DefaultTopicId(type="router", source=ctx.topic_id.source),
        )


# Initialize the agent runtime
async def initialize_agent_runtime() -> SingleThreadedAgentRuntime:
    agent_runtime = SingleThreadedAgentRuntime()

    # Initialize IntentClassifier and AgentRegistry
    intent_classifier = IntentClassifier()
    agent_registry = AgentRegistry()

    await agent_runtime.add_subscription(
        DefaultSubscription(topic_type="user_proxy", agent_type="user_proxy")
    )

    # Register SemanticRouterAgent
    await SemanticRouterAgent.register(
        agent_runtime,
        "router",
        lambda: SemanticRouterAgent(
            name="SemanticRouterAgent",
            agent_registry=agent_registry,
            intent_classifier=intent_classifier,
        ),
    )
    await agent_runtime.add_subscription(
        DefaultSubscription(topic_type="router", agent_type="router")
    )

    # Register DefaultAgent
    await DefaultAgent.register(agent_runtime, "default_agent", lambda: DefaultAgent())
    await agent_runtime.add_subscription(
        DefaultSubscription(topic_type="default_agent", agent_type="default_agent")
    )

    # Register FlightAgent
    await FlightAgent.register(agent_runtime, "flight", lambda: FlightAgent())

    # Register HotelAgent
    await HotelAgent.register(agent_runtime, "hotel", lambda: HotelAgent())

    # Register CarRentalAgent
    await CarRentalAgent.register(agent_runtime, "car_rental", lambda: CarRentalAgent())

    # Register ActivitiesAgent
    await ActivitiesAgent.register(
        agent_runtime, "activities", lambda: ActivitiesAgent()
    )

    # Register DestinationAgent
    await DestinationAgent.register(
        agent_runtime, "destination", lambda: DestinationAgent()
    )

    # Register GroupChatManager
    await GroupChatManager.register(
        agent_runtime,
        "group_chat_manager",
        lambda: GroupChatManager(
            participant_topic_types=[
                "flight",
                "hotel",
                "car_rental",
                "activities",
                "destination",
            ]
        ),
    )
    await agent_runtime.add_subscription(
        DefaultSubscription(
            topic_type="group_chat_manager", agent_type="group_chat_manager"
        )
    )

    # Start the runtime
    agent_runtime.start()

    return agent_runtime


# Initialize the agent runtime at startup
agent_runtime = None


@app.on_event("startup")
async def startup_event():
    global agent_runtime
    agent_runtime = await initialize_agent_runtime()


# WebSocket endpoint to handle user messages
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # await initialize_agent_runtime()
        # Generate a unique session ID for this connection
        session_id = str(uuid.uuid4())

        logger.info(f"New connection: {session_id}")

        # Register UserProxyAgent with the current websocket
        await UserProxyAgent.register(
            agent_runtime, "user_proxy", lambda: UserProxyAgent(websocket)
        )

        while True:
            user_message = await websocket.receive_text()
            # Publish the user's message to the UserProxyAgent
            await agent_runtime.publish_message(
                UserMessage(content=user_message, source="User"),
                DefaultTopicId(type="user_proxy", source=session_id),
            )
            # Wait a short time to allow agents to process the message
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except WebSocketException as e:
        logger.error(f"WebSocket error: {str(e)}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")
    finally:
        logger.info(f"Closing connection: {session_id}")


# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("travel_chatbot:app", host="127.0.0.1", port=8001, reload=True)
