import streamlit as st
from openai import OpenAIError


VECTOR_STORE_ID_KEY = "chatpdf_vector_store_id"
FILE_ID_KEY = "chatpdf_file_id"
MESSAGES_KEY = "chatpdf_messages"


def clear_chat():
	st.session_state[MESSAGES_KEY] = []


def stream_text_deltas(stream):
	for event in stream:
		if event.type == "response.output_text.delta":
			yield event.delta


def delete_partial_upload(client, vector_store_id=None, file_id=None):
	if vector_store_id:
		try:
			client.vector_stores.delete(vector_store_id=vector_store_id)
		except OpenAIError:
			pass
	if file_id:
		try:
			client.files.delete(file_id=file_id)
		except OpenAIError:
			pass


st.title("ChatPDF")
client = st.session_state.get("openai_client")
api_key_fingerprint = st.session_state.get("openai_api_key_fingerprint", "")
vector_store_id = st.session_state.get(VECTOR_STORE_ID_KEY)

if not vector_store_id:
	st.markdown("[예시 PDF 다운로드](https://arxiv.org/pdf/1706.03762)")
	uploaded_file = st.file_uploader(
		"PDF 파일 하나를 업로드하세요",
		type=["pdf"],
		accept_multiple_files=False,
		key="chatpdf_upload",
	)
	if uploaded_file is None:
		st.info("PDF를 업로드하면 문서에 질문할 수 있습니다.")
		st.stop()
	if client is None:
		st.error("사이드바에 OpenAI API Key를 입력하세요.")
		st.stop()

	vector_store = None
	openai_file = None
	try:
		with st.spinner("PDF를 업로드하고 검색 인덱스를 만드는 중입니다..."):
			vector_store = client.vector_stores.create(
				name=f"ChatPDF: {uploaded_file.name}"
			)
			openai_file = client.files.create(
				file=(uploaded_file.name, uploaded_file.getvalue()),
				purpose="assistants",
			)
			vector_store_file = client.vector_stores.files.create_and_poll(
				file_id=openai_file.id,
				vector_store_id=vector_store.id,
			)
		if vector_store_file.status != "completed":
			raise RuntimeError(f"PDF 인덱싱 상태: {vector_store_file.status}")
		st.session_state[VECTOR_STORE_ID_KEY] = vector_store.id
		st.session_state[FILE_ID_KEY] = openai_file.id
		st.session_state["chatpdf_file_name"] = uploaded_file.name
		st.session_state["chatpdf_api_key_fingerprint"] = api_key_fingerprint
		st.session_state[MESSAGES_KEY] = []
		st.rerun()
	except (OpenAIError, RuntimeError) as error:
		delete_partial_upload(
			client,
			vector_store_id=vector_store.id if vector_store else None,
			file_id=openai_file.id if openai_file else None,
		)
		st.error(f"PDF 처리에 실패했습니다: {error}")
		st.stop()

vector_store_id = st.session_state.get(VECTOR_STORE_ID_KEY)
if vector_store_id:
	file_name = st.session_state.get("chatpdf_file_name", "업로드한 PDF")
	store_key_fingerprint = st.session_state.get("chatpdf_api_key_fingerprint", "")
	client_matches_store = client is not None and store_key_fingerprint == api_key_fingerprint
	st.caption(f"문서: {file_name}")

	clear_column, leave_column = st.columns(2)
	with clear_column:
		st.button("Clear", on_click=clear_chat, use_container_width=True)
	with leave_column:
		leave = st.button(
			"Leave",
			disabled=not client_matches_store,
			use_container_width=True,
		)

	if not client_matches_store:
		st.warning("이 PDF를 업로드할 때 사용한 API Key를 입력해야 대화를 이어가거나 나갈 수 있습니다.")
	elif leave:
		try:
			with st.spinner("Vector store를 삭제하고 있습니다..."):
				client.vector_stores.delete(vector_store_id=vector_store_id)
			file_id = st.session_state.get(FILE_ID_KEY)
			if file_id:
				try:
					client.files.delete(file_id=file_id)
				except OpenAIError as error:
					st.warning(f"Vector store는 삭제했지만 업로드 파일 정리는 실패했습니다: {error}")
		except OpenAIError as error:
			st.error(f"Vector store를 삭제하지 못했습니다: {error}")
		else:
			for key in (
				VECTOR_STORE_ID_KEY,
				FILE_ID_KEY,
				"chatpdf_file_name",
				"chatpdf_api_key_fingerprint",
				MESSAGES_KEY,
				"chatpdf_upload",
			):
				st.session_state.pop(key, None)
			st.rerun()

	for message in st.session_state.get(MESSAGES_KEY, []):
		with st.chat_message(message["role"]):
			st.markdown(message["content"])

	if prompt := st.chat_input("PDF에 대해 질문하세요"):
		if not client_matches_store:
			st.error("사이드바에 올바른 OpenAI API Key를 입력하세요.")
		else:
			st.session_state[MESSAGES_KEY].append({"role": "user", "content": prompt})
			with st.chat_message("user"):
				st.markdown(prompt)
			try:
				with st.chat_message("assistant"):
					stream = client.responses.create(
						model="gpt-6-luna",
						instructions=(
							"Answer questions using the uploaded PDF and file search. "
							"If the PDF does not contain the answer, say so and do not guess."
						),
						input=st.session_state[MESSAGES_KEY],
						tools=[
							{"type": "file_search", "vector_store_ids": [vector_store_id]}
						],
						stream=True,
					)
					answer = st.write_stream(stream_text_deltas(stream))
				st.session_state[MESSAGES_KEY].append(
					{"role": "assistant", "content": answer}
				)
			except OpenAIError as error:
				st.error(f"PDF 질문 처리에 실패했습니다: {error}")