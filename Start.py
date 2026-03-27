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
        padding-top: 1rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .hero-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e5e7eb;
        border-radius: 26px;
        padding: 26px 22px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        margin-bottom: 1rem;
    }

    .app-badge {
        display: inline-block;
        background: #eef2ff;
        color: #4338ca;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 6px 10px;
        border-radius: 999px;
        margin-bottom: 0.9rem;
    }

    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        line-height: 1.05;
        color: #111827;
        margin-bottom: 0.45rem;
    }

    .app-subtitle {
        color: #6b7280;
        font-size: 1rem;
        line-height: 1.5;
        margin-bottom: 0;
    }

    .pin-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 22px;
        padding: 20px 18px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        margin-top: 1rem;
        margin-bottom: 1rem;
    }

    .section-title {
        font-size: 1.05rem;
        font-weight: 800;
        color: #111827;
        margin-bottom: 0.5rem;
    }

    .section-subtitle {
        color: #6b7280;
        font-size: 0.95rem;
        line-height: 1.45;
        margin-bottom: 0;
    }

    .menu-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 22px;
        padding: 18px 16px 14px 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        margin-top: 1rem;
        margin-bottom: 1rem;
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

    .security-card {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        border-radius: 18px;
        padding: 14px 16px;
        color: #9a3412;
        font-weight: 600;
        margin-top: 0.75rem;
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
        min-height: 48px;
    }

    .small-caption {
        color: #9ca3af;
        font-size: 0.8rem;
        margin-top: 1rem;
        text-align: center;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.8rem;
            padding-left: 0.85rem;
            padding-right: 0.85rem;
            padding-bottom: 1.2rem;
        }

        .hero-card,
        .pin-card,
        .menu-card {
            border-radius: 20px;
        }

        .hero-card {
            padding: 22px 18px;
        }

        .app-title {
            font-size: 1.95rem;
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

# ===== LOCK SCREEN =====
if not st.session_state.authenticated:
    st.markdown(
        """
        <div class="hero-card">
            <div class="app-badge">MY PORTFOLIO</div>
            <div class="app-title">Zabezpečený vstup</div>
            <div class="app-subtitle">
                Soukromý přehled portfolia pro mobil i desktop.
                Pro pokračování zadej svůj PIN kód.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="pin-card">
            <div class="section-title">Přihlášení</div>
            <div class="section-subtitle">
                Přístup do aplikace je chráněný kvůli citlivým finančním údajům.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pin_input = st.text_input(
        "PIN",
        type="password",
        placeholder="Zadej PIN",
        label_visibility="collapsed",
    )

    if st.button("Odemknout aplikaci"):
        if pin_input == PIN:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Neplatný PIN.")

    st.markdown(
        '<div class="small-caption">Po odemknutí se zobrazí hlavní rozcestník aplikace.</div>',
        unsafe_allow_html=True,
    )

    st.stop()

# ===== LOGOUT BUTTON =====
top_left, top_right = st.columns([3, 1])
with top_right:
    if st.button("Odhlásit se"):
        st.session_state.authenticated = False
        st.rerun()

# ===== HOME =====
st.markdown(
    """
    <div class="hero-card">
        <div class="app-badge">DASHBOARD</div>
        <div class="app-title">My Portfolio</div>
        <div class="app-subtitle">
            Vyber sekci, do které chceš vstoupit. Rozcestník zůstává jednoduchý,
            přehledný a mobilní.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="menu-card">
        <div class="section-title">Hlavní sekce</div>
        <div class="section-subtitle">
            Otevři přehled portfolia, krypta, investic nebo Investown tracker.
        </div>
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
    <div class="security-card">
        Pro ochranu citlivých údajů můžeš aplikaci kdykoliv zamknout tlačítkem „Odhlásit se“.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="note-card">
        Aplikace byla úspěšně aktualizována.
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("VERZE MOBILE UI 27-03")