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
        max-width: 820px;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }

    .main > div {
        padding-top: 0 !important;
    }

    .start-shell {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        position: relative;
        padding: 1.1rem 0 1.4rem 0;
        background:
            radial-gradient(circle at top left, rgba(99, 102, 241, 0.18), transparent 32%),
            radial-gradient(circle at top right, rgba(236, 72, 153, 0.12), transparent 28%),
            linear-gradient(180deg, #f8fafc 0%, #eef2ff 45%, #ffffff 100%);
    }

    .start-shell::before {
        content: "";
        position: absolute;
        top: 28px;
        left: 18px;
        right: 18px;
        height: 220px;
        border-radius: 34px;
        background: linear-gradient(135deg, #312e81 0%, #4338ca 52%, #7c3aed 100%);
        box-shadow: 0 18px 40px rgba(49, 46, 129, 0.22);
        z-index: 0;
    }

    .welcome-hero {
        position: relative;
        z-index: 1;
        color: white;
        padding: 2rem 1.5rem 5.6rem 1.5rem;
    }

    .welcome-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.16);
        border: 1px solid rgba(255, 255, 255, 0.18);
        color: #ffffff;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 1rem;
        backdrop-filter: blur(6px);
    }

    .welcome-title {
        font-size: 2.35rem;
        font-weight: 800;
        line-height: 1.02;
        margin-bottom: 0.8rem;
        letter-spacing: -0.02em;
    }

    .welcome-subtitle {
        font-size: 1rem;
        line-height: 1.55;
        color: rgba(255, 255, 255, 0.9);
        max-width: 480px;
    }

    .login-card {
        position: relative;
        z-index: 2;
        margin-top: -2.6rem;
        background: rgba(255, 255, 255, 0.94);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.7);
        border-radius: 28px;
        padding: 1.35rem 1.1rem 1.15rem 1.1rem;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
    }

    .login-title {
        font-size: 1.18rem;
        font-weight: 800;
        color: #111827;
        margin-bottom: 0.3rem;
    }

    .login-subtitle {
        color: #6b7280;
        font-size: 0.96rem;
        line-height: 1.5;
        margin-bottom: 1rem;
    }

    .security-strip {
        margin-top: 0.9rem;
        background: linear-gradient(135deg, #fef3c7 0%, #fff7ed 100%);
        border: 1px solid #fde68a;
        border-radius: 18px;
        padding: 0.9rem 1rem;
        color: #92400e;
        font-size: 0.92rem;
        line-height: 1.45;
        font-weight: 600;
    }

    .bottom-note {
        position: relative;
        z-index: 1;
        text-align: center;
        color: #94a3b8;
        font-size: 0.8rem;
        margin-top: 1rem;
        padding-bottom: 0.6rem;
    }

    div[data-testid="stTextInput"] {
        margin-top: 0.2rem;
        margin-bottom: 0.9rem;
    }

    div[data-testid="stTextInput"] input {
        min-height: 54px;
        border-radius: 16px;
        border: 1px solid #dbe2ea;
        background: #ffffff;
        font-size: 1rem;
        padding-left: 0.9rem;
    }

    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 56px;
        border-radius: 18px;
        font-weight: 800;
        font-size: 1rem;
        border: none;
        background: linear-gradient(135deg, #4338ca 0%, #7c3aed 100%);
        color: white;
        box-shadow: 0 10px 24px rgba(99, 102, 241, 0.25);
    }

    div[data-testid="stButton"] > button:hover {
        filter: brightness(1.03);
    }

    .home-shell {
        min-height: 100vh;
        padding: 1rem 0 2rem 0;
        background:
            radial-gradient(circle at top left, rgba(99, 102, 241, 0.10), transparent 24%),
            linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
    }

    .top-actions {
        margin-bottom: 0.8rem;
    }

    .top-actions div[data-testid="stButton"] > button {
        min-height: 44px;
        border-radius: 14px;
        font-size: 0.92rem;
        box-shadow: none;
        background: #ffffff;
        color: #111827;
        border: 1px solid #e5e7eb;
    }

    .dashboard-hero {
        background: linear-gradient(135deg, #312e81 0%, #4338ca 55%, #7c3aed 100%);
        color: white;
        border-radius: 28px;
        padding: 1.45rem 1.2rem;
        box-shadow: 0 18px 42px rgba(67, 56, 202, 0.22);
        margin-bottom: 1rem;
    }

    .dashboard-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.14);
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 999px;
        padding: 5px 11px;
        font-size: 0.76rem;
        font-weight: 700;
        margin-bottom: 0.9rem;
    }

    .dashboard-title {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.03;
        margin-bottom: 0.55rem;
    }

    .dashboard-subtitle {
        color: rgba(255, 255, 255, 0.9);
        font-size: 0.97rem;
        line-height: 1.5;
    }

    .menu-panel {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 24px;
        padding: 1rem 1rem 0.9rem 1rem;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
        margin-bottom: 1rem;
    }

    .panel-title {
        font-size: 1.08rem;
        font-weight: 800;
        color: #111827;
        margin-bottom: 0.25rem;
    }

    .panel-subtitle {
        color: #6b7280;
        font-size: 0.94rem;
        line-height: 1.45;
        margin-bottom: 0.9rem;
    }

    .soft-note {
        background: linear-gradient(135deg, #eff6ff 0%, #eef2ff 100%);
        border: 1px solid #c7d2fe;
        border-radius: 18px;
        padding: 0.95rem 1rem;
        color: #3730a3;
        font-weight: 600;
        margin-top: 1rem;
    }

    .security-note {
        background: linear-gradient(135deg, #fff7ed 0%, #fef3c7 100%);
        border: 1px solid #fed7aa;
        border-radius: 18px;
        padding: 0.95rem 1rem;
        color: #9a3412;
        font-weight: 600;
        margin-top: 0.8rem;
    }

    .footer-version {
        text-align: center;
        color: #9ca3af;
        font-size: 0.78rem;
        margin-top: 1rem;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }

        .start-shell::before {
            left: 8px;
            right: 8px;
            top: 14px;
            height: 240px;
            border-radius: 28px;
        }

        .welcome-hero {
            padding: 1.45rem 1rem 5.2rem 1rem;
        }

        .welcome-title {
            font-size: 2.05rem;
        }

        .welcome-subtitle {
            font-size: 0.95rem;
        }

        .login-card {
            border-radius: 24px;
            padding: 1.1rem 0.95rem 1rem 0.95rem;
        }

        .dashboard-hero {
            border-radius: 24px;
            padding: 1.2rem 1rem;
        }

        .dashboard-title {
            font-size: 1.8rem;
        }

        .menu-panel {
            border-radius: 20px;
            padding: 0.95rem 0.9rem 0.85rem 0.9rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="start-shell">', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="welcome-hero">
            <div class="welcome-badge">MY PORTFOLIO</div>
            <div class="welcome-title">Vítej zpět</div>
            <div class="welcome-subtitle">
                Bezpečný vstup do přehledu investic, krypta a portfolia.
                Vše důležité přehledně na jednom místě.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="login-card">
            <div class="login-title">Přihlášení pomocí PIN</div>
            <div class="login-subtitle">
                Aplikace obsahuje citlivé finanční údaje. Pro pokračování zadej svůj PIN.
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
        """
        <div class="security-strip">
            Po dokončení práce se můžeš kdykoliv odhlásit a aplikaci znovu zamknout.
        </div>
        </div>
        <div class="bottom-note">Soukromý přístup chráněný PIN kódem</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()

st.markdown('<div class="home-shell">', unsafe_allow_html=True)

top_left, top_right = st.columns([3, 1])
with top_right:
    st.markdown('<div class="top-actions">', unsafe_allow_html=True)
    if st.button("Odhlásit se"):
        st.session_state.authenticated = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="dashboard-hero">
        <div class="dashboard-badge">DASHBOARD</div>
        <div class="dashboard-title">My Portfolio</div>
        <div class="dashboard-subtitle">
            Vyber sekci, do které chceš vstoupit. Rozcestník je navržený pro mobil,
            čistý vzhled a rychlý přístup.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="menu-panel">
        <div class="panel-title">Hlavní sekce</div>
        <div class="panel-subtitle">
            Portfolio overview, crypto tracker, invest tracker a Investown tracker.
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
    <div class="security-note">
        Kvůli ochraně citlivých údajů se můžeš kdykoliv vrátit na zamčenou obrazovku tlačítkem „Odhlásit se“.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="soft-note">
        Aplikace byla úspěšně aktualizována.
    </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="footer-version">VERZE MOBILE UI 27-03</div>', unsafe_allow_html=True)