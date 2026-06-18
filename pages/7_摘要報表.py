import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import io
from utils.db import fetch_all, fetch_years, TABLES
from utils.calc import get_kpi, get_product_summary, period_label


def fmt(v: float) -> str:
    av = abs(v)
    if av >= 100_000_000:
        return f"${v/100_000_000:,.2f}億"
    if av >= 10_000:
        return f"${v/10_000:,.1f}萬"
    return f"${v:,.0f}"

st.set_page_config(page_title="摘要報表", page_icon="📊", layout="wide")
from utils.sidebar import render_help_link
render_help_link()
st.title("📊 摘要報表")

years = fetch_years()
if not years:
    st.info("尚無資料")
    st.stop()

col1, col2, _ = st.columns([2, 2, 2])
with col1:
    year = st.selectbox("年份", years, format_func=lambda y: f"{y}（民{y-1911}年）")
with col2:
    period = st.selectbox("期別", list(range(1,7)),
        format_func=lambda p: f"第{p}期 {period_label(p)}")

kpi = get_kpi(year, period)

# ── 區塊一：總覽 ──────────────────────────────────────────────────────────
st.subheader("一、期間總覽")
c1, c2, c3 = st.columns(3)
c4, c5, c6 = st.columns(3)

c1.metric("期初庫存",     fmt(kpi['opening']),    help=f"${kpi['opening']:,.0f}")
c2.metric("本期進貨",     fmt(kpi['purchases']),  help=f"${kpi['purchases']:,.0f}")
c3.metric("本期銷售額",   fmt(kpi['sales']),      help=f"${kpi['sales']:,.0f}")
c4.metric("本期費用",     fmt(kpi['expenses']),   help=f"${kpi['expenses']:,.0f}")
c5.metric("本期報廢損失", fmt(kpi['scraps']),     help=f"${kpi['scraps']:,.0f}")
c6.metric("本期剩餘庫存", fmt(kpi['remaining']),  help=f"${kpi['remaining']:,.0f}")

# ── 區塊二：各商品明細 ────────────────────────────────────────────────────
st.divider()
st.subheader("二、各商品明細")

df = get_product_summary(year, period)

if df.empty:
    st.info("無商品資料")
    st.stop()

show_cols = [c for c in ["code","name","ref_price","purchase_amt","sales_amt","inventory"] if c in df.columns]
col_labels = {
    "code":"國碼","name":"商品名稱","ref_price":"參考單價",
    "purchase_amt":"本期進貨","sales_amt":"本期銷售","inventory":"目前庫存",
}
display = df[show_cols].rename(columns=col_labels).reset_index(drop=True)
anomaly_mask = df["anomaly"].reset_index(drop=True) if "anomaly" in df.columns else pd.Series(False, index=display.index)

anomaly_count = int(anomaly_mask.sum())
if anomaly_count > 0:
    st.warning(f"⚠️ 有 {anomaly_count} 件商品本期有銷售但無進貨（標紅）")

money_fmt = {c: "${:,.0f}" for c in ["參考單價","本期進貨","本期銷售","目前庫存"] if c in display.columns}
styled = display.style.apply(
    lambda row: ["background-color: #ffe3e3"] * len(row) if anomaly_mask.iloc[row.name] else [""] * len(row),
    axis=1,
).format(money_fmt)
st.dataframe(styled, use_container_width=True, hide_index=True)

# ── 匯出 Excel ────────────────────────────────────────────────────────────
st.divider()

def build_excel(year, period, kpi, df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        # 摘要
        summary = pd.DataFrame([{
            "項目": "期初庫存",    "金額": kpi["opening"]},
            {"項目": "本期進貨",   "金額": kpi["purchases"]},
            {"項目": "本期銷售",   "金額": kpi["sales"]},
            {"項目": "本期費用",   "金額": kpi["expenses"]},
            {"項目": "本期報廢",   "金額": kpi["scraps"]},
            {"項目": "本期剩餘庫存","金額": kpi["remaining"]},
        ])
        summary.to_excel(writer, sheet_name="摘要", index=False)

        # 商品明細
        exp_cols = [c for c in ["code","name","ref_price","purchase_amt","sales_amt","inventory"] if c in df.columns]
        df[exp_cols].rename(columns=col_labels).to_excel(writer, sheet_name="各商品明細", index=False)

        # 費用明細
        expenses = fetch_all(TABLES["expenses"], {"year": year, "period": period})
        if expenses:
            pd.DataFrame(expenses).to_excel(writer, sheet_name="費用明細", index=False)

        # 報廢明細
        scraps = fetch_all(TABLES["scraps"], {"year": year, "period": period})
        if scraps:
            pd.DataFrame(scraps).to_excel(writer, sheet_name="報廢明細", index=False)

    return buf.getvalue()

if st.button("📥 匯出 Excel"):
    excel_bytes = build_excel(year, period, kpi, df)
    st.download_button(
        "⬇️ 下載報表",
        excel_bytes,
        f"摘要報表_{year}_第{period}期.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
