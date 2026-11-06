import os
import tempfile
import zipfile
from pathlib import Path

import folium
import geopandas as gpd
import streamlit as st
from shapely import wkt
from shapely.geometry import Point
from streamlit.components.v1 import html
from streamlit_folium import st_folium

from utils.iriscc_utils import apply_app_style, visualize_gdf_as_df

BASE_DIR = Path(__file__).resolve().parent.parent

CUSTOM_DATASET_BBOX = (
    -2909511,
    4042059,
    5009377.09,
    11528960,
)

CUSTOM_DATASET_BBOX_CRS = "EPSG:3857"
MAX_UPLOADED_POINTS = 3000

st.set_page_config(page_title="1. Cohort", layout="wide")
apply_app_style()


st.markdown(
    """
    <div class="iriscc-page-header">
        <h2 class="iriscc-page-title">Step 1 — Prepare cohort data</h2>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='iriscc-section-title'><strong>Understanding the cohort</strong></div>",
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="iriscc-grid">
        <div class="iriscc-card">
            <h3>👥 Study population</h3>
            <p>Analysis begins with a study population. Individuals may be recruited for a specific study or selected from a dataset of population health data.
            <br><br>
            Studies are often designed to follow a cohort over time so that changes in health can be linked to changing environmental exposures. <p>
        </div>
        <div class="iriscc-card">
            <h3>📍 Spatial information</h3>
            <p>Each subject is defined by a unique Subject ID and some spatial information. Often it's their residential address, but it can also be their workplace, postcode, or a frequently travelled route.
            It all depends on the research question and available data. 
            <br><br>
            Most of the time, locations are first captured as addresses. They are converted to geographic coordinates (latitude and longitude) using either a geocoding service or the address registry of the country.
            Then, the coordinates are saved in a common geospatial data format such as a shapefile or GeoPackage.
            <p>
            </p>
        </div>
        <div class="iriscc-card">
            <h3>📊 Demographics and health </h3>
            <p>Subjects report demographic information and health status through surveys, or contribute measurement data from medical tests and wearable biosensors.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialize session state for dataset and source selection
if "location_gdf" not in st.session_state:
    st.session_state["location_gdf"] = None

if "data_source" not in st.session_state:
    st.session_state["data_source"] = "sample"


def load_spatial_file(uploaded_file):
    suffix = Path(uploaded_file.name).suffix.lower()

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / uploaded_file.name
        temp_path.write_bytes(uploaded_file.getbuffer())

        # ZIP containing shapefile
        if suffix == ".zip":
            extract_dir = Path(tmpdir) / "unzipped"

            with zipfile.ZipFile(temp_path, "r") as z:
                z.extractall(extract_dir)

            shp = list(extract_dir.rglob("*.shp"))
            if not shp:
                raise ValueError("No .shp found in ZIP")

            return gpd.read_file(shp[0])

        # Default: let geopandas try to read (gpkg, geojson, etc.)
        return gpd.read_file(temp_path)


def validate_gdf(gdf, bounding_box=None):

    if gdf is None:
        raise ValueError("No data loaded")

    if gdf.empty:
        raise ValueError("Dataset is empty.")

    # If there's a geometry column name but not proper geometry objects, try to convert WKT
    if "geometry" in gdf.columns and not isinstance(gdf.geometry.iloc[0], (Point,)):
        try:
            gdf["geometry"] = gdf["geometry"].apply(
                lambda x: wkt.loads(x) if isinstance(x, str) else x
            )
        except Exception:
            pass

    if "geometry" not in gdf.columns:
        raise ValueError("No geometry column found.")

    if gdf.geometry.isna().all():
        raise ValueError("All geometries are null.")

    # Normalize CRS
    try:
        if gdf.crs is None:
            # assume lat/lon if geometry bounds look like lat/lon
            gdf = gdf.set_crs(epsg=4326, allow_override=True)
        else:
            gdf = gdf.to_crs(epsg=4326)
    except Exception as e:
        raise ValueError(f"Failed to set/transform CRS: {e}")

    # explode multipoints so limit applies to real individuals
    geom_types = set(gdf.geometry.geom_type.unique())
    if "MultiPoint" in geom_types:
        try:
            gdf = gdf.explode(index_parts=False).reset_index(drop=True)
        except Exception:
            pass

    # Only allow point-like geometries
    geom_types = set(gdf.geometry.geom_type.unique())
    allowed = {"Point"}
    if geom_types - allowed:
        raise ValueError(f"Only Point geometries allowed. Found: {geom_types}")

    if bounding_box is not None:
        min_x, min_y, max_x, max_y = bounding_box
        bbox_gdf = gdf.to_crs(CUSTOM_DATASET_BBOX_CRS)
        within_bbox = (
            bbox_gdf.geometry.x.between(min_x, max_x)
            & bbox_gdf.geometry.y.between(min_y, max_y)
        )
        gdf = gdf.loc[within_bbox].copy()
        if gdf.empty:
            raise ValueError("No points remain inside the configured bounding box.")

    MAX = 5000
    if len(gdf) > MAX:
        raise ValueError(f"Max {MAX} participants allowed. You uploaded {len(gdf)}.")

    # Ensure SubjectID exists; if not, create one
    if "SubjectID" not in gdf.columns:
        gdf = gdf.reset_index(drop=True)
        gdf["SubjectID"] = gdf.index.astype(str)

    # Standardize column order to put SubjectID first
    cols = gdf.columns.tolist()
    if "SubjectID" in cols:
        cols.insert(0, cols.pop(cols.index("SubjectID")))
        gdf = gdf[cols]

    return gdf


st.markdown(
    "<div class='iriscc-section-title'><strong>Choose your data source</strong></div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="iriscc-body">
        To start your analysis, you can either use a sample cohort dataset or upload your own. Then, use the buttons below to load and visualize the cohort data on a map.
     </div>
    """,
    unsafe_allow_html=True,
)


