import streamlit as st
import requests
import base64
import json
from PIL import Image
import io
import datetime
from openai import OpenAI
import os

def image_to_base64(image):
    # PIL Image를 바이트로 변환
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def init_gpt_api():
    OpenAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=OpenAI_API_KEY)
    return client

def calculate_cost(completion):
    # 토큰 수 계산
    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    
    # 비용 계산 (USD)
    prompt_cost = (prompt_tokens / 1000) * 0.0025
    completion_cost = (completion_tokens / 1000) * 0.01
    
    total_cost = prompt_cost + completion_cost
    
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "prompt_cost": prompt_cost,
        "completion_cost": completion_cost,
        "total_cost": total_cost
    }

def process_arc_image(client, image_base64):
    completion = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
                Extract the following details from the given Alien Registration Card in the image. 
                If any data is obscured or not visible, please return 'masked' for that field.
                The 5 information items are:
                1. 외국인등록번호 (Registration No.): 13 digits, 6 digits for the year, 7 digits for the serial number, separated by '-'.
                2. 성명 (Name): Written in English.
                3. 국가/지역 (Country/Region): Written in English.
                4. 체류자격 (Status): Form of "Explanation(VISA Type)". Explanation is written in Korean. VISA Type is composed of letter - number.
                5. 발급일자 (Iuuse Date): Form of "YYYY.MM.DD"
                Return the extracted information in the following JSON format:
                {
                    "Registration No.": "",
                    "Name": "",
                    "Country/Region": "",
                    "Status": "",
                    "Issue Date": "",
                }
                """,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please extract the 5 information items from the Alien Registration Card: Registration No., Name, Country/Region, Status, Issue Date.",
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                ],
            },
        ],
    )
    result = json.loads(completion.choices[0].message.content)
    cost_info = calculate_cost(completion)
    return result, cost_info

def main():
    st.title("외국인등록증(ARC) OCR 데모")
    st.write("외국인등록증 이미지를 업로드하면 정보를 추출합니다.")

    uploaded_file = st.file_uploader("외국인등록증 이미지를 업로드해주세요", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        # 이미지 표시
        image = Image.open(uploaded_file)
        st.image(image, caption="업로드된 이미지", use_container_width=True)

        # OCR 처리 시작
        if st.button("정보 추출 시작"):
            with st.spinner("처리 중..."):
                start_time = datetime.datetime.now()
                
                # 이미지를 base64로 변환
                image_base64 = image_to_base64(image)
                
                # GPT API 초기화 및 처리
                client = init_gpt_api()
                result, cost_info = process_arc_image(client, image_base64)
                
                end_time = datetime.datetime.now()
                processing_time = (end_time - start_time).total_seconds()

                # 결과 표시
                st.subheader("추출 결과")
                st.json(result)
                
                # 처리 시간 표시
                st.subheader("처리 시간")
                st.write(f"{processing_time:.2f}초")

                # 비용 정보 표시
                st.subheader("비용 정보")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("토큰 사용량:")
                    st.write(f"- 입력 토큰: {cost_info['prompt_tokens']:,}개")
                    st.write(f"- 출력 토큰: {cost_info['completion_tokens']:,}개")
                
                with col2:
                    st.write("비용 상세 (USD):")
                    st.write(f"- 입력 비용: ${cost_info['prompt_cost']:.4f}")
                    st.write(f"- 출력 비용: ${cost_info['completion_cost']:.4f}")
                
                st.write(f"총 비용: ${cost_info['total_cost']:.4f} (약 ₩{cost_info['total_cost']*1447:.0f})")

if __name__ == "__main__":
    main()