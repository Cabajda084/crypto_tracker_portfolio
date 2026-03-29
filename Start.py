from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="My Portfolio",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

PIN = "0602"
PROFILE_IMAGE = Path("assets/profile.jpeg")

st.markdown(
    """
    <style>
    [data-testid="stHeader"] { display: none; }
    [data-testid="stToolbar"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    .block-container {
        max-width: 560px;
        padding-top: 0.9rem !important;
        padding-bottom: 7rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }

    .top-space {
        height: 8px;
    }

    .hero-gradient {
        height: 112px;
        border-radius: 28px;
        background: linear-gradient(135deg, #312e81 0%, #4338ca 55%, #7c3aed 100%);
        box-shadow: 0 18px 42px rgba(67, 56, 202, 0.18);
        margin-bottom: -34px;
    }

    .hero-card {
        background: rgba(255, 255, 255, 0.98);
        border: 1px solid #e5e7eb;
        border-radius: 26px;
        padding: 1rem 1rem 0.95rem 1rem;
        box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
        margin-bottom: 0.85rem;
    }

    .hero-title {
        font-size: 1.95rem;
        font-weight: 800;
        line-height: 1.04;
        letter-spacing: -0.02em;
        color: #111827;
        margin-bottom: 0.45rem;
        text-align: center;
    }

    .hero-subtitle {
        font-size: 0.98rem;
        line-height: 1.45;
        color: #6b7280;
        margin-bottom: 0.45rem;
        text-align: center;
    }

    .quote-box {
        background: linear-gradient(135deg, #eff6ff 0%, #eef2ff 100%);
        border: 1px solid #c7d2fe;
        border-radius: 18px;
        padding: 0.9rem 1rem;
        margin-top: 0.35rem;
    }

    .quote-text {
        color: #3730a3;
        font-size: 0.95rem;
        line-height: 1.46;
        font-weight: 700;
        margin-bottom: 0.35rem;
        text-align: center;
    }

    .quote-author {
        color: #6366f1;
        font-size: 0.82rem;
        font-weight: 600;
        text-align: center;
    }

    .photo-row {
        margin-top: -14px;
        margin-bottom: 0.8rem;
    }

    .logout-note {
        margin-top: 0.15rem;
        margin-bottom: 0.75rem;
    }

    .launcher-space {
        height: 0.25rem;
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
        min-height: 66px;
        border-radius: 22px;
        font-weight: 700;
        font-size: 1.03rem;
        border: none;
        background: linear-gradient(135deg, #4338ca 0%, #7c3aed 100%);
        color: white;
        box-shadow: 0 8px 18px rgba(99, 102, 241, 0.18);
        text-align: left;
        padding-left: 1rem;
        margin-bottom: 0.62rem;
    }

    div[data-testid="stButton"] > button:hover {
        filter: brightness(1.03);
    }

    .center-button div[data-testid="stButton"] > button {
        text-align: center;
        padding-left: 0 !important;
    }

    @media (max-width: 768px) {
        .block-container {
            max-width: 100%;
            padding-top: 0.85rem !important;
            padding-bottom: 7.4rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        .hero-gradient {
            height: 104px;
            border-radius: 26px;
            margin-bottom: -30px;
        }

        .hero-card {
            border-radius: 24px;
            padding: 0.95rem 0.95rem 0.9rem 0.95rem;
        }

        .hero-title {
            font-size: 1.72rem;
            margin-bottom: 0.4rem;
        }

        .hero-subtitle {
            font-size: 0.95rem;
            margin-bottom: 0.42rem;
        }

        .quote-box {
            padding: 0.82rem 0.9rem;
        }

        .quote-text {
            font-size: 0.91rem;
            line-height: 1.4;
        }

        .photo-row {
            margin-top: -10px;
            margin-bottom: 0.7rem;
        }

        div[data-testid="stButton"] > button {
            min-height: 64px;
            font-size: 1rem;
            border-radius: 20px;
            padding-left: 0.95rem;
            margin-bottom: 0.56rem;
        }

        .center-button div[data-testid="stButton"] > button {
            padding-left: 0 !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def render_header(title: str, subtitle: str, show_quote: bool = False):
    st.markdown('<div class="top-space"></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-gradient"></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-card">', unsafe_allow_html=True)

    if PROFILE_IMAGE.exists():
        st.markdown('<div class="photo-row">', unsafe_allow_html=True)
        left, center, right = st.columns([1, 2, 1])
        with center:
            st.image(str(PROFILE_IMAGE), width=180)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="hero-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-subtitle">{subtitle}</div>', unsafe_allow_html=True)

    if show_quote:
        st.markdown(
            """
            <div class="quote-box">
                <div class="quote-text">„Inflace nikdy nespí. Tvoje peníze by také neměly.“</div>
                <div class="quote-author">Lucie Cabáková</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


if not st.session_state.authenticated:
    render_header(
        "Moje portfolio",
        "Možná není perfektní, ale je moje.",
        show_quote=True,
    )

    pin_input = st.text_input(
        "PIN",
        type="password",
        placeholder="Zadej PIN",
        label_visibility="collapsed",
    )

    st.markdown('<div class="center-button">', unsafe_allow_html=True)
    left, center, right = st.columns([1, 2, 1])
    with center:
        if st.button("Odemknout aplikaci"):
            if pin_input == PIN:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Neplatný PIN.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

render_header(
    "Moje portfolio",
    "Možná není perfektní, ale je moje.",
    show_quote=True,
)

st.markdown('<div class="logout-note"></div>', unsafe_allow_html=True)

st.markdown('<div class="center-button">', unsafe_allow_html=True)
left, center, right = st.columns([1, 2, 1])
with center:
    if st.button("Odhlásit se"):
        st.session_state.authenticated = False
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="launcher-space"></div>', unsafe_allow_html=True)

if st.button("💼  Portfolio"):
    st.switch_page("pages/1_Portfolio_Overview.py")

if st.button("₿  Kryptoměny"):
    st.switch_page("pages/2_Crypto_Tracker.py")

if st.button("📈  XTB"):
    st.switch_page("pages/3_Invest_Tracker.py")

if st.button("🏡  Investown"):
    st.switch_page("pages/4_Investown_Tracker.py")