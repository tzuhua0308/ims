import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from utils.db import fetch_all, fetch_years, delete_row, update_row, TABLES
from utils.calc import period_label

st.set_page_config(page_title="費用紀錄", page_icon="💸", layout="wide")
from utils.sidebar import render_help_link
render_help_link()
st.title("💸 費用紀錄")

years = fetch_years()
if not years:
    st.info("尚無資料")
    st.stop()

col1, col2, _ = st.columns([2, 2, 2])
with col1:
    year = st.selectbox("年份", years, format_func=lambda y: f"{y}（民{y-1911}年）")
with col2:
    period = st.selectbox("期別", [0]+list(range(1,7)),
        format_func=lambda p: "全年" if p==0 else f"第{p}期 {period_label(p)}")

filters = {"year": year}
if period != 0:
    filters["period"] = period

rows = fetch_all(TABLES["expenses"], filters)
df = pd.DataFrame(rows) if rows else pd.DataFrame()

if df.empty:
    st.info("此期間無費用資料")
    st.stop()

search = st.text_input("🔍 搜尋（消費內容 / 廠商）", "")
if search:
    mask = (
        df["content"].astype(str).str.contains(search, case=False, na=False) |
        df["vendor_name"].astype(str).str.contains(search, case=False, na=False)
    )
    df = df[mask]

total_exp = df["amount"].sum() if "amount" in df.columns else 0

no_date = df["date"].isna() | (df["date"].astype(str).str.strip() == "")
issue_note = f"　　🔴 日期空白 {no_date.sum()}" if no_date.sum() else ""
st.caption(f"共 {len(df):,} 筆　　金額合計：${total_exp:,.0f}{issue_note}")

show_cols = ["date","invoice_type","invoice_no","content","vendor_name","vendor_tax","amount"]
show_cols = [c for c in show_cols if c in df.columns]
col_labels = {
    "date":"日期","invoice_type":"發票種類","invoice_no":"發票號碼",
    "content":"消費內容","vendor_name":"廠商抬頭","vendor_tax":"廠商統編","amount":"金額",
}
display = df[show_cols].rename(columns=col_labels).reset_index(drop=True)

def highlight_expenses(row):
    if no_date.iloc[row.name]:
        return ["background-color: #ffe3e3"] * len(row)
    return [""] * len(row)

st.dataframe(display.style.apply(highlight_expenses, axis=1).format({"金額": "${:,.0f}"}),
             use_container_width=True, hide_index=True)

csv = display.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ 下載 CSV", csv, f"費用紀錄_{year}_P{period}.csv", "text/csv")

with st.expander("✏️ 編輯資料"):
    has_issues = no_date
    show_all_edit = st.checkbox("顯示全部筆數", value=False, key="show_all_edit_e")
    edit_src = df if show_all_edit else (df[has_issues] if has_issues.any() else df)
    edit_cols = [c for c in ["id","date","invoice_type","invoice_no","content","vendor_name","vendor_tax","amount"] if c in edit_src.columns]
    edit_df = edit_src[edit_cols].copy().reset_index(drop=True)
    if edit_df.empty:
        st.info("無問題筆數")
    else:
        edited = st.data_editor(edit_df, use_container_width=True, hide_index=True,
                                disabled=["id"], key="edit_expenses")
        if st.button("💾 儲存修改", key="save_expenses"):
            changes = 0
            for i in range(len(edit_df)):
                orig = edit_df.iloc[i].to_dict()
                new  = edited.iloc[i].to_dict()
                row_id = int(orig["id"])
                diff = {k: v for k, v in new.items() if k != "id" and str(v) != str(orig.get(k))}
                if diff:
                    update_row(TABLES["expenses"], row_id, diff)
                    changes += 1
            if changes:
                st.success(f"已更新 {changes} 筆")
                st.rerun()
            else:
                st.info("無修改")

with st.expander("🗑 刪除單筆"):
    del_id = st.number_input("輸入要刪除的 ID", min_value=1, step=1)
    confirmed = st.checkbox("確認刪除（無法復原）", key="confirm_del_e")
    if st.button("刪除", type="secondary", disabled=not confirmed):
        delete_row(TABLES["expenses"], int(del_id))
        st.success(f"已刪除 ID={del_id}")
        st.rerun()
