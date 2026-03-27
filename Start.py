import streamlit as st

st.set_page_config(
    page_title="My Portfolio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PIN = "0602"

st.markdown(
    """
    <style>
    [data-testid="stHeader"] {
        display: none;
    }

    [data-testid="stToolbar"] {
        display: none;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    .block-container {
        max-width: 760px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    .hero-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e5e7eb;
        border-radius: 24px;
        padding: 24px 22px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        margin-bottom: 1rem;
    }

    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        line-height: 1.05;
        color: #111827;
        margin-bottom: 0.35rem;
    }

    .app-subtitle {
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 0.25rem;
    }

    .pin-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 22px;
        padding: 20px 18px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        margin-top: 1rem;
    }

    .section-title {
        font-size: 1.05rem;
        font-weight: 800;
        color: #111827;
        margin-top: 0.35rem;
        margin-bottom: 0.65rem;
    }

    .section-subtitle {
        color: #6b7280;
        font-size: 0.95rem;
        margin-bottom: 1rem;
    }

    .menu-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 22px;
        padding: 16px 16px 14px 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        margin-top: 1rem;
    }

    .note-card {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 18px;
        padding: 14px 16px;
        color: #1d4ed8;
        font-weight: 600;
        margin-top: 1rem;
    }

    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 52px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 1rem;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 14px;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.8rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            padding-bottom: 1.2rem;
        }

        .hero-card,
        .pin-card,
        .menu-card {
            border-radius: 20px;
        }

        .hero-card {
            padding: 20px 18px;
        }

        .app-title {
            font-size: 1.85rem;
        }

        .app-subtitle {
            font-size: 0.95rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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