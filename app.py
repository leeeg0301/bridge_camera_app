import streamlit as st
import pandas as pd
from PIL import Image
import io

csv_url = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"
df = pd.read_csv(csv_url)
bridges = df["name"].dropna().unique().tolist()

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

def advanced_filter(keyword, bridges):
    if not keyword:
        return bridges

    keyword_chosung = get_choseong(keyword)
    exact, starts, contains, chosung_match = [], [], [], []

    for name in bridges:
        name_chosung = get_choseong(name)

        if name == keyword:
            exact.append(name)
        elif name.startswith(keyword):
            starts.append(name)
        elif keyword in name:
            contains.append(name)
        elif keyword_chosung in name_chosung:
            chosung_match.append(name)

    return exact + starts + contains + chosung_match


st.title("📸 교량 점검 자동 이름첨부 앱")

search_key = st.text_input("교량 검색 (예: ㅂ / 부 / 부산 / 산 / 천)")
filtered = advanced_filter(search_key, bridges)
bridge = st.selectbox("교량 선택", filtered)

direction = st.selectbox("방향", ["순천", "영암"])
location = st.selectbox("위치", ["A1","A2","P1","P2","P3","P4","P5","P6","P7","P8","P9","P10"])
desc = st.text_input("내용 입력")

uploaded = st.file_uploader(
    "📷 사진 촬영 또는 선택",
    type=["jpg","jpeg","png","heic","heif"]
)

if uploaded and bridge and desc:

    ext = uploaded.name.split(".")[-1].lower()

    if ext in ["heic","heif"]:
        import pillow_heif
        image_data = uploaded.read()
        heif_file = pillow_heif.read_heif(image_data)
        img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data)
    else:
        img = Image.open(uploaded)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=95)
    img_bytes.seek(0)

    filename = f"{bridge}.{direction}.{location}.{desc}.jpg"

    st.download_button(
        label=f"📥 저장: {filename}",
        data=img_bytes,
        file_name=filename,
        mime="image/jpeg"
    )

    st.success(f"✔ 저장할 파일명: {filename}")
