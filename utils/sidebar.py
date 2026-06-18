import streamlit as st


def render_help_link():
    st.sidebar.markdown(
        """
<style>
/* 隱藏側邊欄上方的「使用說明」導覽連結 */
[data-testid="stSidebarNav"] a[href*="%E4%BD%BF%E7%94%A8%E8%AA%AA%E6%98%8E"] {
    display: none !important;
}
[data-testid="stSidebarNav"] a[href*="%E4%BD%BF%E7%94%A8%E8%AA%AA%E6%98%8E"] + * {
    display: none !important;
}

/* 左下角固定連結 */
.sidebar-help-footer {
    position: fixed;
    bottom: 1.5rem;
    left: 0;
    width: 15rem;
    padding: 0 1.2rem;
    font-size: 0.82rem;
    color: #888;
}
.sidebar-help-footer a {
    color: #888;
    text-decoration: none;
}
.sidebar-help-footer a:hover {
    color: #333;
    text-decoration: underline;
}
</style>
<div class="sidebar-help-footer">
    <a href="/使用說明" target="_self">📖 使用說明</a>
</div>
""",
        unsafe_allow_html=True,
    )
