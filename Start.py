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

st.markdown("""
<style>

[data-testid="stHeader"] {display:none;}
[data-testid="stToolbar"] {display:none;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

.block-container{
    max-width:520px;
    padding-top:0.5rem;
    padding-bottom:2rem;
}

/* gradient header */

.hero-gradient{
height:140px;
border-radius:28px;
background: linear-gradient(135deg,#312e81 0%,#4338ca 50%,#7c3aed 100%);
margin-bottom:20px;
}

/* photo */

.photo{
display:flex;
justify-content:center;
margin-top:-80px;
margin-bottom:10px;
}

.photo img{
border-radius:20px;
box-shadow:0 10px 25px rgba(0,0,0,0.15);
}

/* title */

.title{
text-align:center;
font-size:28px;
font-weight:800;
margin-top:5px;
}

.subtitle{
text-align:center;
color:#6b7280;
margin-bottom:15px;
}

/* quote */

.quote{
background:#eef2ff;
border-radius:18px;
padding:14px;
text-align:center;
border:1px solid #c7d2fe;
margin-bottom:15px;
}

.quote-author{
color:#6366f1;
font-size:13px;
margin-top:5px;
}

/* input */

div[data-testid="stTextInput"] input{
height:55px;
border-radius:14px;
}

/* center button */

.center-btn button{
width:100%;
height:60px;
border-radius:18px;
background: linear-gradient(135deg,#4338ca,#7c3aed);
color:white;
font-weight:600;
}

</style>
""", unsafe_allow_html=True)


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def header():

    st.markdown('<div class="hero-gradient"></div>', unsafe_allow_html=True)

    if PROFILE_IMAGE.exists():
        st.markdown('<div class="photo">', unsafe_allow_html=True)
        st.image(str(PROFILE_IMAGE), width=170)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="title">Moje portfolio</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Možná není perfektní, ale je moje.</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="quote">
    „Inflace nikdy nespí. Tvoje peníze by také neměly.“
    <div class="quote-author">Lucie Cabáková</div>
    </div>
    """, unsafe_allow_html=True)


# PIN SCREEN
if not st.session_state.authenticated:

    header()

    pin = st.text_input(
        "PIN",
        type="password",
        placeholder="Zadej PIN",
        label_visibility="collapsed"
    )

    st.markdown('<div class="center-btn">', unsafe_allow_html=True)

    if st.button("Odemknout aplikaci"):
        if pin == PIN:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Neplatný PIN")

    st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


# APP

header()

st.markdown('<div class="center-btn">', unsafe_allow_html=True)

if st.button("Odhlásit se"):
    st.session_state.authenticated = False
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

st.write("")

if st.button("💼 Portfolio"):
    st.switch_page("pages/1_Portfolio_Overview.py")

if st.button("₿ Kryptoměny"):
    st.switch_page("pages/2_Crypto_Tracker.py")

if st.button("📈 XTB"):
    st.switch_page("pages/3_Invest_Tracker.py")

if st.button("🏡 Investown"):
    st.switch_page("pages/4_Investown_Tracker.py")