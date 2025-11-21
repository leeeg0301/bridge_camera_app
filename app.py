Python 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.
pip install streamlit
SyntaxError: invalid syntax
!pip install streamlit
SyntaxError: invalid syntax
import streamlit as st
import unicodedata
import os

# 교량 리스트
bridges = ["부춘1교", "부춘2교", "순천교", "영암대교", "백양1교", "백양2교"]

# 초성 추출 함수
def get_choseong(text):
    CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
    result = ""
    for ch in text:
        if '가' <= ch <= '힣':
            code = ord(ch) - ord('가')
            cho = code // (21 * 28)
...             result += CHO[cho]
...         else:
...             result += ch
...     return result
... 
... # UI
... st.title("📱 구조물 점검 사진 자동 파일명 생성기 (카메라 버전)")
... 
... search_key = st.text_input("교량 이름 검색 (예: 'ㅂ' → 부춘2교 자동 추천)")
... 
... if search_key:
...     filtered = [b for b in bridges if get_choseong(b).startswith(search_key)]
... else:
...     filtered = bridges
... 
... bridge = st.selectbox("교량 선택", filtered)
... 
... direction = st.selectbox("방향", ["순천", "영암"])
... location = st.selectbox("위치", ["A1", "A2", "P1", "P2", "P3", "P4"])
... desc = st.text_input("내용", placeholder="예: 균열, 백태, 파손 등")
... 
... # --------------------------
... # 📸 카메라로 사진 찍기
... # --------------------------
... photo = st.camera_input("사진 촬영")
... 
... if photo and bridge and desc:
...     ext = ".jpg"
...     file_name = f"{bridge}.{direction}.{location}.{desc}{ext}"
... 
...     st.download_button(
...         "📥 촬영한 사진 저장",
...         data=photo.getvalue(),
...         file_name=file_name,
...         mime="image/jpeg"
...     )
... 
...     st.success(f"파일명 생성됨: **{file_name}**")
... else:
