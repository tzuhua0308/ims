import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import plotly.express as px
from utils.db import fetch_years
from utils.calc import get_yearly_comparison, period_label

st.set_page_config(page_title="年際比較", page_icon="📈", layout="wide")
from utils.sidebar import render_help_link
render_help_link()
st.title("📈 年際比較")

years = fetch_years()
if len(years) < 1:
    st.info("尚無資料")
    st.stop()

col1, col2, _ = st.columns([2, 2, 2])
with col1:
    y1 = st.selectbox("年份 A", years, index=0, format_func=lambda y: f"{y}（民{y-1911}年）")
with col2:
    default_y2 = years[1] if len(years) > 1 else years[0]
    y2 = st.selectbox("年份 B", years, index=min(1, len(years)-1), format_func=lambda y: f"{y}（民{y-1911}年）")

df = get_yearly_comparison(y1, y2)
df = df.sort_values("period")
df["期別"] = df["period"].apply(period_label)
df["年份"] = df["year"].astype(str) + "年"
period_order = [period_label(p) for p in range(1, 7)]

metric = st.radio("比較項目", ["銷售額（未稅）", "進貨額"], horizontal=True)
value_col   = "sales" if metric == "銷售額（未稅）" else "purchases"

fig = px.bar(
    df, x="期別", y=value_col, color="年份", barmode="group",
    labels={value_col: metric},
    color_discrete_sequence=["#1f6feb", "#e36209"],
    category_orders={"期別": period_order},
    height=450,
)
fig.update_layout(legend_title="", margin=dict(t=30))
st.plotly_chart(fig, use_container_width=True)

# 數字表格
import pandas as pd
pivot = df.pivot_table(index="period", columns="年份", values=value_col, aggfunc="sum").reset_index()
pivot = pivot.sort_values("period")
pivot["期別"] = pivot["period"].apply(period_label)
pivot = pivot.drop(columns="period")[["期別"] + [c for c in pivot.columns if c not in ("period", "期別")]]
pivot.columns.name = None
fmt = {c: "${:,.0f}" for c in pivot.columns if c != "期別"}
st.dataframe(pivot.style.format(fmt), use_container_width=True, hide_index=True)
