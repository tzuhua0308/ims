import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from utils.sidebar import render_help_link

st.set_page_config(
    page_title="庫存管理系統",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)
render_help_link()

pg = st.navigation([
    st.Page("pages/_儀表板.py",    title="Home",     icon="📦", default=True),
    st.Page("pages/1_進貨紀錄.py", title="進貨紀錄", icon="📥"),
    st.Page("pages/2_銷貨紀錄.py", title="銷貨紀錄", icon="📤"),
    st.Page("pages/3_費用紀錄.py", title="費用紀錄", icon="💸"),
    st.Page("pages/4_報廢紀錄.py", title="報廢紀錄", icon="🗑️"),
    st.Page("pages/5_品項主表.py", title="品項主表", icon="📋"),
    st.Page("pages/6_商品明細.py", title="商品明細", icon="🔍"),
    st.Page("pages/7_摘要報表.py", title="摘要報表", icon="📊"),
    st.Page("pages/8_年際比較.py", title="年際比較", icon="📈"),
    st.Page("pages/9_匯入.py",     title="匯入",     icon="⬆️"),
    st.Page("pages/10_備份還原.py",title="備份還原", icon="💾"),
    st.Page("pages/11_異動紀錄.py",title="異動紀錄", icon="🕵️"),
    st.Page("pages/0_使用說明.py", title="使用說明", icon="📖"),
])

pg.run()
