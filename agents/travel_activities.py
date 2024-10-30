import json
from typing import List
from autogen_ext.models import AzureOpenAIChatCompletionClient
from autogen_core.base import AgentId

from autogen_core.base import MessageContext
from autogen_core.components import (
    DefaultTopicId,
    RoutedAgent,
    default_subscription,
    message_handler,
    type_subscription,
)
from autogen_core.components.models import LLMMessage, SystemMessage, UserMessage
from autogen_core.components.tool_agent import tool_agent_caller_loop

from config import Config
from data_types import Activities, AgentResponse, EndUserMessage, HandoffMessage
from otlp_tracing import logger
from autogen_core.components.tools import Tool


# Activities Agent
@default_subscription
@type_subscription("activities")
class ActivitiesAgent(RoutedAgent):
    def __init__(
        self,
        model_client: AzureOpenAIChatCompletionClient,
        tools: List[Tool],
        tool_agent_id: AgentId,
    ) -> None:
        super().__init__("ActivitiesAgent")
        self._system_messages: List[LLMMessage] = [
            SystemMessage(
                "You are a helpful AI assistant that can advise on activities."
            )
        ]
        self._model_client = model_client
        self._tools = tools
        self._tool_agent_id = tool_agent_id

    @message_handler
    async def handle_message(
        self, message: EndUserMessage, ctx: MessageContext
    ) -> None:
        if "travel plan" in message.content.lower():
            # Cannot handle complex travel plans, hand off back to router
            await self.publish_message(
                HandoffMessage(content=message.content, source=self.id.type),
                DefaultTopicId(type="router", source=ctx.topic_id.source),
            )
            return

        # Create a session for the activities agent
        session: List[LLMMessage] = [
            UserMessage(content=message.content, source="user")
        ]

        # Run the caller loop
        try:
            messages = await tool_agent_caller_loop(
                caller=self,
                tool_agent_id=self._tool_agent_id,
                model_client=self._model_client,
                input_messages=session,
                tool_schema=self._tools,
                cancellation_token=ctx.cancellation_token,
            )
            # logger.info(f"Tool agent caller loop completed: {messages}")
        except Exception as e:
            logger.error(f"Tool agent caller loop failed: {str(e)}")
            pass

        # Ensure the final message content is a string
        assert isinstance(messages[-1].content, str)

        # Get structured data from the final message content
        try:
            response_content = await self._model_client.create(
                [UserMessage(content=messages[-1].content, source="ActivitiesAgent")],
                extra_create_args={"response_format": Activities},
            )
            activities_structured = Activities.model_validate(
                json.loads(response_content.content)
            )
        except Exception as e:
            logger.error(f"Failed to parse activities response: {str(e)}")
            activities_structured = Activities(destination_city="", activities=[])
            pass

        # Publish the response to the group chat manager
        await self.publish_message(
            AgentResponse(
                source=self.id.type,
                content=activities_structured.model_dump_json(),
            ),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
        )
