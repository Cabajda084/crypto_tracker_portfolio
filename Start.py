import streamlit as st

st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide"
)

PIN = "0602"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Portfolio Dashboard")
    st.markdown("Pro vstup do aplikace zadej PIN.")

    pin_input = st.text_input(
        "PIN",
        type="password",
        placeholder="****"
    )

    if st.button("Odemknout"):
        if pin_input == PIN:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Neplatný PIN.")

    st.stop()

st.title("Portfolio Dashboard")
st.markdown("Vyber sekci v levém menu.")

st.divider()

st.info("Aplikace byla úspěšně aktualizována.")

st.caption("VERZE TEST 27-03 RANO")