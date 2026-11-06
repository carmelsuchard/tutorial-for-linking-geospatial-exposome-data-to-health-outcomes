import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import folium
import branca.colormap as cm
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from utils.iriscc_utils import apply_app_style

SCATTER_X_COLUMNS = ["age"]

st.set_page_config(page_title="4. Analysis", layout="wide")
apply_app_style()

st.markdown(
    """
    <div class="iriscc-page-header">
        <h2 class="iriscc-page-title">Step 4 — Analysis</h2>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    "<div class='iriscc-section-title'><strong>Visualizing the spatial distribution</strong></div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="iriscc-body">
        Start by visualizing the spatial distribution of the exposure values linked to your cohort. You can create a map that shows the locations of the cohort members and color-code them based on their exposure values. This will help you identify any spatial patterns or clusters in the data.
        <br><br>
      </div>
    """,
    unsafe_allow_html=True,
)

linked_df = st.session_state.get("linked_df")
raster_list = st.session_state.get("raster_list", [])

if not isinstance(linked_df, gpd.GeoDataFrame) or linked_df.empty:
    st.info("Run the linking procedure on the previous page to create data for analysis.")
    st.stop()

selected_columns = [
    f"{selection.get('variable', '').strip()}_{selection.get('time', '').strip()}"
    for selection in raster_list
    if isinstance(selection, dict)
]
exposure_columns = [
    column for column in dict.fromkeys(selected_columns) if column in linked_df.columns
]

if not exposure_columns:
    st.warning("No selected exposure columns are available in the linked data.")
    st.stop()

selected_variable = st.selectbox("Exposure variable",
                                 exposure_columns,
                                 label_visibility="collapsed",
                                 width=500,
                                 )
numeric_values = pd.to_numeric(linked_df[selected_variable], errors="coerce")
valid_values = numeric_values.dropna()

if valid_values.empty:
    st.warning(f"{selected_variable} does not contain any numeric values to plot.")
    st.stop()

if linked_df.crs is None:
    st.error("The linked points do not have a coordinate reference system.")
    st.stop()

minimum = float(valid_values.min())
maximum = float(valid_values.max())


def normalized_color(value):
    if maximum <= minimum:
        return 0.0
    return (float(value) - minimum) / (maximum - minimum)


panel_height = 560

map_gdf = linked_df.to_crs("EPSG:4326")
colour_map = plt.get_cmap("plasma_r")

bounds = map_gdf.total_bounds
map_center = [float(map_gdf.geometry.y.mean()), float(map_gdf.geometry.x.mean())]
folium_map = folium.Map(
    location=map_center,
    zoom_start=7,
    tiles='https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
)
folium_map.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]], padding=(20, 20))

legend_positions = [
    minimum,
    minimum + (maximum - minimum) * 0.25,
    minimum + (maximum - minimum) * 0.5,
    minimum + (maximum - minimum) * 0.75,
    maximum,
]
exposure_legend = cm.LinearColormap(
    colors=[mcolors.to_hex(colour_map(normalized_color(position))) for position in legend_positions],
    vmin=minimum,
    vmax=maximum,
)
exposure_legend.add_to(folium_map)

for _, row in map_gdf.iterrows():
    value = pd.to_numeric(pd.Series([row[selected_variable]]), errors="coerce").iloc[0]
    marker_colour = "#98a2b3" if pd.isna(value) else mcolors.to_hex(colour_map(normalized_color(value)))
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=5,
        color=marker_colour,
        fill=True,
        fill_color=marker_colour,
        fill_opacity=0.85,
        weight=1,
        tooltip=f"{selected_variable}: {value if pd.notna(value) else 'No data'}",
    ).add_to(folium_map)

st_folium(folium_map, width="100%", height=panel_height, returned_objects=[])

st.markdown(
    "<div class='iriscc-section-title'><strong>Explore relationships between variables</strong></div>",
    unsafe_allow_html=True,
)

available_x_columns = [
    column
    for column in linked_df.columns
    if column != "geometry"
    and any(column.lower() == configured.lower() for configured in SCATTER_X_COLUMNS)
    and pd.to_numeric(linked_df[column], errors="coerce").notna().any()
]

if not available_x_columns:
    st.info("No configured X-axis columns are available in the linked data.")
else:
    x_axis = st.selectbox("X-axis", available_x_columns)
    numeric_columns = [
        column
        for column in linked_df.columns
        if column != "geometry"
        and column != x_axis
        and pd.to_numeric(linked_df[column], errors="coerce").notna().any()
    ]

    if not numeric_columns:
        st.info("No other numeric columns are available for the Y-axis.")
    else:
        y_axis = st.selectbox("Y-axis", numeric_columns)
        scatter_data = pd.DataFrame(
            {
                x_axis: pd.to_numeric(linked_df[x_axis], errors="coerce"),
                y_axis: pd.to_numeric(linked_df[y_axis], errors="coerce"),
            }
        ).dropna()

        if scatter_data.empty:
            st.warning("The selected columns do not contain a pair of numeric values to plot.")
        else:
            st.scatter_chart(
                scatter_data,
                x=x_axis,
                y=y_axis,
                height=panel_height,
                width="stretch",
            )


# st.subheader("Compare exposure between urban and rural areas")
# st.write("""There are various ways to define urban, suburban, and rural areas on a European or country-specific basis.
#         In this tutorial, we will use the Eurostat Degree of Urbanisation (DEGURBA) classification, which is based on population density and settlement patterns. The DEGURBA classification divides areas into three categories: urban, suburban, and rural. You can use this classification to compare the exposure values between these different types of areas.
# """)