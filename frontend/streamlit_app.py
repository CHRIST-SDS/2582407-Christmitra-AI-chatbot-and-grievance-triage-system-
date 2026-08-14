import streamlit as st
import requests
import uuid

# Premium UI Theme Styling
st.set_page_config(
    page_title="ChristMitra — Christ University Campus Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium CSS injection
st.markdown("""
<style>
    /* Premium background and glassmorphism styling */
    .reportview-container {
        background: #0F172A;
    }
    .sidebar .sidebar-content {
        background: #1E293B;
    }
    
    /* Title style */
    .main-title {
        font-family: 'Outfit', 'Inter', sans-serif;
        background: linear-gradient(135deg, #38BDF8, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.2rem;
    }
    
    /* Support banner */
    .support-banner {
        background: linear-gradient(135deg, #1E1B4B, #311042);
        border: 1px solid #4338CA;
        border-radius: 12px;
        padding: 15px;
        color: #E0E7FF;
        margin-bottom: 20px;
    }
    
    /* Card design */
    .ticket-card {
        background-color: #1E293B;
        border-left: 5px solid #F59E0B;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    .ticket-card-critical {
        border-left-color: #EF4444 !important;
    }
    
    .ticket-card-high {
        border-left-color: #F97316 !important;
    }
</style>
""", unsafe_allow_html=True)

# API Endpoint URL
BACKEND_URL = "http://localhost:8000"

# Session State Initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "👋 Hello! I am **ChristMitra**, your local campus assistant.\n\nI can answer questions about campus locations, departments, faculty profiles, and university policies. If you have an issue, describe it to file a grievance ticket."}
    ]

# Layout Setup
st.markdown("<h1 class='main-title'>🎓 ChristMitra</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94A3B8; font-size: 1.1rem; margin-top: -10px;'>Your Intelligent, Fully-Local Campus Support & Grievance Triage System</p>", unsafe_allow_html=True)

# Sidebar contents
with st.sidebar:
    st.image("https://christuniversity.in/images/logo.png", width=200)
    st.markdown("### ⚙️ Chat Settings")
    
    campus = st.selectbox(
        "Select Campus Scope:",
        [
            "all",
            "Bangalore Central Campus",
            "Bangalore Bannerghatta Road Campus",
            "Bangalore Kengeri Campus",
            "Bangalore Yeshwanthpur Campus",
            "Delhi NCR Campus",
            "Pune Lavasa Campus"
        ]
    )
    
    st.markdown("---")
    st.markdown("### 📋 Quick Help Suggestions")
    
    suggestions = [
        "What is the hostel curfew time?",
        "How do I contact the Bangalore Central campus?",
        "File a complaint about poor internet in the library",
        "Who is Dr. John Doe?"
    ]
    
    for s in suggestions:
        if st.button(s, key=f"sug_{s}"):
            st.session_state.messages.append({"role": "user", "content": s})
            # Trigger API
            try:
                res = requests.post(f"{BACKEND_URL}/chat", json={
                    "message": s,
                    "session_id": st.session_state.session_id,
                    "campus": campus if campus != "all" else None
                })
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": data["reply"],
                        "sources": data.get("sources")
                    })
                else:
                    st.session_state.messages.append({"role": "assistant", "content": "Error: Failed to connect to the backend server."})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Connection Error: {e}"})
            st.rerun()

    st.markdown("---")
    # Triage Queue Tracker
    st.markdown("### 🎫 Grievance Status Tracker")
    try:
        g_res = requests.get(f"{BACKEND_URL}/grievances")
        if g_res.status_code == 200:
            tickets = g_res.json()
            if not tickets:
                st.info("No grievances filed yet.")
            else:
                for t in tickets[:5]:  # Show latest 5
                    urg = t.get("urgency", "medium").lower()
                    card_class = "ticket-card"
                    if urg == "critical":
                        card_class = "ticket-card ticket-card-critical"
                    elif urg == "high":
                        card_class = "ticket-card ticket-card-high"
                        
                    st.markdown(f"""
                    <div class='{card_class}'>
                        <strong>Ticket #{t['id']}</strong> ({t['category'].upper()})<br/>
                        <span style='font-size: 0.85rem; color: #94A3B8;'>Routed to: {t['routed_to']}</span><br/>
                        <span style='font-size: 0.85rem; font-style: italic; color: #E2E8F0;'>"{t['ai_summary']}"</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("Could not fetch tickets from backend.")
    except Exception:
        st.info("Start the backend server to see active grievance logs.")

# Chat Interface Column
col_chat, col_side = st.columns([7, 3])

with col_chat:
    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("sources"):
                st.markdown("#### Sources:")
                for s in msg["sources"]:
                    st.markdown(f"- [{s}]({s})")

    # Message Input
    if prompt := st.chat_input("Ask a question or report an issue..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Processing local LLM inference..."):
                try:
                    res = requests.post(f"{BACKEND_URL}/chat", json={
                        "message": prompt,
                        "session_id": st.session_state.session_id,
                        "campus": campus if campus != "all" else None
                    })
                    if res.status_code == 200:
                        data = res.json()
                        st.write(data["reply"])
                        if data.get("sources"):
                            st.markdown("#### Sources:")
                            for s in data["sources"]:
                                st.markdown(f"- [{s}]({s})")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": data["reply"],
                            "sources": data.get("sources")
                        })
                    else:
                        st.write("Error: Backend returned an unhealthy status code.")
                except Exception as e:
                    st.write(f"Error connecting to backend: {e}")
        st.rerun()

with col_side:
    st.markdown("""
    <div class="support-banner">
        <h3>🚨 Emergency & Distress Support</h3>
        <p>If you need immediate counseling, anti-ragging support, or POSH grievance assistance, contact the numbers below:</p>
        <ul>
            <li><strong>Anti-Ragging Squad:</strong> +91 80 4012 9100</li>
            <li><strong>POSH Committee Cell:</strong> ic@christuniversity.in</li>
            <li><strong>Counselling Cell:</strong> Central Block, II Floor</li>
            <li><strong>National Anti-Ragging Help:</strong> 1800-180-5522</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    ### ℹ️ Safe Guardrails
    - **Local Processing:** Chat logs and inputs never leave your MacBook.
    - **Policy Guard:** Answer generation is grounded strictly on index references.
    - **Coordinated Routing:** Classification and ticketing are automated; final resolutions are managed by university staff.
    """)
