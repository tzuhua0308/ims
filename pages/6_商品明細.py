import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
from utils.db import fetch_all, fetch_years, TABLES
from utils.calc import period_label

st.set_page_config(page_title="商品明細", page_icon="🔍", layout="wide")
from utils.sidebar import render_help_link
render_help_link()
st.title("🔍 商品明細")

years = fetch_years()
if not years:
    st.info("尚無資料")
    st.stop()

year = st.selectbox("年份", years, format_func=lambda y: f"{y}（民{y-1911}年）")

# 取得所有有資料的國碼
all_sales = fetch_all(TABLES["sales"], {"year": year})
all_purchases = fetch_all(TABLES["purchases"], {"year": year})

df_s = pd.DataFrame(all_sales) if all_sales else pd.DataFrame()
df_p = pd.DataFrame(all_purchases) if all_purchases else pd.DataFrame()

codes_s = set(df_s["code"].dropna().unique()) if not df_s.empty and "code" in df_s.columns else set()
codes_p = set(df_p["code"].dropna().unique()) if not df_p.empty and "code" in df_p.columns else set()
all_codes = sorted(codes_s | codes_p)

if not all_codes:
    st.info("此年度無商品資料")
    st.stop()

# 也加入 products 表的商品名稱對照
products = fetch_all(TABLES["products"])
name_map = {r["code"]: r["name"] for r in products if r.get("code")}

sel_code = st.selectbox(
    "選擇商品",
    all_codes,
    format_func=lambda c: f"{c} — {name_map.get(c, '')}" if name_map.get(c) else c,
)

st.divider()

# 進貨明細
buy = df_p[df_p["code"] == sel_code] if not df_p.empty and "code" in df_p.columns else pd.DataFrame()
sell = df_s[df_s["code"] == sel_code] if not df_s.empty and "code" in df_s.columns else pd.DataFrame()

col1, col2 = st.columns(2)

with col1:
    st.subheader("進貨明細")
    if not buy.empty:
        show = [c for c in ["period","date","invoice_no","product_name","unit_price","qty","amount","vendor_name"] if c in buy.columns]
        labels = {"period":"期","date":"日期","invoice_no":"發票號碼","product_name":"商品名稱",
                  "unit_price":"單價","qty":"數量","amount":"銷售額","vendor_name":"廠商"}
        st.dataframe(buy[show].rename(columns=labels), use_container_width=True, hide_index=True)
        st.metric("進貨合計", f"${buy['amount'].sum():,.0f}")
    else:
        st.caption("無進貨資料")

with col2:
    st.subheader("銷貨明細")
    if not sell.empty:
        show = [c for c in ["period","date","invoice_no","product_name","qty","untaxed_amount"] if c in sell.columns]
        labels = {"period":"期","date":"日期","invoice_no":"發票號碼","product_name":"商品名稱",
                  "qty":"銷售量","untaxed_amount":"未稅金額"}
        st.dataframe(sell[show].rename(columns=labels), use_container_width=True, hide_index=True)
        st.metric("銷售合計", f"${sell['untaxed_amount'].sum():,.0f}")
    else:
        st.caption("無銷貨資料")

# 各期進銷對比圖
st.divider()
st.subheader("各期進銷對比")

chart_data = []
for p in range(1, 7):
    b = buy[buy["period"]==p]["amount"].sum() if not buy.empty and "period" in buy.columns else 0
    s = sell[sell["period"]==p]["untaxed_amount"].sum() if not sell.empty and "period" in sell.columns else 0
    label = period_label(p)
    chart_data.append({"期別": label, "金額": b, "類型": "進貨"})
    chart_data.append({"期別": label, "金額": s, "類型": "銷售"})

period_order = [period_label(p) for p in range(1, 7)]
df_chart = pd.DataFrame(chart_data)
fig = px.bar(df_chart, x="期別", y="金額", color="類型", barmode="group",
             color_discrete_map={"進貨":"#1f6feb","銷售":"#e36209"},
             category_orders={"期別": period_order}, height=350)
st.plotly_chart(fig, use_container_width=True)
