from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage
from core.graph import app  # The compiled LangGraph application

app = FastAPI(title="Multi-Agent Support API", version="1.0.0")

server = FastAPI(
    title="Customer Support Orchestrator",
    version="2.0 Modular Edition"
)


# API Payloads
class ChatRequest(BaseModel):
    thread_id: str
    message: str

class ChatResponse(BaseModel):
    status: str # "active", "paused", "resolved", "error"
    messages: List[Dict[str, Any]]
    category: str
    
    
@server.post("/api/v1/chat", response_model=ChatResponse)
async def process_chat(request: ChatRequest):
    """
    Submits a message to the multi-tiered orchestrator.
    Maintains memory using thread_id.
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    
    # 1. Check if the thread is currently paused waiting for human input
    current_state = app.get_state(config)
    if current_state.next and "human_escalation" in current_state.next:
        return ChatResponse(
            status="paused",
            messages=[{"role": "system", "content": "Awaiting human review."}],
            category="escalation"
        )
    
    # 2. Submit new user utterance 
    try:
        final_state = app.invoke({"messages": [HumanMessage(content=request.message)]}, config=config)
        
        # 3. Format response for the frontend (clean up LangChain BaseMessage objects)
        formatted_messages = []
        for m in final_state.get("messages", []):
            role = "user" if isinstance(m, HumanMessage) else "ai"
            formatted_messages.append({"role": role, "content": m.content})
            
        # 4. Check if the interaction caused a new pause
        new_state = app.get_state(config)
        status = "paused" if new_state.next else "active"
            
        return ChatResponse(
            status=status,
            messages=formatted_messages,
            category=final_state.get("ticket_category", "unknown")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Routing Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Make sure to run from project root: python -m api.main
    uvicorn.run(server, host="0.0.0.0", port=8000)