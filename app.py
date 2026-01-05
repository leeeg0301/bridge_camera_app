import streamlit as st
import pandas as pd
from PIL import ImageOps
import io
import zipfile
from datetime import date

st.set_page_config(page_title="교량 점검사진 ZIP 생성기", layout="wide")

# =========================
# 설정
# =========================
DELIM = "-"  # 하이픈 구분자
DEFAULT_DATE = date.today().strftime("%Y%m%d")  # YYYYMMDD

def safe(s: str) -> str:
    """윈도우 금지문자 제거 + 구분자 충돌 최소화"""
    if s is None:
        return ""
    s = str(s).strip()
    # 파일명 금지문자 제거
    for ch in r'<>:"/\|?*':
        s = s.replace(ch, "")
    # 구분자(-)가 데이터에 있으면 파싱 애매해져서 '_'로 치환
    s = s.replace("-", "_")
    # 공백 정리
    s = " ".join(s.split())
    return s

@st.cache_data
def load_bridge_list(csv_url: str) -> pd.DataFrame:
    return pd.read_csv(csv_url)

st.title("교량 점검사진 자동 정리 (하이픈 구분자 + ZIP 폴더 생성)")

# =========================
# CSV 로드
# =========================
with st.sidebar:
    st.header("교량 목록(CSV) 설정")
    csv_url = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"
    df = pd.read_csv(csv_url)
    bridges = df["name"].dropna().unique().tolist()

try:
    df = load_bridge_list(csv_url)
except Exception:
    st.error("CSV URL 로드 실패. raw URL과 공개여부를 확인해 주세요.")
    st.stop()

# 컬럼 자동 추정
def pick_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

branch_col = pick_col(df, ["지사", "branch", "본부", "관리단"])
route_col  = pick_col(df, ["노선", "route", "국도", "도로명"])
bridge_col = pick_col(df, ["교량명", "bridge", "교량", "시설명", "명칭"])

if bridge_col is None:
    st.error(f"CSV에 교량명 컬럼이 필요합니다. 현재 컬럼: {list(df.columns)}")
    st.stop()

def make_label(row):
    parts = []
    if branch_col: parts.append(str(row[branch_col]))
    if route_col:  parts.append(str(row[route_col]))
    parts.append(str(row[bridge_col]))
    return " / ".join(parts)

labels = df.apply(make_label, axis=1).tolist()

# =========================
# UI
# =========================
left, right = st.columns([1, 1])

with left:
    st.subheader("1) 점검 정보 선택")

    selected_label = st.selectbox("교량 선택", labels)
    selected_row = df.iloc[labels.index(selected_label)]

    branch = safe(selected_row[branch_col]) if branch_col else "지사미상"
    route  = safe(selected_row[route_col]) if route_col else "노선미상"
    bridge = safe(selected_row[bridge_col])

    comp = safe(st.text_input("부재(예: 거더/교각/받침)", value="거더"))
    spot = safe(st.text_input("세부위치(예: G1-하부플랜지 / P2-전면)", value="G1하부플랜지"))
    insp_date = safe(st.text_input("점검일(YYYYMMDD)", value=DEFAULT_DATE))

    st.markdown("**파일명 예시 (하이픈 구분자)**")
    example_name = f"{bridge}{DELIM}{comp}{DELIM}{spot}{DELIM}{insp_date}{DELIM}001.jpg"
    st.code(example_name)

with right:
    st.subheader("2) 사진 업로드 → ZIP 생성")
    uploaded = st.file_uploader(
        "점검사진 업로드 (여러 장 가능)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    make_folders = st.checkbox("ZIP 내부를 폴더 구조로 만들기", value=True)
    st.caption("폴더 구조 예: 지사/노선/교량/점검일/부재/파일명.jpg")

# =========================
# ZIP 생성
# =========================
if uploaded:
    st.write(f"업로드된 파일: {len(uploaded)}개")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, uf in enumerate(uploaded, start=1):
            raw = uf.read()

            ext = uf.name.split(".")[-1].lower()
            if ext not in ["jpg", "jpeg", "png"]:
                ext = "jpg"

            seq = f"{idx:03d}"
            filename = f"{bridge}{DELIM}{comp}{DELIM}{spot}{DELIM}{insp_date}{DELIM}{seq}.{ext}"

            if make_folders:
                arcname = f"{branch}/{route}/{bridge}/{insp_date}/{comp}/{filename}"
            else:
                arcname = filename

            zf.writestr(arcname, raw)

    zip_buffer.seek(0)
    out_name = f"{bridge}_inspection_{insp_date}.zip"

    st.download_button(
        label="📦 ZIP 다운로드",
        data=zip_buffer,
        file_name=out_name,
        mime="application/zip"
    )
else:
    st.info("사진을 업로드하면 ZIP 다운로드 버튼이 생깁니다.")

