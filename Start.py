import streamlit as st

st.set_page_config(
    page_title="My Portfolio",
    page_icon="📊",
    layout="centered",
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
        max-width: 560px;
        padding-top: 0.9rem !important;
        padding-bottom: 1.6rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }

    .top-space {
        height: 10px;
    }

    .hero-gradient {
        height: 170px;
        border-radius: 28px;
        background: linear-gradient(135deg, #312e81 0%, #4338ca 55%, #7c3aed 100%);
        box-shadow: 0 18px 42px rgba(67, 56, 202, 0.22);
        margin-bottom: -64px;
    }

    .hero-card {
        position: relative;
        background: rgba(255, 255, 255, 0.97);
        border: 1px solid #e5e7eb;
        border-radius: 26px;
        padding: 1.25rem 1.05rem 1rem 1.05rem;
        box-shadow: 0 14px 34px rgba(15, 23, 42, 0.10);
        margin-bottom: 1rem;
    }

    .hero-badge {
        display: inline-block;
        background: #eef2ff;
        color: #4338ca;
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 0.85rem;
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.05;
        letter-spacing: -0.02em;
        color: #111827;
        margin-bottom: 0.65rem;
    }

    .hero-subtitle {
        font-size: 0.98rem;
        line-height: 1.55;
        color: #6b7280;
        margin-bottom: 0;
    }

    .section-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 22px;
        padding: 1rem;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        margin-bottom: 0.9rem;
    }

    .section-title {
        font-size: 1.06rem;
        font-weight: 800;
        color: #111827;
        margin-bottom: 0.35rem;
    }

    .section-subtitle {
        color: #6b7280;
        font-size: 0.94rem;
        line-height: 1.5;
        margin-bottom: 0;
    }

    .security-note {
        background: linear-gradient(135deg, #fff7ed 0%, #fef3c7 100%);
        border: 1px solid #fed7aa;
        border-radius: 18px;
        padding: 0.9rem 1rem;
        color: #9a3412;
        font-size: 0.91rem;
        line-height: 1.45;
        font-weight: 600;
        margin-top: 0.85rem;
    }

    .info-note {
        background: linear-gradient(135deg, #eff6ff 0%, #eef2ff 100%);
        border: 1px solid #c7d2fe;
        border-radius: 18px;
        padding: 0.9rem 1rem;
        color: #3730a3;
        font-size: 0.91rem;
        line-height: 1.45;
        font-weight: 600;
        margin-top: 0.85rem;
    }

    .version-note {
        text-align: center;
        color: #9ca3af;
        font-size: 0.78rem;
        margin-top: 1rem;
    }

    div[data-testid="stTextInput"] {
        margin-top: 0.15rem;
        margin-bottom: 0.8rem;
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
        border-radius: 22px;
        font-weight: 700;
        font-size: 1rem;
        border: none;
        background: linear-gradient(135deg, #4338ca 0%, #7c3aed 100%);
        color: white;
        box-shadow: 0 6px 16px rgba(99, 102, 241, 0.20);
    }

    div[data-testid="stButton"] > button:hover {
        filter: brightness(1.03);
    }

    .logout-wrap div[data-testid="stButton"] > button {
        min-height: 42px;
        border-radius: 14px;
        background: #ffffff;
        color: #111827;
        border: 1px solid #e5e7eb;
        box-shadow: none;
        font-size: 0.9rem;
    }

    @media (max-width: 768px) {
        .block-container {
            max-width: 100%;
            padding-top: 0.75rem !important;
            padding-bottom: 1.15rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        .hero-gradient {
            height: 190px;
            border-radius: 26px;
            margin-bottom: -72px;
        }

        .hero-card {
            border-radius: 24px;
            padding: 1.1rem 0.95rem 0.95rem 0.95rem;
        }

        .hero-title {
            font-size: 1.85rem;
        }

        .hero-subtitle {
            font-size: 0.95rem;
        }

        .section-card {
            border-radius: 20px;
            padding: 0.95rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def render_header(badge: str, title: str, subtitle: str):
    st.markdown('<div class="top-space"></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-gradient"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-badge">{badge}</div>
            <div class="hero-title">{title}</div>
            <div class="hero-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if not st.session_state.authenticated:
    render_header(
        "MY PORTFOLIO",
        "Vítej zpět",
        "Bezpečný vstup do přehledu investic, krypta a portfolia. Pro pokračování zadej svůj PIN kód.",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Přihlášení pomocí PIN</div>
            <div class="section-subtitle">
                Aplikace obsahuje citlivé finanční údaje a je chráněná soukromým přístupem.
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
        """
        <div class="security-note">
            Po dokončení práce doporučujeme aplikaci znovu zamknout kvůli ochraně citlivých údajů.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="version-note">Soukromý přístup chráněný PIN kódem</div>',
        unsafe_allow_html=True,
    )

    st.stop()

left, right = st.columns([4, 1])
with right:
    st.markdown('<div class="logout-wrap">', unsafe_allow_html=True)
    if st.button("Odhlásit se"):
        st.session_state.authenticated = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

render_header(
    "DASHBOARD",
    "My Portfolio",
    "Vyber sekci, do které chceš vstoupit. Rozcestník je navržený pro rychlý a přehledný mobilní přístup.",
)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="section-card">
        <div class="section-title">Hlavní sekce</div>
        <div class="section-subtitle">
            Otevři Portfolio Overview, Crypto Tracker, Invest Tracker nebo Investown Tracker.
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
    <div class="security-note">
        Kvůli ochraně citlivých údajů se můžeš kdykoliv vrátit na zamčenou obrazovku tlačítkem „Odhlásit se“.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="info-note">
        Aplikace byla úspěšně aktualizována.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="version-note">VERZE MOBILE UI 27-03</div>',
    unsafe_allow_html=True,
)