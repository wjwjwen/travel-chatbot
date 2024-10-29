from typing import List

from autogen_core.base import MessageContext
from autogen_core.components import (DefaultTopicId, RoutedAgent,
                                     default_subscription, message_handler)

from data_types import (AgentResponse, GroupChatMessage, TravelRequest,
                        UserMessage)
from otlp_tracing import logger


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
