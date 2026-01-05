import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import io
import zipfile

# ======================================
# 설정
# ======================================
DELIM = "-"  # 파일명 구분자

# ======================================
# 유틸 함수
# ======================================
def safe_text(s: str) -> str:
    """파일/폴더명에 쓰기 위험한 문자 제거"""
    if s is None:
        return ""
    s = str(s).strip()
    for ch in r'<>:"/\|?*':
        s = s.replace(ch, "")
    s = s.replace("-", "_").replace(".", "_")
    return " ".join(s.split())

def load_image_bytes(file):
    """이미지를 JPEG bytes로 변환 (EXIF 회전 반영, HEIC 지원)"""
    ext = file.name.split(".")[-1].lower()

    if ext in ["heic", "heif"]:
        try:
            import pillow_heif
            heif = pillow_heif.read_heif(file.read())
            img = Image.frombytes(heif.mode, heif.size, heif.data)
        except Exception:
            st.error("HEIC/HEIF 변환 실패 (pillow-heif 필요)")
            return None
    else:
        img = Image.open(file)

    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()

# ======================================
# 교량 목록 로드
# ======================================
csv_url = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"
df = pd.read_csv(csv_url)
bridges = df["name"].dropna().unique().tolist()

# ======================================
# 페이지 선택 (상단)
# ======================================
page = st.radio(
    "페이지 선택",
    ["① 사진 파일명 생성 (현장)", "② 사진 선택 → 폴더 분류 ZIP"],
    horizontal=True
)

st.markdown("---")

# ======================================
# 위치 라디오 공통 정의
# ======================================
LOCATION_OPTIONS = [
    "A1", "A2",
    "P1", "P2", "P3", "P4", "P5",
    "P6", "P7", "P8", "P9", "P10", "P11",
    "S1", "S2", "S3", "S4", "S5",
    "S6", "S7", "S8", "S9", "S10", "S11"
]

# ======================================
# ① 1페이지: 파일명 생성 & 개별 저장
# ======================================
if page.startswith("①"):

    st.header("📷 사진 파일명 생성 (개별 저장)")

    bridge = st.selectbox("교량", bridges)
    direction = st.selectbox("방향", ["순천", "영암"])

    location = st.radio(
        "위치",
        LOCATION_OPTIONS,
        horizontal=True
    )

    desc = st.text_input("내용 (선택) 예: 균열, 박리, 누수")

    uploaded = st.file_uploader(
        "사진 선택 (1장씩)",
        type=["jpg", "jpeg", "png", "heic", "heif"]
    )

    if uploaded and bridge and location:
        data = load_image_bytes(uploaded)

        if data:
            parts = [
                safe_text(bridge),
                safe_text(direction),
                safe_text(location)
            ]
            if desc:
                parts.append(safe_text(desc))

            filename = DELIM.join(parts) + ".jpg"

            st.download_button(
                "📥 사진 저장",
                data=data,
                file_name=filename,
                mime="image/jpeg"
            )

            st.success(f"저장 파일명: {filename}")

    st.info(
        "✔ 이 페이지는 사진을 누적 저장하지 않습니다.\n"
        "✔ 현장에서는 파일명만 정확히 만들어 바로 휴대폰에 저장하세요."
    )

# ======================================
# ② 2페이지: 선택 → 폴더 분류 → ZIP
# ======================================
else:

    st.header("📦 사진 선택 → 폴더 분류 → ZIP 생성")

    uploaded_files = st.file_uploader(
        "분류할 사진 선택 (여러 장)",
        type=["jpg"],
        accept_multiple_files=True
    )

    make_folders = st.checkbox(
        "교량/방향/위치 폴더로 분류",
        value=True
    )

    if uploaded_files:
        selected = st.multiselect(
            "ZIP에 포함할 사진 선택",
            uploaded_files,
            default=uploaded_files,
            format_func=lambda x: x.name
        )

        if selected and st.button("📦 ZIP 생성"):
            zip_buf = io.BytesIO()

            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in selected:
                    base = f.name.replace(".jpg", "")
                    parts = base.split(DELIM)

                    if make_folders and len(parts) >= 3:
                        arcname = f"{parts[0]}/{parts[1]}/{parts[2]}/{f.name}"
                    else:
                        arcname = f.name

                    zf.writestr(arcname, f.read())

            zip_buf.seek(0)

            st.download_button(
                "📥 ZIP 다운로드",
                data=zip_buf,
                file_name="점검사진.zip",
                mime="application/zip"
            )

    st.info(
        "✔ 이 페이지는 선택한 순간에만 메모리를 사용합니다.\n"
        "✔ 새로고침해도 휴대폰에 저장된 사진은 영향을 받지 않습니다."
    )
