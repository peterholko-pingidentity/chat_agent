from strands import Agent
from strands.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp

import jwt
import json
import asyncio
import logging
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, TextPart

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300  # set request timeout to 5 minutes

def create_message(*, role: Role = Role.user, text: str) -> Message:
    return Message(
        kind="message",
        role=role,
        parts=[Part(TextPart(kind="text", text=text))],
        message_id=uuid4().hex,
    )

async def send_sync_message(message: str):
    # Get runtime URL from environment variable
    runtime_url = 'https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/arn%3Aaws%3Abedrock-agentcore%3Aus-east-1%3A574076504146%3Aruntime%2Faction_agent-eJIKYT7d5s/invocations/'
    
    # Generate a unique session ID
    session_id = str(uuid4())
    print(f"Generated session ID: {session_id}")

    # Add authentication headers for Amazon Bedrock AgentCore
    headers = {"Authorization": f"Bearer eyJraWQiOiIzYzFmMWY4MC1kYjczLTExZjAtYmE4ZC0xMzI3NzZkNjFhNDYiLCJhbGciOiJSUzI1NiJ9.eyJjbGllbnRfaWQiOiI5OTY0Mzc3NC00NDU0LTQyOTctYjJjMS05MjMyZjNlYTM5MmUiLCJpc3MiOiJodHRwczovL2F1dGgucGluZ29uZS5jb20vNDg0YzhkNjktMjc4My00YjU1LWI3ODctYmU3MWM0Y2QxNTMyL2FzIiwianRpIjoiMWJhMDY5MTEtMGNjZC00OGVkLThkYmMtOTJkMWY5ZGY1ZGMzIiwiaWF0IjoxNzY2MTA3MTI3LCJleHAiOjE3NjYxMTA3MjcsImF1ZCI6WyJBY3Rpb25BZ2VudCJdLCJzY29wZSI6ImFjdGlvbmFnZW50IiwiZW52IjoiNDg0YzhkNjktMjc4My00YjU1LWI3ODctYmU3MWM0Y2QxNTMyIiwib3JnIjoiNWJmY2MzN2UtZDhmYy00ODE2LWIxOTEtNmJiOWE2NjZhZTU4IiwicDEucmlkIjoiMWJhMDY5MTEtMGNjZC00OGVkLThkYmMtOTJkMWY5ZGY1ZGMzIn0.Nn9oWi7aFYCxKQLQ_DU_drc4Pmh_24MaLe3BQontlOtLDZbdf1XcQsmq5q0MadfGc1Q0EYFbBb6v5Dlzz4Sk_1JWYu0znjM_CHgEBJ8c13nTtWhEvqGEihE8GV9PRUnpjhU7oPKPlEqxk1EPFyC35pnespLRQtbugj8kfU2LaMI2S1ZhFicXZ38gjFvlX9reaSeVC0WqilUxMJ90NO0ZTb4TffECi9teukwm_3tJ0ln17kNQYU4z4-wFWUGAibMjrUztaf1Xy9gU3KAPk-D3KbMSFqDxpH3-qqXzzltAM02E7zxV7o_0jPg4_rS4YoqUt-YxHmxbYxsJyVAAgq8oPA",
        'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': session_id}
        
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers) as httpx_client:
        # Get agent card from the runtime URL
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=runtime_url)
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
                logger.info(event.model_dump_json(exclude_none=True, indent=2))
                return event
            elif isinstance(event, tuple) and len(event) == 2:
                # (Task, UpdateEvent) tuple
                task, update_event = event
                logger.info(f"Task: {task.model_dump_json(exclude_none=True, indent=2)}")
                if update_event:
                    logger.info(f"Update: {update_event.model_dump_json(exclude_none=True, indent=2)}")
                return task
            else:
                # Fallback for other response types
                logger.info(f"Response: {str(event)}")
                return event


def extract_operation_type(user_message: str) -> str:
    """Determine the type of operation from the user message."""
    message_lower = user_message.lower()
    if any(word in message_lower for word in ['delete', 'remove', 'deactivate']):
        return 'delete'
    elif any(word in message_lower for word in ['create', 'add', 'new']):
        return 'create'
    elif any(word in message_lower for word in ['update', 'modify', 'change', 'edit']):
        return 'update'
    elif any(word in message_lower for word in ['read', 'get', 'fetch', 'show', 'list']):
        return 'read'
    return 'unknown'


