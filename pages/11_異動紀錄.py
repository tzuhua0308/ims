import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import pandas as pd
from utils.db import fetch_audit_log, restore_deleted_row, clear_audit_log
from utils.sidebar import render_help_link

st.set_page_config(page_title="異動紀錄", page_icon="🔍", layout="wide")
render_help_link()
st.title("🔍 異動紀錄")

TABLE_LABELS = {
    "ims_purchases": "進貨",
    "ims_sales":     "銷貨",
    "ims_expenses":  "費用",
    "ims_scraps":    "報廢",
    "ims_products":  "品項",
}

rows = fetch_audit_log(limit=500)
if not rows:
    st.info("尚無異動紀錄")
    st.stop()

df = pd.DataFrame(rows)
df["資料表"] = df["table_name"].map(TABLE_LABELS).fillna(df["table_name"])
df["操作"]   = df["action"].map({"DELETE": "🗑 刪除", "UPDATE": "✏️ 修改"}).fillna(df["action"])

# 產生異動摘要欄
def _summary(row):
    if row["action"] == "UPDATE":
        old = json.loads(row["old_data"]) if row.get("old_data") else {}
        new = json.loads(row["new_data"]) if row.get("new_data") else {}
        changed = [k for k in new if str(new.get(k)) != str(old.get(k))]
        return "、".join(changed) if changed else "—"
    return "整筆刪除"

df["異動欄位"] = df.apply(_summary, axis=1)

# ── 篩選 ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 2])
with col1:
    tbl_opts = ["全部"] + sorted(df["資料表"].unique().tolist())
    sel_tbl = st.selectbox("資料表", tbl_opts)
with col2:
    sel_act = st.selectbox("操作類型", ["全部", "🗑 刪除", "✏️ 修改"])

view = df.copy()
if sel_tbl != "全部":
    view = view[view["資料表"] == sel_tbl]
if sel_act != "全部":
    view = view[view["操作"] == sel_act]

st.caption(f"共 {len(view):,} 筆（最近 500 筆）")

disp = view[["id","changed_at","資料表","row_id","操作","異動欄位"]].rename(
    columns={"id":"Log ID","changed_at":"時間","row_id":"資料 ID"}
)
st.dataframe(disp, use_container_width=True, hide_index=True)

# ── 查看單筆詳細差異 ──────────────────────────────────────────────────────
st.divider()
st.subheader("查看單筆詳細差異")
log_id = st.number_input("輸入 Log ID", min_value=1, step=1)
matched = df[df["id"] == log_id]

if not matched.empty:
    row = matched.iloc[0]
    st.markdown(f"**{row['changed_at']}　{row['操作']}　{row['資料表']}　資料 ID={row['row_id']}**")

    old = json.loads(row["old_data"]) if row.get("old_data") else {}
    new = json.loads(row["new_data"]) if row.get("new_data") else {}

    if row["action"] == "UPDATE":
        diff = [{"欄位": k, "改前": old.get(k, ""), "改後": new.get(k, "")}
                for k in new if str(new.get(k)) != str(old.get(k))]
        if diff:
            st.dataframe(pd.DataFrame(diff), use_container_width=True, hide_index=True)
        else:
            st.info("無差異")

    elif row["action"] == "DELETE":
        st.dataframe(
            pd.DataFrame([old]).T.rename(columns={0: "刪除前的值"}),
            use_container_width=True,
        )
        confirmed = st.checkbox("確認還原此筆（將重新寫入資料庫）", key=f"confirm_restore_{log_id}")
        if st.button("↩️ 還原此筆", disabled=not confirmed):
            ok = restore_deleted_row(int(log_id))
            if ok:
                st.success("✅ 已還原，請至對應紀錄頁面確認")
            else:
                st.error("還原失敗（此 Log 非刪除操作）")

# ── 清除 log ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("🗑 清除異動紀錄")
st.warning("清除後無法復原。")
confirmed_clear = st.checkbox("確認清除全部異動紀錄")
if st.button("清除", type="secondary", disabled=not confirmed_clear):
    clear_audit_log()
    st.success("已清除")
    st.rerun()
