# ui/app.py
import streamlit as st
import requests
import uuid

# Backend Address
API_URL = "http://localhost:8005/api/v1/chat"

st.set_page_config(page_title="AI Customer Support (Modular)", layout="centered")
st.title("🛡️ Multi-Tiered AI Support")

# Maintain Session State
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display entire history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# User prompt
if prompt := st.chat_input("Describe your issue..."):
    # Render user prompt locally immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Trigger backend orchestrator via REST protocol
    with st.spinner("Analyzing intent and routing..."):
        try:
            resp = requests.post(
                API_URL, 
                json={"thread_id": st.session_state.thread_id, "message": prompt}
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
                        st.caption(f"*Processed via '{handled_by}' pathway.*")

        except Exception as e:
            st.error(f"Backend offline or LLM limit reached: {e}")