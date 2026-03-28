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
        padding-top: 1.25rem !important;
        padding-bottom: 5.5rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }

    .top-space {
        height: 18px;
    }

    .hero-gradient {
        height: 138px;
        border-radius: 28px;
        background: linear-gradient(135deg, #312e81 0%, #4338ca 55%, #7c3aed 100%);
        box-shadow: 0 18px 42px rgba(67, 56, 202, 0.20);
        margin-bottom: -46px;
    }

    .hero-card {
        position: relative;
        background: rgba(255, 255, 255, 0.98);
        border: 1px solid #e5e7eb;
        border-radius: 26px;
        padding: 1.05rem 1rem 0.95rem 1rem;
        box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
        margin-bottom: 0.85rem;
    }

    .hero-badge {
        display: inline-block;
        background: #eef2ff;
        color: #4338ca;
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 0.7rem;
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.04;
        letter-spacing: -0.02em;
        color: #111827;
        margin-bottom: 0.5rem;
    }

    .hero-subtitle {
        font-size: 0.98rem;
        line-height: 1.45;
        color: #6b7280;
        margin-bottom: 0.55rem;
    }

    .quote-box {
        background: linear-gradient(135deg, #eff6ff 0%, #eef2ff 100%);
        border: 1px solid #c7d2fe;
        border-radius: 18px;
        padding: 0.9rem 1rem;
        margin-top: 0.45rem;
    }

    .quote-text {
        color: #3730a3;
        font-size: 0.95rem;
        line-height: 1.48;
        font-weight: 700;
        margin-bottom: 0.35rem;
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
        padding: 0.95rem;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        margin-bottom: 0.75rem;
    }

    .section-title {
        font-size: 1.04rem;
        font-weight: 800;
        color: #111827;
        margin-bottom: 0.25rem;
    }

    .section-subtitle {
        color: #6b7280;
        font-size: 0.93rem;
        line-height: 1.45;
        margin-bottom: 0;
    }

    .launcher-wrap {
        margin-top: 0.2rem;
        margin-bottom: 0.2rem;
    }

    .launcher-wrap div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 68px;
        border-radius: 22px;
        font-weight: 700;
        font-size: 1.05rem;
        border: none;
        background: linear-gradient(135deg, #4338ca 0%, #7c3aed 100%);
        color: white;
        box-shadow: 0 8px 18px rgba(99, 102, 241, 0.16);
        text-align: left;
        padding-left: 1rem;
        margin-bottom: 0.65rem;
    }

    .launcher-wrap div[data-testid="stButton"] > button:hover {
        filter: brightness(1.03);
    }

    .logout-wrap {
        margin-top: 0.25rem;
        margin-bottom: 0.7rem;
    }

    .logout-wrap div[data-testid="stButton"] > button {
        min-height: 40px;
        border-radius: 14px;
        background: #ffffff;
        color: #111827;
        border: 1px solid #e5e7eb;
        box-shadow: none;
        font-size: 0.9rem;
        white-space: nowrap;
        margin-bottom: 0;
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

    .pin-wrap div[data-testid="stButton"] > button {
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

    @media (max-width: 768px) {
        .block-container {
            max-width: 100%;
            padding-top: 1rem !important;
            padding-bottom: 6rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        .top-space {
            height: 12px;
        }

        .hero-gradient {
            height: 126px;
            border-radius: 26px;
            margin-bottom: -42px;
        }

        .hero-card {
            border-radius: 24px;
            padding: 0.95rem 0.95rem 0.9rem 0.95rem;
        }

        .hero-title {
            font-size: 1.75rem;
            margin-bottom: 0.42rem;
        }

        .hero-subtitle {
            font-size: 0.95rem;
            margin-bottom: 0.45rem;
        }

        .quote-box {
            padding: 0.85rem 0.9rem;
            margin-top: 0.35rem;
        }

        .quote-text {
            font-size: 0.92rem;
            line-height: 1.42;
        }

        .launcher-wrap div[data-testid="stButton"] > button {
            min-height: 64px;
            font-size: 1rem;
            border-radius: 20px;
            padding-left: 0.95rem;
            margin-bottom: 0.58rem;
        }

        .logout-wrap {
            margin-top: 0.1rem;
            margin-bottom: 0.5rem;
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

    st.markdown('<div class="pin-wrap">', unsafe_allow_html=True)
    if st.button("Odemknout aplikaci"):
        if pin_input == PIN:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Neplatný PIN.")
    st.markdown('</div>', unsafe_allow_html=True)

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

st.markdown('<div class="launcher-wrap">', unsafe_allow_html=True)

if st.button("💼  Portfolio"):
    st.switch_page("pages/1_Portfolio_Overview.py")

if st.button("₿  Kryptoměny"):
    st.switch_page("pages/2_Crypto_Tracker.py")

if st.button("📈  XTB"):
    st.switch_page("pages/3_Invest_Tracker.py")

if st.button("🏡  Investown"):
    st.switch_page("pages/4_Investown_Tracker.py")

st.markdown('</div>', unsafe_allow_html=True)