def validate_token_for_operation(access_token: str, operation: str) -> tuple[bool, str]:
    """
    Validate that the access token has the required scope for the operation.
    Returns (is_valid, error_message)
    """
    import jwt
    
    if not access_token:
        return False, "No access token provided. Authentication required."
    
    try:
        # Decode without verification to extract scopes
        # In production, you should verify the signature
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        scopes = decoded.get('scope', '')
        
        # Convert scope string to list
        if isinstance(scopes, str):
            scope_list = scopes.split()
        else:
            scope_list = scopes if isinstance(scopes, list) else []
        
        logger.info(f"Token scopes: {scope_list}")
        logger.info(f"Required operation: {operation}")
        
        # Check if required scope exists for delete operations
        if operation == 'delete':
            if 'delete' not in scope_list and 'user:delete' not in scope_list:
                return False, f"Insufficient permissions. Delete operations require 'delete' scope. Your token has scopes: {', '.join(scope_list)}"
        
        # You can add similar checks for create/update if needed
        # elif operation == 'create':
        #     if 'create' not in scope_list and 'user:create' not in scope_list:
        #         return False, "Insufficient permissions for create operation."
        
        return True, ""
        
    except jwt.DecodeError:
        return False, "Invalid access token format."
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return False, f"Token validation failed: {str(e)}"


app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload):
    print(payload)
    user_message = payload.get("prompt")
    print("Printing User message and Access Token")
    print(user_message)
    access_token = payload.get("accessToken")  # Get access token from payload
    print(access_token)

    if not access_token:
        response = coordinator_agent("The user does not have access token, response to the user with this URL https://example.com indicating to click on it to initiate authentication")
        print("=== DEBUG: response.message attributes ===")
        print(dir(response.message))
        print("=== response.message type ===")
        print(type(response.message))
        print("=== response.message value ===")
        print(response.message)
        print("=== response.message value ===")
        print(response.message)
        return {"response": str(response.message)}
    
    # Determine operation type from user message
    
    #print("Detected operation" + operation)
    
    # Validate token for the operation BEFORE involving the coordinator agent
    #if operation == 'delete':
    #    is_valid, error_message = validate_token_for_operation(access_token, operation)
        
    #    if not is_valid:
    #        return {
    #            "response": f"Authorization Error: {error_message}",
    #            "authorized": False,
    #            "operation": operation
    #        }

    decoded = jwt.decode(access_token, options={"verify_signature": False})
    scopes = decoded.get('scope', '')
    
    # Convert scope string to list
    if isinstance(scopes, str):
        scope_list = scopes.split()
    else:
        scope_list = scopes if isinstance(scopes, list) else []
    
    print("Token scopes: " + str(scope_list))

    operation = extract_operation_type(user_message)

    if operation == 'delete': 
        if 'delete' in scope_list:
            # If we get here, either it's not a delete operation, or it is and token is valid
            print("Authorization check passed, proceeding to coordinator agent")
            
            # Now invoke the coordinator agent for conversational handling
            response = coordinator_agent(user_message)
            print("=== DEBUG: response.message attributes ===")
            print(dir(response.message))
            print("=== response.message type ===")
            print(type(response.message))
            print("=== response.message value ===")
            print(response.message)
            print("=== response.message value ===")
            print(response.message)
            
            # Send to Action Agent only after authorization passed
            result = asyncio.run(send_sync_message(str(response.message)))
            print(str(result))

            if isinstance(result, Message):
                text = next(
                    (p.content.text for p in result.parts if hasattr(p, "content") and hasattr(p.content, "text")),
                    ""
                )
                return {"response": text}
            else:
                return {"response": str(result)}
        else:
            response = coordinator_agent("The user does not have the delete scope, response to the user with this URL https://example.com to perform step-up authorization")
            return {"response": str(response.message)}
    else:
        response = coordinator_agent(user_message)

        # Send to Action Agent only after authorization passed
        result = asyncio.run(send_sync_message(str(response.message)))
        print(result)
        if isinstance(result, Message):
            text = next(
                (p.content.text for p in result.parts if hasattr(p, "content") and hasattr(p.content, "text")),
                ""
            )
            return {"response": text}
        else:
            return {"response": str(result)}


coordinator_system_prompt = """
    You are the Coordinator Agent that is being used to submit Create User, Read User, Update User 
    and Delete User on PingOne and Microsoft 365.  Anytime you submit a request you must do it on both systems. 

    If the user asks to delete any user/account, you must check if the inputted access token contains the "delete" scope.   

    Use the Agent Card to find the decode_jwt tool and use it to inspect the access token.  

    Do not ever expose the user's access token.  

    Your responsibilities:
    1. Talk with the human user and understand their request.
    2. If the request is ambiguous, ask brief clarifying questions.
    3. When the request is clear, summarize it as a single concise instruction

    Important:
    - Do NOT perform complex reasoning or calculations yourself.
    - Your main focus is: understanding, clarifying, and delegating.
"""

coordinator_agent = Agent(
    system_prompt=coordinator_system_prompt
)

if __name__ == "__main__":
    app.run()
