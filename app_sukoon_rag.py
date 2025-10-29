import streamlit as st
from datetime import datetime
from sukoon_rag_pinecone_gemini import handle_user_input

# --------------------------
# 🕊️ Sukoon App Config
# --------------------------
st.set_page_config(page_title="🕊️ Sukoon AI", page_icon="🕊️", layout="wide")

# --------------------------
# 💾 Initialize Session State
# --------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Hello, I'm **Sukoon AI** — your calm and caring companion. How are you feeling today?"}
    ]

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# --------------------------
# 🖼️ Page Layout (Swapped Columns)
# --------------------------
col1, col2 = st.columns([1, 3], gap="medium")  # ✅ sidebar (col1) now on LEFT

# --------------------------
# 📚 LEFT COLUMN — Saved Chats
# --------------------------
with col1:
    st.header("🗂️ Saved Chats")

    # Save + reset for new chat
    if st.button("🆕 New Chat"):
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        st.session_state.chat_history.append({
            "timestamp": timestamp,
            "conversation": st.session_state.messages.copy()
        })
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello again 🌿 I'm Sukoon AI — ready for a fresh conversation. What's on your mind?"}
        ]
        st.rerun()

    # Show saved chats
    if st.session_state.chat_history:
        for chat in reversed(st.session_state.chat_history):
            with st.expander(f"🕓 {chat['timestamp']}"):
                for msg in chat["conversation"]:
                    role_emoji = "🧍‍♂️" if msg["role"] == "user" else "🕊️"
                    st.markdown(f"**{role_emoji} {msg['role'].capitalize()}:** {msg['content']}")
    else:
        st.info("No previous chats yet. Start one to see it here!")

# --------------------------
# 💬 RIGHT COLUMN — Current Chat
# --------------------------
with col2:
    # 🎨 Style
    st.markdown(
        """
        <style>
        body { background-color: #f5f7fa; }
        .sukoon-bubble {
            padding: 12px 16px;
            border-radius: 12px;
            margin: 6px 0;
            max-width: 80%;
            line-height: 1.5;
        }
        .user {
            background-color: #DCF8C6;
            text-align: right;
            align-self: flex-end;
        }
        .assistant {
            background-color: #E8EAF6;
            text-align: left;
            align-self: flex-start;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Header
    st.title("🕊️ Sukoon AI — Your Calm Companion")
    st.caption("A gentle, empathetic chat powered by Gemini + Pinecone 💙")

    # Display messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"<div class='sukoon-bubble user'>🧍‍♂️ You: {msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='sukoon-bubble assistant'>🕊️ Sukoon AI: {msg['content']}</div>", unsafe_allow_html=True)

    # Input
    user_input = st.chat_input("How are you feeling?")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.spinner("Sukoon AI is thinking... 🕊️"):
            try:
                reply = handle_user_input(user_input)
            except Exception as e:
                reply = f"⚠️ Sorry, something went wrong: {e}"
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    st.caption("Made with 💙 by Sukoon AI — Supporting mental well-being through calm technology.")
