import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="교량 사진 촬영기", layout="centered")
 
st.title("📸 교량 사진 자동 촬영 & 파일명 생성")
 
# ------------------------------------
 # 1) 교량 데이터 불러오기
# ------------------------------------
bridge_file = "bridge.xlsx"
csv_file = "bridge.csv"
 
df = None

if os.path.exists(bridge_file):
    df = pd.read_excel(bridge_file)
elif os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
else:
    st.error("❌ bridge.xlsx 또는 bridge.csv 파일이 없습니다.")
    st.stop()

if "name" not in df.columns:
   st.error("❌ 'name' 컬럼이 없습니다.")
   st.stop()

bridge_list = df["name"].dropna().unique().tolist()

# ------------------------------------
# 2) 교량 자동 검색 + 선택
# ------------------------------------
st.subheader("🔎 교량명 검색 후 선택")

keyword = st.text_input("교량명 일부 입력 (예: ㅂ → 부춘 / 보성 / 벌교 자동 필터)")

if keyword == "":
   filtered = bridge_list
else:
    filtered = [b for b in bridge_list if keyword in b]

bridge_name = st.selectbox("검색 결과", filtered)

# ------------------------------------
# 3) 방향 / 지점 / 항목 선택
# ------------------------------------
direction = st.radio("방향", ["순천", "영암"])
point = st.radio("지점", ["A1", "A2", "P1", "P2", "P3", "P4"])
item = st.radio("점검 항목", ["신축이음", "받침부", "균열", "박리", "철근노출"])

st.write("---")
st.header("📸 사진 촬영")

# ------------------------------------
# 4) 사진 1장 촬영 → 파일명 자동 생성 → 다운로드
# ------------------------------------

img = st.camera_input("사진 촬영하기")

if img is not None:
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{bridge_name}_{direction}_{point}_{item}_{now}.jpg"

    st.success(f"📄 생성된 파일명: **{filename}**")

    st.download_button(
        label="⬇️ 사진 다운로드 (핸드폰 저장)",
        data=img.getvalue(),
        file_name=filename,
        mime="image/jpeg"
    )






