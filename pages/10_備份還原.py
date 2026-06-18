import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import pandas as pd
from utils.db import fetch_all, fetch_years, upsert_batch, delete_all, TABLES

st.set_page_config(page_title="備份還原", page_icon="💾", layout="wide")
from utils.sidebar import render_help_link
render_help_link()
st.title("💾 備份還原")

tab1, tab2 = st.tabs(["備份（匯出 JSON）", "還原（匯入 JSON）"])

with tab1:
    years = fetch_years()
    if not years:
        st.info("尚無資料")
    else:
        year_opt = st.selectbox("備份年份", ["全部"] + [str(y) for y in years])

        if st.button("🔽 產生備份檔"):
            backup = {}
            for key, tbl in TABLES.items():
                if year_opt == "全部":
                    rows = fetch_all(tbl)
                else:
                    rows = fetch_all(tbl, {"year": int(year_opt)} if key != "products" else None)
                backup[key] = rows

            json_bytes = json.dumps(backup, ensure_ascii=False, indent=2, default=str).encode("utf-8")
            fname = f"ims_backup_{year_opt}.json"
            st.download_button("⬇️ 下載備份 JSON", json_bytes, fname, "application/json")
            st.success(f"備份包含：" + "、".join(f"{k} {len(v)} 筆" for k, v in backup.items()))

with tab2:
    restore_file = st.file_uploader("上傳備份 JSON", type=["json"])

    if restore_file:
        data = json.loads(restore_file.read().decode("utf-8"))
        st.write("備份內容：", {k: f"{len(v)} 筆" for k, v in data.items()})

        clear_first = st.checkbox("還原前先清空各資料表（完整還原，現有資料將全部移除）")
        if clear_first:
            st.error("⚠️ 勾選後按下還原，資料庫所有資料將被刪除再重建，無法復原。")

        confirmed = st.checkbox("確認還原（無法復原）")
        if st.button("▶️ 開始還原", type="primary", disabled=not confirmed):
            total = 0
            if clear_first:
                for tbl in TABLES.values():
                    delete_all(tbl)
            for key, tbl in TABLES.items():
                rows = data.get(key, [])
                if rows:
                    clean = [{k2: v for k2, v in r.items() if k2 != "id"} for r in rows]
                    upsert_batch(tbl, clean)
                    total += len(clean)
            st.success(f"✅ 還原完成，共 {total} 筆")
