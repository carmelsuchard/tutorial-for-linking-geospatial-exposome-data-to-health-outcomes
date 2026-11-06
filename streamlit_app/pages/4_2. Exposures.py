import base64
import mimetypes
import os
from datetime import date, timedelta
from html import escape
from pathlib import Path

import streamlit as st

from utils.iriscc_utils import apply_app_style

BASE_DIR = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="2. Exposures", layout="wide")
apply_app_style()

st.markdown(
    """
    <div class="iriscc-page-header">
        <h2 class="iriscc-page-title">Step 2 — Select exposure variables</h2>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='iriscc-section-title'><strong>Exposure variables</strong></div>",
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="iriscc-grid">
        <div class="iriscc-card">
            <h3>🔠 Types of exposures</h3>
            <p> In the field of exposomics, exposure variables are environmental factors that individuals or populations are exposed to, which can have an impact on their health. 
            These variables can be physical (e.g., temperature, noise), chemical (e.g., air pollutants, pesticides), related to the built environment (e.g. greenspaces, walkability), and more. </p>
            <p>This tutorial focuses on two main types of exposure variables: air quality and the built environment.
            </div>
        <div class="iriscc-card">
            <h3>📏 Estimating exposure</h3>
            <p>Exposure can be estimated in various ways. It can be measured directly, for example by using sensors in houses, collecting surveys, or giving wearable devices to cohort members. Or it can be estimated based on models,
            which is useful when some exposures are impossible to measure comprehensively. Models use data from measurement stations
            and other data sources, such as satellite imagery, to estimate exposure levels across different locations and times. </p>
        </div>
        <div class="iriscc-card">
            <h3>🗂️ Data sources</h3>
            <p>There are many data catalogues on the internet where you can find datasets of modeled exposure variables. In this tutorial, we'll use datasets created in the <a href=\"https://expanseproject.eu/">Expanse Project</a>.
            All of the datasets created in this project are available in a <a href=\"https://exposome.uu.nl/">Exposome Maps catalogue</a> so other researchers can access them for their own studies.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="iriscc-body">
          <br><br>
     </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='iriscc-section-title'><strong>Your choice</strong></div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="iriscc-body">
        Use the selection cards below to select the exposure variables you want to link to your cohort. You can select multiple exposures, but up to 100 variables or times in total.
        <br><br>
        Watch out! Different variables are available at differnet temporal and spatial resolutions, which will affect your subsequent analysis. Think about your research question and the available data when making your selections.
        <br><br>
      </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
if "pollutant_selection" not in st.session_state:
    st.session_state["pollutant_selection"] = {}

if "weather_selection" not in st.session_state:
    st.session_state["weather_selection"] = {}


def default_selection_record(name):
    return {
        "variable": name,
        "timeframe_type": "single_day",
        "single_day": "",
        "start_date": "",
        "end_date": "",
        "daily_year": "",
        "single_year": "",
        "start_year": "",
        "end_year": "",
    }


def ensure_selection_record(state_key, name):
    store = st.session_state[state_key]
    if name not in store:
        store[name] = default_selection_record(name)
    return store[name]


def toggle_selection(state_key, name):
    store = st.session_state[state_key]
    if name in store:
        del store[name]
    else:
        store[name] = default_selection_record(name)


def format_timeframe_summary(record):
    if not record:
        return "No timeframe selected"

    timeframe_type = record.get("timeframe_type", "single_day")
    if timeframe_type == "single_year":
        single_year = record.get("single_year", "").strip()
        if single_year:
            return f"{single_year}"
        return "Single year: not set"

    if timeframe_type == "year_range":
        start_year = record.get("start_year", "").strip()
        end_year = record.get("end_year", "").strip()
        if start_year and end_year:
            return f"{start_year} to {end_year}"
        if start_year:
            return f"{start_year}"
        if end_year:
            return f"{end_year}"
        return "Year range: not set"

    if timeframe_type == "single_day":
        single_day = record.get("single_day", "")
        if single_day:
            return f"{single_day}"
        return "Single day: not set"

    start_date = record.get("start_date", "").strip()
    end_date = record.get("end_date", "").strip()
    if start_date and end_date:
        return f"{start_date} to {end_date}"
    if start_date:
        return f"{start_date}"
    if end_date:
        return f"{end_date}"
    return "Day range: not set"


def get_temporal_mode(name):
    metadata = variable_metadata.get(name, {})
    mode = str(metadata.get("temporal_mode", "daily")).strip().lower()
    return "yearly" if mode == "yearly" else "daily"


def parse_metadata_date(value):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def parse_metadata_year(value):
    value = str(value).strip()
    return int(value) if len(value) == 4 and value.isdigit() else None


def metadata_time_bounds(metadata, temporal_mode):
    start_time = metadata.get("start_time", "")
    end_time = metadata.get("end_time", "")
    if temporal_mode == "yearly":
        return parse_metadata_year(start_time), parse_metadata_year(end_time)
    return parse_metadata_date(start_time), parse_metadata_date(end_time)


def slugify(value):
    return (
        value.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "_")
        .replace(".", "")
    )


def thumbnail_data_uri(relative_path):
    if not relative_path:
        return ""

    thumbnail_path = BASE_DIR / relative_path
    if not thumbnail_path.is_file():
        return ""

    mime_type = (
        mimetypes.guess_type(thumbnail_path.name)[0] or "application/octet-stream"
    )
    encoded_image = base64.b64encode(thumbnail_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded_image}"


def variable_selection_to_raster_list(variable_selection_dict):
    raster_selection = []
    for variable, record in variable_selection_dict.items():
        geoserver_name = variable_metadata[variable]["geoserver_name"]
        pixel_size = variable_metadata[variable]["pixel_size"]

        if record.get("timeframe_type") == "single_day":
            selected_date = parse_metadata_date(record.get("single_day"))
            if selected_date:
                raster_selection.append(
                    {
                        "variable": variable,
                        "geoserver_name": geoserver_name,
                        "time": selected_date.isoformat(),
                        "pixel_size": pixel_size,
                    }
                )
        elif record.get("timeframe_type") == "day_range":
            start_date = parse_metadata_date(record.get("start_date"))
            end_date = parse_metadata_date(record.get("end_date"))
            if start_date and end_date and start_date <= end_date:
                current_date = start_date
                while current_date <= end_date:
                    raster_selection.append(
                        {
                            "variable": variable,
                            "geoserver_name": geoserver_name,
                            "time": current_date.isoformat(),
                            "pixel_size": pixel_size,
                        }
                    )
                    current_date += timedelta(days=1)
        elif record.get("timeframe_type") == "single_year":
            selected_year = parse_metadata_year(record.get("single_year"))
            if selected_year:
                raster_selection.append(
                    {
                        "variable": variable,
                        "geoserver_name": geoserver_name,
                        "time": f"{selected_year:04d}",
                        "pixel_size": pixel_size,
                    }
                )
        elif record.get("timeframe_type") == "year_range":
            start_year = parse_metadata_year(record.get("start_year"))
            end_year = parse_metadata_year(record.get("end_year"))
            if start_year and end_year and start_year <= end_year:
                for year in range(start_year, end_year + 1):
                    raster_selection.append(
                        {
                            "variable": variable,
                            "geoserver_name": geoserver_name,
                            "time": f"{year:04d}",
                            "pixel_size": pixel_size,
                        }
                    )
    return raster_selection


# -----------------------------------------------------------------------------
# Dataset definitions
# -----------------------------------------------------------------------------
pollutant_options = ["Annual PM10", "Annual PM2.5", "Annual O3", "Annual NO2"]

weather_options = [
    "Mean NDVI within 300m buffer",
    "Walkability index within 300m buffer",
    "Imperviousness index within 300m buffer",
    "Distance to nearest blue space",
]

variable_metadata = {
    "Annual PM10": {
        "spatial_resolution": "100x100m",
        "pixel_size": 100,
        "temporal_mode": "yearly",
        "start_time": "2019",
        "end_time": "2023",
        "time_period": "2019-2023",
        "unit": "μg/m³",
        "description": "Inhalable particles with diameters 10 micrometers and smaller",
        "thumbnail": "Resources/thumbnails/pm10.png",
        "geoserver_name": "P10B25_AAV",
    },
    "Annual PM2.5": {
        "spatial_resolution": "100x100m",
        "pixel_size": 100,
        "temporal_mode": "yearly",
        "start_time": "2019",
        "end_time": "2023",
        "time_period": "2019-2023",
        "unit": "μg/m³",
        "description": "Inhalable particles with diameters 2.5 micrometers and smaller",
        "thumbnail": "Resources/thumbnails/pm25.png",
        "geoserver_name": "P25B25_AAV",
    },
    "Annual O3": {
        "spatial_resolution": "100x100m",
        "pixel_size": 100,
        "temporal_mode": "yearly",
        "start_time": "2019",
        "end_time": "2023",
        "time_period": "2019-2023",
        "unit": "μg/m³",
        "description": "Ground-level ozone, the result of reactions of man-made volatile organic compounds and nitrogen oxides",
        "thumbnail": "Resources/thumbnails/o3.png",
        "geoserver_name": "OZOB25_AAV",
    },
    "Annual NO2": {
        "spatial_resolution": "100x100m",
        "pixel_size": 100,
        "temporal_mode": "yearly",
        "start_time": "2019",
        "end_time": "2023",
        "time_period": "2019-2023",
        "unit": "μg/m³",
        "description": "Nitrogen dioxide that gets in the air from the burning of fuel, primarily from vehicles and power plants",
        "thumbnail": "Resources/thumbnails/no2.png",
        "geoserver_name": "NO2B25_AAV",
    },
    "Mean NDVI within 300m buffer": {
        "spatial_resolution": "250x250m",
        "pixel_size": 250,
        "temporal_mode": "yearly",
        "start_time": "2020",
        "end_time": "2020",
        "time_period": "2020-2020",
        "unit": "NDVI",
        "description": "Modeled mean NDVI within 300m buffer, a measure of vegetation density and health",
        "thumbnail": "Resources/thumbnails/mean_ndvi.png",
        "geoserver_name": "NDV_ME3",
    },
    "Walkability index within 300m buffer": {
        "spatial_resolution": "100x100m",
        "pixel_size": 100,
        "temporal_mode": "yearly",
        "start_time": "2020",
        "end_time": "2020",
        "time_period": "2020-2020",
        "unit": "Walkability index",
        "description": "Modeled walkability index within 300m buffer",
        "thumbnail": "Resources/thumbnails/walkability.png",
        "geoserver_name": "WAL_B03",
    },
    "Imperviousness index within 300m buffer": {
        "spatial_resolution": "100x100m",
        "pixel_size": 100,
        "temporal_mode": "yearly",
        "start_time": "2006",
        "end_time": "2018",
        "time_period": "2006-2018",
        "unit": "Imperviousness index",
        "description": "Modeled imperviousness index within 300m buffer",
        "thumbnail": "Resources/thumbnails/imperviousness.png",
        "geoserver_name": "IMP_B03",
    },
    "Distance to nearest blue space": {
        "spatial_resolution": "100x100m",
        "pixel_size": 100,
        "temporal_mode": "yearly",
        "start_time": "2013",
        "end_time": "2013",
        "time_period": "2013-2013",
        "unit": "m",
        "description": "Distance to the nearest blue space (water body)",
        "thumbnail": "Resources/thumbnails/nearest_blue.png",
        "geoserver_name": "	BSW_DIS",
    }
}


def render_variable_card(name, state_key, selected):
    metadata = variable_metadata.get(name, {})
    thumbnail_uri = thumbnail_data_uri(metadata.get("thumbnail", ""))
    thumbnail_html = (
        f'<img src="{escape(thumbnail_uri, quote=True)}" alt="{escape(name, quote=True)} thumbnail" style="width:100%; height:100%; object-fit:cover; display:block;" />'
        if thumbnail_uri
        else '<div style="padding:0.8rem; text-align:center; color:#5f6b7a; font-size:0.84rem; line-height:1.35;">Thumbnail<br>placeholder</div>'
    )

    metadata_grid = []
    for label, value in [
        ("Spatial resolution", metadata.get("spatial_resolution", "TBD")),
        (
            "Available window",
            f"{metadata.get('time_period', 'TBD')}",
        ),
        ("Unit", metadata.get("unit", "TBD")),
    ]:
        metadata_grid.append(
            f'<div><div style="font-size:0.72rem; text-transform:uppercase; letter-spacing:0.06em; color:#5f6b7a; font-weight:700;">{escape(label)}</div><div style="font-weight:600;">{escape(str(value))}</div></div>'
        )
    metadata_grid_html = "".join(metadata_grid)

    with st.container():
        st.markdown(
            f"""
            <div class="iriscc-card {"is-selected" if selected else ""}">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; margin-bottom:0.8rem;">
                </div>
                <div style="display:flex; gap:1rem; align-items:stretch; flex-wrap:wrap;">
                    <div style="flex: 0 0 160px; min-width: 160px;">
                        <div style="
                            width: 160px;
                            height: 120px;
                            border-radius: 16px;
                            border: 1px solid rgba(16, 24, 40, 0.10);
                            background: linear-gradient(135deg, rgba(18, 59, 93, 0.06), rgba(15, 118, 110, 0.10));
                            overflow: hidden;
                            display:flex;
                            align-items:center;
                            justify-content:center;
                        ">
                            {thumbnail_html}
                        </div>
                    </div>
                    <div style="flex: 1 1 320px; min-width: 280px;">
                        <div class="iriscc-card-title">{escape(name)}</div>
                        <div class="iriscc-card-subtitle" style="margin-bottom:0.9rem;">{escape(metadata.get("description"))}</div>
                        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:0.6rem;">{metadata_grid_html}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        select_button_label = "Remove variable" if selected else "Select variable"
        if st.button(
            select_button_label,
            key=f"{state_key}_{slugify(name)}_toggle",
            use_container_width=True,
        ):
            toggle_selection(state_key, name)
            st.rerun()

        if selected:
            record = ensure_selection_record(state_key, name)
            temporal_mode = get_temporal_mode(name)
            start_time, end_time = metadata_time_bounds(metadata, temporal_mode)

            if temporal_mode == "yearly":
                valid_timeframe = (
                    start_time is not None
                    and end_time is not None
                    and start_time <= end_time
                )

                if not valid_timeframe:
                    st.warning(
                        "Set valid start_time and end_time years in this variable's metadata."
                    )
                else:
                    available_years = [
                        str(year) for year in range(start_time, end_time + 1)
                    ]
                    if len(available_years) > 1:
                        timeframe_type = st.radio(
                            "Timeframe type",
                            ["Single year", "Year range"],
                            index=(
                                0
                                if record.get("timeframe_type") != "year_range"
                                else 1
                            ),
                            horizontal=True,
                            key=f"{state_key}_{slugify(name)}_timeframe",
                        )
                        record["timeframe_type"] = (
                            "single_year"
                            if timeframe_type == "Single year"
                            else "year_range"
                        )
                    else:
                        record["timeframe_type"] = "single_year"
                        record["start_year"] = ""
                        record["end_year"] = ""

                    if record["timeframe_type"] == "single_year":
                        selected_year = record.get("single_year", "")
                        if selected_year not in available_years:
                            selected_year = available_years[0]
                        record["single_year"] = st.selectbox(
                            "Year",
                            available_years,
                            index=available_years.index(selected_year),
                            key=f"{state_key}_{slugify(name)}_single_year",
                        )
                        record["start_year"] = ""
                        record["end_year"] = ""
                    else:
                        selected_start = record.get("start_year", "")
                        if selected_start not in available_years:
                            selected_start = available_years[0]
                        start_year = st.selectbox(
                            "Start year",
                            available_years,
                            index=available_years.index(selected_start),
                            key=f"{state_key}_{slugify(name)}_start_year",
                        )
                        end_year_options = [
                            year
                            for year in available_years
                            if int(year) >= int(start_year)
                        ]
                        selected_end = record.get("end_year", "")
                        if selected_end not in end_year_options:
                            selected_end = end_year_options[-1]
                        end_year = st.selectbox(
                            "End year",
                            end_year_options,
                            index=end_year_options.index(selected_end),
                            key=f"{state_key}_{slugify(name)}_end_year",
                        )
                        record["start_year"] = start_year
                        record["end_year"] = end_year
                        record["single_year"] = ""

                record["single_day"] = ""
                record["start_date"] = ""
                record["end_date"] = ""
            else:
                valid_timeframe = (
                    start_time is not None
                    and end_time is not None
                    and start_time <= end_time
                )
                timeframe_type = st.radio(
                    "Timeframe type",
                    ["Single day", "Day range"],
                    index=0
                    if record.get("timeframe_type") not in ("time_range", "day_range")
                    else 1,
                    horizontal=True,
                    key=f"{state_key}_{slugify(name)}_timeframe",
                )
                record["timeframe_type"] = (
                    "single_day" if timeframe_type == "Single day" else "day_range"
                )

                if not valid_timeframe:
                    st.warning(
                        "Set valid start_time and end_time dates (YYYY-MM-DD) in this variable's metadata."
                    )
                else:
                    available_years = list(range(start_time.year, end_time.year + 1))
                    selected_year = record.get("daily_year")
                    selected_year = (
                        int(selected_year)
                        if str(selected_year).isdigit()
                        else start_time.year
                    )
                    if selected_year not in available_years:
                        selected_year = start_time.year
                    selected_year = st.selectbox(
                        "Year",
                        available_years,
                        index=available_years.index(selected_year),
                        key=f"{state_key}_{slugify(name)}_daily_year",
                    )

                    record["daily_year"] = str(selected_year)
                    available_start = max(date(selected_year, 6, 1), start_time)
                    available_end = min(date(selected_year, 8, 31), end_time)

                    if available_start > available_end:
                        st.warning(
                            "No daily data is available between June and August for this year."
                        )
                    elif record["timeframe_type"] == "single_day":
                        selected_day = (
                            parse_metadata_date(record.get("single_day"))
                            or available_start
                        )
                        selected_day = min(
                            max(selected_day, available_start), available_end
                        )
                        selected_day = st.date_input(
                            "Day",
                            value=selected_day,
                            min_value=available_start,
                            max_value=available_end,
                            key=f"{state_key}_{slugify(name)}_single_day_{selected_year}",
                            format="YYYY-MM-DD",
                        )
                        record["single_day"] = selected_day.isoformat()
                        record["start_date"] = ""
                        record["end_date"] = ""
                    else:
                        selected_start = (
                            parse_metadata_date(record.get("start_date"))
                            or available_start
                        )
                        selected_end = (
                            parse_metadata_date(record.get("end_date"))
                            or available_end
                        )
                        selected_start = min(
                            max(selected_start, available_start), available_end
                        )
                        selected_end = min(
                            max(selected_end, available_start), available_end
                        )
                        if selected_end < selected_start:
                            selected_end = selected_start
                        selected_range = st.date_input(
                            "Day range",
                            value=(selected_start, selected_end),
                            min_value=available_start,
                            max_value=available_end,
                            key=f"{state_key}_{slugify(name)}_day_range_{selected_year}",
                            format="YYYY-MM-DD",
                        )
                        if (
                            isinstance(selected_range, (tuple, list))
                            and len(selected_range) == 2
                        ):
                            record["start_date"] = selected_range[0].isoformat()
                            record["end_date"] = selected_range[1].isoformat()
                        record["single_day"] = ""

                record["single_year"] = ""
                record["start_year"] = ""
                record["end_year"] = ""

            st.caption(f"Selection saved: {format_timeframe_summary(record)}")


# -----------------------------------------------------------------------------
# UI layout
# -----------------------------------------------------------------------------
air_quality_col, weather_col = st.columns(2, gap="large")

with air_quality_col:
    st.subheader("Air quality datasets")
    for name in pollutant_options:
        render_variable_card(
            name, "pollutant_selection", name in st.session_state["pollutant_selection"]
        )

with weather_col:
    st.subheader("Built environment datasets")
    for name in weather_options:
        render_variable_card(
            name, "weather_selection", name in st.session_state["weather_selection"]
        )

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
st.markdown("---")

st.subheader("Your selections")
st.markdown(
    '<div class="variable-section-note">These choices are stored for the next step of the workflow.</div>',
    unsafe_allow_html=True,
)

summary_col_a, summary_col_b = st.columns(2)

with summary_col_a:
    with st.container(border=True):
        st.markdown("**Air quality**")
        if st.session_state["pollutant_selection"]:
            for name, record in st.session_state["pollutant_selection"].items():
                st.write(f"{name}  \n_{format_timeframe_summary(record)}_")
        else:
            st.caption("No pollutants selected yet")

with summary_col_b:
    with st.container(border=True):
        st.markdown("**Built environment**")
        if st.session_state["weather_selection"]:
            for name, record in st.session_state["weather_selection"].items():
                st.write(f"{name}  \n_{format_timeframe_summary(record)}_")
        else:
            st.caption("No built environment variables selected yet")


raster_list = variable_selection_to_raster_list(
    st.session_state["weather_selection"]
) + variable_selection_to_raster_list(st.session_state["pollutant_selection"])
if len(raster_list) > 100:
    st.warning(f"""You have selected more than 100 variables or times.
               This may take a long time to process in the next step.
               Reduce the number of variables or narrow
               the timeframes before continuing.""")
    st.session_state["raster_list"] = []
else:
    st.session_state["raster_list"] = raster_list