source = st.radio(
    "Data source",
    ("Sample dataset", "Upload your own"),
    index=0,
    horizontal=True,
    label_visibility="collapsed",
)
st.session_state["data_source"] = "sample" if source == "Sample dataset" else "upload"

# If the user switched the chosen data source, clear any shown map to avoid mixing sources
prev_choice = st.session_state.get("choice_prev")
if prev_choice is None:
    st.session_state["choice_prev"] = st.session_state["data_source"]
elif prev_choice != st.session_state["data_source"]:
    st.session_state["show_map"] = False
    st.session_state["choice_prev"] = st.session_state["data_source"]

uploaded_file = None
if st.session_state["data_source"] == "upload":
    st.markdown(
        """
        <div class="iriscc-body">
            Please ensure that your file is in a supported geospatial format (GeoPackage, GeoJSON, or ZIP containing a shapefile).
            Make sure that there is a geometry column, and a column with a unique identifier for each subject (e.g., SubjectID). There can be up to 2000 points in the uploaded dataset.
            <br><br>
            The tutorial currently only supports European locations. If your dataset contains points outside Europe, they'll be dropped.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.warning(
        "Warning! This is an unsecure tutorial. When uploading real addresses, never upload real health data. Instead, upload a table with just addresses and a pseudo code and link the returned results to your health data on your local work environment. In addition, add dummy addresses to your data so addresses that belong to study participants are not recognizable. Alternatively, use synthetic data or anonymized datasets, and make sure to comply with your local data protection regulations."
    )
    uploaded_file = st.file_uploader(
        "Upload cohort file",
        label_visibility="collapsed",
        type=["gpkg", "geojson", "json", "zip"],
    )
else:
    st.markdown(
        """
        <div class="iriscc-body">
            The sample cohort is a synthetic dataset of 711 subjects called <i>utrechtCardiovascularCohort</i>.
            Based on survey responses, health history, and a few measurements in the lab, the researchers have calculated the participants' risk of having or developing cardiovascular diseases (CVDs). They normalized this risk, calling it the <i>Cardiovascular_Score</i>, and saved it in the dataset. The score is a number between 0 and 1, where higher values indicate a higher risk (they probably already have been diagnosed with a CVD), and lower values indicate a lower risk (they are likely healthy). 
            They also collected demographic and socio-economic data.
            <br><br>
            The researchers already know that the risk of CVDs is influenced by environmental exposures [<a href="https://www.sciencedirect.com/science/article/pii/S0021915025001200">1</a>], but they want to explore how the risk of CVDs is related to air quality and the built environment.
            After following this tutorial, they'll will be able to see the pattern of exposures that suggest causality.
            <br><br>
            The subjects were recruited from around the municipality of Utrecht, in the Netherlands. A geocoding service has already been used to convert their street addresses into geographic coordinates (latitude and longitude). The data has been saved in a GeoPackage file.
            <br><br>
            </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Bottom action buttons: Load cohort and Visualize
# -----------------------------------------------------------------------------
col_load, col_vis = st.columns([1, 1])

with col_load:
    if st.button("Load cohort"):
        if st.session_state.get("data_source") == "sample":
            path = BASE_DIR / "Resources" / "utrecht_cohort.gpkg"
            if not path.exists():
                st.error("Sample dataset not found in Resources.")
            else:
                gdf = gpd.read_file(path)
                gdf = validate_gdf(gdf)
                st.dataframe(visualize_gdf_as_df(gdf), hide_index=True)
                try:
                    csv = gdf.drop(columns=["geometry"], errors="ignore").to_csv(
                        index=False
                    )
                    st.download_button(
                        "Download CSV",
                        data=csv,
                        file_name="utrecht_cohort.csv",
                        mime="text/csv",
                    )
                except Exception:
                    pass

            st.session_state["location_gdf"] = gdf
            st.session_state["loaded_source"] = "sample"
            st.session_state["uploaded_file_name"] = "utrecht_cohort.gpkg"

            st.success(f"Loaded sample cohort ({len(gdf)} records)")

        else:
            if uploaded_file is None:
                st.warning("Please upload a file first (choose 'Upload your own').")
            else:
                st.session_state["location_gdf"] = None
                st.session_state.pop("loaded_source", None)
                try:
                    gdf = load_spatial_file(uploaded_file)
                    uploaded_count = len(gdf)
                    if uploaded_count > MAX_UPLOADED_POINTS:
                        raise ValueError(
                            f"Uploaded datasets may contain at most {MAX_UPLOADED_POINTS} points. "
                            f"This dataset contains {uploaded_count}."
                        )
                    gdf = validate_gdf(gdf, bounding_box=CUSTOM_DATASET_BBOX)
                    if len(gdf) < uploaded_count:
                        st.warning(
                            "Points outside Europe have been dropped from the uploaded dataset."
                        )
                    st.dataframe(visualize_gdf_as_df(gdf), hide_index=True)
                    try:
                        csv = gdf.drop(columns=["geometry"], errors="ignore").to_csv(
                            index=False
                        )
                        st.download_button(
                            "Download CSV",
                            data=csv,
                            file_name="uploaded_cohort.csv",
                            mime="text/csv",
                        )
                    except Exception:
                        pass

                except Exception as e:
                    st.error(f"Failed to load uploaded file: {e}")
                else:
                    st.session_state["location_gdf"] = gdf
                    st.session_state["loaded_source"] = "upload"
                    st.session_state["uploaded_file_name"] = uploaded_file.name
                    st.success(f"Loaded uploaded cohort ({len(gdf)} records)")

with col_vis:
    if st.button("Visualize cohort on map"):
        # Only allow visualizing when a dataset has been loaded for the currently selected source
        if st.session_state.get("location_gdf") is None:
            st.warning("Load cohort data first (use 'Load cohort').")
        elif st.session_state.get("loaded_source") != st.session_state.get(
            "data_source"
        ):
            st.warning(
                "The currently selected data source has not been loaded. Please load it first."
            )
        else:
            st.session_state["show_map"] = True

if "show_map" not in st.session_state:
    st.session_state["show_map"] = False

if "show_all_locations" not in st.session_state:
    st.session_state["show_all_locations"] = True

# -----------------------------------------------------------------------------
# Map section
# -----------------------------------------------------------------------------
if st.session_state["show_map"]:
    location_gdf = st.session_state["location_gdf"]

    # Ensure coordinates are in lat/lon
    if location_gdf.crs != "EPSG:4326":
        location_gdf = location_gdf.to_crs(4326)

    col_map, col_controls = st.columns([4, 1])

    # -------------------------------------------------------------------------
    # Controls
    # -------------------------------------------------------------------------
    with col_controls:
        st.subheader("Zoom to")

        if st.button("All subjects"):
            st.session_state["show_all_locations"] = True
            st.rerun()
    # -------------------------------------------------------------------------
    # Map
    # -------------------------------------------------------------------------
    with col_map:
        m = folium.Map(
            tiles='https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        )

        bounds = [
            [location_gdf.geometry.y.min(), location_gdf.geometry.x.min()],
            [location_gdf.geometry.y.max(), location_gdf.geometry.x.max()],
        ]
        m.fit_bounds(bounds, padding=(30, 30))

        # ---------------------------------------------------------------------
        # Add points
        # ---------------------------------------------------------------------
        for _, row in location_gdf.iterrows():
            if row.geometry is None:
                continue

            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=4,
                fill=True,
                fill_opacity=0.8,
                popup=str(row.get("Cardiovascular_Score", "")),
            ).add_to(m)

        st_folium(m, width="100%", height=700, returned_objects=[])
