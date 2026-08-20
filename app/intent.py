import re
import requests

OLLAMA_CHAT_URL = 'http://localhost:11434/api/chat'
MODEL_NAME = 'llama3.1:8b-instruct-q4_K_M'

DISTRESS_KEYWORDS = [
    r'\bragging\b', r'\bharassment\b', r'\bself-harm\b', r'\bsuicide\b', 
    r'\bsuicidal\b', r'\bdepression\b', r'\bdepressed\b', r'\bassault\b', 
    r'\bphysical abuse\b', r'\bsexual harassment\b', r'\babuse\b', r'\bbullying\b',
    r'\bbully\b'
]

def classify_intent(query: str) -> str:
    query_lower = query.lower()
    
    # 1. Quick distress keyword check (Bypass LLM)
    for kw in DISTRESS_KEYWORDS:
        if re.search(kw, query_lower):
            return "distress"
            
    # 2. Call LLM for standard intent classification
    system_prompt = (
        "You are an intent classification assistant for a university chatbot.\n"
        "Classify the user's query into exactly one of these categories:\n"
        "- informational: the user is asking a question, asking who someone is (e.g. 'who is dalvin', 'who is professor X'), looking for contact details, faculty info, staff room/building locations, department details, or policies.\n"
        "- grievance: the user is complaining, reporting an issue, submitting a grievance, or asking how to complain.\n"
        "- unclear: pure single-word greetings ('hello', 'hi'), test messages, or complete gibberish.\n\n"
        "Reply with ONLY the category name in lowercase (informational / grievance / unclear). Do not explain or add punctuation."
    )
    
    try:
        res = requests.post(OLLAMA_CHAT_URL, json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "options": {
                "temperature": 0.0
            },
            "stream": False
        }, timeout=10)
        res.raise_for_status()
        reply = res.json()["message"]["content"].strip().lower()
        
        # Clean up potential extra output
        for category in ["informational", "grievance", "unclear"]:
            if category in reply:
                return category
        return "unclear"
    except Exception as e:
        print(f"Error in LLM intent classification: {e}")
        # Default fallback
        return "informational"

if __name__ == "__main__":
    test_queries = [
        "What is the hostel curfew time?",
        "Someone is ragging me in the hostel block, please help!",
        "Hello there",
        "The fan in Block II Room 302 is not working, can someone fix it?"
    ]
    for q in test_queries:
        print(f"Query: '{q}' -> Intent: {classify_intent(q)}")
