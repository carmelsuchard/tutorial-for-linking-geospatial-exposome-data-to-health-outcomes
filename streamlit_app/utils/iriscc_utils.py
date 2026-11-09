import base64
import io

import matplotlib.pyplot as plt

# import pandas as pd
import streamlit as st


def apply_app_style():
    st.markdown(
        """
        <style>
        :root {
            --iriscc-primary: #123b5d;
            --iriscc-accent: #f59e0b;
            --iriscc-accent-soft: rgba(245, 158, 11, 0.12);
            --iriscc-accent-strong: #d97706;
            --iriscc-surface: rgba(255, 255, 255, 0.84);
            --iriscc-surface-strong: rgba(255, 255, 255, 0.96);
            --iriscc-border: rgba(16, 24, 40, 0.10);
            --iriscc-text: #102133;
            --iriscc-muted: #5f6b7a;
            --iriscc-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(245, 158, 11, 0.12), transparent 28%),
                radial-gradient(circle at top right, rgba(18, 59, 93, 0.10), transparent 30%),
                linear-gradient(180deg, #f6f8fb 0%, #eef3f8 100%);
            color: var(--iriscc-text);
        }

        section.main > div {
            padding-top: 1.5rem;
            max-width: 1220px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #10263c 0%, #123b5d 100%);
        }

        [data-testid="stSidebar"] * {
            color: #f6fbff;
        }

        [data-testid="stSidebar"] a {
            color: #d9efff;
        }

        [data-testid="stSidebarNav"] {
            padding-top: 0.5rem;
        }

        div[data-testid="stHeader"] {
            display: none;
        }

        div[data-testid="stHeader"] + div {
            padding-top: 0;
        }

        div[data-testid="stTitle"] h1,
        .stTitle h1,
        .iriscc-page-title {
            color: var(--iriscc-text);
            letter-spacing: -0.03em;
            font-weight: 800;
            line-height: 1.08;
        }

        h2, h3, h4, h5, h6 {
            color: var(--iriscc-text);
            letter-spacing: -0.02em;
        }

        p, li, div, span, label {
            color: var(--iriscc-text);
        }

        .stMarkdown p {
            color: var(--iriscc-text);
            line-height: 1.65;
        }

        .stInfo, .stWarning, .stSuccess, .stError {
            border-radius: 16px;
            border: 1px solid var(--iriscc-border);
            box-shadow: var(--iriscc-shadow);
        }

        .stInfo {
            border-left: 4px solid var(--iriscc-accent);
            background: linear-gradient(180deg, rgba(255, 249, 240, 0.96), rgba(255, 255, 255, 0.98));
        }

        .stRadio > div,
        .stSelectbox > div,
        [data-baseweb="select"] > div,
        [data-testid="stRadio"] {
            accent-color: var(--iriscc-accent) !important;
        }

        div[role="radiogroup"] label,
        div[role="radiogroup"] span,
        div[role="radiogroup"] div {
            font-size: 1.08rem !important;
        }

        .stRadio [role="radio"] {
            border-color: var(--iriscc-accent) !important;
        }

        .stRadio input:checked + div,
        .stRadio input:checked + span {
            color: var(--iriscc-accent) !important;
        }

        [data-testid="stDataFrame"] {
            border-radius: 18px;
            box-shadow: var(--iriscc-shadow);
            overflow: hidden;
        }

        [data-testid="stExpander"] {
            border-radius: 18px;
            background: var(--iriscc-surface);
            border: 1px solid var(--iriscc-border);
            box-shadow: var(--iriscc-shadow);
        }

        [data-testid="stHorizontalBlock"] {
            gap: 1rem;
        }

        .stButton > button {
            border-radius: 999px;
            border: 1px solid rgba(16, 24, 40, 0.10);
            background: var(--iriscc-surface-strong);
            color: var(--iriscc-text);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
            transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            border-color: rgba(245, 158, 11, 0.55);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
        }

        .stButton > button:focus-visible {
            outline: 3px solid rgba(245, 158, 11, 0.22);
            outline-offset: 2px;
        }

        .iriscc-page-header,
        .iriscc-hero {
            border-radius: 28px;
            padding: 2rem 2rem 1.6rem 2rem;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(233, 239, 246, 0.90)),
                radial-gradient(circle at top right, rgba(15, 118, 110, 0.12), transparent 30%),
                radial-gradient(circle at bottom left, rgba(18, 59, 93, 0.10), transparent 28%);
            border: 1px solid rgba(16, 24, 40, 0.10);
            box-shadow: 0 24px 48px rgba(15, 23, 42, 0.10);
            margin-bottom: 1.25rem;
        }

        .iriscc-page-title {
            margin: 0;
            font-size: clamp(2.2rem, 3.2vw, 3.2rem);
            line-height: 1.08;
            letter-spacing: -0.04em;
            color: var(--iriscc-text);
        }

        .iriscc-subtitle,
        .iriscc-instruction,
        .iriscc-body,
        .iriscc-copy,
        .iriscc-note-content,
        .iriscc-page-copy {
            color: #425466;
            line-height: 1.8;
            font-size: 1.18rem;
        }

        .iriscc-card-grid,
        .iriscc-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
            margin: 1.3rem 0 0.4rem 0;
        }
        .iriscc-grid2 {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1rem;
            margin: 1.3rem 0 0.4rem 0;
        }

        .iriscc-card {
            border-radius: 18px;
            border: 1px solid var(--iriscc-border);
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 252, 0.95));
            box-shadow: var(--iriscc-shadow);
            padding: 1rem 1rem 0.95rem 1rem;
            transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
            height: 100%;
        }

        .iriscc-card.is-selected {
            border-color: rgba(18, 59, 93, 0.34);
            background: linear-gradient(180deg, rgba(230, 242, 252, 0.96), rgba(247, 250, 252, 0.98));
        }

        .iriscc-card:hover {
            transform: translateY(-1px);
            box-shadow: 0 20px 42px rgba(15, 23, 42, 0.12);
        }

        .iriscc-card-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--iriscc-text);
            margin-bottom: 0.2rem;
        }

        .iriscc-card-subtitle,
        .iriscc-card p,
        .iriscc-copy p,
        .iriscc-note-content p {
            color: var(--iriscc-muted);
            font-size: 1.2rem;
            line-height: 1.45;
        }

        .iriscc-card h3,
        .iriscc-copy h3 {
            margin: 0 0 0.45rem 0;
            font-size: 1.38rem;
        }

        .iriscc-card-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            padding: 0.22rem 0.65rem;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            background: rgba(15, 118, 110, 0.10);
            color: var(--iriscc-accent);
            margin-bottom: 0.7rem;
        }

        .iriscc-story {
            display: grid;
            gap: 1rem;
            margin-top: 1.25rem;
        }

        .iriscc-story-row,
        .iriscc-note {
            display: grid;
            grid-template-columns: 52px minmax(0, 1fr);
            gap: 1rem;
            align-items: start;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(16, 24, 40, 0.08);
            border-left: 4px solid #f59e0b;
            border-radius: 20px;
            padding: 1rem 1.1rem 1rem 1rem;
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.05);
        }

        .iriscc-icon,
        .iriscc-note-icon {
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 14px;
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(251, 191, 36, 0.10));
            font-size: 1.6rem;
            box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.18);
        }

        .iriscc-note {
            margin-top: 1.2rem;
            padding: 1rem 1.1rem;
            border-radius: 18px;
            border: 1px solid rgba(245, 158, 11, 0.25);
            background: linear-gradient(135deg, rgba(255, 247, 237, 0.95), rgba(255, 255, 255, 0.9));
            box-shadow: 0 12px 28px rgba(245, 158, 11, 0.08);
        }

        .iriscc-note-content strong {
            display: inline-block;
            margin-bottom: 0.38rem;
            color: #7c4a00;
            font-size: 1.02rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .iriscc-section-title {
            margin-top: 1.4rem;
            margin-bottom: 0.5rem;
            font-size: 1.45rem;
            letter-spacing: -0.02em;
        }

        [data-testid="stTabs"] button {
            font-weight: 800;
        }

        [data-testid="stTabs"] [aria-selected="true"] {
            color: #123b5d;
        }

        .summary-panel {
            padding: 1rem 1.1rem;
            border: 1px solid rgba(16, 24, 40, 0.10);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.72);
        }

        .iriscc-card-grid > .iriscc-card,
        .iriscc-grid > .iriscc-card {
            display: flex;
            flex-direction: column;
        }

        hr {
            border-color: rgba(16, 24, 40, 0.08);
        }

        @media (max-width: 900px) {
            .iriscc-card-grid,
            .iriscc-grid {
                grid-template-columns: 1fr;
            }

            .iriscc-page-header,
            .iriscc-hero {
                padding: 1.4rem 1.1rem 1.2rem 1.1rem;
            }

            .iriscc-story-row,
            .iriscc-note {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_story_block(icon, title, paragraphs):
    paragraph_html = "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)
    st.markdown(
        f"""
        <div class="iriscc-story">
            <div class="iriscc-story-row">
                <div class="iriscc-icon">{icon}</div>
                <div class="iriscc-copy">
                    <h3>{title}</h3>
                    {paragraph_html}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dataframe_to_html(df, max_rows=10):
    table_html = df.to_html(max_rows=max_rows, index=False)
    table_html = table_html.replace(
        "<table", '<table style="display:block; overflow-y:auto; max-height:400px;"'
    )
    return table_html


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def visualize_gdf_as_df(gdf):
    """Return an Arrow-safe preview dataframe for Streamlit tables."""
    preview = gdf.drop(columns=["geometry"], errors="ignore").copy()

    if "geometry" in gdf.columns:
        try:
            preview["longitude"] = gdf.geometry.x
            preview["latitude"] = gdf.geometry.y
        except Exception:
            preview["longitude"] = None
            preview["latitude"] = None

    return preview
