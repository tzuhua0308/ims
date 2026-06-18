import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(page_title="使用說明", page_icon="📖", layout="wide")
from utils.sidebar import render_help_link
render_help_link()
st.title("📖 使用說明")

tab1, tab2, tab3 = st.tabs(["系統介紹", "操作流程", "Claude Code 維護"])

# ── Tab 1：系統介紹 ─────────────────────────────────────────────────────────
with tab1:
    st.subheader("系統架構")
    st.markdown("""
本系統以 **民國兩個月一期** 的稅額計算 XLS 為資料來源，匯入後可查詢進貨、銷貨、費用、報廢等紀錄，
並自動計算各期庫存與 KPI。

| 頁面 | 功能 |
|------|------|
| 🏠 Home（儀表板） | 選定年份＋期別後，顯示 5 項 KPI 卡片、商品進銷長條圖、全年銷售趨勢 |
| 📥 進貨紀錄 | 查詢／搜尋／編輯／刪除進貨明細，紅色標示國碼或日期空白的資料 |
| 📤 銷貨紀錄 | 同上，黃色另標示 UUID 格式國碼（電子發票平台自動產生的代號） |
| 💸 費用紀錄 | 查詢費用（含稅額），紅色標示日期空白 |
| 🗑️ 報廢紀錄 | 查詢報廢損失，紅色標示代號或日期空白 |
| 📋 品項主表 | 國碼對照表＋各期進銷累計＋庫存估算；可直接編輯參考單價 |
| 🔍 商品明細 | 選定商品查看全年逐期進銷明細與對比圖 |
| 📊 摘要報表 | 期間總覽＋各商品明細，有銷無進的商品標紅；可匯出 Excel |
| 📈 年際比較 | 任選兩年，切換銷售額／進貨額做各期對比 |
| ⬆️ 匯入 | 上傳稅額計算 XLS，解析預覽後確認匯入；另支援報廢 Excel |
| 💾 備份還原 | 將全部資料匯出為 JSON 備份，或從備份還原 |
""")

    st.subheader("異常標示說明")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.error("🔴 紅色")
        st.caption("國碼空白、日期空白等必填欄位缺漏")
    with col2:
        st.warning("🟡 黃色")
        st.caption("UUID 格式國碼（電子發票平台代號，建議補對應商品代號）")
    with col3:
        st.info("🟠 橘色提示")
        st.caption("品項主表中有交易紀錄但未建檔的國碼")

# ── Tab 2：操作流程 ─────────────────────────────────────────────────────────
with tab2:
    st.subheader("一、每期資料匯入")
    st.markdown("""
1. 取得財政部稅額計算 XLS（例如 `115年01-02月稅額計算.xls`）
2. 前往 **⬆️ 匯入** 頁面，上傳檔案
3. 系統自動從檔名偵測年份與期別（可手動調整）
4. 點「📊 解析預覽」確認筆數與驗算結果
5. 驗算比對通過後點「✅ 確認匯入」
""")

    st.subheader("二、資料品質檢查")
    st.markdown("""
匯入後建議至各紀錄頁面確認：
- **進貨紀錄**：確認紅色列（國碼空白）是否需要補填
- **銷貨紀錄**：確認黃色列（UUID 國碼）是否能對應到正確商品代號
- **品項主表**：確認橘色未認列國碼是否需要新增到品項主表
""")

    st.subheader("三、修正資料")
    st.markdown("""
各紀錄頁面底部有「✏️ 編輯資料」展開區：
- 預設只顯示有問題的筆數，勾選「顯示全部筆數」可編輯任意筆
- 直接在表格內修改，按「💾 儲存修改」寫入資料庫
- 刪除需勾選「確認刪除」才能執行，避免誤刪
""")

    st.subheader("四、查看報表")
    st.markdown("""
- **儀表板**：快速掌握本期 KPI 與進銷概覽
- **摘要報表**：完整期間報表，可下載 Excel 版本（含費用與報廢明細）
- **年際比較**：同期不同年份的銷售額或進貨額對比
- **商品明細**：單一商品全年逐期進銷對比圖
""")

    st.subheader("五、備份建議")
    st.markdown("""
每次匯入新期別資料後，建議至「💾 備份還原」頁面做一次全量備份，
下載 JSON 備份檔存放於安全位置。還原時勾選「還原前先清空」可做完整還原。
""")

# ── Tab 3：Claude Code 維護 ──────────────────────────────────────────────────
with tab3:
    st.subheader("什麼是 Claude Code？")
    st.markdown("""
**Claude Code** 是 Anthropic 官方的 AI 程式助理 CLI，
可以直接在終端機對話、讀寫程式碼、執行指令，讓你用自然語言維護或擴充本系統。
""")

    st.subheader("啟動方式")
    st.code("""# 在終端機切換到本專案目錄
cd ~/Desktop/庫存管理系統/ims

# 啟動 Claude Code
claude""", language="bash")

    st.subheader("常見維護需求範例")

    with st.expander("📥 修改 Excel 解析邏輯"):
        st.markdown("""
當稅額計算 XLS 的欄位位置或工作表名稱有異動時：

```
進項-可扣抵發票(進貨) 工作表的日期改到第 2 欄，金額改到第 11 欄，
請幫我更新 parser.py
```
""")

    with st.expander("📊 新增欄位或頁面"):
        st.markdown("""
```
幫我在摘要報表加一個「毛利率」欄位，
計算方式是 (銷售額 - 進貨額) / 銷售額 × 100%
```

```
新增一個頁面，可以查詢某個廠商的所有進貨紀錄
```
""")

    with st.expander("🐛 回報 Bug"):
        st.markdown("""
直接描述畫面上的錯誤訊息：

```
進貨紀錄頁面出現這個錯誤：
ValueError: cannot convert float NaN to integer
完整 traceback 如下：...
```
""")

    with st.expander("🔢 數字對不起來"):
        st.markdown("""
```
第 3 期進貨合計應該是 28,500,000，
但系統顯示 27,800,000，
幫我找出差異原因
```
""")

    with st.expander("🚀 部署與環境問題"):
        st.markdown("""
```
我要部署到 Streamlit Community Cloud，
幫我確認 requirements.txt 是否完整，
以及 secrets.toml 應該設定哪些項目
```
""")

    st.subheader("本系統的技術架構（給 Claude Code 的背景知識）")
    st.code("""ims/
├── Home.py                  # 儀表板
├── pages/
│   ├── 0_使用說明.py
│   ├── 1_進貨紀錄.py
│   ├── 2_銷貨紀錄.py
│   ├── 3_費用紀錄.py
│   ├── 4_報廢紀錄.py
│   ├── 5_品項主表.py
│   ├── 6_商品明細.py
│   ├── 7_摘要報表.py
│   ├── 8_年際比較.py
│   ├── 9_匯入.py
│   └── 10_備份還原.py
├── utils/
│   ├── db.py       # SQLite / Supabase CRUD（USE_LOCAL 控制）
│   ├── parser.py   # xlrd 解析稅額 XLS
│   └── calc.py     # KPI 計算、期別彙總
└── .streamlit/
    └── secrets.toml  # USE_LOCAL, SUPABASE_URL, SUPABASE_KEY""", language="bash")

    st.info("""**提示：** 在 Claude Code 裡直接說「這個系統」，它會自動讀取 CLAUDE.md 與現有程式碼，
不需要每次解釋背景。若遇到無法理解的問題，可以把 Streamlit 的完整錯誤訊息貼給它。""")
