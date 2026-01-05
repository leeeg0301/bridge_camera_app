import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import io
import zipfile
from pathlib import Path
import uuid

# ======================================
# 설정
# ======================================
CSV_URL = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"

# 앱이 실행되는 컴퓨터(로컬/서버)에 저장될 루트 폴더
STORE_ROOT = Path("./_store")
STORE_ROOT.mkdir(parents=True, exist_ok=True)

# ======================================
# 유틸
# ======================================
def safe_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    for ch in r'<>:"/\|?*':
        s = s.replace(ch, "")
    # 폴더명 안전 처리
    s = s.replace("/", "_").replace("\\", "_")
    s = " ".join(s.split())
    return s

def unique_path(path: Path) -> Path:
    """중복 파일명 방지: (2)(3)..."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    i = 2
    while True:
        p = path.with_name(f"{stem}({i}){suffix}")
        if not p.exists():
            return p
        i += 1

def load_image_as_jpeg_bytes(file) -> bytes | None:
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
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()

def list_sessions() -> list[str]:
    sessions = []
    for p in STORE_ROOT.iterdir():
        if p.is_dir():
            sessions.append(p.name)
    sessions.sort(reverse=True)
    return sessions

def list_all_files(folder: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png"}
    files = []
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return sorted(files)

# ======================================
# 세션 초기화
# ======================================
if "session_id" not in st.session_state:
    st.session_state["session_id"] = uuid.uuid4().hex[:8]

# ======================================
# 교량 목록 로드
# ======================================
df = pd.read_csv(CSV_URL)
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
st.title("📷 점검사진 자동 저장 & 폴더분류 ZIP (교량/방향/위치)")

st.caption(f"현재 세션ID: {st.session_state['session_id']}  |  저장루트: {STORE_ROOT.resolve()}")

tab1, tab2 = st.tabs(["1) 사진 저장", "2) ZIP 생성(세션 선택)"])

# --------------------------------------
# 1) 사진 저장
# --------------------------------------
with tab1:
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

    uploaded = st.file_uploader(
        "사진 선택 (여러 장 가능)",
        type=["jpg","jpeg","png","heic","heif"],
        accept_multiple_files=True
    )

    if st.button("➕ 사진 저장(교량/방향/위치 폴더에 바로 저장)"):
        if not (uploaded and bridge):
            st.warning("사진 / 교량은 필수입니다.")
        else:
            bridge_s = safe_text(bridge)
            direction_s = safe_text(direction)
            location_s = safe_text(location)

            # ✅ 저장 경로: 세션/raw/교량/방향/위치/
            session_dir = STORE_ROOT / st.session_state["session_id"] / "raw"
            save_dir = session_dir / bridge_s / direction_s / location_s
            save_dir.mkdir(parents=True, exist_ok=True)

            saved = 0
            for file in uploaded:
                data = load_image_as_jpeg_bytes(file)
                if data is None:
                    continue

                # 파일명은 짧게 uuid (중복 걱정 없이)
                out_path = save_dir / f"{uuid.uuid4().hex}.jpg"
                out_path.write_bytes(data)
                saved += 1

            st.success(f"저장 완료: {saved}장  |  저장 위치: {save_dir.as_posix()}")

    # 현재 세션 파일 개수 보여주기
    session_raw = STORE_ROOT / st.session_state["session_id"] / "raw"
    if session_raw.exists():
        files = list_all_files(session_raw)
        st.write(f"현재 세션 누적 저장: {len(files)}장")
        if len(files) > 0:
            st.caption("※ 파일 미리보기는 성능을 위해 생략(원하면 상위 9개만 미리보기로 추가 가능).")

    st.markdown("---")
    if st.button("🆕 새 세션 시작(기존 저장 유지)"):
        st.session_state["session_id"] = uuid.uuid4().hex[:8]
        st.rerun()

# --------------------------------------
# 2) ZIP 생성(세션 선택)
# --------------------------------------
with tab2:
    sessions = list_sessions()
    if not sessions:
        st.info("저장된 세션이 없습니다. 먼저 '사진 저장'에서 사진을 저장하세요.")
    else:
        selected_session = st.selectbox("세션 선택", sessions, index=0)
        raw_dir = STORE_ROOT / selected_session / "raw"

        if not raw_dir.exists():
            st.warning("선택한 세션에 raw 폴더가 없습니다.")
        else:
            files = list_all_files(raw_dir)
            st.write(f"세션 '{selected_session}' 저장 사진: {len(files)}장")

            if st.button("📦 ZIP 만들기 (교량/방향/위치 구조 유지)"):
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fp in files:
                        # raw_dir 기준 상대경로를 그대로 ZIP에 넣으면
                        # 교량/방향/위치/... 구조가 유지됨
                        arcname = fp.relative_to(raw_dir).as_posix()
                        zf.write(fp, arcname=arcname)

                zip_buf.seek(0)
                st.session_state["zip_ready"] = zip_buf
                st.success("ZIP 생성 완료! 아래에서 다운로드하세요.")

            if "zip_ready" in st.session_state and st.session_state["zip_ready"] is not None:
                st.download_button(
                    "⬇️ ZIP 다운로드",
                    data=st.session_state["zip_ready"],
                    file_name=f"{selected_session}_점검사진.zip",
                    mime="application/zip"
                )

st.markdown("---")
if st.button("🔄 앱 상태 초기화(저장파일 유지)"):
    st.session_state.clear()
    st.rerun()
