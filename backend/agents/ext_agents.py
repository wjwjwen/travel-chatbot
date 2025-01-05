from typing import List, Optional

from autogen_core import MessageContext
from autogen_core import (
    DefaultTopicId,
    RoutedAgent,
    default_subscription,
    message_handler,
    type_subscription,
)
from llama_index.core.agent.runner.base import AgentRunner
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.memory.types import BaseMemory

from ..data_types import (
    AgentStructuredResponse, 
    EndUserMessage, 
    Resource, 
    GroupChatMessage
)
from ..otlp_tracing import logger


@default_subscription
@type_subscription("default_agent")
class LlamaIndexAgent(RoutedAgent):
    """
    A routed agent that handles interactions using the LlamaIndex agent.

    Attributes:
        llama_index_agent (AgentRunner): The Llama Index agent runner.
        memory (Optional[BaseMemory]): Memory component to track historical messages.
    """

    def __init__(
        self,
        llama_index_agent: AgentRunner,
        memory: Optional[BaseMemory] = None,
    ) -> None:
        logger.info("=" * 50)
        logger.info("Initializing LlamaIndexAgent")
        try:
            super().__init__("LlamaIndexAgent")
            logger.info("Base RoutedAgent initialized")
            
            self._llama_index_agent = llama_index_agent
            logger.info(f"LlamaIndex agent runner set: {type(llama_index_agent)}")
            
            self._memory = memory
            logger.info(f"Memory initialized: {type(memory) if memory else 'No memory'}")
            
            self._session_id = None
            
            logger.info("LlamaIndexAgent initialization completed successfully")
            
        except Exception as e:
            logger.error("Error initializing LlamaIndexAgent")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error message: {str(e)}")
            logger.error("Error details:", exc_info=True)
            raise
        logger.info("=" * 50)

    @message_handler
    async def handle_user_message(
        self, message: EndUserMessage, ctx: MessageContext
    ) -> None:
        try:
            self._session_id = ctx.topic_id.source
            
            history_messages = []
            if self._memory is not None:
                history_messages = self._memory.get(input=message.content)

            try:
                if history_messages:
                    response = await self._llama_index_agent.achat(
                        message=message.content, history_messages=history_messages
                    )
                else:
                    response = await self._llama_index_agent.achat(message=message.content)
                    
            except ValueError as ve:
                if "Reached max iterations" in str(ve):
                    # 处理最大迭代错误
                    response_text = "I apologize, but I'm having trouble processing your request. Could you please rephrase it or break it down into smaller parts?"
                    structured_response = AgentStructuredResponse(
                        agent_type="default_agent",
                        data=GroupChatMessage(
                            source="default_agent",
                            content=response_text
                        ),
                        message=response_text,
                    )
                    await self.publish_message(
                        structured_response,
                        DefaultTopicId(type="user_proxy", source=self._session_id),
                    )
                    return
                else:
                    raise

            if isinstance(response, AgentChatResponse):
                try:
                    if self._memory is not None:
                        self._memory.put(
                            ChatMessage(role=MessageRole.USER, content=message.content)
                        )
                        self._memory.put(
                            ChatMessage(role=MessageRole.ASSISTANT, content=response.response)
                        )

                    structured_response = AgentStructuredResponse(
                        agent_type="default_agent",
                        data=GroupChatMessage(
                            source="default_agent",
                            content=response.response
                        ),
                        message=f"\n{response.response}\n",
                    )

                    target_topic = DefaultTopicId(type="user_proxy", source=self._session_id)
                    await self.publish_message(structured_response, target_topic)
                    
                except Exception as process_error:
                    logger.error("Error processing agent response")
                    logger.error(f"Error type: {type(process_error)}")
                    logger.error(f"Error message: {str(process_error)}")
                    logger.error("Processing error details:", exc_info=True)
                    raise

        except Exception as e:
            logger.error("Error in handle_user_message")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error message: {str(e)}")
            logger.error("Error details:", exc_info=True)
            
            # 发送友好的错误消息给用户
            await self.publish_message(
                AgentStructuredResponse(
                    agent_type="default_agent",
                    data=GroupChatMessage(
                        source="default_agent",
                        content="I apologize, but I encountered an error while processing your request."
                    ),
                    message="I apologize, but I encountered an error while processing your request.",
                ),
                DefaultTopicId(type="user_proxy", source=self._session_id),
            )
