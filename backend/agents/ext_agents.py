from typing import List, Optional

from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     default_subscription, message_handler,
                                     type_subscription)
from llama_index.core.agent.runner.base import AgentRunner
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.memory.types import BaseMemory
from pydantic import BaseModel

from ..data_types import AgentResponse, EndUserMessage
from ..otlp_tracing import logger


class Resource(BaseModel):
    content: str
    node_id: str
    score: Optional[float] = None


class Message(BaseModel):
    content: str
    sources: Optional[List[Resource]] = None


@default_subscription
@type_subscription("default_agent")
class LlamaIndexAgent(RoutedAgent):
    def __init__(
        self,
        llama_index_agent: AgentRunner,
        memory: BaseMemory | None = None,
    ) -> None:
        super().__init__("LlamaIndexAgent")
        self._llama_index_agent = llama_index_agent
        self._memory = memory

    @message_handler
    async def handle_user_message(
        self, message: EndUserMessage, ctx: MessageContext
    ) -> None:
        # retriever history messages from memory!
        logger.info("Handling user message in LlamaIndexAgent")
        history_messages: List[ChatMessage] = []
        self._session_id = ctx.topic_id.source

        response: AgentChatResponse  # pyright: ignore
        if self._memory is not None:
            history_messages = self._memory.get(input=message.content)

            response = await self._llama_index_agent.achat(
                message=message.content, history_messages=history_messages
            )  # pyright: ignore
        else:
            response = await self._llama_index_agent.achat(
                message=message.content
            )  # pyright: ignore

        if isinstance(response, AgentChatResponse):
            if self._memory is not None:
                self._memory.put(
                    ChatMessage(role=MessageRole.USER, content=message.content)
                )
                self._memory.put(
                    ChatMessage(role=MessageRole.ASSISTANT, content=response.response)
                )

            assert isinstance(response.response, str)

            resources: List[Resource] = [
                Resource(
                    content=source_node.get_text(),
                    score=source_node.score,
                    node_id=source_node.id_,
                )
                for source_node in response.source_nodes
            ]

            tools: List[Resource] = [
                Resource(content=source.content, node_id=source.tool_name)
                for source in response.sources
            ]

            resources.extend(tools)
            logger.info(response.response)
            await self.publish_message(
                AgentResponse(
                    source="LlamaIndexAgent",
                    content=f"\n{response.response}\n",
                ),
                DefaultTopicId(type="user_proxy", source=self._session_id),
            )
        else:
            await self.publish_message(
                AgentResponse(
                    source="LlamaIndexAgent",
                    content="I'm sorry, I don't have an answer for you.",
                ),
                DefaultTopicId(type="user_proxy", source=self._session_id),
            )
