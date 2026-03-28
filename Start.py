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
        margin-bottom: 0.6rem;
    }

    .quote-box {
        background: linear-gradient(135deg, #eff6ff 0%, #eef2ff 100%);
        border: 1px solid #c7d2fe;
        border-radius: 18px;
        padding: 0.9rem 1rem;
        margin-top: 0.75rem;
    }

    .quote-text {
        color: #3730a3;
        font-size: 0.95rem;
        line-height: 1.5;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }

    .quote-author {
        color: #6366f1;
        font-size: 0.82rem;
        font-weight: 600;
    }

    .section-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 22px;
        padding: 1rem;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        margin-bottom: 0.9rem;
    }

    .grid-wrap {
        margin-top: 0.35rem;
        margin-bottom: 0.5rem;
    }

    .app-tile button {
        aspect-ratio: 1 / 1;
        min-height: 135px !important;
        border-radius: 24px !important;
        font-weight: 700 !important;
        font-size: 1.02rem !important;
        line-height: 1.35 !important;
        padding: 1rem !important;
        border: none !important;
        background: linear-gradient(135deg, #4338ca 0%, #7c3aed 100%) !important;
        color: white !important;
        box-shadow: 0 10px 22px rgba(99, 102, 241, 0.18) !important;
        white-space: pre-line !important;
    }

    .app-tile button:hover {
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
        white-space: nowrap;
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

        .app-tile button {
            min-height: 128px !important;
            border-radius: 22px !important;
            font-size: 0.98rem !important;
            padding: 0.85rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def render_header(badge: str, title: str, subtitle: str, show_quote: bool = False):
    st.markdown('<div class="top-space"></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-gradient"></div>', unsafe_allow_html=True)

    quote_html = ""
    if show_quote:
        quote_html = """
        <div class="quote-box">
            <div class="quote-text">„Inflace nikdy nespí. Tvoje peníze by také neměly.“</div>
            <div class="quote-author">Lucie Cabáková</div>
        </div>
        """

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-badge">{badge}</div>
            <div class="hero-title">{title}</div>
            <div class="hero-subtitle">{subtitle}</div>
            {quote_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


if not st.session_state.authenticated:
    render_header(
        "MOJE PORTFOLIO",
        "Moje portfolio",
        "Možná není perfektní, ale je moje.",
        show_quote=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Přihlášení pomocí PIN</div>
            <div class="section-subtitle">
                Zadej svůj PIN pro odemknutí aplikace.
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

    st.stop()

left, right = st.columns([4, 1])
with right:
    st.markdown('<div class="logout-wrap">', unsafe_allow_html=True)
    if st.button("Odhlásit se"):
        st.session_state.authenticated = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

render_header(
    "PŘEHLED",
    "Moje portfolio",
    "Možná není perfektní, ale je moje.",
    show_quote=True,
)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="grid-wrap">', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="app-tile">', unsafe_allow_html=True)
    if st.button("💼\nPortfolio"):
        st.switch_page("pages/1_Portfolio_Overview.py")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="app-tile">', unsafe_allow_html=True)
    if st.button("₿\nKryptoměny"):
        st.switch_page("pages/2_Crypto_Tracker.py")
    st.markdown('</div>', unsafe_allow_html=True)

c3, c4 = st.columns(2)
with c3:
    st.markdown('<div class="app-tile">', unsafe_allow_html=True)
    if st.button("📈\nXTB"):
        st.switch_page("pages/3_Invest_Tracker.py")
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="app-tile">', unsafe_allow_html=True)
    if st.button("🏡\nInvestown"):
        st.switch_page("pages/4_Investown_Tracker.py")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)