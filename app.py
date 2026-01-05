import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import io
import zipfile
from datetime import date

# ======================================
# 설정
# ======================================
DELIM = "-"  # 하이픈 구분자
DEFAULT_DATE = date.today().strftime("%Y%m%d")

# ======================================
# 유틸
# ======================================
def safe_text(s: str) -> str:
    """파일/폴더명에 쓰기 위험한 문자 제거 + 구분자 충돌 최소화"""
    if s is None:
        return ""
    s = str(s).strip()
    # 윈도우 금지문자 제거
    for ch in r'<>:"/\|?*':
        s = s.replace(ch, "")
    # 구분자인 '-'가 내용에 들어오면 파싱 애매해질 수 있어 '_'로 치환
    s = s.replace("-", "_")
    # 점(.)은 구분자/확장자와 헷갈릴 수 있으니 '_'로 치환(원하면 제거 가능)
    s = s.replace(".", "_")
    # 연속 공백 정리
    s = " ".join(s.split())
    return s

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

    # 스마트폰 회전정보 반영
    img = ImageOps.exif_transpose(img)

    # JPEG 저장을 위해 RGB로
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

if "seq" not in st.session_state:
    st.session_state["seq"] = 0  # 전체 사진 일련번호

# ======================================
# 교량 목록 로드 (GitHub raw)
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
st.title("📷 점검사진 파일명 생성기 (하이픈 + ZIP 폴더 정리)")

search = st.text_input("교량 검색")
bridge_list = advanced_filter(search, bridges)
bridge = st.selectbox("교량 선택", bridge_list)

direction = st.selectbox("방향", ["순천", "영암"])

insp_date = st.text_input("점검일 (YYYYMMDD)", value=DEFAULT_DATE)

location = st.radio(
    "위치",
    ["A1","A2",
     "P1","P2","P3","P4","P5","P6","P7","P8","P9","P10","P11",
     "S1","S2","S3","S4","S5","S6","S7","S8","S9","S10","S11"],
    horizontal=True
)

desc = st.text_input("내용 (예: 균열, 박리, 누수)")

# ZIP 안에 폴더 구조로 저장할지
make_folders = st.checkbox("ZIP 내부를 폴더 구조로 저장", value=True)
st.caption("폴더 예시: 교량/점검일/방향/위치/파일.jpg")

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
        bridge_s = safe_text(bridge)
        direction_s = safe_text(direction)
        location_s = safe_text(location)
        desc_s = safe_text(desc)
        date_s = safe_text(insp_date)

        added = 0
        for file in uploaded:
            data = load_image_bytes(file)
            if data is None:
                continue

            st.session_state["seq"] += 1
            seq = f"{st.session_state['seq']:03d}"

            # ✅ 파일명: 하이픈 구분자 (점(.) 사용 X, 확장자만 .jpg)
            filename = f"{bridge_s}{DELIM}{direction_s}{DELIM}{location_s}{DELIM}{desc_s}{DELIM}{seq}.jpg"

            # ✅ ZIP 내부 경로(폴더 구조)
            if make_folders:
                arcname = f"{bridge_s}/{date_s}/{direction_s}/{location_s}/{filename}"
            else:
                arcname = filename

            st.session_state["saved_images"].append((arcname, data))
            st.session_state["saved_names"].append(arcname)
            added += 1

        st.success(f"추가 완료: {added}장 / 현재 저장된 사진 수: {len(st.session_state['saved_names'])}장")

# ======================================
# 저장 예정 파일명 표시
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

    # zip 이름도 안전하게
    zip_bridge = safe_text(bridge) if bridge else "점검사진"
    zip_date = safe_text(insp_date) if insp_date else DEFAULT_DATE

    st.download_button(
        "📦 ZIP 전체 저장",
        data=zip_buf,
        file_name=f"{zip_bridge}_{zip_date}_점검사진.zip",
        mime="application/zip"
    )

# ======================================
# 전체 초기화
# ======================================
st.markdown("---")
if st.button("🔄 전체 초기화"):
    st.session_state.clear()
    st.rerun()
