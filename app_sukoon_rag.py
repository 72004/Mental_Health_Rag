import streamlit as st
from sukoon_rag_pinecone_gemini import handle_user_input

# --------------------------
# 🕊️ Sukoon App Config
# --------------------------
st.set_page_config(page_title="🕊️ Sukoon AI", page_icon="🕊️", layout="centered")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Hello, I'm Sukoon AI — your calm and caring companion. How are you feeling today?"}
    ]

# --------------------------
# 🎨 App Header
# --------------------------
st.markdown(
    """
    <style>
    body {
        background-color: #f5f7fa;
    }
    .sukoon-bubble {
        padding: 12px 16px;
        border-radius: 12px;
        margin: 6px 0;
        max-width: 80%;
        line-height: 1.5;
    }
    .user {
        background-color: #DCF8C6;
        align-self: flex-end;
        text-align: right;
    }
    .assistant {
        background-color: #E8EAF6;
        align-self: flex-start;
        text-align: left;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🕊️ Sukoon AI — Your Calm Companion")
st.caption("A gentle, empathetic chat powered by Gemini + Pinecone 💙")

# --------------------------
# 💬 Display Chat History
# --------------------------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"<div class='sukoon-bubble user'>🧍‍♂️ You: {msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='sukoon-bubble assistant'>🕊️ Sukoon AI: {msg['content']}</div>", unsafe_allow_html=True)

# --------------------------
# 🧘 User Input Area
# --------------------------
user_input = st.chat_input("How are you feeling?")

if user_input:
    # Store user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display immediately
    st.markdown(f"<div class='sukoon-bubble user'>🧍‍♂️ You: {user_input}</div>", unsafe_allow_html=True)

    # Generate Sukoon's reply
    with st.spinner("Sukoon AI is thinking... 🕊️"):
        try:
            reply = handle_user_input(user_input)
        except Exception as e:
            reply = f"⚠️ Sorry, something went wrong: {e}"

    # Store and display Sukoon's message
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.markdown(f"<div class='sukoon-bubble assistant'>🕊️ Sukoon AI: {reply}</div>", unsafe_allow_html=True)

# --------------------------
# 🌸 Footer
# --------------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.caption("Made with 💙 by Sukoon AI — Supporting mental well-being through calm technology.")
