import asyncio
import uuid
from typing import Optional, Dict

from autogen_core.base import MessageContext
from autogen_core.components import (
    DefaultTopicId,
    RoutedAgent,
    default_subscription,
    message_handler,
)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, WebSocketException
from starlette.websockets import WebSocketState  # Import WebSocketState

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from data_types import AgentResponse, UserMessage
from otlp_tracing import logger
from utils import initialize_agent_runtime

# Define FastAPI app
app = FastAPI()

# Instrument FastAPI app for tracing
FastAPIInstrumentor.instrument_app(app)

# Initialize the agent runtime at startup
agent_runtime = None
user_proxy_agent_instance = None  # Global variable to store the UserProxyAgent instance


class WebSocketConnectionManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}

    def add_connection(self, session_id: str, websocket: WebSocket) -> None:
        self.connections[session_id] = websocket

    def remove_connection(self, session_id: str) -> None:
        if session_id in self.connections:
            del self.connections[session_id]

    async def handle_websocket(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.add_connection(session_id, websocket)
        try:
            while True:
                user_message_text = await websocket.receive_text()
                chat_id = str(uuid.uuid4())
                user_message = UserMessage(content=user_message_text, source="User")

                logger.info(f"Received message with chat_id: {chat_id}")

                # Publish the user's message to the agent
                await agent_runtime.publish_message(
                    user_message,
                    DefaultTopicId(type="user_proxy", source=session_id),
                )
                await asyncio.sleep(0.1)
        except WebSocketDisconnect:
            logger.info(f"WebSocket connection closed: {session_id}")
        except Exception as e:
            logger.error(f"Exception in WebSocket connection {session_id}: {str(e)}")
        finally:
            self.remove_connection(session_id)
            try:
                if websocket.client_state != WebSocketState.DISCONNECTED:
                    await websocket.close()
            except WebSocketDisconnect:
                logger.info(f"WebSocket already closed: {session_id}")


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


# User Proxy Agent
@default_subscription
class UserProxyAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("UserProxyAgent")

    @message_handler
    async def handle_agent_response(
        self, message: AgentResponse, ctx: MessageContext
    ) -> None:
        logger.info(f"UserProxyAgent received agent response: {message.content}")
        session_id = ctx.topic_id.source
        try:
            websocket = connection_manager.connections.get(session_id)
            if websocket:
                await websocket.send_text(f"{message.content}")
        except Exception as e:
            logger.error(f"Failed to send message to session {session_id}: {str(e)}")

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


# Initialize the WebSocket connection manager
connection_manager = WebSocketConnectionManager()


@app.on_event("startup")
async def startup_event():
    global agent_runtime
    global user_proxy_agent_instance
    agent_runtime = await initialize_agent_runtime()

    # Register the UserProxyAgent instance with the AgentRuntime
    await UserProxyAgent.register(agent_runtime, "user_proxy", lambda: UserProxyAgent())


# WebSocket endpoint to handle user messages
@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    session_id = str(uuid.uuid4())
    await connection_manager.handle_websocket(websocket, session_id)


# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
