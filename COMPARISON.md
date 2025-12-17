# Sync vs Async Coordination Agent - Comparison

This document compares the two implementations of the coordination agent.

## Branches

- **Synchronous**: `claude/coordination-agent-flow-eOzGW`
- **Asynchronous**: `claude/coordination-agent-async-flow-eOzGW`

## Key Differences

### 1. Client Configuration

**Synchronous:**
```python
config = ClientConfig(
    httpx_client=httpx_client,
    streaming=False,  # Non-streaming mode
)
```

**Asynchronous:**
```python
config = ClientConfig(
    httpx_client=httpx_client,
    streaming=True,   # Streaming mode enabled
)
```

### 2. Communication Functions

**Synchronous:**
```python
async def send_to_action_agent(message: str, base_url: str) -> str:
    # Returns single complete response
    async for event in client.send_message(msg):
        if isinstance(event, Message):
            return extracted_text
    return "No response from action agent"
```

**Asynchronous:**
```python
async def send_to_action_agent_async(message: str, base_url: str) -> AsyncIterator[str]:
    # Yields chunks as they arrive
    async for event in client.send_message(msg):
        if isinstance(event, Message):
            text = extract_text(event)
            if text:
                yield text  # Stream chunks
```

### 3. Response Handling

**Synchronous:**
- Waits for complete response
- Single return statement
- No intermediate updates

**Asynchronous:**
- Streams chunks in real-time
- Uses `yield` to emit chunks
- Provides progress feedback
- Includes collector function to aggregate chunks when needed

### 4. Tools Available

**Synchronous:**
```python
coordination_agent = Agent(
    name="CoordinationAgent",
    system_prompt=coordinator_system_prompt,
    tools=[delegate_to_action_agent]  # Single tool
)
```

**Asynchronous:**
```python
coordination_agent = Agent(
    name="CoordinationAgent",
    system_prompt=coordinator_system_prompt,
    tools=[
        delegate_to_action_agent,           # Collects full response
        delegate_to_action_agent_streaming  # Real-time streaming
    ]
)
```

## Feature Comparison Table

| Feature | Synchronous | Asynchronous |
|---------|------------|--------------|
| **Streaming** | No (`streaming=False`) | Yes (`streaming=True`) |
| **Response Pattern** | Request → Wait → Complete Response | Request → Stream Chunks → Complete |
| **Real-Time Updates** | ❌ | ✅ |
| **Progress Feedback** | ❌ | ✅ |
| **AsyncIterator** | ❌ | ✅ |
| **Number of Tools** | 1 | 2 |
| **Event Handling** | Basic | Advanced (Message + UpdateEvent) |
| **Resource Usage** | Blocking until complete | Non-blocking |
| **Best For** | Quick tasks (< 5s) | Long tasks (> 5s) |
| **Complexity** | Lower | Higher |
| **Latency Perception** | Higher (wait for all) | Lower (see chunks immediately) |

## Code Size Comparison

| Metric | Synchronous | Asynchronous |
|--------|-------------|--------------|
| **Lines of Code** | ~150 | ~217 |
| **Functions** | 5 | 7 |
| **Tools** | 1 | 2 |
| **Complexity** | Simple | Moderate |

## Use Case Recommendations

### Use Synchronous When:
- ✅ Task completes quickly (< 2-5 seconds)
- ✅ Simple request/response pattern is sufficient
- ✅ No need for progress updates
- ✅ Working with simple calculations or lookups
- ✅ Simplicity is preferred over features
- ✅ Lower code complexity is important

### Use Asynchronous When:
- ✅ Tasks are long-running (> 5 seconds)
- ✅ Users benefit from seeing progress
- ✅ Real-time feedback improves UX
- ✅ Processing large datasets or files
- ✅ High concurrency scenarios
- ✅ Tasks with unpredictable completion times
- ✅ Need to handle multiple concurrent agent calls
- ✅ Want to implement cancellation or retries

