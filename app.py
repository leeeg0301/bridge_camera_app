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

def load_image_bytes_from_uploaded(uploaded_file):
    """업로드된 파일을 JPEG bytes로 변환 (EXIF 회전 반영, HEIC 지원)"""
    ext = uploaded_file.name.split(".")[-1].lower()
    try:
        if ext in ["heic", "heif"]:
            import pillow_heif
            heif = pillow_heif.read_heif(uploaded_file.read())
            img = Image.frombytes(heif.mode, heif.size, heif.data)
        else:
            uploaded_file.seek(0)
            img = Image.open(uploaded_file)
    except Exception as e:
        st.error(f"이미지 로드 실패: {e}")
        return None

    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf.getvalue()

def bytes_to_image(data: bytes):
    return Image.open(io.BytesIO(data))

# ======================================
# 교량 목록 로드 (원격 CSV)
# ======================================
csv_url = "https://raw.githubusercontent.com/leeeg0301/bridge_camera_app/main/data.csv"
try:
    df = pd.read_csv(csv_url)
    bridges = df["name"].dropna().unique().tolist()
except Exception:
    bridges = ["교량A", "교량B", "교량C"]

# ======================================
# 위치 라디오 옵션
# ======================================
LOCATION_OPTIONS = [
    "A1", "A2",
    "P1", "P2", "P3", "P4", "P5",
    "P6", "P7", "P8", "P9", "P10", "P11",
    "S1", "S2", "S3", "S4", "S5",
    "S6", "S7", "S8", "S9", "S10", "S11"
]

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
# ① 페이지: 파일명 생성 & 개별 저장 (현장)
# ======================================
if page.startswith("①"):
    st.header("📷 사진 파일명 생성 (개별 저장)")

    bridge = st.selectbox("교량", bridges)
    direction = st.selectbox("방향", ["순천", "영암"])
    location = st.radio("위치", LOCATION_OPTIONS, horizontal=True)
    desc = st.text_input("내용 (선택) 예: 균열, 박리, 누수")

    uploaded = st.file_uploader(
        "사진 선택 (1장씩) — 저장 버튼으로 바로 핸드폰/로컬에 저장",
        type=["jpg", "jpeg", "png", "heic", "heif"]
    )

    if uploaded and bridge and location:
        data = load_image_bytes_from_uploaded(uploaded)
        if data:
            parts = [safe_text(bridge), safe_text(direction), safe_text(location)]
            if desc:
                parts.append(safe_text(desc))
            filename = DELIM.join(parts) + ".jpg"

            st.download_button(
                "📥 사진 저장 (파일명 적용)",
                data=data,
                file_name=filename,
                mime="image/jpeg"
            )
            st.success(f"저장 파일명: {filename}")

    st.info(
        "이 페이지는 사진을 누적 저장하지 않습니다. "
        "현장에서는 파일명만 정확히 만들어 바로 휴대폰에 저장하세요."
    )

