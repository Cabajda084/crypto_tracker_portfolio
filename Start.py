import streamlit as st
from ui.styles import load_styles

st.set_page_config(
    page_title="My Portfolio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_styles()

PIN = "0602"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown(
        """
        <div class="hero-card">
            <div class="app-title">🔐 My Portfolio</div>
            <div class="app-subtitle">Soukromý přehled tvého portfolia v mobilu i na PC.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="pin-card">
            <div class="section-title">Zabezpečený vstup</div>
            <div class="section-subtitle">Pro vstup do aplikace zadej PIN.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pin_input = st.text_input(
        "PIN",
        type="password",
        placeholder="••••",
        label_visibility="collapsed",
    )

    if st.button("Odemknout"):
        if pin_input == PIN:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Neplatný PIN.")

    st.stop()

st.markdown(
    """
    <div class="hero-card">
        <div class="app-title">📊 My Portfolio</div>
        <div class="app-subtitle">Vyber sekci. Na mobilu už nemusíš používat boční menu.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="menu-card">
        <div class="section-title">Hlavní sekce</div>
        <div class="section-subtitle">Rychlý vstup do jednotlivých částí aplikace.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2 = st.columns(2)
with c1:
    if st.button("Portfolio Overview"):
        st.switch_page("pages/1_Portfolio_Overview.py")
with c2:
    if st.button("Crypto Tracker"):
        st.switch_page("pages/2_Crypto_Tracker.py")

c3, c4 = st.columns(2)
with c3:
    if st.button("Invest Tracker"):
        st.switch_page("pages/3_Invest_Tracker.py")
with c4:
    if st.button("Investown Tracker"):
        st.switch_page("pages/4_Investown_Tracker.py")

st.markdown(
    """
    <div class="note-card">
        Aplikace byla úspěšně aktualizována.
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("VERZE MOBILE UI 27-03")