import hashlib

import streamlit as st
from openai import OpenAI


st.set_page_config(page_title="국립부경대학교 도서관 챗봇")

with st.sidebar:
	api_key = st.text_input("OpenAI API Key", type="password", key="openai_api_key")

api_key_fingerprint = hashlib.sha256(api_key.encode()).hexdigest() if api_key else ""
if api_key.strip():
	if st.session_state.get("openai_api_key_fingerprint") != api_key_fingerprint:
		st.session_state["openai_client"] = OpenAI(api_key=api_key)
		st.session_state["openai_api_key_fingerprint"] = api_key_fingerprint
else:
	st.session_state.pop("openai_client", None)
	st.session_state.pop("openai_api_key_fingerprint", None)

page = st.navigation(
	[
		st.Page("app_pages/Home.py", title="Home", icon=":material/home:"),
		st.Page("app_pages/Chat.py", title="Chat", icon=":material/chat:"),
		st.Page("app_pages/ChatPDF.py", title="ChatPDF", icon=":material/picture_as_pdf:"),
		st.Page(
			"app_pages/Chatbot.py",
			title="도서관 챗봇",
			icon=":material/local_library:",
		),
	]
)
page.run()