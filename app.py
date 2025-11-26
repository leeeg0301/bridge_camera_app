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
# 고도화 검색(정확도 우선)
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
st.title("자동 교량사진 ")

search_key = st.text_input("교량 검색 (예: ㅂ / 부 / 부산 / 산 / 천)")
filtered = advanced_filter(search_key, bridges)
bridge = st.selectbox("교량 선택", filtered)

direction = st.selectbox("방향", ["순천", "영암", " "])
location = st.selectbox("위치", ["A1","A2","P1","P2","P3","P4","P5","P6","P7","P8","P9","P10","P11"])

# desc는 key로 session_state에 저장 → 초기화 안함
desc = st.text_input("내용 입력", key="desc")

# --------------------------------------
# 파일 업로드 (카메라/앨범)
# --------------------------------------
uploaded = st.file_uploader(
    "📷 사진 촬영 또는 선택",
    type=["jpg","jpeg","png","heic","heif"],
    key="uploaded_file"
)

# --------------------------------------
# 저장 처리
# --------------------------------------
if uploaded and bridge and desc:

    ext = uploaded.name.split(".")[-1].lower()

    # HEIC 변환
    if ext in ["heic","heif"]:
        import pillow_heif
        image_data = uploaded.read()
        heif_file = pillow_heif.read_heif(image_data)
        img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data)
    else:
        img = Image.open(uploaded)

    # JPG 변환
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=95)
    img_bytes.seek(0)

    filename = f"{bridge}.{direction}.{location}.{desc}.jpg"

    # 저장 버튼
    saved = st.download_button(
        label=f"📥 저장: {filename}",
        data=img_bytes,
        file_name=filename,
        mime="image/jpeg",
        key="download_btn"
    )

    # 저장 후 업로드만 초기화 + 리프레시
    if saved:
        st.session_state['uploaded_file'] = None   # 파일만 초기화
        st.experimental_rerun()



