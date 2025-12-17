from strands import Agent
from strands.tools import tool
from strands_tools import http_request
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/chat")
async def chat(req: Request):
    data = await req.json()
    user_input = data["input"]
    response = coordinator_agent(user_input)
    return {"response": response.text}

coordinator_system_prompt = """
You are the Coordinator Agent.

Your responsibilities:
1. Talk with the human user and understand their request.

Important:
- Do NOT perform complex reasoning or calculations yourself
- Your main focus is: understanding, clarifying, and delegating.
"""

coordinator_agent = Agent(
    system_prompt=coordinator_system_prompt
)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8007,
        reload=True
    )
