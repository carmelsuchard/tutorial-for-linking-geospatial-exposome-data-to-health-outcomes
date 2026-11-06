import base64
from pathlib import Path

import streamlit as st

from utils.iriscc_utils import apply_app_style

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(page_title="Linking Tutorial", layout="wide")
apply_app_style()


col1, col2 = st.columns(2)
with col1:
    image_path = BASE_DIR / "Resources" / "ihen_logo.png"
    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    st.markdown(
        f'<img src="data:image/png;base64,{image_data}" width="620">',
        unsafe_allow_html=True,
    )
with col2:
    image_path = BASE_DIR / "Resources" / "iras_logo.png"
    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    st.markdown(
        f'<img src="data:image/png;base64,{image_data}" width="620">',
        unsafe_allow_html=True,
    )

# Streamlit small space buffer
st.markdown(
    """
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="iriscc-page-header">
        <h2 class="iriscc-page-title">Tutorial for Linking Geospatial Exposome Data to Health Outcomes</h2>

    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='iriscc-section-title'><strong>Background</strong></div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="iriscc-body">
        Understanding how environmental exposures relate to health outcomes requires combining exposure data with data from study populations.
        This tutorial provides a general workflow for linking geospatial exposure datasets to cohort data based on location and time.
        <br><br>
        The resulting linked data can be used to explore relationships between exposures and health outcomes. This is a common step in an exposure assessment studies, which aims to find the patterns of exposure to environmental factors. Epidemiologists and public health researchers can use this data to identify causal factors and propose mitigation strategies.
        <br><br>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    "<div class='iriscc-section-title'><strong>What this tutorial does</strong></div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="iriscc-grid">
        <div class="iriscc-card">
            <h3>Select the cohort</h3>
            <p>Based on your research question, define the study population, location data, and exposure variables of interest.</p>
        </div>
        <div class="iriscc-card">
            <h3>Link exposures</h3>
            <p>Match selected exposure variables to cohort locations and time periods.</p>
        </div>
        <div class="iriscc-card">
            <h3>Explore the results</h3>
            <p>Analyze and visualize the linked dataset to understand patterns of risk.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.space("medium")

st.markdown(
    """
    <div class="iriscc-body">
        Use the navigation bar on the left to move through the workflow!
    </div>
    """,
    unsafe_allow_html=True,
)
