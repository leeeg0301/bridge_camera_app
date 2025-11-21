import streamlit as st
import pandas as pd

# --------------------------------------
# 1) GitHub CSV 불러오기
# --------------------------------------
csv_url = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"
df = pd.read_csv(csv_url)

# 교량 리스트
bridges = df["name"].dropna().unique().tolist()


# --------------------------------------
# 2) 한글 초성 추출 함수
# --------------------------------------
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


# --------------------------------------
# 3) 통합 검색 함수 (초성 + 부분 + 중간)
# --------------------------------------
def filter_bridges(keyword, bridges):
    if not keyword:
        return bridges
    
    keyword_chosung = get_choseong(keyword)

    filtered = []
    for name in bridges:
        name_chosung = get_choseong(name)

        cond1 = keyword_chosung in name_chosung    # 초성 검색
        cond2 = keyword in name                    # 부분 문자열 검색
        cond3 = keyword in name                    # 중간 검색 (같은 로직)

        if cond1 or cond2 or cond3:
            filtered.append(name)

    return filtered


# --------------------------------------
# 4) Streamlit UI
# --------------------------------------
st.title("📸 교량 점검 사진 자동 파일명 생성기")

search_key = st.text_input("교량 검색 (예: ㅂ / 부 / 부산 / 산 / 천)")

filtered_bridges = filter_bridges(search_key, bridges)
bridge = st.selectbox("교량 선택", filtered_bridges)

direction = st.selectbox("방향", ["순천", "영암"])
location = st.selectbox("위치 (A1/A2/P1~P4)", ["A1", "A2", "P1", "P2", "P3", "P4"])
desc = st.text_input("내용 (예: 균열, 박리, 파손 등 입력)")


# --------------------------------------
# 5) 카메라로 사진 촬영
# --------------------------------------
photo = st.camera_input("📷 사진 촬영")


# --------------------------------------
# 6) 파일명 생성 및 다운로드
# --------------------------------------
if photo and bridge and desc:
    filename = f"{bridge}.{direction}.{location}.{desc}.jpg"

    st.download_button(
        label=f"📥 {filename} 저장",
        data=photo.getvalue(),
        file_name=filename,
        mime="image/jpeg"
    )

    st.success(f"✔ 생성된 파일명: **{filename}**")
else:
    st.info("사진을 찍으면 자동으로 파일명 생성 버튼이 표시됩니다.")
