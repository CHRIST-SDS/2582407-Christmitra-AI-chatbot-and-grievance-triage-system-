import os
import requests
import chromadb
import sqlite3
import json
from .intent import classify_intent
from .db import get_db_connection

CHROMA_DIR = '/Users/sarathkumar/.gemini/antigravity-ide/scratch/college-chatbot/data/chroma_db'
OLLAMA_EMBED_URL = 'http://localhost:11434/api/embed'
OLLAMA_CHAT_URL = 'http://localhost:11434/api/chat'
EMBED_MODEL = 'nomic-embed-text'
LLM_MODEL = 'llama3.1:8b-instruct-q4_K_M'

# Initialize Chroma client
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
try:
    collection = chroma_client.get_collection("christ_university_knowledge")
except Exception:
    collection = None

def get_query_embedding(query: str):
    try:
        res = requests.post(OLLAMA_EMBED_URL, json={
            "model": EMBED_MODEL,
            "input": query
        }, timeout=10)
        res.raise_for_status()
        return res.json()["embeddings"][0]
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

def vector_search(query: str, campus: str = None, top_k: int = 4):
    if not collection:
        return []
    
    query_embedding = get_query_embedding(query)
    if not query_embedding:
        return []
    
    where = None
    if campus and campus != "all":
        # Search for exact campus or "all" campus documents
        where = {"$or": [{"campus": campus}, {"campus": "all"}]}
        
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where
    )
    
    chunks = []
    if results and results["documents"]:
        for idx in range(len(results["documents"][0])):
            chunks.append({
                "id": results["ids"][0][idx],
                "text": results["documents"][0][idx],
                "metadata": results["metadatas"][0][idx]
            })
    return chunks

def call_llm(system_prompt: str, user_content: str, temperature: float = 0.2):
    try:
        res = requests.post(OLLAMA_CHAT_URL, json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "options": {
                "temperature": temperature
            },
            "stream": False
        }, timeout=30)
        res.raise_for_status()
        return res.json()["message"]["content"].strip()
    except Exception as e:
        print(f"LLM generation error: {e}")
        return "Sorry, I encountered an error communicating with the model."

def log_grievance_to_db(message: str, summary: str, urgency: str, category: str, campus: str = None) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Simple routing cell mapping based on category
    # academic | hostel | ragging | harassment | fee | other
    routed_cells = {
        "academic": "Academic Office",
        "hostel": "Hostel Warden Office",
        "ragging": "Anti-Ragging Squad (URGENT)",
        "harassment": "Internal Committee / POSH Cell (URGENT)",
        "fee": "Accounts & Finance Department",
        "other": "General Grievance Cell"
    }
    routed_to = routed_cells.get(category.lower(), "General Grievance Cell")
    
    cursor.execute("""
        INSERT INTO grievances (category, urgency, raw_message, ai_summary, routed_to, campus, status)
        VALUES (?, ?, ?, ?, ?, ?, 'open')
    """, (category, urgency, message, summary, routed_to, campus))
    
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id

