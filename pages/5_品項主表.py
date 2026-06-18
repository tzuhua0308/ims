import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from utils.db import fetch_all, fetch_years, upsert_product, update_row, TABLES
from utils.calc import period_label

st.set_page_config(page_title="品項主表", page_icon="📋", layout="wide")
from utils.sidebar import render_help_link
render_help_link()
st.title("📋 品項主表")

years = fetch_years()
col1, col2, _ = st.columns([2, 2, 2])
with col1:
    year = st.selectbox("年份", years or [2026], format_func=lambda y: f"{y}（民{y-1911}年）")
with col2:
    period = st.selectbox("期別", list(range(1,7)),
        format_func=lambda p: f"第{p}期 {period_label(p)}")

products = fetch_all(TABLES["products"])
purchases = fetch_all(TABLES["purchases"], {"year": year, "period": period})
sales     = fetch_all(TABLES["sales"],     {"year": year, "period": period})

df_prod = pd.DataFrame(products) if products else pd.DataFrame(columns=["id","code","name","ref_price"])
df_p    = pd.DataFrame(purchases) if purchases else pd.DataFrame(columns=["code","amount"])
df_s    = pd.DataFrame(sales)     if sales     else pd.DataFrame(columns=["code","untaxed_amount"])

buy_sum  = df_p.groupby("code", dropna=False)["amount"].sum().rename("進貨累計") if not df_p.empty else pd.Series(dtype=float, name="進貨累計")
sell_sum = df_s.groupby("code", dropna=False)["untaxed_amount"].sum().rename("銷貨累計") if not df_s.empty else pd.Series(dtype=float, name="銷貨累計")

# outer join：品項主表 + 所有有交易的國碼
prod_idx = df_prod.set_index("code") if not df_prod.empty else pd.DataFrame()
df = prod_idx.join(buy_sum, how="outer").join(sell_sum, how="outer")
df["進貨累計"] = df["進貨累計"].fillna(0)
df["銷貨累計"] = df["銷貨累計"].fillna(0)
df["ref_price"] = df["ref_price"].fillna(0)
df["進銷差額"]  = df["ref_price"] + df["進貨累計"] - df["銷貨累計"]  # 參考單價 ＋ 本期進貨 － 本期銷售（不含費用/報廢/跨期遞推）
df = df.reset_index().rename(columns={"index": "code"})

# 分成「已認列」與「未認列（無品項資料）」
known   = df[df["name"].notna()].copy()
unknown = df[df["name"].isna()].copy()

fmt_cols = {"參考單價":"${:,.0f}", "進貨累計":"${:,.0f}", "銷貨累計":"${:,.0f}", "進銷差額":"${:,.0f}"}
# 進銷差額 ＝ 參考單價（期初） ＋ 本期進貨 － 本期銷售
# ⚠️ 不含費用、報廢，也不跨期遞推；與 Home 的「剩餘庫存」計算方式不同
col_labels = {"code":"國碼", "name":"商品名稱", "ref_price":"參考單價"}

# 異常標示
def highlight_known(row):
    # 銷>進+期初 → 庫存為負（紅）
    if row.get("進銷差額", 0) < 0:
        return ["background-color: #ffe3e3"] * len(row)
    # 有銷貨但無進貨（本期）
    if row.get("銷貨累計", 0) > 0 and row.get("進貨累計", 0) == 0 and row.get("參考單價", 0) == 0:
        return ["background-color: #fff3cd"] * len(row)
    return [""] * len(row)

show_cols = [c for c in ["code","name","ref_price","進貨累計","銷貨累計","進銷差額"] if c in known.columns]
anomaly_cnt = int((known["進銷差額"] < 0).sum()) if "進銷差額" in known.columns else 0
no_purchase_cnt = int(((known["銷貨累計"] > 0) & (known["進貨累計"] == 0) & (known["ref_price"] == 0)).sum())

