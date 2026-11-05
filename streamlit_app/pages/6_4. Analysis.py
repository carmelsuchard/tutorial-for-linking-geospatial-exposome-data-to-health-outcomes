import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import folium
import branca.colormap as cm
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from utils.iriscc_utils import apply_app_style

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
    """
    Your linked dataset can be used to explore the relationship between air pollution, heatwaves, and health outcomes. You can perform various analyses, such as descriptive statistics, visualizations, and statistical modeling, to gain insights into the data.
    This is done offline. You can go back to the last page to download the linked dataset and perform your own analysis using your preferred tools and methods.

    Here are a few examples of analyses you can perform on the linked dataset:
    """,
    unsafe_allow_html=True,
)

# st.markdown(
#     """Here is one kind of analysis you can do: you can create a scatter plot of the linked data to visualize the relationship between two variables. You can also perform statistical tests or build regression models to quantify the relationship between exposures and health outcomes.
#     You can also use machine learning algorithms to predict health outcomes based on exposures. The possibilities are endless, and you can customize the analysis based on your specific research questions and data.
#     """
#         unsafe_allow_html=True,
# )

# st.markdown(
#     "Explore the spatial distribution and frequency of the exposure values linked to your cohort.",
#     unsafe_allow_html=True,
# )

st.markdown(
    "<div class='iriscc-section-title'><strong>Visualizing the spatial distribution</strong></div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="iriscc-body">
        Start by visualizing the spatial distribution of the exposure values linked to your cohort. You can create a map that shows the locations of the cohort members and color-code them based on their exposure values. This will help you identify any spatial patterns or clusters in the data.
        To see the overall distribution of values, you can also create a histogram of the exposure values. This will give you an idea of the range and frequency of the values in your dataset. Go back to the exposures page to see the units of each exposure.
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


map_column, histogram_column = st.columns([3, 2])
panel_height = 560

with map_column:
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

with histogram_column:
    bin_count = st.slider("Number of bins", min_value=5, max_value=50, value=20)
    figure, axis = plt.subplots(figsize=(7, panel_height / 100), dpi=100)
    figure.patch.set_facecolor("#f8fafc")
    axis.set_facecolor("#f8fafc")
    axis.hist(
        valid_values,
        bins=bin_count,
        color="#f5b042",
        edgecolor="#ffffff",
        linewidth=1.0,
        alpha=0.9,
    )
    axis.set_xlabel(selected_variable, fontsize=10, fontweight="semibold")
    axis.set_ylabel("Number of points", fontsize=10, fontweight="semibold")
    axis.set_title(f"Distribution of {selected_variable}", fontsize=12, fontweight="bold", pad=8)
    axis.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    axis.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_color("#cbd5e1")
    axis.spines["bottom"].set_color("#cbd5e1")
    axis.tick_params(axis="both", labelsize=9, colors="#475569")
    figure.tight_layout()
    st.pyplot(figure, clear_figure=True)
    plt.close(figure)


# st.subheader("Compare exposure between urban and rural areas")
# st.write("""There are various ways to define urban, suburban, and rural areas on a European or country-specific basis.
#         In this demonstrator, we will use the Eurostat Degree of Urbanisation (DEGURBA) classification, which is based on population density and settlement patterns. The DEGURBA classification divides areas into three categories: urban, suburban, and rural. You can use this classification to compare the exposure values between these different types of areas.
# """)