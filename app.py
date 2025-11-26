import streamlit as st
import pandas as pd
from PIL import Image
import io

# --------------------------------------
# 세션 상태 초기화 (업로더용 key)
# --------------------------------------
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

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
# UI 시작
# --------------------------------------
st.title("📸 교량 점검 사진 자동 파일명 생성기 (안정 버전)")

# 🔹 교량 검색
search_key = st.text_input("교량 검색 (예: ㅂ / 부 / 부산)", key="search_box")
filtered = advanced_filter(search_key, bridges)

# 🔹 교량 선택
bridge = st.selectbox("교량 선택", filtered, key="bridge_select")

# 🔹 방향
direction = st.selectbox("방향 선택", ["순천", "영암"], key="dir_select")

# 🔹 위치 (P6~P11 포함, radio = 입력 불가)
location_list = [
    "A1", "A2",
    "P1", "P2", "P3", "P4", "P5",
    "P6", "P7", "P8", "P9", "P10", "P11"
]

location = st.radio("위치 선택", location_list, key="loc_select")

# 🔹 내용 desc (텍스트 입력 유지)
desc = st.text_input("내용 입력", key="desc_input")


# --------------------------------------
# 파일 업로드 (업로더 key를 session_state로 관리)
# --------------------------------------
uploaded = st.file_uploader(
    "📷 사진 촬영 또는 선택",
    type=["jpg", "jpeg", "png", "heic", "heif"],
    key=f"upload_file_{st.session_state['uploader_key']}"
)


# --------------------------------------
# 파일 처리 및 저장
# --------------------------------------
if uploaded and bridge and desc:

    ext = uploaded.name.split(".")[-1].lower()

    # HEIC 변환
    if ext in ["heic", "heif"]:
        try:
            import pillow_heif
        except:
            st.error("⚠ HEIC 변환을 위해 requirements.txt에 'pillow-heif'를 추가해야 합니다.")
            st.stop()

        image_data = uploaded.read()
        heif_file = pillow_heif.read_heif(image_data)
        img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data)

    else:
        img = Image.open(uploaded)

    # JPG 변환
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=95)
    img_bytes.seek(0)

    # 파일명 만들기
    filename = f"{bridge}.{direction}.{location}.{desc}.jpg"

    # 다운로드 버튼
    saved = st.download_button(
        label=f"📥 저장: {filename}",
        data=img_bytes,
        file_name=filename,
        mime="image/jpeg",
        key="download_btn"
    )

    # 저장 후: 업로더만 초기화 (desc/선택값 유지)
    if saved:
        st.session_state["uploader_key"] += 1  # 업로더 key 변경 → 위젯 새로 생성
        st.experimental_rerun()
