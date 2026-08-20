# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from typing import Optional, List
from .rag import handle_user_message, get_db_connection

app = FastAPI(title="ChristMitra Local Chatbot Backend")

class ChatRequest(BaseModel):
    message: str
    session_id: str
    campus: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    intent: str
    ticket_id: Optional[int] = None
    sources: Optional[List[str]] = None

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    try:
        res = handle_user_message(req.message, req.session_id, req.campus)
        return ChatResponse(
            reply=res.get("reply", ""),
            intent=res.get("intent", "unclear"),
            ticket_id=res.get("ticket_id"),
            sources=res.get("sources")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/grievance/{ticket_id}")
def get_grievance_endpoint(ticket_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grievances WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Grievance ticket not found")
        
    return dict(row)

@app.get("/grievances")
def list_grievances():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grievances ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/")
def root():
    return {"status": "online", "model": "llama3.1:8b-instruct-q4_K_M"}