def log_chat_turn(session_id: str, role: str, message: str, intent: str = None, retrieved_chunk_ids: list = None, grievance_id: int = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    chunk_ids_str = json.dumps(retrieved_chunk_ids) if retrieved_chunk_ids else None
    cursor.execute("""
        INSERT INTO chat_logs (session_id, role, message, intent, retrieved_chunk_ids, grievance_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, role, message, intent, chunk_ids_str, grievance_id))
    conn.commit()
    conn.close()

def process_grievance(query: str, campus: str = None) -> dict:
    # Use LLM to extract Category
    category_prompt = (
        "You are a grievance routing system. Classify the student complaint into exactly one category:\n"
        "- academic\n- hostel\n- ragging\n- harassment\n- fee\n- other\n\n"
        "Reply with only the lowercase category name. Do not write anything else."
    )
    category = call_llm(category_prompt, query).lower().strip()
    valid_categories = ["academic", "hostel", "ragging", "harassment", "fee", "other"]
    if category not in valid_categories:
        category = "other"
        
    # Use LLM to extract Urgency
    urgency_prompt = (
        "You are an urgency analysis assistant. Score the urgency of this complaint as exactly one of:\n"
        "- low\n- medium\n- high\n- critical\n\n"
        "Reply with only the lowercase urgency level. Do not write anything else."
    )
    urgency = call_llm(urgency_prompt, query).lower().strip()
    if urgency not in ["low", "medium", "high", "critical"]:
        urgency = "medium"
        
    # Use LLM to summarize
    summary_prompt = (
        "You are a grievance administrator. Summarize the user's grievance in 1-2 concise lines.\n"
        "Focus only on the key facts of the issue. Do not introduce yourself or explain."
    )
    summary = call_llm(summary_prompt, query)
    
    ticket_id = log_grievance_to_db(query, summary, urgency, category, campus)
    
    routed_cells = {
        "academic": "Academic Office",
        "hostel": "Hostel Warden Office",
        "ragging": "Anti-Ragging Squad (URGENT)",
        "harassment": "Internal Committee / POSH Cell (URGENT)",
        "fee": "Accounts & Finance Department",
        "other": "General Grievance Cell"
    }
    routed_to = routed_cells.get(category, "General Grievance Cell")
    
    reply = (
        f"🚨 **Grievance Logged** 🚨\n\n"
        f"I've logged your concern as **Ticket #{ticket_id}**.\n\n"
        f"- **Category:** {category.capitalize()}\n"
        f"- **Assigned Severity:** {urgency.upper()}\n"
        f"- **Assigned Handling Cell:** {routed_to}\n\n"
        f"**Summary of issue:** *{summary}*\n\n"
        f"A human coordinator from the designated cell has been notified and will review your ticket shortly. "
        f"You can reference Ticket #{ticket_id} when contacting the cell directly."
    )
    
    return {
        "reply": reply,
        "ticket_id": ticket_id,
        "category": category,
        "urgency": urgency,
        "routed_to": routed_to
    }

def handle_user_message(query: str, session_id: str, campus: str = None) -> dict:
    intent = classify_intent(query)
    
    # 1. Distress Hand-off
    if intent == "distress":
        reply = (
            "🚨 **IMPORTANT: EMERGENCY CONTACT INFORMATION** 🚨\n\n"
            "If you or someone you know is experiencing distress, harassment, ragging, or needs urgent assistance, please contact the support cells immediately:\n\n"
            "📞 **Emergency Contacts & Helpline Numbers:**\n"
            "- **Anti-Ragging Squad / Helpline:** +91 80 4012 9100 | Email: antiragging@christuniversity.in\n"
            "- **Sexual Harassment / Internal Committee (IC):** Email: ic@christuniversity.in\n"
            "- **Student Counselling Centre:** Office at Block II, Central Campus | Phone: +91 80 4012 9100\n"
            "- **National Anti-Ragging Helpline:** 1800-180-5522\n\n"
            "This chatbot is a local informational tool and does not provide counseling. "
            "Please reach out to the contacts listed above to speak with a human support officer."
        )
        # Log to grievances with critical urgency
        ticket_id = log_grievance_to_db(query, "Immediate Distress / Emergency Flag", "critical", "other", campus)
        log_chat_turn(session_id, "user", query, intent=intent, grievance_id=ticket_id)
        log_chat_turn(session_id, "assistant", reply, intent=intent, grievance_id=ticket_id)
        return {"reply": reply, "intent": "distress", "ticket_id": ticket_id}
        
    # 2. Grievance Log
    if intent == "grievance":
        result = process_grievance(query, campus)
        log_chat_turn(session_id, "user", query, intent=intent, grievance_id=result["ticket_id"])
        log_chat_turn(session_id, "assistant", result["reply"], intent=intent, grievance_id=result["ticket_id"])
        return {**result, "intent": "grievance"}
        
    # 3. Informational RAG
    if intent == "informational":
        chunks = vector_search(query, campus=campus, top_k=4)
        
        context_str = ""
        retrieved_ids = []
        sources = []
        for c in chunks:
            context_str += f"--- Document Source URL: {c['metadata']['source_url']} ---\n{c['text']}\n\n"
            retrieved_ids.append(c["id"])
            if c["metadata"]["source_url"] not in sources:
                sources.append(c["metadata"]["source_url"])
                
        system_prompt = (
            "You are ChristMitra, a helpful, highly accurate assistant for Christ University students.\n"
            "Answer the query using ONLY the provided document context below.\n"
            "If the answer is not in the context, say 'I don't have that information. Please contact the relevant office.' and do not invent details or assume anything.\n"
            "Never invent policy, rules, contact emails, fees, or deadlines.\n\n"
            f"=== Context ===\n{context_str}\n"
        )
        
        reply = call_llm(system_prompt, query)
        
        log_chat_turn(session_id, "user", query, intent=intent, retrieved_chunk_ids=retrieved_ids)
        log_chat_turn(session_id, "assistant", reply, intent=intent, retrieved_chunk_ids=retrieved_ids)
        
        return {
            "reply": reply,
            "intent": "informational",
            "sources": sources
        }
        
    # 4. Unclear or General Conversation
    reply = (
        "Hello! I am ChristMitra, your campus assistant. How can I help you today?\n\n"
        "- Ask me about campuses, departments, or faculty details.\n"
        "- If you have a complaint or issue, write it here to file a grievance ticket.\n"
        "- Type an emergency keyword if you need immediate helpline contacts."
    )
    log_chat_turn(session_id, "user", query, intent=intent)
    log_chat_turn(session_id, "assistant", reply, intent=intent)
    return {"reply": reply, "intent": "unclear"}
