import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import io
import zipfile

st.set_page_config(layout="wide")

# ======================================
# 설정
# ======================================
DELIM = "-"

# ======================================
# 유틸
# ======================================
def safe_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    for ch in r'<>:"/\|?*':
        s = s.replace(ch, "")
    s = s.replace("-", "_").replace(".", "_")
    return " ".join(s.split())

def load_image(uploaded):
    img = Image.open(uploaded)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf.getvalue()

# ======================================
# 교량 목록
# ======================================
csv_url = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"
try:
    df = pd.read_csv(csv_url)
    bridges = df["name"].dropna().unique().tolist()
except:
    bridges = ["교량A", "교량B"]

LOCATION_OPTIONS = [
    "A1","A2",
    "P1","P2","P3","P4","P5","P6","P7","P8","P9","P10","P11",
    "S1","S2","S3","S4","S5","S6","S7","S8","S9","S10","S11"
]

# ======================================
# 탭 GUI
# ======================================
tab1, tab2 = st.tabs(["📷 1페이지 : 사진 저장", "📦 2페이지 : 사진 분류 / ZIP"])

# ======================================
# 1페이지 : 파일명 생성
# ======================================
with tab1:
    st.header("📷 사진 파일명 생성")

    bridge = st.selectbox("교량", bridges)
    direction = st.selectbox("방향", ["순천", "영암"])
    location = st.radio("위치", LOCATION_OPTIONS, horizontal=True)
    desc = st.text_input("내용 (선택)", placeholder="예: 균열, 박리, 누수")

    uploaded = st.file_uploader(
        "사진 선택 (1장)",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded:
        img_bytes = load_image(uploaded)

        parts = [safe_text(bridge), safe_text(direction), safe_text(location)]
        if desc:
            parts.append(safe_text(desc))

        filename = DELIM.join(parts) + ".jpg"

        st.download_button(
            "📥 파일명 적용해서 저장",
            data=img_bytes,
            file_name=filename,
            mime="image/jpeg"
        )

        st.success(f"저장될 파일명: {filename}")

    st.info("✔ 현장에서는 여기서 저장 → 나중에 2페이지에서 한꺼번에 분류")

# ======================================
# 2페이지 : 분류 & ZIP
# ======================================
with tab2:
    st.header("📦 사진 선택 → 폴더 분류 → ZIP")

    uploaded_files = st.file_uploader(
        "사진 여러 장 선택",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    make_folders = st.checkbox(
        "교량 / 방향 / 위치 기준으로 폴더 분류",
        value=True
    )

    if uploaded_files:
        st.markdown("### 📄 ZIP에 포함할 파일 선택")

        for i, f in enumerate(uploaded_files):
            if f"chk{i}" not in st.session_state:
                st.session_state[f"chk{i}"] = True

            st.checkbox(f.name, key=f"chk{i}")

        st.markdown("---")

        if st.button("📦 ZIP 생성"):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for i, f in enumerate(uploaded_files):
                    if st.session_state.get(f"chk{i}", False):
                        fname = f.name
                        base = fname.rsplit(".", 1)[0]
                        parts = base.split(DELIM)

                        if make_folders and len(parts) >= 3:
                            arcname = f"{parts[0]}/{parts[1]}/{parts[2]}/{fname}"
                        else:
                            arcname = fname

                        zf.writestr(arcname, f.read())
                        f.seek(0)

            zip_buf.seek(0)
            st.download_button(
                "⬇ ZIP 다운로드",
                data=zip_buf,
                file_name="점검사진_분류.zip",
                mime="application/zip"
            )

    else:
        st.info("사진을 업로드하면 분류 리스트가 표시됩니다.")
