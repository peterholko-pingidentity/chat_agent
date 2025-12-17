from strands import Agent
from strands.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp
import asyncio
import logging
from uuid import uuid4
from typing import AsyncIterator

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, TextPart

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300  # set request timeout to 5 minutes

app = BedrockAgentCoreApp()


def create_message(*, role: Role = Role.user, text: str) -> Message:
    """Create a message for A2A communication"""
    return Message(
        kind="message",
        role=role,
        parts=[Part(TextPart(kind="text", text=text))],
        message_id=uuid4().hex,
    )


async def send_to_action_agent_async(message: str, base_url: str = "http://127.0.0.1:9000") -> AsyncIterator[str]:
    """
    Send a message to the action agent via A2A protocol with streaming support.
    Yields responses as they arrive from the action agent.
    """
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as httpx_client:
        # Get agent card
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()

        # Create client using factory with streaming enabled
        config = ClientConfig(
            httpx_client=httpx_client,
            streaming=True,  # Enable streaming mode for async responses
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)

        # Create and send message
        msg = create_message(text=message)

        # With streaming=True, this will yield multiple events as they arrive
        async for event in client.send_message(msg):
            if isinstance(event, Message):
                logger.info(f"Received message chunk from action agent")
                # Extract text from the message
                text = next(
                    (p.content.text for p in event.parts if hasattr(p, "content") and hasattr(p.content, "text")),
                    ""
                )
                if text:
                    yield text
            elif isinstance(event, tuple) and len(event) == 2:
                # (Task, UpdateEvent) tuple
                task, update_event = event
                if update_event:
                    logger.info(f"Update event: {update_event.kind}")
                    yield f"[Update: {update_event.kind}]"
            else:
                # Handle other event types
                logger.info(f"Event type: {type(event)}")


async def collect_streaming_response(message: str, base_url: str = "http://127.0.0.1:9000") -> str:
    """
    Collect all streaming responses from the action agent into a single string.
    """
    response_parts = []
    async for chunk in send_to_action_agent_async(message, base_url):
        response_parts.append(chunk)
        logger.info(f"Received chunk: {chunk[:100]}...")  # Log first 100 chars

    full_response = "".join(response_parts)
    return full_response if full_response else "No response from action agent"


# Define the tool for the coordination agent to delegate to action agent
@tool
async def delegate_to_action_agent(task_description: str) -> str:
    """
    Delegate a task to the action agent for execution with async streaming.

    Args:
        task_description: A clear description of the task to be performed by the action agent

    Returns:
        The complete response from the action agent (collected from stream)
    """
    logger.info(f"Delegating task to action agent (async): {task_description}")
    response = await collect_streaming_response(task_description)
    logger.info(f"Action agent complete response: {response[:200]}...")  # Log first 200 chars
    return response


# Define a tool that streams responses back in real-time
@tool
async def delegate_to_action_agent_streaming(task_description: str) -> str:
    """
    Delegate a task to the action agent and stream responses as they arrive.
    This provides real-time feedback to the user.

    Args:
        task_description: A clear description of the task to be performed by the action agent

    Returns:
        Streaming responses from the action agent
    """
    logger.info(f"Delegating task to action agent (streaming): {task_description}")

    response_parts = []
    async for chunk in send_to_action_agent_async(task_description):
        response_parts.append(chunk)
        # In a real implementation, you could yield these chunks
        # to provide real-time feedback to the user
        logger.info(f"Streaming chunk: {chunk[:100]}")

    full_response = "".join(response_parts)
    return full_response if full_response else "No response from action agent"


# Coordination Agent system prompt
coordinator_system_prompt = """
You are the Coordination Agent in an asynchronous agent-to-agent flow.

Your responsibilities:
1. Receive and understand user requests
2. Analyze whether the request requires action from another agent
3. If action is needed, use the delegate_to_action_agent tool to send the task to the action agent
4. Handle streaming responses from the action agent in real-time
5. Relay the action agent's response back to the user in a clear and helpful manner

Important guidelines:
- For simple greetings or questions about yourself, respond directly
- For tasks that require execution, calculation, or external actions, delegate to the action agent
- Always provide context when delegating - be clear and specific about what needs to be done
- When you receive a response from the action agent, present it to the user in a clear format
- The action agent communicates asynchronously via streaming - responses may arrive incrementally

You are the coordinator - your job is to orchestrate the asynchronous workflow between the user and the action agent.
"""

# Create the coordination agent with the delegation tools
coordination_agent = Agent(
    name="CoordinationAgent",
    system_prompt=coordinator_system_prompt,
    tools=[delegate_to_action_agent, delegate_to_action_agent_streaming]
)


@app.entrypoint
def invoke(payload):
    """
    Main entry point for the coordination agent.
    Receives user input and coordinates asynchronously with the action agent.
    """
    user_message = payload.get("prompt", "Hello! How can I help you today?")

    logger.info(f"Received user message: {user_message}")

    # Run the coordination agent with the user message
    # The agent will decide whether to delegate to the action agent
    response = asyncio.run(run_coordination_agent(user_message))

    logger.info(f"Final response: {response[:200]}...")  # Log first 200 chars

    return {"response": response}


async def run_coordination_agent(user_message: str) -> str:
    """
    Run the coordination agent with the user's message asynchronously.
    The agent will use its tools to delegate to the action agent if needed.
    """
    # Send the message to the coordination agent
    # Note: Agent.run() is synchronous, but the tools it calls can be async
    result = coordination_agent.run(user_message)

    # Extract the text response
    if hasattr(result, 'text'):
        return result.text
    else:
        return str(result)


async def run_with_streaming_feedback(user_message: str):
    """
    Alternative runner that could provide streaming feedback to users.
    This is a demonstration of how you could implement real-time streaming.
    """
    logger.info(f"Starting async coordination for: {user_message}")

    # In a real streaming implementation, you would:
    # 1. Start the coordination agent
    # 2. Capture tool calls as they happen
    # 3. Stream responses back to the user in real-time
    # 4. Yield final result

    result = coordination_agent.run(user_message)

    if hasattr(result, 'text'):
        return result.text
    else:
        return str(result)


if __name__ == "__main__":
    app.run()