## Example Scenarios

### Scenario 1: Simple Calculation
**Task:** "What is 123 + 456?"

**Recommendation:** **Synchronous**
- Completes in < 1 second
- No benefit from streaming
- Simpler code is better

### Scenario 2: Large Dataset Analysis
**Task:** "Analyze this CSV with 1 million rows and provide insights"

**Recommendation:** **Asynchronous**
- Takes 30+ seconds
- User wants to see progress
- Can show: "Processing rows...", "Computing statistics...", etc.

### Scenario 3: Multiple API Calls
**Task:** "Fetch data from 10 different APIs and aggregate"

**Recommendation:** **Asynchronous**
- Long-running
- Can show completion of each API call
- Better resource utilization

### Scenario 4: Text Translation
**Task:** "Translate this sentence to French"

**Recommendation:** **Synchronous**
- Quick operation
- Complete response needed
- No intermediate value

## Performance Characteristics

### Synchronous
```
User Request → [Wait 10s] → Complete Response
Total Time: 10 seconds
User sees nothing until complete
```

### Asynchronous
```
User Request → [Stream starts immediately]
  → [1s] "Starting..."
  → [3s] "Processing..."
  → [7s] "Finalizing..."
  → [10s] Complete Response
Total Time: 10 seconds
User sees progress throughout
```

**Result:** Same total time, but async provides better UX with progress visibility.

## Migration Guide

### Converting Synchronous to Asynchronous

1. **Change streaming flag:**
   ```python
   # From:
   streaming=False
   # To:
   streaming=True
   ```

2. **Update function signature:**
   ```python
   # From:
   async def send_to_action_agent(...) -> str:
   # To:
   async def send_to_action_agent_async(...) -> AsyncIterator[str]:
   ```

3. **Change return to yield:**
   ```python
   # From:
   return extracted_text
   # To:
   yield extracted_text
   ```

4. **Add collector if needed:**
   ```python
   async def collect_streaming_response(message: str) -> str:
       response_parts = []
       async for chunk in send_to_action_agent_async(message):
           response_parts.append(chunk)
       return "".join(response_parts)
   ```

5. **Update tool to use collector:**
   ```python
   @tool
   async def delegate_to_action_agent(task: str) -> str:
       # From:
       response = await send_to_action_agent(task)
       # To:
       response = await collect_streaming_response(task)
       return response
   ```

### Converting Asynchronous to Synchronous

1. **Change streaming flag to False**
2. **Remove AsyncIterator return type**
3. **Change `yield` to `return`**
4. **Remove collector function**
5. **Simplify tool to directly call send function**

## Testing Differences

### Synchronous Testing
```python
async def test_sync_delegation():
    result = await send_to_action_agent("test task")
    assert result == "expected response"
```

### Asynchronous Testing
```python
async def test_async_delegation():
    chunks = []
    async for chunk in send_to_action_agent_async("test task"):
        chunks.append(chunk)
    full_response = "".join(chunks)
    assert full_response == "expected response"
```

## Logging Differences

### Synchronous
```
INFO: Received user message: Calculate sum
INFO: Delegating task to action agent: Calculate sum
INFO: Action agent response: The sum is 579
INFO: Final response: The sum is 579
```

### Asynchronous
```
INFO: Received user message: Process dataset
INFO: Delegating task to action agent (async): Process dataset
INFO: Received chunk: Processing started...
INFO: Received chunk: Analyzing data...
INFO: Received chunk: Computing statistics...
INFO: Received chunk: Results: ...
INFO: Action agent complete response: Processing started...Analyzing...
INFO: Final response: [Complete analysis]
```

## Summary

Both implementations accomplish the same goal but with different trade-offs:

- **Synchronous**: Simpler, better for quick tasks
- **Asynchronous**: More complex, better for long tasks with streaming benefits

Choose based on your specific use case, user experience requirements, and task characteristics.
