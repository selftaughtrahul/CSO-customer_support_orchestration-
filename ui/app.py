import streamlit as st
import requests
import uuid
import hashlib
import base64
import sys
import os

# Add the project root to sys.path so we can import core.db securely
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.db import get_db_connection

# Backend Address
API_URL = "http://localhost:8005/api/v1/chat"

st.set_page_config(page_title="AI Customer Support (Modular)", layout="centered")

# --- AUTHENTICATION HELPER FUNCTIONS ---
def check_django_password(password: str, encoded: str) -> bool:
    """Validate a python plain-text string against Django's pbkdf2_sha256 hash format."""
    try:
        parts = encoded.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        
        algo, iterations, salt, expected_hash = parts
        iterations = int(iterations)
        
        # Hash the plain-text password using the same PBKDF2 parameters
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        
        # Base64 encode it and compare
        computed_hash_b64 = base64.b64encode(computed_hash).decode('utf-8')
        return computed_hash_b64 == expected_hash
    except Exception:
        return False

def authenticate_user(identifier, password):
    """Query MySQL database to check valid Django credentials."""
    conn = get_db_connection()
    if not conn:
        st.error("Database connection failed.")
        return None
        
    try:
        cursor = conn.cursor(dictionary=True)
        # Allow login via phone number or email (commonly used in Django apps)
        query = "SELECT id, first_name, last_name, password FROM sp_users WHERE primary_contact_number = %s OR official_email = %s LIMIT 1"
        cursor.execute(query, (identifier, identifier))
        user = cursor.fetchone()
        
        if user and user['password']:
            if check_django_password(password, user['password']):
                return user
    except Exception as e:
        st.error(f"Error during authentication: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return None


# --- MAINTAIN SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []


# ==========================================
# FLOW 1: LOGIN SCREEN (UNAUTHENTICATED)
# ==========================================
if not st.session_state.authenticated:
    st.title("🔒 Login to AI Dashboard")
    st.write("Please log in using your registered phone number or email.")
    
    with st.form("login_form"):
        identifier = st.text_input("Email or Phone Number")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            user = authenticate_user(identifier, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_data = user
                st.rerun()
            else:
                st.error("Invalid credentials. Please make sure your password is correct.")


# ==========================================
# FLOW 2: CHAT DASHBOARD (AUTHENTICATED)
# ==========================================
else:
    user_name = st.session_state.user_data.get('first_name', 'Customer')
    user_id = st.session_state.user_data.get('id', '')
    
    # Render Sidebar with Logout and User Details
    with st.sidebar:
        st.title("User Profile")
        st.write(f"**Name:** {user_name} {st.session_state.user_data.get('last_name', '')}")
        st.write(f"**Customer ID:** {user_id}")
        st.write("---")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.session_state.messages = []
            st.rerun()

    st.title("🛡️ Multi-Tiered AI Support")
    st.write(f"Welcome back, **{user_name}**! I am securely connected to your account. How can I assist you?")
    
    # Display entire history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    # User prompt
    if prompt := st.chat_input("Describe your issue..."):
        
        # INGENIOUS IMPROVEMENT: Automatically append the User ID secretly 
        # to the backend LLM, so the user doesn't have to manually type their ID!
        enriched_prompt = f"[{user_name}'s Account ID is: {user_id}]. {prompt}"
        
        # Render user prompt locally immediately (we render just the plain 'prompt')
        st.session_state.messages.append({"role": "user", "content": prompt, "enriched": enriched_prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Trigger backend orchestrator via REST protocol
        with st.spinner("Analyzing intent and securely searching your datasets..."):
            try:
                resp = requests.post(
                    API_URL, 
                    # Send the ENRICHED prompt to the backend orchestration agent
                    json={"thread_id": st.session_state.thread_id, "message": enriched_prompt}
                )
                resp.raise_for_status()
                data = resp.json()

                # Inspect the Graph State returned by FastAPI
                backend_status = data.get("status")
                handled_by = data.get("category", "N/A")

                if backend_status == "paused":
                    st.error(f"🛑 Thread Blocked. Escalated due to: {handled_by}")
                    st.info("A human administrator will review this ticket.")

                # Filter out historical messages to strictly print only the newest ones
                new_msgs = data.get("messages", [])
                for ai_msg in new_msgs:
                    if ai_msg["role"] == "ai":
                        # Note: You should ideally track message sync better, 
                        # but for prototyping, we just append the latest response.
                        st.session_state.messages.append({"role": "ai", "content": ai_msg["content"]})
                        with st.chat_message("ai"):
                            st.write(ai_msg["content"])
                            st.caption(f"*Processed automatically via the '{handled_by}' pathway.*")

            except Exception as e:
                st.error(f"Backend offline or AI limit reached: {e}")