import base64
from pathlib import Path

import streamlit as st

from utils.iriscc_utils import apply_app_style

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(page_title="IRISCC Demonstrator", layout="wide")
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
        Summer in Europe is increasingly marked by two overlapping threats to health: extreme heat and poor air quality.
        Research has shown that combined exposure to these environmental risk factors presents a greater risk to health than the sum of their individual risks [<a href="https://www.eea.europa.eu/en/newsroom/editorial/combined-effects-of-air-pollution-and-heat-exposure">1</a>].
        Worryingly, climate change is projected to not only increase the frequency and intensity of heatwaves, but to impact the emission of air pollutants during extreme events.
        <br><br>
        This demonstrator allows you to link data on air pollutants and temperature to existing cohorts, thereby revealing spatial patterns and enabling the analysis 
        of how these exposures may be linked to health outcomes. This is a key workflow in Health Risk Assessments (HRA).
        <br><br>        
        These insights can be used to guide urban design, build resilient healthcare systems,
        inform local public health interventions, and develop strategic public policy (at national and global levels) that addresses health considerations [<a href="https://sciencemediahub.eu/2026/07/15/a-scientists-opinion-interview-with-prof-dr-roel-vermeulen-on-extreme-weather-and-the-impact-on-our-health/">2</a>].
        <br><br>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    "<div class='iriscc-section-title'><strong>What this demonstrator does</strong></div>",
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="iriscc-body">
        The demonstrator integrates climate data (temperature, both retrospective and prospective), air-quality measurements (pollutant concentrations), and (residential) address data of study cohorts. The workflow demonstrates how to link exposures to locations to derive scientific insights.
        <br><br>
        You'll do these steps:
    </div>
    """,
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
            <h3>Attach exposures</h3>
            <p>Match temperature and air-quality data to each address at the relevant time.</p>
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