# ======================================
# ② 페이지: 사진 업로드 리스트(클릭/체크) → 폴더 분류 → ZIP
# ======================================
else:
    st.header("📦 사진 선택 → 폴더 분류 → ZIP 생성")

    uploaded_files = st.file_uploader(
        "분류할 사진 선택 (여러 장 업로드, 파일명 길어도 OK)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    make_folders = st.checkbox("교량/방향/위치 폴더로 분류", value=True)
    st.caption("파일명 형식: 교량-방향-위치(-내용).jpg 를 권장합니다. (긴 이름 허용)")

    # 세션에 미리보기 인덱스 유지
    if "preview_idx" not in st.session_state:
        st.session_state["preview_idx"] = None

    if uploaded_files:
        # 선택/해제 버튼
        col_a, col_b, col_c = st.columns([1, 1, 1])
        with col_a:
            if st.button("전체 선택"):
                for i, _ in enumerate(uploaded_files):
                    st.session_state[f"chk_{i}"] = True
        with col_b:
            if st.button("전체 해제"):
                for i, _ in enumerate(uploaded_files):
                    st.session_state[f"chk_{i}"] = False
        with col_c:
            if st.button("선택 미리보기"):
                # 누른 순간 표시할 preview_idx를 -1로 세팅해서 아래에서 체크한 것들 모두 보여줌
                st.session_state["preview_idx"] = -1

        st.markdown("### 업로드된 파일 목록 (클릭하면 해당 파일 미리보기)")
        st.caption("파일명을 클릭하면 미리보기가 뜹니다. 체크박스로 ZIP 포함 여부 선택.")

        # 리스트 표시 (각 행: 체크박스 | 파일명 버튼 | 크기 | 제거)
        for i, f in enumerate(uploaded_files):
            # 기본 체크박스 상태가 없으면 False로 초기화
            key_chk = f"chk_{i}"
            if key_chk not in st.session_state:
                st.session_state[key_chk] = False

            c1, c2, c3, c4 = st.columns([0.06, 0.66, 0.14, 0.14])
            with c1:
                chk = st.checkbox("", value=st.session_state[key_chk], key=key_chk)
            with c2:
                # 긴 파일명도 잘 보이게 HTML 스타일로 감싸서 표시
                safe_label = f"<div style='word-wrap:break-word; white-space:normal; font-size:14px'>{f.name}</div>"
                if st.button(safe_label, key=f"btn_name_{i}", on_click=None):
                    # 클릭하면 이 파일을 미리보기
                    st.session_state["preview_idx"] = i
            with c3:
                try:
                    size_kb = int(len(f.getbuffer()) / 1024)
                except Exception:
                    size_kb = None
                st.write(f"{size_kb} KB" if size_kb else "")
            with c4:
                if st.button("제거", key=f"btn_remove_{i}"):
                    # 제거 버튼: 이건 간단하게 로컬에서만 제거하려면 재업로드 필요 -> 안내만 함
                    st.warning("브라우저 업로드 목록에서 제거하려면 페이지를 새로고침하세요.")
                    # (업로드된 객체 자체를 삭제하려면 더 복잡한 상태관리 필요하므로 안내만 합니다.)

        st.markdown("---")

        # 미리보기 영역
        if st.session_state.get("preview_idx") is not None:
            idx = st.session_state["preview_idx"]
            if idx == -1:
                st.subheader("✅ 선택된 항목 미리보기")
                # 선택된 모든 항목의 미리보기
                for i, f in enumerate(uploaded_files):
                    if st.session_state.get(f"chk_{i}", False):
                        data = f.read()
                        try:
                            img = bytes_to_image(data)
                            st.image(img, caption=f.name, use_column_width=True)
                        except Exception as e:
                            st.error(f"{f.name} 미리보기 실패: {e}")
                        # ensure file pointer reset for later reads
                        try:
                            f.seek(0)
                        except Exception:
                            pass
            else:
                st.subheader("🔍 파일 미리보기")
                f = uploaded_files[idx]
                try:
                    data = f.read()
                    img = bytes_to_image(data)
                    st.image(img, caption=f.name, use_column_width=True)
                except Exception as e:
                    st.error(f"{f.name} 미리보기 실패: {e}")
                try:
                    f.seek(0)
                except Exception:
                    pass

        # ZIP 생성: 체크된 항목만 포함
        if st.button("📦 선택한 사진으로 ZIP 생성"):
            checked_indices = [i for i in range(len(uploaded_files)) if st.session_state.get(f"chk_{i}", False)]
            if not checked_indices:
                st.warning("먼저 ZIP에 포함할 사진을 체크하세요.")
            else:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i in checked_indices:
                        f = uploaded_files[i]
                        # 파일이름 그대로 쓰고, 폴더 분류 옵션이 있으면 분류
                        fname = f.name
                        base = fname.rsplit(".", 1)[0]
                        parts = base.split(DELIM)
                        if make_folders and len(parts) >= 3:
                            arcname = f"{parts[0]}/{parts[1]}/{parts[2]}/{fname}"
                        else:
                            arcname = fname
                        # read bytes
                        data = f.read()
                        zf.writestr(arcname, data)
                        try:
                            f.seek(0)
                        except Exception:
                            pass

                zip_buf.seek(0)
                st.download_button(
                    "📥 ZIP 다운로드",
                    data=zip_buf,
                    file_name="점검사진_분류.zip",
                    mime="application/zip"
                )

    else:
        st.info("먼저 분류할 사진들을 업로드하세요. (파일명은 1페이지에서 만든 표준 형식 권장)")

    st.info(
        "✔ 이 페이지는 업로드 후 사용자가 직접 선택해서 분류/ZIP을 만듭니다.\n"
        "✔ '전체 선택' 등 버튼으로 대량 처리 가능."
    )

