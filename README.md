# Explanation of the Code

## Agents:

FlightAgent, HotelAgent, CarRentalAgent, ActivitiesAgent, and DestinationAgent handle their respective services.
Each agent can process simple tasks or hand off complex tasks back to the router.

## GroupChatManager:

Coordinates multiple agents to handle complex travel plans.
Manages a round-robin conversation among the agents.
Compiles the final comprehensive travel plan.

## SemanticRouterAgent:

Classifies user messages using the IntentClassifier.
Routes messages to the appropriate agent based on the intent.
Handles handoffs from agents.

## UserProxyAgent:

Acts as an interface between the user and the agents.
Sends agent responses back to the user via the WebSocket connection.

## WebSocket Endpoint:

Receives messages from the end user.
Publishes user messages to the UserProxyAgent for processing.
Manages the WebSocket connection lifecycle.

# How to run

## Run the Application:

```bash
uvicorn travel_chatbot:app --reload
```

## Connect via WebSocket:

Use a WebSocket client to connect to `ws://127.0.0.1:8001/ws`. I am using vscode extension

## Send a Simple Travel Request:

### Send a message like:

```yaml
I need to rent a car in Paris
```

#### Expected Output:

You should now receive below:

```yaml
Car rented in Paris from 2023-12-21 to 2023-12-26
```

## Send a Complex Travel Request:

### Send a message like:

```yaml
I want to plan a vacation to Paris
```

#### Expected Output:

You should now receive the comprehensive travel plan:

```yaml
Here is your comprehensive travel plan:
Flight booked: Flight from New York to Paris on 2023-12-20
Hotel booked: Hotel in Paris from 2023-12-20 to 2023-12-27
Car rented: Car rented in Paris from 2023-12-21 to 2023-12-26
Activities booked: Booked activities in Paris: Eiffel Tower tour, Seine River cruise
Destination info: Top attractions in Paris
```
