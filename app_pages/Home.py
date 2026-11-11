import base64
import hashlib

import streamlit as st
from openai import OpenAI, OpenAIError


@st.cache_data(show_spinner=False)
def get_response(_client: OpenAI, api_key_fingerprint: str, question: str) -> str:
	response = _client.responses.create(
		model="gpt-6-luna",
		input=question,
	)
	return response.output_text


st.title("OpenAI 질문 앱")
api_key_fingerprint = st.session_state.get("openai_api_key_fingerprint", "")
question = st.text_area("질문을 입력하세요")

if st.button("질문하기", type="primary"):
	if "openai_client" not in st.session_state:
		st.session_state.pop("submitted_question", None)
		st.session_state.pop("submitted_api_key_fingerprint", None)
		st.error("사이드바에 OpenAI API Key를 입력하세요.")
	elif not question.strip():
		st.session_state.pop("submitted_question", None)
		st.session_state.pop("submitted_api_key_fingerprint", None)
		st.error("질문을 입력하세요.")
	else:
		st.session_state["submitted_question"] = question
		st.session_state["submitted_api_key_fingerprint"] = api_key_fingerprint

submitted_question = st.session_state.get("submitted_question")
if submitted_question:
	if "openai_client" not in st.session_state:
		st.info("응답을 보려면 사이드바에 OpenAI API Key를 입력하세요.")
	elif st.session_state.get("submitted_api_key_fingerprint") != api_key_fingerprint:
		st.info("API Key가 변경되었습니다. 질문을 다시 제출하세요.")
	else:
		try:
			answer = get_response(
				st.session_state["openai_client"],
				api_key_fingerprint,
				submitted_question,
			)
			st.subheader("응답")
			st.write(answer)
		except OpenAIError as error:
			st.error(f"OpenAI API 요청 실패: {error}")

st.divider()
st.header("이미지 생성")
image_prompt = st.text_area("이미지 프롬프트", key="image_prompt")

if st.button("이미지 생성", key="generate_image"):
	if "openai_client" not in st.session_state:
		st.error("사이드바에 OpenAI API Key를 입력하세요.")
	elif not image_prompt.strip():
		st.error("이미지 프롬프트를 입력하세요.")
	else:
		try:
			with st.spinner("이미지를 생성하고 있습니다..."):
				image = st.session_state["openai_client"].images.generate(
					model="gpt-image-2.6-flare",
					prompt=image_prompt,
				)
				image_bytes = base64.b64decode(image.data[0].b64_json)
			st.session_state["generated_image"] = image_bytes
			st.session_state["generated_image_api_key_fingerprint"] = api_key_fingerprint
		except OpenAIError as error:
			st.error(f"이미지 생성 요청에 실패했습니다: {error}")

generated_image = st.session_state.get("generated_image")
if (
	generated_image
	and st.session_state.get("generated_image_api_key_fingerprint") == api_key_fingerprint
):
	st.image(generated_image)