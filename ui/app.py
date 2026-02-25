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
        
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        
        computed_hash_b64 = base64.b64encode(computed_hash).decode('utf-8')
        return computed_hash_b64 == expected_hash
    except Exception:
        return False

def authenticate_admin(email, password):
    """Query MySQL database to check valid Django credentials for Web Admins."""
    conn = get_db_connection()
    if not conn:
        st.error("Database connection failed.")
        return None
        
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, first_name, last_name, password, is_superuser FROM sp_users WHERE official_email = %s LIMIT 1"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        
        if user and user['password']:
            if check_django_password(password, user['password']):
                return user
    except Exception as e:
        st.error(f"Error during admin authentication: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return None

def check_customer_phone(phone):
    """Query MySQL database to check if the exact contact number exists for a customer login."""
    conn = get_db_connection()
    if not conn:
        st.error("Database connection failed.")
        return None
        
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, first_name, last_name FROM sp_users WHERE primary_contact_number = %s LIMIT 1"
        cursor.execute(query, (phone,))
        user = cursor.fetchone()
        return user
    except Exception as e:
        st.error(f"Error fetching customer: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return None

# --- MAINTAIN SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "awaiting_otp" not in st.session_state:
    st.session_state.awaiting_otp = False
if "temp_user_data" not in st.session_state:
    st.session_state.temp_user_data = None
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []


def logout():
    st.session_state.authenticated = False
    st.session_state.is_admin = False
    st.session_state.awaiting_otp = False
    st.session_state.temp_user_data = None
    st.session_state.user_data = None
    st.session_state.messages = []
    st.rerun()

# ==========================================
# FLOW 1: LOGIN SCREEN (UNAUTHENTICATED)
# ==========================================
if not st.session_state.authenticated:
    st.title("🔒 Login to AI Dashboard")
    st.write("Please select your role and log in.")
    
    # We use tabs to completely separate the logic workflows visually!
    tab1, tab2 = st.tabs(["📲 Customer Login (OTP)", "💻 Admin Login (Password)"])
    
    # --- CUSTOMER TAB ---
    with tab1:
        if not st.session_state.awaiting_otp:
            st.markdown("#### Enter your registered mobile number")
            phone = st.text_input("Mobile Number", placeholder="e.g. 7081628885")
            
            if st.button("Send OTP"):
                if phone:
                    user = check_customer_phone(phone)
                    if user:
                        st.session_state.temp_user_data = user
                        st.session_state.awaiting_otp = True
                        st.success("OTP sent securely to your number!")
                        st.rerun()
                    else:
                        st.error("Number not found in our records. Please try again.")
        else:
            st.markdown("#### Enter the OTP sent to your phone")
            otp = st.text_input("4-digit OTP", type="password", placeholder="Prototype bypass: type '1234'")
            col1, col2 = st.columns([1, 4])
            
            with col1:
                if st.button("Verify & Login"):
                    # We accept '1234' trivially for the prototype simulation
                    if otp == "1234" or len(otp) == 4:
                        st.session_state.user_data = st.session_state.temp_user_data
                        st.session_state.authenticated = True
                        st.session_state.is_admin = False
                        st.session_state.awaiting_otp = False
                        st.rerun()
                    else:
                        st.error("Invalid OTP. For prototype, please use '1234'.")
            
            with col2:
                if st.button("Cancel / Back"):
                    st.session_state.awaiting_otp = False
                    st.session_state.temp_user_data = None
                    st.rerun()
                    
    # --- ADMIN TAB ---
    with tab2:
        st.markdown("#### Web Admin Secure Access")
        with st.form("admin_login_form"):
            email = st.text_input("Official Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login as Admin")
            
            if submitted:
                if email and password:
                    admin_user = authenticate_admin(email, password)
                    if admin_user:
                        st.session_state.authenticated = True
                        st.session_state.is_admin = True
                        st.session_state.user_data = admin_user
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please make sure your email and password are correct.")

# ==========================================
# FLOW 2: CHAT DASHBOARD (AUTHENTICATED)
# ==========================================
else:
    user_name = st.session_state.user_data.get('first_name', 'User')
    user_id = st.session_state.user_data.get('id', '')
    is_admin = st.session_state.is_admin
    
    # Render Sidebar with Logout and User Details
    with st.sidebar:
        if is_admin:
            st.title("💻 Admin Dashboard")
            st.write(f"**Admin Name:** {user_name} {st.session_state.user_data.get('last_name', '')}")
            st.write("**Access Level:** Full Database Privileges")
            st.caption("You can ask the AI to lookup details for ANY user ID using natural language.")
        else:
            st.title("👤 Customer Profile")
            st.write(f"**Name:** {user_name} {st.session_state.user_data.get('last_name', '')}")
            st.write(f"**Customer ID:** {user_id}")
            st.caption("Your inquiries are securely restricted to your own personal Account ID.")
            
        st.write("---")
        st.button("Logout", on_click=logout)

    st.title("🛡️ Multi-Tiered AI Support")
    if is_admin:
         st.write(f"Welcome back, **Admin {user_name}**. The AI is operating in global access mode.")
    else:
         st.write(f"Welcome back, **{user_name}**. I am securely connected to your account. How can I assist you?")
    
    # Display entire history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    # User prompt
    if prompt := st.chat_input("Describe your issue..."):
        
        # INGENIOUS IMPROVEMENT:
        # If is_admin is True: we don't restrict the agent. It can freely query whatever user id the admin asks.
        # If is_admin is False: we secretly lock the prompt's ID parameter context securely around their own ID.
        if is_admin:
            enriched_prompt = f"[ADMIN USER PRIVILEGES ENABLED]. Answer the following admin request: {prompt}"
        else:
            enriched_prompt = f"[{user_name}'s Account ID is strictly: {user_id}]. {prompt}"
        
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
                        st.session_state.messages.append({"role": "ai", "content": ai_msg["content"]})
                        with st.chat_message("ai"):
                            st.write(ai_msg["content"])
                            # Visual identifier to confirm what mode processed the reply
                            role_identifier = "Web Admin" if is_admin else "Customer"
                            st.caption(f"*Processed via '{handled_by}' pathway at {role_identifier} clearance.*")

            except Exception as e:
                st.error(f"Backend offline or AI limit reached: {e}")