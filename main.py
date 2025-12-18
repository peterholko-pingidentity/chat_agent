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

DEFAULT_TIMEOUT = 300 # set request timeout to 5 minutes
ACTION_AGENT_URL = "http://127.0.0.1:9001"  # URL for the action_agent

app = BedrockAgentCoreApp()

def create_message(*, role: Role = Role.user, text: str) -> Message:
    return Message(
        kind="message",
        role=role,
        parts=[Part(TextPart(kind="text", text=text))],
        message_id=uuid4().hex,
    )

async def send_streaming_message(message: str, base_url: str = "http://127.0.0.1:9000"):
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as httpx_client:
        # Get agent card
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()

        # Create client using factory
        config = ClientConfig(
            httpx_client=httpx_client,
            streaming=True,  # Use streaming mode
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)

        # Create and send message
        msg = create_message(text=message)

        async for event in client.send_message(msg):
            if isinstance(event, Message):
                logger.info(event.model_dump_json(exclude_none=True, indent=2))
            elif isinstance(event, tuple) and len(event) == 2:
                # (Task, UpdateEvent) tuple
                task, update_event = event
                logger.info(f"Task: {task.model_dump_json(exclude_none=True, indent=2)}")
                if update_event:
                    logger.info(f"Update: {update_event.model_dump_json(exclude_none=True, indent=2)}")
            else:
                # Fallback for other response types
                logger.info(f"Response: {str(event)}")

async def call_action_agent(task: str) -> str:
    """
    Call the action_agent via A2A protocol to execute a task.

    Args:
        task: The task description to send to the action_agent

    Returns:
        The response from the action_agent as a string
    """
    logger.info(f"Calling action_agent with task: {task}")

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as httpx_client:
        # Get action agent card
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=ACTION_AGENT_URL)
        agent_card = await resolver.get_agent_card()

        # Create client using factory
        config = ClientConfig(
            httpx_client=httpx_client,
            streaming=True,
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)

        # Create and send message
        msg = create_message(text=task)

        # Collect response parts
        response_text = ""

        async for event in client.send_message(msg):
            if isinstance(event, Message):
                logger.info(f"Action agent response: {event.model_dump_json(exclude_none=True, indent=2)}")
                # Extract text from message parts
                for part in event.parts:
                    if hasattr(part, "content") and hasattr(part.content, "text"):
                        response_text += part.content.text
            elif isinstance(event, tuple) and len(event) == 2:
                # (Task, UpdateEvent) tuple
                task_event, update_event = event
                logger.info(f"Task: {task_event.model_dump_json(exclude_none=True, indent=2)}")
                if update_event:
                    logger.info(f"Update: {update_event.model_dump_json(exclude_none=True, indent=2)}")

        return response_text if response_text else "No response received from action_agent"

@tool
def execute_action(task: str) -> str:
    """
    Execute a task by delegating it to the action_agent via A2A protocol.

    Use this tool when you need to:
    - Perform complex actions or calculations
    - Execute tasks that require specialized capabilities
    - Delegate work to the action agent

    Args:
        task: A clear, concise description of the task to execute

    Returns:
        The result from the action_agent
    """
    result = asyncio.run(call_action_agent(task))
    return result

@app.entrypoint
def invoke(payload):
    user_message = payload.get("prompt", "Hello! How can I help you today?")
    response = coordinator_agent(user_message)
    result = asyncio.run(send_streaming_message(response.text))

    if isinstance(result, Message):
        text = next(
            (p.content.text for p in result.parts if hasattr(p, "content") and hasattr(p.content, "text")),
            ""
        )
        return {"response": text}
    else:
        return {"response": str(result)}

coordinator_system_prompt = """
    You are the Coordinator Agent.

    Your responsibilities:
    1. Talk with the human user and understand their request.
    2. If the request is ambiguous, ask brief clarifying questions.
    3. When the request is clear, use the execute_action tool to delegate the task to the action_agent.

    Important:
    - Do NOT perform complex reasoning or calculations yourself.
    - Your main focus is: understanding, clarifying, and delegating.
    - Use the execute_action tool to send tasks to the action_agent for execution.
    - The action_agent will handle the actual task execution and return results.
"""

coordinator_agent = Agent(
    system_prompt=coordinator_system_prompt,
    tools=[execute_action]
)

if __name__ == "__main__":
    app.run()
