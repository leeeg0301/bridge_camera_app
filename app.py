import streamlit as st
import pandas as pd
from PIL import Image
import io

# --------------------------------------
# GitHub CSV 불러오기
# --------------------------------------
csv_url = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"
df = pd.read_csv(csv_url)

bridges = df["name"].dropna().unique().tolist()

# --------------------------------------
# 초성 추출
# --------------------------------------
CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]

def get_choseong(text):
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
# 고도화 검색
# --------------------------------------
def advanced_filter(keyword, bridges):
    if not keyword:
        return bridges

    keyword_chosung = get_choseong(keyword)
    exact, starts, contains, chosung = [], [], [], []

    for name in bridges:
        name_chosung = get_choseong(name)

        if name == keyword:
            exact.append(name)
        elif name.startswith(keyword):
            starts.append(name)
        elif keyword in name:
            contains.append(name)
        elif keyword_chosung in name_chosung:
            chosung.append(name)

    return exact + starts + contains + chosung


# --------------------------------------
# UI
# --------------------------------------
st.title("📸 교량 점검 사진 자동 파일명 생성기 (초기화 선택형)")

# 교량 검색
search_key = st.text_input("교량 검색 (예: ㅂ / 부 / 부산)", key="search_box")
filtered = advanced_filter(search_key, bridges)

bridge = st.selectbox("교량 선택", filtered)
direction = st.selectbox("방향", ["순천", "영암"])

# 위치 라디오 선택 (P6~P11 포함)
location = st.radio(
    "위치 선택",
    ["A1", "A2",
     "P1", "P2", "P3", "P4", "P5",
     "P6", "P7", "P8", "P9", "P10", "P11"
    ],horizontal = false
)

# 내용 입력
desc = st.text_input("내용 입력", key="desc_input")

# 파일 업로드 (key 충돌 방지 위해 고정 key 사용 X)
uploaded = st.file_uploader(
    "📷 사진 촬영 또는 선택",
    type=["jpg", "jpeg", "png", "heic", "heif"]
)

# --------------------------------------
# 저장 처리
# --------------------------------------
if uploaded and bridge and desc:

    ext = uploaded.name.split(".")[-1].lower()

    # HEIC 변환
    if ext in ["heic", "heif"]:
        try:
            import pillow_heif
            image_data = uploaded.read()
            heif_file = pillow_heif.read_heif(image_data)
            img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data)
        except:
            st.error("⚠ requirements.txt에 pillow-heif 추가 필요")
            st.stop()
    else:
        img = Image.open(uploaded)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=95)
    img_bytes.seek(0)

    filename = f"{bridge}.{direction}.{location}.{desc}.jpg"

    saved = st.download_button(
        label=f"📥 저장: {filename}",
        data=img_bytes,
        file_name=filename,
        mime="image/jpeg"
    )

    # 저장되면 초기화 여부 질문
    if saved:
        st.success("저장 완료!")

        choice = st.radio(
            "📌 다음 작업을 선택하세요:",
            ("초기화 안함 (계속 촬영)", "초기화하기")
        )

        if choice == "초기화하기":
            st.info("초기화되었습니다! 새로운 사진을 선택하세요.")
            st.experimental_rerun()
