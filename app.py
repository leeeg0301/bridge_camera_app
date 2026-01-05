import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import io
import zipfile

# ======================================
# 설정
# ======================================
DELIM = "-"  # 하이픈 구분자

# ======================================
# 유틸
# ======================================
def safe_text(s: str) -> str:
    """파일/폴더명에 쓰기 위험한 문자 제거 + 구분자 충돌 최소화"""
    if s is None:
        return ""
    s = str(s).strip()
    for ch in r'<>:"/\|?*':
        s = s.replace(ch, "")
    # 구분자(-) 충돌 최소화
    s = s.replace("-", "_")
    # 점(.)은 확장자와 헷갈릴 수 있어 치환
    s = s.replace(".", "_")
    s = " ".join(s.split())
    return s

def unique_name(name: str, used: set) -> str:
    """같은 이름이 이미 있으면 (2),(3)... 붙여 유니크하게"""
    if name not in used:
        used.add(name)
        return name
    base, ext = name.rsplit(".", 1)
    i = 2
    while f"{base}({i}).{ext}" in used:
        i += 1
    new = f"{base}({i}).{ext}"
    used.add(new)
    return new

def load_image_bytes(file) -> bytes | None:
    """업로드 파일을 JPEG bytes로 변환(HEIC/HEIF 포함), EXIF 회전 반영"""
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

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()

# ======================================
# 세션 초기화
# ======================================
if "saved_images" not in st.session_state:
    # (arcname, bytes)
    st.session_state["saved_images"] = []

if "saved_names" not in st.session_state:
    st.session_state["saved_names"] = []

if "used_names" not in st.session_state:
    st.session_state["used_names"] = set()

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
st.title("점검사진 분류 자동화")

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

# ✅ 내용 선택(안 적어도 됨)
desc = st.text_input("내용 (선택)  예: 균열, 박리, 누수")

# ✅ ZIP 내부 폴더 분류 옵션
make_folders = st.checkbox("ZIP 내부를 폴더별로 분류해서 저장", value=True)
st.caption("폴더 구조: 교량/방향/위치/ (원하면 교량/위치/ 로 더 줄일 수 있음)")

uploaded = st.file_uploader(
    "사진 선택 (여러 장 가능)",
    type=["jpg","jpeg","png","heic","heif"],
    accept_multiple_files=True
)

# ======================================
# 사진 저장
# ======================================
if st.button("➕ 사진 추가"):
    if not (uploaded and bridge):
        st.warning("사진 / 교량은 필수입니다.")
    else:
        bridge_s = safe_text(bridge)
        direction_s = safe_text(direction)
        location_s = safe_text(location)
        desc_s = safe_text(desc)

        added = 0
        for file in uploaded:
            data = load_image_bytes(file)
            if data is None:
                continue

            # 파일명: 교량-방향-위치(-내용).jpg  (내용 있으면 포함)
            parts = [bridge_s, direction_s, location_s]
            if desc_s:
                parts.append(desc_s)

            filename = DELIM.join(parts) + ".jpg"
            filename = unique_name(filename, st.session_state["used_names"])

            # ✅ ZIP 내부 경로(폴더 분류)
            if make_folders:
                arcname = f"{bridge_s}/{direction_s}/{location_s}/{filename}"
            else:
                arcname = filename

            st.session_state["saved_images"].append((arcname, data))
            st.session_state["saved_names"].append(arcname)
            added += 1

        st.success(f"추가 완료: {added}장 / 현재 저장된 사진 수: {len(st.session_state['saved_names'])}장")

# ======================================
# 저장 예정 표시
# ======================================
if st.session_state["saved_names"]:
    st.markdown("### 📄 저장 예정 경로/파일명")
    st.caption("ZIP 파일 안에 아래 경로로 저장됩니다.")
    for name in st.session_state["saved_names"]:
        st.text(name)

# ======================================
# ZIP 다운로드
# ======================================
if st.session_state["saved_images"]:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, data in st.session_state["saved_images"]:
            zf.writestr(arcname, data)

    zip_buf.seek(0)

    zip_bridge = safe_text(bridge) if bridge else "점검사진"

    st.download_button(
        "📦 ZIP 전체 저장",
        data=zip_buf,
        file_name=f"{zip_bridge}_점검사진.zip",
        mime="application/zip"
    )

# ======================================
# 전체 초기화
# ======================================
st.markdown("---")
if st.button("🔄 전체 초기화"):
    st.session_state.clear()
    st.rerun()

