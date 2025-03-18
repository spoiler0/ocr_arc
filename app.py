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

def process_arc_front(client, image_base64):
    completion = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
                Extract the following details from the given Alien Registration Card (Front side) in the image. 
                If any data is obscured or not visible, please return 'masked' for that field.
                The 5 information items are:
                1. 외국인등록번호 (Registration No.): 13 digits, 6 digits for the year, 7 digits for the serial number, separated by '-'.
                2. 성명 (Name): Written in English.
                3. 국가/지역 (Country/Region): Written in English.
                4. 체류자격 (Status): Form of "Explanation(VISA Type)". Explanation is written in Korean. VISA Type is composed of letter - number.
                5. 발급일자 (Issue Date): Form of "YYYY.MM.DD"
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

def process_arc_back(client, image_base64):
    completion = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
                Extract the following details from the given Alien Registration Card (Back side) in the image. 
                If any data is obscured or not visible, please return 'masked' for that field.
                The 5 information items are:
                1. 일련번호: 10 digits, separated by '-'. Format is like X-XXX-XXX-XXXX. Don't miss any digit and make sure the every digit is correct.
                2. 체류기간 (Duration of Stay): Tabular format. There are 3 columns: 허가일자, 만료일자, 확인. 허가일자 and 만료일자 are written in "YYYY.MM.DD" format. 확인 is written in Korean. Get every row of the table.
                    Don't miss any row of the table.
                    Make sure the every digit is correct and the format is correct.
                Return the extracted information in the following JSON format:
                {
                    "Serial No.": "",
                    "Duration of Stay": [
                        {
                            "Start Date": "",
                            "End Date": "",
                            "Check": ""
                        },
                        ...
                    ]
                }
                """,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please extract the 5 information items from the Alien Registration Card back side.",
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                ],
            },
        ],
    )
    result = json.loads(completion.choices[0].message.content)
    cost_info = calculate_cost(completion)
    return result, cost_info

def display_results(result, cost_info, processing_time, side=""):
    # 결과 표시
    st.subheader(f"{side} 추출 결과")
    st.json(result)
    
    # 처리 시간 표시
    st.write(f"처리 시간: {processing_time:.2f}초")

    # 비용 정보 표시
    st.write("비용 정보:")
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

def main():
    st.title("외국인등록증(ARC) OCR 데모")
    st.write("외국인등록증 앞면과 뒷면 이미지를 업로드하면 정보를 추출합니다.")

    col1, col2 = st.columns(2)
    
    with col1:
        front_file = st.file_uploader("외국인등록증 앞면 이미지를 업로드해주세요", type=["jpg", "jpeg", "png"])
        if front_file is not None:
            front_image = Image.open(front_file)
            st.image(front_image, caption="앞면 이미지", use_container_width=True)

    with col2:
        back_file = st.file_uploader("외국인등록증 뒷면 이미지를 업로드해주세요", type=["jpg", "jpeg", "png"])
        if back_file is not None:
            back_image = Image.open(back_file)
            st.image(back_image, caption="뒷면 이미지", use_container_width=True)

    # OCR 처리 시작
    if st.button("정보 추출 시작"):
        client = init_gpt_api()
        total_cost = 0
        
        if front_file is not None:
            with st.spinner("앞면 처리 중..."):
                start_time = datetime.datetime.now()
                front_image_base64 = image_to_base64(front_image)
                front_result, front_cost_info = process_arc_front(client, front_image_base64)
                processing_time = (datetime.datetime.now() - start_time).total_seconds()
                display_results(front_result, front_cost_info, processing_time, "앞면")
                total_cost += front_cost_info['total_cost']

        if back_file is not None:
            with st.spinner("뒷면 처리 중..."):
                start_time = datetime.datetime.now()
                back_image_base64 = image_to_base64(back_image)
                back_result, back_cost_info = process_arc_back(client, back_image_base64)
                processing_time = (datetime.datetime.now() - start_time).total_seconds()
                display_results(back_result, back_cost_info, processing_time, "뒷면")
                total_cost += back_cost_info['total_cost']

        if front_file is not None or back_file is not None:
            st.subheader("총 비용")
            st.write(f"전체 처리 비용: ${total_cost:.4f} (약 ₩{total_cost*1447:.0f})")

if __name__ == "__main__":
    main()
