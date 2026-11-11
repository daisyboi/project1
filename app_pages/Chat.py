import streamlit as st
from openai import OpenAIError


def clear_messages():
	st.session_state.messages = []


def stream_text_deltas(stream):
	for event in stream:
		if event.type == "response.output_text.delta":
			yield event.delta


st.title("Chat")

if "messages" not in st.session_state:
	st.session_state.messages = []

st.button("Clear", on_click=clear_messages)

for message in st.session_state.messages:
	with st.chat_message(message["role"]):
		st.markdown(message["content"])

if prompt := st.chat_input("메시지를 입력하세요"):
	client = st.session_state.get("openai_client")
	if client is None:
		st.error("사이드바에 OpenAI API Key를 입력하세요.")
	else:
		st.session_state.messages.append({"role": "user", "content": prompt})
		with st.chat_message("user"):
			st.markdown(prompt)
		try:
			with st.chat_message("assistant"):
				stream = client.responses.create(
					model="gpt-6-luna",
					input=st.session_state.messages,
					stream=True,
				)
				response = st.write_stream(stream_text_deltas(stream))
			st.session_state.messages.append(
				{"role": "assistant", "content": response}
			)
		except OpenAIError as error:
			st.error(f"OpenAI API 요청 실패: {error}")
