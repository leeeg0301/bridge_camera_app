import streamlit as st
import pandas as pd
from PIL import Image
import io
import zipfile

# ======================================
# 세션 초기화
# ======================================
if "saved_images" not in st.session_state:
    st.session_state["saved_images"] = []

if "saved_names" not in st.session_state:
    st.session_state["saved_names"] = []

# ======================================
# 교량 목록 로드
# ======================================
csv_url = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"
df = pd.read_csv(csv_url)
bridges = df["name"].dropna().unique().tolist()

# ======================================
# 초성 검색
# ======================================
CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]

def get_choseong(text):
    result = ""
    for ch in text:
        if '가' <= ch <= '힣':
            code = ord(ch) - ord('가')
            result += CHO[code // (21 * 28)]
        else:
            result += ch
    return result

def advanced_filter(keyword, bridges):
    if not keyword:
        return bridges

    k_cho = get_choseong(keyword)
    exact, starts, contains, chosung = [], [], [], []

    for b in bridges:
        b_cho = get_choseong(b)
        if b == keyword:
            exact.append(b)
        elif b.startswith(keyword):
            starts.append(b)
        elif keyword in b:
            contains.append(b)
        elif k_cho in b_cho:
            chosung.append(b)

    return exact + starts + contains + chosung

# ======================================
# UI
# ======================================
st.title("📷 점검사진 파일명 생성기")

search = st.text_input("교량 검색")
bridge_list = advanced_filter(search, bridges)
bridge = st.selectbox("교량 선택", bridge_list)

direction = st.selectbox("방향", ["순천", "영암"])

location = st.radio(
    "위치",
    ["A1","A2",
     "P1","P2","P3","P4","P5","P6","P7","P8","P9","P10","P11",
     "S1","S2","S3","S4","S5","S6","S7","S8","S9","S10","S11"],
    horizontal=True
)

desc = st.text_input("내용 (예: 균열, 박리, 누수)")

uploaded = st.file_uploader(
    "사진 선택 (여러 장 가능)",
    type=["jpg","jpeg","png","heic","heif"],
    accept_multiple_files=True
)

# ======================================
# 사진 저장
# ======================================
if st.button("➕ 사진 추가"):

    if not (uploaded and bridge and desc):
        st.warning("사진 / 교량 / 내용은 필수입니다.")
    else:
        for file in uploaded:
            ext = file.name.split(".")[-1].lower()

            if ext in ["heic", "heif"]:
                try:
                    import pillow_heif
                    heif = pillow_heif.read_heif(file.read())
                    img = Image.frombytes(heif.mode, heif.size, heif.data)
                except:
                    st.error("HEIC 변환 실패 (pillow-heif 필요)")
                    continue
            else:
                img = Image.open(file)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=95)
            buf.seek(0)

            filename = f"{bridge}.{direction}.{location}.{desc}.jpg"

            # 세션 저장
            st.session_state["saved_images"].append(
                (filename, buf.getvalue())
            )
            st.session_state["saved_names"].append(filename)

        st.success(f"현재 저장된 사진 수: {len(st.session_state['saved_names'])}장")

# ======================================
# 저장 예정 파일명 표시
# ======================================
if st.session_state["saved_names"]:
    st.markdown("### 📄 저장 예정 파일명")
    st.caption("ZIP 파일 안에 아래 이름으로 저장됩니다.")

    for name in st.session_state["saved_names"]:
        st.text(name)

# ======================================
# ZIP 다운로드
# ======================================
if st.session_state["saved_images"]:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in st.session_state["saved_images"]:
            zf.writestr(name, data)

    zip_buf.seek(0)

    st.download_button(
        "📦 ZIP 전체 저장",
        data=zip_buf,
        file_name=f"{bridge}_점검사진.zip",
        mime="application/zip"
    )

# ======================================
# 전체 초기화
# ======================================
st.markdown("---")
if st.button("🔄 전체 초기화"):
    st.session_state.clear()
    st.rerun()
