import streamlit as st


def load_styles():
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
            padding-left: 1rem;
            padding-right: 1rem;
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