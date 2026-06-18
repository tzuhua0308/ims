import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.parser import parse_tax_xls, parse_scraps_xlsx, detect_year_period
from utils.db import upsert_batch, delete_period, count_period, import_products, TABLES

st.set_page_config(page_title="匯入", page_icon="⬆️", layout="wide")
from utils.sidebar import render_help_link
render_help_link()
st.title("⬆️ 資料匯入")

tab1, tab2 = st.tabs(["稅額計算 XLS（進貨 / 銷貨 / 費用）", "報廢紀錄 Excel"])

# ── Tab 1：稅額計算 XLS ────────────────────────────────────────────────────

with tab1:
    uploaded = st.file_uploader("上傳稅額計算 .xls", type=["xls", "xlsx"], key="tax_xls")

    if uploaded:
        file_bytes = uploaded.read()
        auto_year, auto_period = detect_year_period(uploaded.name)

        # 用檔名當 key，換檔時 widget 自動重置為新的自動偵測值
        fkey = uploaded.name.replace(" ", "_")
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("年份（西元）", value=auto_year or 2026,
                                   min_value=2020, max_value=2099, step=1,
                                   key=f"year_{fkey}")
        with col2:
            period = st.selectbox(
                "期別",
                options=[1,2,3,4,5,6],
                index=(auto_period - 1) if auto_period else 0,
                format_func=lambda p: f"第{p}期（{'1-2月,3-4月,5-6月,7-8月,9-10月,11-12月'.split(',')[p-1]}）",
                key=f"period_{fkey}",
            )
        st.caption(f"📁 {uploaded.name}")

        if st.button("📊 解析預覽", type="primary"):
            with st.spinner("解析中..."):
                try:
                    result = parse_tax_xls(file_bytes, uploaded.name, year, period)
                    st.session_state["import_result"] = result
                    st.session_state["import_year"] = year
                    st.session_state["import_period"] = period
                except Exception as e:
                    st.error(f"解析失敗：{e}")

    if "import_result" in st.session_state:
        result = st.session_state["import_result"]
        year   = st.session_state["import_year"]
        period = st.session_state["import_period"]

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("進貨筆數", len(result["purchases"]))
        c2.metric("銷貨筆數", len(result["sales"]))
        c3.metric("費用筆數", len(result["expenses"]))
        c4.metric("品項筆數", len(result.get("products", [])))

        # ── 驗算比對 ────────────────────────────────────────────────
        if result.get("checksums"):
            st.subheader("驗算比對")
            chk_rows = []
            all_pass = True
            for sheet_name, info in result["checksums"].items():
                declared = info["declared"]
                parsed   = info["parsed"]
                count    = info["count"]
                if declared is None:
                    status = "—"
                else:
                    diff = abs(parsed - declared)
                    pct  = diff / declared * 100 if declared else 0
                    if pct < 0.1:
                        status = "✅" if pct < 0.01 else f"✅ 差 ${diff:,.0f}（{pct:.3f}%，浮點誤差）"
                    elif pct < 10:
                        status = f"⚠️ 差 ${diff:,.0f}（{pct:.1f}%）"
                    else:
                        status = f"❌ 差 ${diff:,.0f}（{pct:.1f}%）"
                        all_pass = False
                chk_rows.append({
                    "工作表": sheet_name,
                    "解析筆數": count,
                    "解析合計": f"${parsed:,.0f}",
                    "工作表驗算值": f"${declared:,.0f}" if declared else "無",
                    "比對": status,
                })
            import pandas as pd
            st.dataframe(pd.DataFrame(chk_rows), use_container_width=True, hide_index=True)
            if all_pass:
                st.success("所有工作表驗算通過。")

        with st.expander("進貨預覽（前10筆）"):
            if result["purchases"]:
                st.dataframe(result["purchases"][:10], use_container_width=True)
        with st.expander("銷貨預覽（前10筆）"):
            if result["sales"]:
                st.dataframe(result["sales"][:10], use_container_width=True)
        with st.expander("費用預覽（前10筆）"):
            if result["expenses"]:
                st.dataframe(result["expenses"][:10], use_container_width=True)

        # 重複偵測
        existing = {
            "purchases": count_period(TABLES["purchases"], year, period),
            "sales":     count_period(TABLES["sales"],     year, period),
            "expenses":  count_period(TABLES["expenses"],  year, period),
        }
        any_exist = any(v > 0 for v in existing.values())

        if any_exist:
            st.warning(
                f"⚠️ 資料庫已有 {year} 年第{period}期資料："
                f" 進貨 {existing['purchases']} 筆、"
                f"銷貨 {existing['sales']} 筆、"
                f"費用 {existing['expenses']} 筆。\n\n"
                "匯入前將先清除該期舊資料。"
            )
            overwrite = st.checkbox("確認覆蓋舊資料")
        else:
            overwrite = True

        if st.button("✅ 確認匯入", type="primary", disabled=(any_exist and not overwrite)):
            progress = st.progress(0, text="匯入中...")
            try:
                if any_exist:
                    for tbl in ["purchases", "sales", "expenses"]:
                        delete_period(TABLES[tbl], year, period)

                steps = [
                    ("purchases", result["purchases"], "進貨"),
                    ("sales",     result["sales"],     "銷貨"),
                    ("expenses",  result["expenses"],  "費用"),
                ]
                for i, (key, rows, label) in enumerate(steps):
                    if rows:
                        upsert_batch(TABLES[key], rows)
                    progress.progress((i + 1) / len(steps), text=f"寫入{label}...")

                # 品項主表：upsert（只更新 name，不覆蓋 ref_price）
                products = result.get("products", [])
                if products:
                    import_products(products)

                progress.empty()
                prod_note = f"、品項 {len(products)} 筆" if products else ""
                st.success(
                    f"✅ 匯入完成！進貨 {len(result['purchases'])} 筆、"
                    f"銷貨 {len(result['sales'])} 筆、"
                    f"費用 {len(result['expenses'])} 筆{prod_note}。"
                )
                del st.session_state["import_result"]
            except Exception as e:
                progress.empty()
                st.error(f"匯入失敗：{e}")


