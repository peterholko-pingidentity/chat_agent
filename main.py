from strands import Agent
from strands.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp
import asyncio
import logging
from uuid import uuid4

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


async def send_to_action_agent(message: str, base_url: str = "http://127.0.0.1:9000") -> str:
    """Send a message to the action agent via A2A protocol"""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as httpx_client:
        # Get agent card
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()

        # Create client using factory
        config = ClientConfig(
            httpx_client=httpx_client,
            streaming=False,  # Use non-streaming mode for sync response
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)

        # Create and send message
        msg = create_message(text=message)

        # With streaming=False, this will yield exactly one result
        async for event in client.send_message(msg):
            if isinstance(event, Message):
                logger.info(f"Received message from action agent: {event.model_dump_json(exclude_none=True, indent=2)}")
                # Extract text from the message
                text = next(
                    (p.content.text for p in event.parts if hasattr(p, "content") and hasattr(p.content, "text")),
                    ""
                )
                return text
            elif isinstance(event, tuple) and len(event) == 2:
                # (Task, UpdateEvent) tuple
                task, update_event = event
                logger.info(f"Task: {task.model_dump_json(exclude_none=True, indent=2)}")
                if update_event:
                    logger.info(f"Update: {update_event.model_dump_json(exclude_none=True, indent=2)}")
                return str(task)
            else:
                # Fallback for other response types
                logger.info(f"Response: {str(event)}")
                return str(event)

        return "No response from action agent"


# Define the tool for the coordination agent to delegate to action agent
@tool
async def delegate_to_action_agent(task_description: str) -> str:
    """
    Delegate a task to the action agent for execution.

    Args:
        task_description: A clear description of the task to be performed by the action agent

    Returns:
        The response from the action agent
    """
    logger.info(f"Delegating task to action agent: {task_description}")
    response = await send_to_action_agent(task_description)
    logger.info(f"Action agent response: {response}")
    return response


# Coordination Agent system prompt
coordinator_system_prompt = """
You are the Coordination Agent in an agent-to-agent flow.

Your responsibilities:
1. Receive and understand user requests
2. Analyze whether the request requires action from another agent
3. If action is needed, use the delegate_to_action_agent tool to send the task to the action agent
4. Relay the action agent's response back to the user in a clear and helpful manner

Important guidelines:
- For simple greetings or questions about yourself, respond directly
- For tasks that require execution, calculation, or external actions, delegate to the action agent
- Always provide context when delegating - be clear and specific about what needs to be done
- When you receive a response from the action agent, present it to the user in a clear format

You are the coordinator - your job is to orchestrate the workflow between the user and the action agent.
"""

# Create the coordination agent with the delegation tool
coordination_agent = Agent(
    name="CoordinationAgent",
    system_prompt=coordinator_system_prompt,
    tools=[delegate_to_action_agent]
)


@app.entrypoint
def invoke(payload):
    """
    Main entry point for the coordination agent.
    Receives user input and coordinates with the action agent.
    """
    user_message = payload.get("prompt", "Hello! How can I help you today?")

    logger.info(f"Received user message: {user_message}")

    # Run the coordination agent with the user message
    # The agent will decide whether to delegate to the action agent
    response = asyncio.run(run_coordination_agent(user_message))

    logger.info(f"Final response: {response}")

    return {"response": response}


async def run_coordination_agent(user_message: str) -> str:
    """
    Run the coordination agent with the user's message.
    The agent will use its tools to delegate to the action agent if needed.
    """
    # Send the message to the coordination agent
    result = coordination_agent.run(user_message)

    # Extract the text response
    if hasattr(result, 'text'):
        return result.text
    else:
        return str(result)


if __name__ == "__main__":
    app.run()
