import altair as alt
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import folium
import branca.colormap as cm
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from utils.iriscc_utils import apply_app_style

SCATTER_Y_COLUMNS = ["Cardiovascular_Score", "frailty_index"]
SCATTER_CATEGORICAL_COLUMNS = {"marital_status", "education_level"}

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


def is_categorical_column(column):
    return column.lower() in SCATTER_CATEGORICAL_COLUMNS


def numeric_column(column):
    return pd.to_numeric(linked_df[column], errors="coerce")


def axis_format(column):
    return ".0f" if column.lower() == "birth_year" else ".2f"


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

available_y_columns = [
    column
    for column in linked_df.columns
    if column != "geometry"
    and any(column.lower() == configured.lower() for configured in SCATTER_Y_COLUMNS)
    and pd.to_numeric(linked_df[column], errors="coerce").notna().any()
]

if not available_y_columns:
    st.info("No configured Y-axis columns are available in the linked data.")
else:
    y_axis = st.selectbox(
        "Y-axis",
        available_y_columns,
        key="analysis_y_axis",
    )
    configured_y_columns = {column.lower() for column in SCATTER_Y_COLUMNS}
    available_x_columns = [
        column
        for column in linked_df.columns
        if column != "geometry"
        and column.lower() != "subjectid"
        and column.lower() not in configured_y_columns
        and (
            is_categorical_column(column)
            or numeric_column(column).notna().any()
        )
    ]

    if not available_x_columns:
        st.info("No other numeric columns are available for the X-axis.")
    else:
        x_axis = st.selectbox(
            "X-axis",
            available_x_columns,
            key="analysis_x_axis",
        )
        y_values = numeric_column(y_axis)
        if is_categorical_column(x_axis):
            x_values = linked_df[x_axis].astype("string")
            x_type = "nominal"
        else:
            x_values = numeric_column(x_axis)
            x_type = "quantitative"

        scatter_data = pd.DataFrame({x_axis: x_values, y_axis: y_values}).dropna()

        if scatter_data.empty:
            st.warning("The selected columns do not contain a pair of numeric values to plot.")
        else:
            y_min, y_max = scatter_data[y_axis].min(), scatter_data[y_axis].max()
            if y_min == y_max:
                y_min, y_max = y_min - 0.5, y_max + 0.5

            if x_type == "quantitative":
                x_min, x_max = scatter_data[x_axis].min(), scatter_data[x_axis].max()
                if x_min == x_max:
                    x_min, x_max = x_min - 0.5, x_max + 0.5
                x_encoding = alt.X(
                    x_axis,
                    type=x_type,
                    scale=alt.Scale(domain=[x_min, x_max]),
                    axis=alt.Axis(format=axis_format(x_axis)),
                )
            else:
                x_encoding = alt.X(
                    x_axis,
                    type=x_type,
                    axis=alt.Axis(labelAngle=0),
                )

            x_tooltip = (
                alt.Tooltip(
                    x_axis,
                    type="quantitative",
                    format=axis_format(x_axis),
                )
                if x_type == "quantitative"
                else alt.Tooltip(x_axis, type="nominal")
            )
            scatterplot = (
                alt.Chart(scatter_data)
                .mark_circle(size=60)
                .encode(
                    x=x_encoding,
                    y=alt.Y(
                        y_axis,
                        type="quantitative",
                        scale=alt.Scale(domain=[y_min, y_max]),
                        axis=alt.Axis(format=axis_format(y_axis)),
                    ),
                    tooltip=[
                        x_tooltip,
                        alt.Tooltip(
                            y_axis,
                            type="quantitative",
                            format=axis_format(y_axis),
                        ),
                    ],
                )
                .properties(height=panel_height)
            )
            st.altair_chart(scatterplot, use_container_width=True)


# st.markdown(
#     "<div class='iriscc-section-title'><strong>Examples from literature</strong></div>",
#     unsafe_allow_html=True,
# )

# st.markdown(
#     """
#     <div class="iriscc-grid2">
#         <div class="iriscc-card">
#             <h3>👥 Study population</h3>
#             <p>Analysis begins with a study population. Individuals may be recruited for a specific study or selected from a dataset of population health data.
#             <br><br>
#             Studies are often designed to follow a cohort over time so that changes in health can be linked to changing environmental exposures. <p>
#         </div>
#         <div class="iriscc-card">
#             <h3>📍 Spatial information</h3>
#             <p>Each subject is defined by a unique Subject ID and some spatial information. Often it's their residential address, but it can also be their workplace, postcode, or a frequently travelled route.
#             It all depends on the research question and available data. 
#             <br><br>
#             Most of the time, locations are first captured as addresses. They are converted to geographic coordinates (latitude and longitude) using either a geocoding service or the address registry of the country.
#             Then, the coordinates are saved in a common geospatial data format such as a shapefile or GeoPackage.
#             <p>
#             </p>
#         </div>
#         <div class="iriscc-card">
#             <h3>📊 Demographics and health </h3>
#             <p>Subjects report demographic information and health status through surveys, or contribute measurement data from medical tests and wearable biosensors.</p>
#         </div>
#         <div class="iriscc-card">
#             <h3>📊 Demographics and health </h3>
#             <p> Baranyi, G., Harron, K., Shen, Y. et al. studied the relationship between <b> early life course air pollution exposure</b> and <b> general health in adolescence</b> in the UK.
#             They linked air pollution exposure to buffers around postcode centroids over the life course of participants. Annual averages of PM2.5, PM10, and NO2
#             were used to calculate mean exposures during different life stages, then compared to self-reported general health and hospital episodes. </p>
#         </div>
#     </div>
#     """,
#     unsafe_allow_html=True,
# )
