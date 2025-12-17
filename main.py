from strands import Agent
from strands.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload):
    user_message = payload.get("prompt", "Hello! How can I help you today?")
    response = coordinator_agent(user_message)
    return {"result": result.message}

coordinator_system_prompt = """
    You are the Coordinator Agent.

    Your responsibilities:
    1. Talk with the human user and understand their request.
    2. If the request is ambiguous, ask brief clarifying questions.
    3. When the request is clear, summarize it as a single concise instruction
    and call the `perform_action` tool with that instruction.
    4. Once you get the result from `perform_action`, present it nicely to the user.

    Important:
    - Do NOT perform complex reasoning or calculations yourself.
    - Always delegate work to `perform_action` for the actual execution.
    - Your main focus is: understanding, clarifying, and delegating.
"""

coordinator_agent = Agent(
    system_prompt=coordinator_system_prompt
)

if __name__ == "__main__":
    app.run()
