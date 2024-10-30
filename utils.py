import asyncio
import json
from typing import List

import aiohttp
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId
from autogen_core.components import DefaultSubscription
from autogen_core.components.tool_agent import ToolAgent
from autogen_core.components.tools import FunctionTool, Tool
from bs4 import BeautifulSoup
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatSummaryMemoryBuffer
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.tools.wikipedia import WikipediaToolSpec
from tenacity import stop_after_attempt  # for exponential backoff
from tenacity import retry, wait_random_exponential
from typing_extensions import Annotated

from agents.ext_agents import LlamaIndexAgent
from agents.travel_activities import ActivitiesAgent
from agents.travel_car import CarRentalAgent
from agents.travel_destination import DestinationAgent
from agents.travel_flight import FlightAgent
from agents.travel_group_chat import GroupChatManager
from agents.travel_hotel import HotelAgent
from agents.travel_router import SemanticRouterAgent
from config import Config
from intent import IntentClassifier
from otlp_tracing import configure_oltp_tracing, logger
from registry import AgentRegistry

wiki_spec = WikipediaToolSpec()
wikipedia_tool = wiki_spec.to_tool_list()[1]

tracer = configure_oltp_tracing()

# Create LLM
llm = AzureOpenAI(
    deployment_name=Config.AZURE_OPENAI_DEPLOYMENT_NAME,
    temperature=0.0,
    max_tokens=1000,
    # azure_ad_token_provider=get_bearer_token_provider(DefaultAzureCredential()),
    api_key=Config.AZURE_OPENAI_API_KEY,
    azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
    api_version=Config.AZURE_OPENAI_API_VERSION,
)

model_capabilities = {
    "vision": False,
    "function_calling": True,
    "json_output": True,
}
aoai_model_client = Config.GetAzureOpenAIChatCompletionClient(model_capabilities)


# Retry logic for Bing search with exponential backoff
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
async def _search_custom_bing(session, query_params: dict) -> dict:
    custom_config_id = Config.BING_CUSTOM_CONFIG_ID
    headers = {"Ocp-Apim-Subscription-Key": Config.BING_CUSTOM_SEARCH_KEY}
    async with session.get(
        url="https://api.bing.microsoft.com/v7.0/custom/search",
        params={
            "q": query_params["q"],
            "customConfig": custom_config_id,
            "count": query_params.get("count", 10),
            "freshness": query_params.get("freshness", "Month"),
        },
        headers=headers,
    ) as response:
        return await response.json()


# Fetch the content of a given URL and return the text
async def _fetch_content(session, url: str) -> str:
    async with session.get(url) as response:
        html_content = await response.text()
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator=" ", strip=True)


# Perform Bing search and extract content from the search results
async def get_info_from_bing_search(
    search_query: Annotated[str, "query to search on Bing for information"]
) -> str:
    """
    Perform a Bing search for the given query, extract URLs, snippets, and fetch content.

    This function performs a Bing search using the provided search query, extracts URLs and snippets
    from the search results, and fetches the content of each URL. The function returns a JSON string

    Args:
        search_query (str): The search query string to be used for the Bing search.

    Returns:
        list[dict]: A list of dictionaries, each containing the URL, snippet, and content of a search result.
                    Example:
                    [
                        {
                            "url": "https://example.com",
                            "snippet": "This is a snippet from the search result.",
                            "content": "This is the content fetched from the URL."
                        },
                        ...
                    ]
    """
    logger.info(f"Performing Bing search for: {search_query}")
    session = aiohttp.ClientSession()
    search_params = {"q": search_query, "count": 6}

    search_results = await _search_custom_bing(
        session=session, query_params=search_params
    )
    urls = [result["url"] for result in search_results["webPages"]["value"]]
    snippets = [result["snippet"] for result in search_results["webPages"]["value"]]

    # Limit the number of concurrent requests
    semaphore = asyncio.Semaphore(6)

    # Fetch content with semaphore to limit concurrency
    async def fetch_with_semaphore(url: str) -> str:
        async with semaphore:
            return await _fetch_content(session, url)

    tasks = [fetch_with_semaphore(url) for url in urls]
    contents = await asyncio.gather(*tasks)

    # Merge URLs, snippets, and contents into a single list of dictionaries
    merged_results = [
        {"url": url, "snippet": snippet, "content": content}
        for url, snippet, content in zip(urls, snippets, contents)
    ]
    logger.info(f"Search results: {merged_results}")
    # return AssistantMessage(content=json.dumps(merged_results))
    return json.dumps(merged_results)


def get_travel_tools() -> List[Tool]:
    # Create a function tool.
    return [
        FunctionTool(
            get_info_from_bing_search,
            description="This function performs a Bing search using the provided search query",
        )
    ]


# Initialize the agent runtime
async def initialize_agent_runtime() -> SingleThreadedAgentRuntime:
    agent_runtime = SingleThreadedAgentRuntime(tracer_provider=tracer)
    # agent_runtime = SingleThreadedAgentRuntime()

    # Initialize IntentClassifier and AgentRegistry
    intent_classifier = IntentClassifier()
    agent_registry = AgentRegistry()
    travel_tools = get_travel_tools()
    travel_tool_agent_id = AgentId("tool_executor_agent", "default")
    await ToolAgent.register(
        agent_runtime,
        "tool_executor_agent",
        lambda: ToolAgent("Travel tool executor agent", travel_tools),
    )

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

    # Register FlightAgent
    await FlightAgent.register(agent_runtime, "flight", lambda: FlightAgent())

    # Register HotelAgent
    await HotelAgent.register(agent_runtime, "hotel", lambda: HotelAgent())

    # Register CarRentalAgent
    await CarRentalAgent.register(agent_runtime, "car_rental", lambda: CarRentalAgent())

    # Register ActivitiesAgent
    await ActivitiesAgent.register(
        agent_runtime,
        "activities",
        lambda: ActivitiesAgent(
            aoai_model_client,
            travel_tools,
            travel_tool_agent_id,
        ),
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
