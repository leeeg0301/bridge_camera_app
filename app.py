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
DELIM = "-"  # 파일명 구분자(파일명 구성에만 사용, 폴더는 / 로 구분)
CSV_URL = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"

# 앱이 실행되는 곳(로컬/서버)에 저장될 폴더
BASE_STORE = Path("./_photo_store")  # 같은 폴더 아래 생성됨

# ======================================
# 유틸
# ======================================
def safe_text(s: str) -> str:
    """파일/폴더명 안전 처리"""
    if s is None:
        return ""
    s = str(s).strip()
    for ch in r'<>:"/\|?*':
        s = s.replace(ch, "")
    s = s.replace("-", "_")   # 구분자 충돌 방지
    s = s.replace(".", "_")   # 확장자 혼동 방지
    s = " ".join(s.split())
    return s

def unique_name(name: str, used: set) -> str:
    """중복 파일명 방지: (2),(3)..."""
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
    img.save(buf, format="JPEG", quality=92)  # 품질/용량 타협(원하면 95로)
    return buf.getvalue()

def ensure_session_dirs(session_id: str) -> Path:
    """세션별 raw 저장 폴더 생성"""
    raw_dir = BASE_STORE / session_id / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir

# ======================================
# 세션 초기화
# ======================================
if "session_id" not in st.session_state:
    st.session_state["session_id"] = uuid.uuid4().hex[:8]

if "records" not in st.session_state:
    # 각 원소: {raw_path, bridge, direction, location, desc}
    st.session_state["records"] = []

if "used_zip_paths" not in st.session_state:
    # ZIP 내부의 arcname 중복 방지용
    st.session_state["used_zip_paths"] = set()

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
st.title("📷 점검사진 자동정리 (저장 후, 마지막에 폴더분류 실행)")

st.caption(f"세션ID: {st.session_state['session_id']}  |  저장폴더: {BASE_STORE.resolve()}")

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

desc = st.text_input("내용 (선택)  예: 균열, 박리, 누수")

uploaded = st.file_uploader(
    "사진 선택 (여러 장 가능)",
    type=["jpg","jpeg","png","heic","heif"],
    accept_multiple_files=True
)

# ======================================
# 사진 저장(즉시 디스크에 저장)
# ======================================
if st.button("➕ 사진 추가 (즉시 저장)"):
    if not (uploaded and bridge):
        st.warning("사진 / 교량은 필수입니다.")
    else:
        raw_dir = ensure_session_dirs(st.session_state["session_id"])

        bridge_s = safe_text(bridge)
        direction_s = safe_text(direction)
        location_s = safe_text(location)
        desc_s = safe_text(desc)

        added = 0
        for file in uploaded:
            data = load_image_as_jpeg_bytes(file)
            if data is None:
                continue

            # 원본 보관용(raw) 파일명은 충돌 없게 uuid 사용
            raw_name = f"{uuid.uuid4().hex}.jpg"
            raw_path = raw_dir / raw_name
            raw_path.write_bytes(data)

            st.session_state["records"].append({
                "raw_path": str(raw_path),
                "bridge": bridge_s,
                "direction": direction_s,
                "location": location_s,
                "desc": desc_s
            })
            added += 1

        st.success(f"저장 완료: {added}장 / 누적: {len(st.session_state['records'])}장")

# ======================================
# 저장 목록 표시
# ======================================
if st.session_state["records"]:
    st.markdown("### ✅ 저장된 사진 목록(메타데이터)")
    st.caption("사진은 이미 디스크에 저장되어 있고, 아래는 분류용 정보입니다.")
    for i, r in enumerate(st.session_state["records"], start=1):
        d = r["desc"] if r["desc"] else "(내용없음)"
        st.text(f"{i:03d}  {r['bridge']} / {r['location']} / {d}  -  {r['direction']}")

# ======================================
# 폴더분류 실행 → ZIP 생성
# ======================================
st.markdown("---")
st.subheader("📦 폴더분류 실행 (교량/위치/내용) → ZIP 생성")

folder_order_hint = "ZIP 폴더 구조: 교량/위치/내용/파일.jpg  (내용 없으면 '내용없음')"
st.caption(folder_order_hint)

if st.button("🧩 폴더분류 실행"):
    if not st.session_state["records"]:
        st.warning("저장된 사진이 없습니다.")
    else:
        zip_buf = io.BytesIO()
        used = set()  # ZIP 내부 경로 중복 방지(세션 내에서 매번 새로)

        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in st.session_state["records"]:
                bridge_s = r["bridge"]
                direction_s = r["direction"]
                location_s = r["location"]
                desc_s = r["desc"] if r["desc"] else "내용없음"

                # 파일명(뒤 번호 제거 요청 반영)
                # - 파일명에는 '내용'을 빼고, 폴더에 내용이 들어가게 해서 길이 최소화
                # - 중복이면 (2)(3) 자동
                base_filename = f"{bridge_s}{DELIM}{direction_s}{DELIM}{location_s}.jpg"
                filename = unique_name(base_filename, used)

                arcname = f"{bridge_s}/{location_s}/{desc_s}/{filename}"

                raw_path = Path(r["raw_path"])
                if raw_path.exists():
                    zf.write(raw_path, arcname=arcname)
                else:
                    # 원본이 없으면 경고용 텍스트를 남김
                    zf.writestr(f"{bridge_s}/_ERRORS/missing_files.txt",
                                f"Missing: {r['raw_path']}\n")

            # 인덱스(추적성) 같이 넣기
            index_lines = ["bridge,location,desc,direction,zip_path,raw_path"]
            for r in st.session_state["records"]:
                bridge_s = r["bridge"]
                location_s = r["location"]
                desc_s = r["desc"] if r["desc"] else "내용없음"
                direction_s = r["direction"]
                raw_path = r["raw_path"]
                # zip_path는 위에서 중복처리 후 결정되지만, 여기서는 참고용으로 동일 규칙 재구성(대략적)
                index_lines.append(f"{bridge_s},{location_s},{desc_s},{direction_s},(see folders),{raw_path}")
            zf.writestr("_index.csv", "\n".join(index_lines))

        zip_buf.seek(0)
        st.session_state["zip_ready"] = zip_buf
        st.success("폴더분류 및 ZIP 생성 완료! 아래에서 다운로드하세요.")

# ZIP 다운로드 버튼
if "zip_ready" in st.session_state and st.session_state["zip_ready"] is not None:
    # zip 파일명은 현재 선택 교량 기준(세션 전체가 단일 교량이 아닐 수도 있으니 일반명도 가능)
    st.download_button(
        "⬇️ ZIP 다운로드",
        data=st.session_state["zip_ready"],
        file_name="점검사진_폴더분류.zip",
        mime="application/zip"
    )

# ======================================
# 전체 초기화(저장파일 포함)
# ======================================
st.markdown("---")
if st.button("🔄 전체 초기화 (저장파일 삭제)"):
    # 세션 폴더 삭제
    session_dir = BASE_STORE / st.session_state["session_id"]
    try:
        if session_dir.exists():
            for p in session_dir.rglob("*"):
                if p.is_file():
                    p.unlink()
            for p in sorted(session_dir.rglob("*"), reverse=True):
                if p.is_dir():
                    p.rmdir()
            if session_dir.exists():
                session_dir.rmdir()
    except Exception as e:
        st.warning(f"세션 폴더 정리 중 일부 실패: {e}")

    st.session_state.clear()
    st.rerun()