caption_parts = [f"已認列 {len(known)} 項"]
if anomaly_cnt:    caption_parts.append(f"🔴 庫存為負 {anomaly_cnt} 項")
if no_purchase_cnt: caption_parts.append(f"🟡 有銷無進 {no_purchase_cnt} 項")
if unknown.empty is False: caption_parts.append(f"🟠 未認列 {len(unknown)} 項")
st.caption("　｜　".join(caption_parts))

disp_known = known[show_cols].rename(columns=col_labels)
st.dataframe(
    disp_known.style.apply(highlight_known, axis=1).format(fmt_cols),
    use_container_width=True, hide_index=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("參考單價合計", f"${known['ref_price'].sum():,.0f}",
          help="品項主表各商品參考單價加總，作為第1期期初庫存基準")
c2.metric("進貨累計合計", f"${df['進貨累計'].sum():,.0f}",
          help="本期所有進貨銷售額合計（含未認列國碼）")
c3.metric("銷貨累計合計", f"${df['銷貨累計'].sum():,.0f}",
          help="本期所有銷貨未稅金額合計（含未認列國碼）")
c4.metric("進銷差額合計", f"${df['進銷差額'].sum():,.0f}",
          help="公式：參考單價 ＋ 本期進貨 － 本期銷售\n⚠️ 不含費用與報廢，不跨期遞推\n與 Home「本期剩餘庫存」公式不同")

if not unknown.empty:
    unk_p_total = unknown["進貨累計"].sum()
    unk_s_total = unknown["銷貨累計"].sum()
    st.warning(f"🟠 未認列國碼 {len(unknown)} 項　進貨 ${unk_p_total:,.0f}　銷貨 ${unk_s_total:,.0f}（國碼不在品項主表，不影響 KPI 計算）")
    with st.expander("展開未認列國碼明細"):
        # 補上商品名稱（從交易紀錄抓）
        if not df_p.empty:
            name_map = df_p.groupby("code")["product_name"].first()
            unknown = unknown.join(name_map, on="code", how="left")
        elif not df_s.empty:
            name_map2 = df_s.groupby("code")["product_name"].first()
            unknown = unknown.join(name_map2, on="code", how="left")
        unk_show = [c for c in ["code","product_name","進貨累計","銷貨累計","進銷差額"] if c in unknown.columns]
        unk_fmt = {k: v for k, v in fmt_cols.items() if k in [c.replace("code","").replace("product_name","") for c in unk_show]}
        st.dataframe(
            unknown[unk_show].rename(columns={"code":"國碼","product_name":"商品名稱（來自交易）"})
                .style.format({k: v for k, v in fmt_cols.items()}),
            use_container_width=True, hide_index=True,
        )

# 更新參考單價（直接在表格編輯）
st.divider()
st.subheader("✏️ 更新參考單價")
if not df_prod.empty and "id" in df_prod.columns:
    price_cols = [c for c in ["id","code","name","ref_price"] if c in df_prod.columns]
    price_df = df_prod[price_cols].copy().reset_index(drop=True)
    edited_prices = st.data_editor(
        price_df, use_container_width=True, hide_index=True,
        disabled=[c for c in price_df.columns if c != "ref_price"],
        key="edit_ref_price",
    )
    if st.button("💾 儲存參考單價"):
        changes = 0
        for i in range(len(price_df)):
            if str(price_df.iloc[i]["ref_price"]) != str(edited_prices.iloc[i]["ref_price"]):
                update_row(TABLES["products"], int(price_df.iloc[i]["id"]),
                           {"ref_price": edited_prices.iloc[i]["ref_price"]})
                changes += 1
        if changes:
            st.success(f"已更新 {changes} 筆")
            st.rerun()
        else:
            st.info("無修改")

# 新增商品
with st.expander("➕ 新增商品"):
    nc = st.text_input("國碼")
    nn = st.text_input("商品名稱")
    new_ref_price = st.number_input("參考單價", min_value=0.0, step=1.0, key="new_ref_price")
    if st.button("新增"):
        if nc and nn:
            upsert_product(nc, nn, new_ref_price)
            st.success(f"✅ 已新增 {nc} {nn}")
            st.rerun()
