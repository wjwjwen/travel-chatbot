import asyncio
from collections import defaultdict
from typing import List

from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     message_handler, type_subscription)

from ..data_types import (AgentResponse, EndUserMessage, GroupChatMessage,
                          TravelPlan, TravelRequest)
from ..otlp_tracing import logger


# Group Chat Manager
@type_subscription("group_chat_manager")
class GroupChatManager(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("GroupChatManager")
        self._chat_history: List[GroupChatMessage] = []
        self._conversation_complete = False
        self._session_id = None
        self._responses = defaultdict(list)

    @message_handler
    async def handle_travel_request(
        self, message: EndUserMessage, ctx: MessageContext
    ) -> None:
        logger.info(f"GroupChatManager received travel request: {message.content}")
        self._session_id = ctx.topic_id.source
        # Start the group chat by requesting only relevant agents to respond concurrently
        await self.request_relevant_agents(ctx.topic_id.type)

    @message_handler
    async def handle_complex_travel_request(
        self, message: TravelPlan, ctx: MessageContext
    ) -> None:
        logger.info(f"GroupChatManager received complex travel request: {message}")
        self._session_id = ctx.topic_id.source
        # Create a list of tasks to be run concurrently
        tasks = [
            self.publish_message(
                TravelRequest(
                    source="GroupChatManager",
                    content=task.task_details,
                    original_task=message.main_task,
                ),
                DefaultTopicId(type=task.assigned_agent, source=self._session_id),
            )
            for task in message.subtasks
        ]

        # Run all tasks concurrently
        await asyncio.gather(*tasks)

        # Compile and send the final response to the user
        await self.publish_message(
            AgentResponse(
                source=self.id.type,
                content="Finished processing the travel plan",
            ),
            DefaultTopicId(type="user_proxy", source=ctx.topic_id.source),
        )

    async def request_relevant_agents(self, relevant_agents: List[str]) -> None:
        logger.info(
            "GroupChatManager requesting relevant agents to provide details for the travel plan"
        )
        for agent_type in relevant_agents:
            await self.publish_message(
                TravelRequest(
                    source="GroupChatManager",
                    content="Provide details for the travel plan",
                    requirements={"destination_city": "Paris"},
                ),
                DefaultTopicId(type=agent_type, source=self._session_id),
            )

    async def compile_final_plan(self) -> None:
        # Combine all messages to create a comprehensive plan
        plan = "\n".join(
            [
                f"{agent}: {', '.join(responses)}"
                for agent, responses in self._responses.items()
            ]
        )
        logger.info(f"Final travel plan:\n{plan}")
        # Send the final plan to the user
        await self.publish_message(
            AgentResponse(
                source="GroupChatManager",
                content=f"Here is your comprehensive travel plan:\n{plan}",
            ),
            DefaultTopicId(type="user_proxy", source=self._session_id),
        )
