# Coordination Agent - Agent-to-Agent Flow

This project implements a coordination agent using Python and the Strands SDK that orchestrates communication between a user and an action agent in an agent-to-agent (A2A) flow.

## Architecture

The system consists of two main components:

1. **Coordination Agent**: Receives user input, analyzes requests, and delegates tasks to the action agent when needed
2. **Action Agent**: Executes tasks delegated by the coordination agent (runs separately at http://127.0.0.1:9000)

## How It Works

### Flow Diagram

```
User Input → Coordination Agent → (decides) → delegate_to_action_agent tool → Action Agent → Response → User
```

### Key Components

#### 1. Coordination Agent
- **Purpose**: Acts as an intelligent router and coordinator
- **Responsibilities**:
  - Understands user requests
  - Decides whether to handle requests directly or delegate
  - Uses the `delegate_to_action_agent` tool to communicate with the action agent
  - Formats and returns responses to the user

#### 2. delegate_to_action_agent Tool
- **Type**: Async tool decorated with `@tool` from Strands SDK
- **Function**: Sends task descriptions to the action agent via A2A protocol
- **Returns**: Response from the action agent

#### 3. A2A Communication Layer
- Uses `httpx` client for async HTTP communication
- Implements A2A protocol using `a2a.client` library
- Communicates with action agent via HTTP messages

## Usage

### Prerequisites

Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Coordination Agent

```bash
python main.py
```

The coordination agent will start and listen for requests through the BedrockAgentCore framework.

### Example Interaction

**User Input:**
```json
{
  "prompt": "Calculate the sum of 123 and 456"
}
```

**Agent Flow:**
1. Coordination agent receives the request
2. Determines this requires calculation (action agent task)
3. Calls `delegate_to_action_agent("Calculate the sum of 123 and 456")`
4. Action agent performs the calculation
5. Coordination agent receives result and formats response
6. Returns to user: `{"response": "The sum is 579"}`

## Configuration

- **Action Agent URL**: Default is `http://127.0.0.1:9000`
  - Can be modified in the `send_to_action_agent` function's `base_url` parameter
- **Timeout**: Set to 300 seconds (5 minutes) in `DEFAULT_TIMEOUT`

## Key Features

- **Intelligent Delegation**: The coordination agent uses LLM reasoning to decide when to delegate
- **Tool-Based Communication**: Uses Strands SDK's `@tool` decorator for clean integration
- **Async/Await Support**: Fully asynchronous communication with the action agent
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **A2A Protocol**: Standard agent-to-agent communication protocol

## Code Structure

```
main.py
├── create_message()              # Creates A2A message objects
├── send_to_action_agent()        # Sends messages to action agent via A2A
├── delegate_to_action_agent()    # Tool for coordination agent
├── coordination_agent            # Strands Agent instance
├── run_coordination_agent()      # Async runner for the agent
└── invoke()                      # BedrockAgentCore entrypoint
```

## Dependencies

- `strands-agents`: Core agent framework
- `strands-agents-tools`: Tool decorators and utilities
- `bedrock-agentcore`: AWS Bedrock agent runtime
- `httpx`: Async HTTP client
- `a2a`: Agent-to-agent communication protocol

## Customization

### Modify Coordination Logic

Edit the `coordinator_system_prompt` to change how the agent decides to delegate:

```python
coordinator_system_prompt = """
Your custom instructions here...
"""
```

### Add More Tools

Add additional tools for the coordination agent:

```python
@tool
async def your_custom_tool(param: str) -> str:
    # Your implementation
    return result

coordination_agent = Agent(
    name="CoordinationAgent",
    system_prompt=coordinator_system_prompt,
    tools=[delegate_to_action_agent, your_custom_tool]
)
```

## Notes

- The action agent must be running and accessible at the configured URL
- The coordination agent uses non-streaming mode for synchronous responses
- All communication is logged for debugging purposes
