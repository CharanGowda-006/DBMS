import html

import streamlit as st


_STATUS_STYLES = {
    "APPROVED": ("#15803d", "Approved"),
    "PENDING": ("#b45309", "Pending"),
    "REJECTED": ("#b91c1c", "Rejected"),
    "ARCHIVED": ("#64748b", "Archived"),
    "ACTIVE": ("#15803d", "Active"),
    "INACTIVE": ("#64748b", "Inactive"),
}


def install_styles():
    st.markdown(
        """
        <style>
        html, body {
            font-family: Inter, "Segoe UI", sans-serif;
        }
        [data-testid="stMetric"] {
            border: 1px solid color-mix(in srgb, currentColor 16%, transparent);
            border-radius: 12px;
            padding: 0.9rem 1rem;
            background: color-mix(in srgb, currentColor 4%, transparent);
        }
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            border-radius: 10px;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid color-mix(in srgb, currentColor 14%, transparent);
        }
        [data-testid="stSidebarNav"] {
            padding-top: 0.35rem;
        }
        [data-testid="stAlert"] {
            border-radius: 10px;
        }
        [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button {
            border-radius: 9px;
            min-height: 2.55rem;
        }
        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus,
        [data-testid="stSelectbox"] [role="combobox"]:focus {
            outline: 2px solid var(--primary-color);
            outline-offset: 1px;
        }
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px;
        }
        @media (max-width: 720px) {
            [data-testid="stMetricValue"] { font-size: 1.45rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title, subtitle=None):
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def section_header(title, description=None):
    st.subheader(title)
    if description:
        st.caption(description)


def empty_state(message):
    st.info(message)


def status_badge(status):
    key = str(status).upper()
    color, label = _STATUS_STYLES.get(key, ("#64748b", str(status).title()))
    st.markdown(
        f'<span style="display:inline-block;padding:0.18rem 0.55rem;'
        f'border-radius:999px;border:1px solid {color};color:{color};'
        f'font-size:0.78rem;font-weight:600">{html.escape(label)}</span>',
        unsafe_allow_html=True,
    )
