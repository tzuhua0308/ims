import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import plotly.express as px
import pandas as pd
from utils.db import fetch_all, fetch_years, TABLES
from utils.calc import get_kpi, period_label


def fmt(v: float) -> str:
    av = abs(v)
    if av >= 100_000_000:
        return f"${v/100_000_000:,.2f}億"
    if av >= 10_000:
        return f"${v/10_000:,.1f}萬"
    return f"${v:,.0f}"


st.title("📦 庫存管理系統")

years = fetch_years()
if not years:
    st.info("尚無資料，請先至「匯入」頁面上傳稅額計算 XLS。")
    st.stop()

col_y, col_p, _ = st.columns([2, 2, 2])
with col_y:
    year = st.selectbox("年份", years, format_func=lambda y: f"{y}（民{y-1911}年）")
with col_p:
    period = st.selectbox("期別", list(range(1, 7)), format_func=lambda p: f"第{p}期 {period_label(p)}")

kpi = get_kpi(year, period)

st.divider()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("本期進貨",     fmt(kpi['purchases']),
          help=f"本期進項-可扣抵發票(進貨) 銷售額合計\n＝ ${kpi['purchases']:,.0f}")
c2.metric("本期銷售",     fmt(kpi['sales']),
          help=f"本期銷項未稅金額合計\n＝ ${kpi['sales']:,.0f}")
c3.metric("本期費用",     fmt(kpi['expenses']),
          help=f"本期進項-費用雜項 含稅金額合計\n＝ ${kpi['expenses']:,.0f}")
c4.metric("本期報廢損失", fmt(kpi['scraps']),
          help=f"本期報廢損失金額合計\n＝ ${kpi['scraps']:,.0f}")
c5.metric("本期剩餘庫存", fmt(kpi['remaining']),
          delta=f"期初 {fmt(kpi['opening'])}", delta_color="off",
          help=(
              f"公式：期初庫存 ＋ 本期進貨 － 本期銷售 － 本期費用 － 本期報廢\n"
              f"＝ {fmt(kpi['opening'])} ＋ {fmt(kpi['purchases'])} － {fmt(kpi['sales'])} "
              f"－ {fmt(kpi['expenses'])} － {fmt(kpi['scraps'])}\n"
              f"＝ ${kpi['remaining']:,.0f}\n\n"
              f"※ 期初庫存：第1期 ＝ 品項主表參考單價合計；第2期起 ＝ 上一期剩餘庫存"
          ))

st.divider()
st.subheader("各商品進貨 vs 銷售")

purchases = fetch_all(TABLES["purchases"], {"year": year, "period": period})
sales     = fetch_all(TABLES["sales"],     {"year": year, "period": period})

df_p = pd.DataFrame(purchases)
df_s = pd.DataFrame(sales)

if not df_p.empty and "code" in df_p.columns:
    buy = df_p.groupby("code")["amount"].sum().reset_index().rename(columns={"amount": "金額", "code": "國碼"})
    buy["類型"] = "進貨"
else:
    buy = pd.DataFrame(columns=["國碼","金額","類型"])

if not df_s.empty and "code" in df_s.columns:
    sell = df_s.groupby("code")["untaxed_amount"].sum().reset_index().rename(columns={"untaxed_amount": "金額", "code": "國碼"})
    sell["類型"] = "銷售"
else:
    sell = pd.DataFrame(columns=["國碼","金額","類型"])

df_chart = pd.concat([buy, sell], ignore_index=True)
df_chart = df_chart[df_chart["國碼"].notna() & (df_chart["國碼"] != "")]

if not df_chart.empty:
    fig = px.bar(
        df_chart, x="國碼", y="金額", color="類型", barmode="group",
        color_discrete_map={"進貨": "#1f6feb", "銷售": "#e36209"},
        height=420,
    )
    fig.update_layout(xaxis_tickangle=-45, legend_title="", margin=dict(t=30))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("無商品進銷資料")

st.divider()
st.subheader(f"{year} 年各期銷售趨勢")

period_data = []
for p in range(1, 7):
    s = fetch_all(TABLES["sales"], {"year": year, "period": p})
    total = sum(r["untaxed_amount"] or 0 for r in s)
    period_data.append({"期別": period_label(p), "銷售額": total})

df_trend = pd.DataFrame(period_data)
fig2 = px.line(df_trend, x="期別", y="銷售額", markers=True,
               color_discrete_sequence=["#1f6feb"], height=300)
fig2.update_layout(margin=dict(t=20))
st.plotly_chart(fig2, use_container_width=True)
