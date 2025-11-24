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
# 한글 초성 추출 함수
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
# 고도화 검색 (정확도 우선 정렬)
# --------------------------------------
def advanced_filter(keyword, bridges):
    if not keyword:
        return bridges

    keyword_chosung = get_choseong(keyword)

    exact = []
    starts = []
    contains = []
    chosung_match = []

    for name in bridges:
        name_chosung = get_choseong(name)

        if name == keyword:  # 완전일치
            exact.append(name)
            continue

        if name.startswith(keyword):  # 시작 동일
            starts.append(name)
            continue

        if keyword in name:  # 중간 포함
            contains.append(name)
            continue

        if keyword_chosung in name_chosung:  # 초성 매칭
            chosung_match.append(name)

    return exact + starts + contains + chosung_match


# --------------------------------------
# Streamlit UI
# --------------------------------------
st.title("📸 교량 점검 사진 자동 파일명 생성기 (고화질/아이폰_HEIC 지원)")

search_key = st.text_input("교량 검색 (예: ㅂ / 부 / 부산 / 산 / 천)")
filtered = advanced_filter(search_key, bridges)

bridge = st.selectbox("교량 선택", filtered)

direction = st.selectbox("방향", ["순천", "영암"])
location = st.selectbox("위치 선택", ["A1", "A2", "P1", "P2", "P3", "P4"])
desc = st.text_input("내용 입력 (예: 균열, 박리, 파손)")


# --------------------------------------
# 모바일 후면카메라 열기
# --------------------------------------
st.markdown("""
### 📷 촬영 버튼 (고화질 기본 카메라 실행)
<input type="file" id="cameraInput" accept="image/*" capture="environment">
""", unsafe_allow_html=True)


# --------------------------------------
# 파일 업로드 (아이폰 HEIC 포함)
# --------------------------------------
uploaded = st.file_uploader("📁 촬영된 사진 선택", type=["jpg", "jpeg", "png", "heic", "heif"])

# --------------------------------------
# 이미지 변환 및 파일명 저장
# --------------------------------------
if uploaded and bridge and desc:

    original_ext = uploaded.name.split(".")[-1].lower()

    # HEIC → JPG 변환
    if original_ext in ["heic", "heif"]:
        try:
            import pillow_heif
            heif_file = pillow_heif.read_heif(uploaded.read())
            img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data)
        except:
            st.error("⚠ HEIC 사진 변환 오류 — requirements.txt에 pillow-heif 추가 필요")
            st.stop()
    else:
        img = Image.open(uploaded)

    # JPG 변환
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=95)
    img_bytes.seek(0)

    filename = f"{bridge}.{direction}.{location}.{desc}.jpg"

    st.download_button(
        label=f"📥 저장: {filename}",
        data=img_bytes,
        file_name=filename,
        mime="image/jpeg",
    )

    st.success(f"✔ 생성된 파일명: **{filename}**")
