# Coordination Agent - Agent-to-Agent Flow (Async Version)

This project implements a coordination agent using Python and the Strands SDK that orchestrates **asynchronous streaming communication** between a user and an action agent in an agent-to-agent (A2A) flow.

## Architecture

The system consists of two main components:

1. **Coordination Agent**: Receives user input, analyzes requests, and delegates tasks to the action agent when needed
2. **Action Agent**: Executes tasks delegated by the coordination agent (runs separately at http://127.0.0.1:9000)

## How It Works (Async/Streaming)

### Flow Diagram

```
User Input → Coordination Agent → (decides) → delegate_to_action_agent tool →
  → Async Stream → Action Agent → Stream Response → Coordination Agent → User
```

### Key Differences: Sync vs Async

| Feature | Synchronous (Previous) | Asynchronous (This Version) |
|---------|----------------------|----------------------------|
| **Streaming** | `streaming=False` | `streaming=True` |
| **Response Model** | Single response after completion | Incremental streaming responses |
| **Latency** | Wait for full response | Real-time feedback as chunks arrive |
| **Tool Pattern** | Returns complete string | Async generator yields chunks |
| **Use Case** | Simple request/response | Long-running tasks, real-time updates |

### Key Components

#### 1. Coordination Agent
- **Purpose**: Acts as an intelligent router and coordinator for async operations
- **Responsibilities**:
  - Understands user requests
  - Decides whether to handle requests directly or delegate
  - Uses async tools to communicate with the action agent
  - Streams and collects responses in real-time
  - Formats and returns final responses to the user

#### 2. Async Delegation Tools

**delegate_to_action_agent** (Async with collection):
- **Type**: Async tool with `@tool` decorator from Strands SDK
- **Function**: Sends task to action agent and collects streaming responses
- **Returns**: Complete response after collecting all chunks
- **Best for**: Tasks where you need the full response before proceeding

**delegate_to_action_agent_streaming** (Real-time streaming):
- **Type**: Async tool optimized for streaming
- **Function**: Streams responses as they arrive from action agent
- **Returns**: Collects and returns full response with real-time logging
- **Best for**: Long-running tasks where users benefit from incremental feedback

#### 3. Async Communication Layer

**send_to_action_agent_async()**: AsyncIterator function
- Yields response chunks as they arrive
- Handles streaming events from A2A protocol
- Processes `Message` events and `UpdateEvent` tuples
- Provides real-time logging for monitoring

**collect_streaming_response()**: Collector function
- Aggregates streaming chunks into complete response
- Useful when tools need full response before returning

## Usage

### Prerequisites

Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Async Coordination Agent

```bash
python main.py
```

The coordination agent will start and listen for requests through the BedrockAgentCore framework.

### Example Interaction (Async Mode)

**User Input:**
```json
{
  "prompt": "Process a large dataset and provide analysis"
}
```

**Agent Flow (Async):**
1. Coordination agent receives the request
2. Determines this requires processing (action agent task)
3. Calls `delegate_to_action_agent("Process a large dataset and provide analysis")`
4. **Async streaming begins:**
   - Chunk 1: "Processing started..."
   - Chunk 2: "Analyzing first 1000 rows..."
   - Chunk 3: "Computing statistics..."
   - Chunk 4: "Analysis complete. Results: ..."
5. Tool collects all chunks into final response
6. Coordination agent formats and returns: `{"response": "[Complete analysis]"}`

### Example with Real-Time Updates

```python
# The async iterator allows processing chunks as they arrive
async for chunk in send_to_action_agent_async("Long running task"):
    print(f"Received: {chunk}")  # Real-time output
    # Could update UI, send notifications, etc.
```

## Configuration

- **Action Agent URL**: Default is `http://127.0.0.1:9000`
  - Modify in `send_to_action_agent_async` function's `base_url` parameter
- **Timeout**: Set to 300 seconds (5 minutes) in `DEFAULT_TIMEOUT`
- **Streaming**: Enabled via `streaming=True` in `ClientConfig`

## Key Features

- **Asynchronous Streaming**: Real-time response chunks from action agent
- **Dual Tool Pattern**: Choose between collected or streaming delegation
- **Intelligent Delegation**: LLM-powered decision making for when to delegate
- **AsyncIterator Support**: Proper async/await patterns throughout
- **Comprehensive Logging**: Track streaming chunks and events
- **A2A Protocol**: Standard agent-to-agent communication with streaming support
- **Event Handling**: Processes Message events and UpdateEvent tuples

## Code Structure

```
main.py
├── create_message()                        # Creates A2A message objects
├── send_to_action_agent_async()            # AsyncIterator: yields streaming chunks
├── collect_streaming_response()            # Collects stream into complete response
├── delegate_to_action_agent()              # Tool: async with collection
├── delegate_to_action_agent_streaming()    # Tool: async with real-time feedback
├── coordination_agent                      # Strands Agent instance with async tools
├── run_coordination_agent()                # Async runner for the agent
├── run_with_streaming_feedback()           # Alternative streaming implementation
└── invoke()                                # BedrockAgentCore entrypoint
```

## Benefits of Async Implementation

### 1. **Real-Time Feedback**
```python
# Users see progress as it happens:
"Processing started..."
"50% complete..."
"Finalizing results..."
"Complete!"
```

### 2. **Better Resource Utilization**
- Non-blocking I/O operations
- Handle multiple concurrent requests efficiently
- Improved throughput for long-running tasks

### 3. **Scalability**
- Async/await patterns scale better than synchronous blocking
- Can handle more concurrent agent-to-agent communications

### 4. **User Experience**
- Incremental updates prevent timeout perception
- Progress visibility for long operations
- Can implement cancellation and retries more easily

## Async Patterns Used

### AsyncIterator Pattern
```python
async def send_to_action_agent_async(message: str) -> AsyncIterator[str]:
    async for event in client.send_message(msg):
        if isinstance(event, Message):
            yield extracted_text
```

### Collector Pattern
```python
async def collect_streaming_response(message: str) -> str:
    response_parts = []
    async for chunk in send_to_action_agent_async(message):
        response_parts.append(chunk)
    return "".join(response_parts)
```

### Tool Integration Pattern
```python
@tool
async def delegate_to_action_agent(task_description: str) -> str:
    response = await collect_streaming_response(task_description)
    return response
```

## Dependencies

- `strands-agents`: Core agent framework with async support
- `strands-agents-tools`: Tool decorators with async compatibility
- `bedrock-agentcore`: AWS Bedrock agent runtime
- `httpx`: Async HTTP client for streaming
- `a2a`: Agent-to-agent communication protocol with streaming

## Customization

### Modify Streaming Behavior

Control how chunks are processed:

```python
async def send_to_action_agent_async(message: str) -> AsyncIterator[str]:
    async for event in client.send_message(msg):
        if isinstance(event, Message):
            text = extract_text(event)
            # Add custom processing here
            yield process_chunk(text)
```

### Add Custom Event Handlers

```python
async for event in client.send_message(msg):
    if isinstance(event, Message):
        yield extract_text(event)
    elif isinstance(event, tuple):
        task, update = event
        if update.kind == "progress":
            yield f"Progress: {update.data}"
```

### Create Streaming Response Tools

```python
@tool
async def stream_to_user(task: str) -> str:
    results = []
    async for chunk in send_to_action_agent_async(task):
        # Process chunk immediately
        notify_user(chunk)
        results.append(chunk)
    return "".join(results)
```

## Comparison with Synchronous Version

### When to Use Async (This Version)
- Long-running tasks (> 5 seconds)
- Tasks where users benefit from progress updates
- High-concurrency scenarios
- Real-time data processing
- Tasks with unpredictable completion times

### When to Use Sync (Previous Version)
- Quick request/response (< 2 seconds)
- Simple calculations or lookups
- When final result is needed before proceeding
- Simpler code when streaming isn't beneficial

## Advanced: Full Streaming to End User

For truly streaming responses to the end user, you could extend the entrypoint:

```python
@app.entrypoint_streaming  # Hypothetical streaming entrypoint
async def invoke_streaming(payload):
    user_message = payload.get("prompt")

    async for chunk in run_coordination_agent_streaming(user_message):
        yield {"chunk": chunk}  # Stream to user in real-time

    yield {"complete": True}
```

## Notes

- The action agent must be running and accessible at the configured URL
- Streaming mode (`streaming=True`) enables real-time chunk processing
- All communication is logged for debugging and monitoring
- Async tools work seamlessly with Strands SDK's Agent.run()
- The coordination agent's `run()` method is sync, but calls async tools internally
