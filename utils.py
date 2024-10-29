from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.components import DefaultSubscription
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatSummaryMemoryBuffer
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.tools.wikipedia import WikipediaToolSpec

from config import Config
from ext_agents import LlamaIndexAgent
from intent import IntentClassifier
from otlp_tracing import configure_oltp_tracing
from registry import AgentRegistry
from travel_activities import ActivitiesAgent
from travel_car import CarRentalAgent
from travel_destination import DestinationAgent
from travel_flight import FlightAgent
from travel_group_chat import GroupChatManager
from travel_hotel import HotelAgent
from travel_router import SemanticRouterAgent

wiki_spec = WikipediaToolSpec()
wikipedia_tool = wiki_spec.to_tool_list()[1]

tracer = configure_oltp_tracing()


# Create LLM
llm = AzureOpenAI(
    deployment_name=Config.AZURE_OPENAI_DEPLOYMENT_NAME,
    temperature=0.0,
    # azure_ad_token_provider=get_bearer_token_provider(DefaultAzureCredential()),
    api_key=Config.AZURE_OPENAI_API_KEY,
    azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
    api_version=Config.AZURE_OPENAI_API_VERSION,
)


# Initialize the agent runtime
async def initialize_agent_runtime() -> SingleThreadedAgentRuntime:
    agent_runtime = SingleThreadedAgentRuntime(tracer_provider=tracer)

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

    # # Register DefaultAgent
    # await DefaultAgent.register(agent_runtime, "default_agent", lambda: DefaultAgent())
    # await agent_runtime.add_subscription(
    #     DefaultSubscription(topic_type="default_agent", agent_type="default_agent")
    # )

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
    # Register WikipediaAgent
    await LlamaIndexAgent.register(
        agent_runtime,
        "default_agent",
        lambda: LlamaIndexAgent(
            description="LlamaIndexAgent",
            llama_index_agent=ReActAgent.from_tools(
                tools=[wikipedia_tool],
                llm=llm,
                max_iterations=5,
                memory=ChatSummaryMemoryBuffer(llm=llm, token_limit=1000),
            ),
        ),
    )
    # await agent_runtime.add_subscription(
    #     DefaultSubscription(topic_type="default_agent", agent_type="default_agent")
    # )

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
