import json
from collections import deque
import asyncio

from autogen_core import MessageContext
from autogen_core import (
    DefaultTopicId,
    RoutedAgent,
    message_handler,
    type_subscription,
)
from autogen_core.models import SystemMessage
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

from ..data_types import (
    EndUserMessage,
    HandoffMessage,
    TravelPlan,
    AgentStructuredResponse,
    Greeter,
)
from ..otlp_tracing import logger
from ..registry import AgentRegistry
from ..session_state import SessionStateManager

agent_registry = AgentRegistry()


@type_subscription(topic_type="router")
class SemanticRouterAgent(RoutedAgent):
    """
    The SemanticRouterAgent routes incoming messages to appropriate agents based on the intent.

    Attributes:
        name (str): Name of the agent.
        model_client (AzureOpenAIChatCompletionClient): The model client for agent routing.
        agent_registry (AgentRegistry): The registry containing agent information.
        intent_classifier (IntentClassifier): Classifier to determine intent from user messages.
        session_manager (SessionStateManager): Manages the session state for each user.
    """

    def __init__(
        self,
        name: str,
        model_client: AzureOpenAIChatCompletionClient,
        agent_registry: AgentRegistry,
        session_manager: SessionStateManager,
    ) -> None:
        super().__init__("SemanticRouterAgent")
        self._name = name
        self._model_client = model_client
        self._registry = agent_registry
        self._session_manager = session_manager

    @message_handler
    async def route_message(self, message: EndUserMessage, ctx: MessageContext) -> None:
        """
        Routes user messages to appropriate agents based on conversation context.

        Args:
            message (EndUserMessage): The incoming user message.
            ctx (MessageContext): Context information for the message.
        """
        session_id = ctx.topic_id.source

        # Add the current message to session history
        self._session_manager.add_to_history(session_id, message)

        # Analyze conversation history for better context
        history = self._session_manager.get_history(session_id)
        logger.info("Analyzing conversation history for context")

        travel_plan: TravelPlan = await self._get_agents_to_route(message, history)
        logger.info(f"Routing message to agents: {travel_plan}")

        if travel_plan.is_greeting:
            logger.info("User greeting detected")
            await self.publish_message(
                AgentStructuredResponse(
                    agent_type="default_agent",
                    data=Greeter(
                        greeting=f"Greetings, Adventurer! 🌍 Ready to embark on your next journey? I'm here to turn your travel dreams into reality. Let's dive into the details and craft an unforgettable adventure together. From flights to sights, I've got you covered. Let's get started!"
                    ),
                    message=f"User greeting detected: {message.content}",
                ),
                DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
            )
            return

        if not travel_plan.subtasks:
            logger.info("No agents selected for routing")
            return

        # If only one agent is involved, send the message directly
        if len(travel_plan.subtasks) == 1:
            subtask = travel_plan.subtasks[0]
            assigned_agent = subtask["assigned_agent"]

            await self.publish_message(
                EndUserMessage(content=message.content, source=message.source),
                DefaultTopicId(type=assigned_agent, source=session_id),
            )
            
            logger.info(f"Message published successfully to {assigned_agent}")
            
        else:
            # If more than one agent is involved, send the message to GroupChatManager for coordination
            #logger.info(
            #    f"Routing message to GroupChatManager for coordination: {[subtask.assigned_agent for subtask in travel_plan.subtasks]}"
            #)
            logger.info(f"Routing message to GroupChatManager for coordination: {travel_plan}")
            await self.publish_message(
                travel_plan,
                DefaultTopicId(type="group_chat_manager", source=session_id),
            )

    @message_handler
    async def handle_handoff(
        self, message: HandoffMessage, ctx: MessageContext
    ) -> None:
        """
        Handles handoff messages from other agents.

        Args:
            message (HandoffMessage): The handoff message from another agent.
            ctx (MessageContext): Context information for the message.
        """
        session_id = ctx.topic_id.source
        logger.info(f"Received handoff message from {message.source}")

        # Clear session if conversation is complete, otherwise continue routing
        if message.original_task and "complete" in message.content.lower():
            self._session_manager.clear_session(session_id)
        else:
            await self.route_message(
                EndUserMessage(content=message.content, source=message.source), ctx
            )

    def _build_system_message(self, message: EndUserMessage, history: deque) -> str:
        """构建系统消息，包含期望的 JSON 结构说明"""
        base_prompt = """
        你是一个智能旅行助手。请根据用户的输入确定合适的处理方式并返回JSON格式响应。

        请严格按照以下JSON格式返回：
        {
            "main_task": "用户的主要任务描述",
            "subtasks": [
                {
                    "task_details": "具体任务描述",
                    "assigned_agent": "处理该任务的代理名称"
                }
            ],
            "is_greeting": true/false
        }

        规则：
        1. 对于问候语（如"你好"、"hello"等），设置 is_greeting 为 true，使用 default_agent
        2. 对于旅行相关问题，创建相应的任务并分配给适当的代理：
           - 目的地信息查询 → destination_info
           - 航班预订相关 → flight_booking
           - 酒店预订相关 → hotel_booking
           - 租车服务相关 → car_rental
           - 活动和景点相关 → activities_booking
        3. 其他一般性问题使用 default_agent 处理
        """

        if history:
            context = "\n当前对话历史：\n" + "\n".join([f"- {msg}" for msg in history])
            base_prompt += f"\n{context}"

        base_prompt += f"\n\n用户输入：{message.content}"
        
        logger.debug(f"Built system message: {base_prompt}")
        return base_prompt

    async def _get_agents_to_route(
        self, message: EndUserMessage, history: deque
    ) -> TravelPlan:
        try:
            system_message = self._build_system_message(message, history)
            logger.debug(f"System message: {system_message}")

            # 简化的响应格式设置
            response = await self._model_client.create(
                [SystemMessage(content=system_message)],
                extra_create_args={
                    "response_format": {"type": "json_object"}  # 只指定类型为 json_object
                },
            )
            
            logger.debug(f"Raw response content: {response.content}")
            
            try:
                if isinstance(response.content, str):
                    content_dict = json.loads(response.content)
                else:
                    content_dict = response.content
                    
                travel_plan = TravelPlan.model_validate(content_dict)
                logger.info(f"Successfully parsed travel plan: {travel_plan}")
                
            except Exception as parse_error:
                logger.error(f"Error parsing response: {parse_error}", exc_info=True)
                travel_plan = TravelPlan(
                    main_task=message.content,
                    subtasks=[],
                    is_greeting=False
                )

            if any(greeting in message.content.lower() for greeting in ["hello", "hi", "你好"]):
                logger.info("Greeting detected, updating travel plan")
                travel_plan = TravelPlan(
                    main_task="Greeting",
                    subtasks=[{
                        "task_details": f"Greeting - {message.content}",
                        "assigned_agent": "default_agent"
                    }],
                    is_greeting=True
                )

            return travel_plan

        except Exception as e:
            logger.error(f"Failed to route message: {str(e)}", exc_info=True)
            return TravelPlan(
                main_task="",
                subtasks=[],
                is_greeting=False
            )

    async def _debug_publish(self, message, topic_id):
        logger.info(f"Publishing message to {topic_id.type}")
        logger.info(f"Available subscriptions: {self._runtime.list_subscriptions()}")  # 需要确保有这个方法
        
        try:
            await self.publish_message(message, topic_id)
            logger.info("Message published successfully")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise
