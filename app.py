import streamlit as st
import pandas as pd
import unicodedata

# -----------------------
# 1) GitHub CSV 읽기
# -----------------------
csv_url = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"

df = pd.read_csv(csv_url)

# name 컬럼에서 교량 리스트 추출
bridges = df['name'].dropna().unique().tolist()


# -----------------------
# 한글 초성 검색 함수
# -----------------------
def get_choseong(text):
    CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
    result = ""
    for ch in text:
        if '가' <= ch <= '힣':
            code = ord(ch) - ord('가')
            cho = code // (21 * 28)
            result += CHO[cho]
        else:
            result += ch
    return result


# -----------------------
# Streamlit UI
# -----------------------
st.title("📸 교량 점검 사진 자동 파일명 생성기")

search_key = st.text_input("교량 검색 (초성 가능: 'ㅂ' → 부춘2교)")

if search_key:
    filtered = [b for b in bridges if get_choseong(b).startswith(search_key)]
else:
    filtered = bridges

bridge = st.selectbox("교량 선택", filtered)

direction = st.selectbox("방향", ["순천", "영암"])
location = st.selectbox("위치", ["A1","A2","P1","P2","P3","P4"])
desc = st.text_input("내용 (예: 균열, 박리, 파손)")

# -----------------------
# 카메라 입력
# -----------------------
photo = st.camera_input("사진 촬영")

if photo and bridge and desc:
    file_name = f"{bridge}.{direction}.{location}.{desc}.jpg"

    st.download_button(
        "📥 사진 저장",
        data=photo.getvalue(),
        file_name=file_name,
        mime="image/jpeg"
    )

    st.success(f"파일명 생성됨: **{file_name}**")
