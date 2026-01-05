import streamlit as st
from pathlib import Path
import zipfile
import io

st.set_page_config(page_title="점검사진 폴더분류 ZIP", layout="wide")

IMG_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}  # 이미 JPEG로 저장해두면 jpg만으로도 OK
DELIM = "-"  # 파일명 구분자

def safe_part(s: str) -> str:
    # ZIP 내부 폴더명 안전화
    s = (s or "").strip()
    for ch in r'<>:"/\|?*':
        s = s.replace(ch, "_")
    s = " ".join(s.split())
    return s

def parse_parts(filename: str):
    """
    기대 파일명 예:
      교량-방향-위치.jpg
      교량-방향-위치(2).jpg
    """
    stem = Path(filename).stem  # 확장자 제거
    parts = stem.split(DELIM)
    # 최소 3개 필요: 교량, 방향, 위치
    if len(parts) < 3:
        return None
    bridge = safe_part(parts[0])
    direction = safe_part(parts[1])
    location = safe_part(parts[2])
    return bridge, direction, location

def list_images(folder: Path):
    files = []
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            files.append(p)
    return sorted(files)

st.title("📦 점검사진 파일명 기반 폴더분류 → ZIP 생성")
st.caption("전제: 사진이 이미 '내 폴더'에 저장되어 있고, 파일명이 '교량-방향-위치.jpg' 규칙을 따른다.")

base_dir_str = st.text_input("분류할 사진 폴더 경로", value="")
st.caption("예) Windows: C:\\Users\\me\\Pictures\\inspection   |   Mac: /Users/me/Pictures/inspection")

only_top = st.checkbox("하위 폴더까지 포함(rglob)", value=True)

if st.button("🔍 폴더 스캔"):
    if not base_dir_str.strip():
        st.error("폴더 경로를 입력해 주세요.")
        st.stop()

    base_dir = Path(base_dir_str)
    if not base_dir.exists() or not base_dir.is_dir():
        st.error("유효한 폴더 경로가 아닙니다.")
        st.stop()

    if only_top:
        files = list_images(base_dir)
    else:
        files = [p for p in base_dir.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS]

    st.session_state["scanned_dir"] = str(base_dir)
    st.session_state["files"] = [str(p) for p in files]

if "files" in st.session_state:
    files = [Path(p) for p in st.session_state["files"]]
    st.write(f"스캔 결과: {len(files)}개")

    # 미리 분류 통계
    ok, bad = 0, 0
    sample_bad = []
    for p in files:
        parts = parse_parts(p.name)
        if parts is None:
            bad += 1
            if len(sample_bad) < 5:
                sample_bad.append(p.name)
        else:
            ok += 1

    col1, col2 = st.columns(2)
    col1.metric("규칙 일치 파일", ok)
    col2.metric("미분류(규칙 불일치)", bad)

    if sample_bad:
        st.warning("아래 파일은 '교량-방향-위치.jpg' 형식이 아니라서 _미분류로 들어갑니다:")
        for n in sample_bad:
            st.text(n)

    st.markdown("---")
    st.subheader("ZIP 생성")

    zip_name = st.text_input("ZIP 파일명", value="점검사진_폴더분류.zip")
    include_unclassified = st.checkbox("규칙 불일치 파일도 _미분류 폴더로 포함", value=True)

    # ZIP 내부 폴더 구조 선택 (네가 원한: 교량/방향/위치)
    st.caption("ZIP 내부 구조: 교량/방향/위치/원본파일명")

    if st.button("🧩 폴더분류 실행 → ZIP 만들기"):
        if not files:
            st.error("파일이 없습니다.")
            st.stop()

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in files:
                parts = parse_parts(fp.name)
                if parts is None:
                    if not include_unclassified:
                        continue
                    arcname = f"_미분류/{fp.name}"
                else:
                    bridge, direction, location = parts
                    arcname = f"{bridge}/{direction}/{location}/{fp.name}"

                # 디스크 파일을 바로 ZIP에 넣음(메모리에 사진 bytes 안 쌓음)
                zf.write(fp, arcname=arcname)

        zip_buf.seek(0)
        st.success("ZIP 생성 완료!")
        st.download_button(
            "⬇️ ZIP 다운로드",
            data=zip_buf,
            file_name=zip_name,
            mime="application/zip"
        )

st.markdown("---")
st.caption("※ 이 앱은 사진을 '업로드 저장'하지 않고, 네 폴더의 파일을 읽어서 ZIP만 생성합니다(로컬 실행 기준).")
