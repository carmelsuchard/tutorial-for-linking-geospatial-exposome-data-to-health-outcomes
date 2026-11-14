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
        Start by visualizing the spatial distribution of the exposure values linked to your cohort. You can make a map that shows the locations of the cohort members, color-coded by their exposure values. This will help you identify any spatial patterns or clusters in the data.
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
    f"{selection.get('variable', '').strip()}_{selection.get('time', '').strip()}".replace(
        ".", "_"
    )
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


st.markdown(
    """
    <div class="iriscc-body">
        Next, use plots like heatmaps and scatterplots to get an initial idea of the relationship between variables.
      </div>
    """,
    unsafe_allow_html=True,
)


def render_correlation_heatmap(dataframe):
    """Render correlations as a native Altair chart."""
    excluded_columns = [
        column
        for column in dataframe.columns
        if column.lower() in {"geometry", "subjectid"}
    ]
    numeric_data = dataframe.drop(columns=excluded_columns).apply(
        pd.to_numeric, errors="coerce"
    )
    usable_columns = [
        column
        for column in numeric_data.columns
        if numeric_data[column].notna().sum() >= 2
        and numeric_data[column].nunique(dropna=True) >= 2
    ]

    if len(usable_columns) < 2:
        st.info(
            "At least two numeric columns with two varying observations are needed "
            "for a correlation heatmap."
        )
        return

    correlation_matrix = numeric_data[usable_columns].corr(min_periods=2)
    correlation_matrix = correlation_matrix.dropna(axis=0, how="all").dropna(
        axis=1, how="all"
    )
    if correlation_matrix.empty:
        st.info("No pairwise correlations could be calculated from the linked data.")
        return

    columns = correlation_matrix.columns.tolist()
    heatmap_data = correlation_matrix.rename_axis("row").reset_index().melt(
        id_vars="row",
        var_name="column",
        value_name="correlation",
    )
    heatmap_data = heatmap_data.dropna(subset=["correlation"])
    heatmap = alt.Chart(heatmap_data).mark_rect().encode(
        x=alt.X(
            "column:N",
            sort=columns,
            title=None,
            axis=alt.Axis(
                labelAngle=-45,
                labelAlign="right",
                labelLimit=500,
                labelOverlap=False,
            ),
        ),
        y=alt.Y(
            "row:N",
            sort=columns,
            title=None,
            axis=alt.Axis(labelLimit=500, labelOverlap=False),
        ),
        color=alt.Color(
            "correlation:Q",
            title="Correlation",
            scale=alt.Scale(domain=[-1, 1], scheme="redblue", reverse=True),
        ),
        tooltip=[
            alt.Tooltip("row:N", title="Variable"),
            alt.Tooltip("column:N", title="Variable"),
            alt.Tooltip("correlation:Q", title="Correlation", format=".2f"),
        ],
    )
    labels = heatmap.mark_text().encode(
        text=alt.Text("correlation:Q", format=".2f"),
        color=alt.condition(
            "abs(datum.correlation) > 0.5",
            alt.value("white"),
            alt.value("black"),
        ),
    )
    chart = (heatmap + labels).properties(
        title="Correlation of numeric variables",
        width="container",
        height=max(400, min(800, 45 * len(columns))),
    )
    st.altair_chart(chart, use_container_width=True)


render_correlation_heatmap(linked_df)

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

        # Use safe field names for Altair: exposure names such as "Annual PM2.5_2020"
        # contain dots that Vega-Lite interprets as nested-field access.
        x_field = "_scatter_x"
        y_field = "_scatter_y"
        scatter_data = pd.DataFrame(
            {x_field: x_values, y_field: y_values}
        ).dropna()

        if scatter_data.empty:
            st.warning("The selected columns do not contain a pair of numeric values to plot.")
        else:
            y_min, y_max = scatter_data[y_field].min(), scatter_data[y_field].max()
            if y_min == y_max:
                y_min, y_max = y_min - 0.5, y_max + 0.5

            if x_type == "quantitative":
                x_min, x_max = scatter_data[x_field].min(), scatter_data[x_field].max()
                if x_min == x_max:
                    x_min, x_max = x_min - 0.5, x_max + 0.5
                x_encoding = alt.X(
                    x_field,
                    type=x_type,
                    scale=alt.Scale(domain=[x_min, x_max]),
                    axis=alt.Axis(format=axis_format(x_axis)),
                    title=x_axis,
                )
            else:
                x_encoding = alt.X(
                    x_field,
                    type=x_type,
                    axis=alt.Axis(labelAngle=0),
                    title=x_axis,
                )

            x_tooltip = (
                alt.Tooltip(
                    x_field,
                    type="quantitative",
                    format=axis_format(x_axis),
                    title=x_axis,
                )
                if x_type == "quantitative"
                else alt.Tooltip(x_field, type="nominal", title=x_axis)
            )
            scatterplot = (
                alt.Chart(scatter_data)
                .mark_circle(size=60)
                .encode(
                    x=x_encoding,
                    y=alt.Y(
                        y_field,
                        type="quantitative",
                        scale=alt.Scale(domain=[y_min, y_max]),
                        axis=alt.Axis(format=axis_format(y_axis)),
                        title=y_axis,
                    ),
                    tooltip=[
                        x_tooltip,
                        alt.Tooltip(
                            y_field,
                            type="quantitative",
                            format=axis_format(y_axis),
                            title=y_axis,
                        ),
                    ],
                )
                .properties(height=panel_height)
            )
            st.altair_chart(scatterplot, use_container_width=True)