# ── Tab 2：報廢紀錄 ────────────────────────────────────────────────────────

with tab2:
    st.caption("支援 .xlsx / .xls，欄位：日期、代號、張數、原因、損失金額、備註")
    scrap_file = st.file_uploader("上傳報廢 Excel", type=["xls","xlsx"], key="scrap_xls")

    if scrap_file:
        scrap_bytes = scrap_file.read()
        sfkey = scrap_file.name.replace(" ", "_")
        col1, col2 = st.columns(2)
        with col1:
            s_year   = st.number_input("年份（西元）", value=2026, min_value=2020, max_value=2099, step=1, key=f"sy_{sfkey}")
        with col2:
            s_period = st.selectbox("期別", options=[1,2,3,4,5,6], key=f"sp_{sfkey}",
                format_func=lambda p: f"第{p}期（{'1-2月,3-4月,5-6月,7-8月,9-10月,11-12月'.split(',')[p-1]}）")
        st.caption(f"📁 {scrap_file.name}")

        if st.button("📊 解析報廢預覽"):
            try:
                rows = parse_scraps_xlsx(scrap_bytes, s_year, s_period)
                st.session_state["scrap_rows"] = rows
                st.session_state["scrap_year"] = s_year
                st.session_state["scrap_period"] = s_period
            except Exception as e:
                st.error(f"解析失敗：{e}")

    if "scrap_rows" in st.session_state:
        rows = st.session_state["scrap_rows"]
        st.metric("報廢筆數", len(rows))
        st.dataframe(rows[:10], use_container_width=True)

        existing_s = count_period(TABLES["scraps"], st.session_state["scrap_year"], st.session_state["scrap_period"])
        if existing_s > 0:
            st.warning(f"⚠️ 已有 {existing_s} 筆舊資料，將覆蓋。")
            ok = st.checkbox("確認覆蓋報廢舊資料")
        else:
            ok = True

        if st.button("✅ 匯入報廢", disabled=(existing_s > 0 and not ok)):
            try:
                if existing_s > 0:
                    delete_period(TABLES["scraps"], st.session_state["scrap_year"], st.session_state["scrap_period"])
                upsert_batch(TABLES["scraps"], rows)
                st.success(f"✅ 報廢匯入完成，共 {len(rows)} 筆。")
                del st.session_state["scrap_rows"]
            except Exception as e:
                st.error(f"匯入失敗：{e}")
