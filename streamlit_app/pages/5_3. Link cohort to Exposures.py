import geopandas as gpd
import pandas as pd
import streamlit as st

from scripts.raster_extraction import create_linked_dataframe
from utils.iriscc_utils import apply_app_style, visualize_gdf_as_df

st.set_page_config(page_title="3. Link Locations to Exposure Data", layout="wide")
apply_app_style()

st.markdown(
    """
    <div class="iriscc-page-header">
        <h2 class="iriscc-page-title">Step 3 — Link cohort to exposures</h2>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='iriscc-section-title'><strong>Linking process</strong></div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
            <div class="iriscc-instruction">
            Now you can programmatically link the addresses in the cohort dataset to the exposure datasets.
			<br><br>
            Locations are represented as points, and exposure datasets are represented as surfaces. In terms of data models, these are examples of a vector and a raster dataset, respectively.
            When a point is placed on a surface, you can sample the value at that point. This is how you link the cohort to the exposure datasets.
			<br><br>
            It's important to consider differences in spatial resolution between datasets. If a raster dataset has a spatial resolution of 100 meters, it means that each pixel represents 100 meters on the ground.
            Therefore, two points that are within this pixel will be assigned the same value, even though in reality they're up to 100 meters apart.
            <br><br>
            Press the button to run the linking procedure. Be patient, as this may take a few minutes depending on the number of locations and exposure datasets.
            <br><br>
            </div>
            """,
    unsafe_allow_html=True,
)


location_gdf = st.session_state.get("location_gdf")
raster_list = st.session_state.get("raster_list")

cohort_ready = (
    isinstance(location_gdf, gpd.GeoDataFrame)
    and not location_gdf.empty
    and "geometry" in location_gdf.columns
    and location_gdf.geometry.notna().any()
    and set(location_gdf.geometry.dropna().geom_type.unique()) <= {"Point"}
)
exposures_ready = (
    isinstance(raster_list, list)
    and 0 < len(raster_list) <= 100
    and all(
        isinstance(selection, dict)
        and all(
            str(selection.get(key, "")).strip()
            for key in ("variable", "geoserver_name", "time")
        )
        for selection in raster_list
    )
)

if not cohort_ready:
    st.warning(
        "Load a valid cohort dataset on the Cohort page before starting the linking procedure."
    )

if not exposures_ready:
    st.warning(
        "Select at least one pollutant or temperature exposure, with no more than 100 time granules, on the Exposures page before starting the linking procedure."
    )

if exposures_ready:
    st.markdown("**Selected exposure variables**")
    selected_exposures = "\n".join(
        f"- {selection['variable']} {selection['time']}" for selection in raster_list
    )
    st.markdown(selected_exposures)

run = st.button(
    "Run linking procedure",
    disabled=not (cohort_ready and exposures_ready),
)


def get_data():
    return st.session_state.get("linked_df")


def convert_for_download(df):
    if df is None:
        return b""

    if isinstance(df, gpd.GeoDataFrame):
        download_df = df.drop(columns="geometry").copy()
        coordinates = df.to_crs("EPSG:4326").geometry
        if "longitude" not in download_df.columns:
            download_df["longitude"] = coordinates.x
        if "latitude" not in download_df.columns:
            download_df["latitude"] = coordinates.y
    else:
        download_df = df.copy()

    return download_df.to_csv(index=False).encode("utf-8")


if run:
    st.session_state.pop("linked_df", None)
    st.session_state.pop("linking_failures", None)
    try:
        with st.status(
            "Linking exposure variables...", expanded=True
        ) as linking_status:

            def update_linking_status(state, variable_name):
                if state == "started":
                    linking_status.write(f"Linking `{variable_name}`...")
                    linking_status.update(label=f"Linking `{variable_name}`...")
                elif state == "progress":
                    linking_status.write(variable_name)
                    linking_status.update(label=variable_name)
                elif state == "completed":
                    linking_status.write(f"Finished `{variable_name}`")
                else:
                    linking_status.write(f"Could not link `{variable_name}`")

            linked_df, linking_failures = create_linked_dataframe(
                selected_variable_dict=raster_list,
                points_dataframe=location_gdf,
                return_failures=True,
                progress_callback=update_linking_status,
            )
            linking_status.update(label="Exposure linking finished", state="complete")
        st.session_state["linked_df"] = linked_df
        st.session_state["linking_failures"] = linking_failures

    except Exception as e:
        st.error(f"Error occurred while linking cohort to exposures: {e}")

linked_df_for_download = get_data()
if linked_df_for_download is not None:
    linking_failures = st.session_state.get("linking_failures", [])
    if linking_failures:
        failed_tiles = ", ".join(
            f"{failure['variable']} (tile {failure['tile']})"
            for failure in linking_failures
        )
        st.warning(
            f"Could not link these tiles: {failed_tiles}. "
            "Points in those tiles have null values for the affected exposure."
        )
    st.success("""The linking procedure ran successfully!
    Notice the resulting table. Each row represents a subject in the cohort,
    and each column contains the value of an exposure variable.""")
    st.dataframe(visualize_gdf_as_df(linked_df_for_download), hide_index=True)

    csv = convert_for_download(linked_df_for_download)

    print(f"Type: {type(csv)}, Length: {len(csv)}")

    file_name = st.session_state.get("uploaded_file_name")
    file_name = file_name.split(".")[0]
    file_name = f"{file_name}_linked.csv"

    print("file name", file_name)

    st.download_button(
        label="Download linked data as CSV",
        data=csv,
        file_name=file_name,
        mime="text/csv",
        key="download_button",
        on_click="ignore",
        icon=":material/download:",
        type="secondary",
        disabled=linked_df_for_download.empty,
    )


code_expander = st.expander("Want to see the code used in the linking process?")
with code_expander:
    st.write(
        '''
        ```python
            def _format_wms_time(timestamp):
                if len(timestamp) == 10 and timestamp[4] == "-" and timestamp[7] == "-":
                    return f"{timestamp}T00:00:00.000Z"
                return timestamp


            async def _fetch_gray_index(
                session,
                semaphore,
                position,
                original_index,
                params,
                output_column,
                total_points,
            ):
                async with semaphore:
                    try:
                        async with session.get(WMS_URL, params=params) as response:
                            response.raise_for_status()
                            data = await response.json(content_type=None)
                            features = data.get("features", [])
                            if features:
                                properties = features[0].get("properties", {})
                                value = properties.get("GRAY_INDEX")
                                return position, value, None
                            return position, None, None
                    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError, AttributeError) as error:
                        return position, None, {
                            "variable": output_column,
                            "point": position,
                            "error": str(error),
                        }


            async def _fetch_raster_values(requests_to_make, output_column, progress_callback):
                values = [None] * len(requests_to_make)
                failures = []
                semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
                timeout = aiohttp.ClientTimeout(total=WMS_TIMEOUT)
                connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)

                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    tasks = [
                        asyncio.create_task(
                            _fetch_gray_index(
                                session,
                                semaphore,
                                position,
                                original_index,
                                params,
                                output_column,
                                len(requests_to_make),
                            )
                        )
                        for position, (original_index, params) in enumerate(requests_to_make)
                    ]
                    for task in asyncio.as_completed(tasks):
                        position, value, failure = await task
                        values[position] = value
                        if failure:
                            failures.append(failure)
                        if progress_callback:
                            progress_callback(
                                "progress",
                                f"Processed point {position + 1} of {len(requests_to_make)} for {output_column}",
                            )
                return values, failures
            

            def link_to_raster(selected_variable_dict, points_dataframe, progress_callback=None, return_failures=False):
                if not isinstance(selected_variable_dict, dict):
                    raise TypeError("Each raster selection must be a dictionary.")
                required_keys = {"variable", "geoserver_name", "time", "pixel_size"}
                missing_keys = required_keys.difference(selected_variable_dict)
                if missing_keys:
                    raise ValueError(f"Raster selection is missing: {sorted(missing_keys)}")
                if not isinstance(points_dataframe, gpd.GeoDataFrame):
                    raise TypeError("points_dataframe must be a GeoDataFrame.")
                if points_dataframe.empty:
                    raise ValueError("points_dataframe contains no points.")
                if points_dataframe.crs is None:
                    raise ValueError("points_dataframe has no CRS defined.")
                if (
                    points_dataframe.geometry.isna().any()
                    or not points_dataframe.geometry.geom_type.eq("Point").all()
                ):
                    raise ValueError(
                        "points_dataframe must contain only non-null Point geometries."
                    )

                variable_name = str(selected_variable_dict["variable"]).strip()
                geoserver_name = str(selected_variable_dict["geoserver_name"]).strip()
                timestamp = str(selected_variable_dict["time"]).strip()
                try:
                    pixel_size = float(selected_variable_dict["pixel_size"])
                except (TypeError, ValueError):
                    raise ValueError("Raster pixel_size must be a positive number.")
                if not variable_name or not geoserver_name or not timestamp:
                    raise ValueError("Raster variable, GeoServer name, and time must be non-empty.")
                if pixel_size <= 0:
                    raise ValueError("Raster pixel_size must be a positive number.")

                output_column = f"{variable_name}_{timestamp}"
                wms_timestamp = _format_wms_time(timestamp)

                points_in_wms_crs = points_dataframe.to_crs(TARGET_CRS)
                layer_name = f"{WMS_WORKSPACE}:{geoserver_name}"
                values = [None] * len(points_dataframe)
                failures = []

                requests_to_make = []
                for point_index, point in enumerate(points_in_wms_crs.geometry):
                    x = float(point.x)
                    y = float(point.y)
                    half_pixel = pixel_size / 2
                    params = {
                        "SERVICE": "WMS",
                        "VERSION": "1.1.1",
                        "REQUEST": "GetFeatureInfo",
                        "LAYERS": layer_name,
                        "QUERY_LAYERS": layer_name,
                        "STYLES": "",
                        "SRS": TARGET_CRS,
                        "BBOX": f"{x - half_pixel},{y - half_pixel},{x + half_pixel},{y + half_pixel}",
                        "WIDTH": 1,
                        "HEIGHT": 1,
                        "X": 0,
                        "Y": 0,
                        "INFO_FORMAT": "application/json",
                        "FEATURE_COUNT": 1,
                        "TIME": wms_timestamp,
                    }
                    requests_to_make.append((points_dataframe.index[point_index], params))

                if len(requests_to_make) > MAX_REQUESTS:
                    requests_to_make = requests_to_make[:MAX_REQUESTS]

                requested_values, request_failures = asyncio.run(
                    _fetch_raster_values(requests_to_make, output_column, progress_callback)
                )
                values[: len(requested_values)] = requested_values
                failures.extend(request_failures)

                linked_points = points_dataframe.copy()
                linked_points[output_column] = values
                if return_failures:
                    return linked_points, failures
                return linked_points


            def create_linked_dataframe(
                selected_variable_dict,
                points_dataframe,
                return_failures=False,
                progress_callback=None,
            ):
                if not isinstance(selected_variable_dict, list) or not selected_variable_dict:
                    raise ValueError("selected_variable_dict must be a non-empty list.")

                if not all(isinstance(selection, dict) for selection in selected_variable_dict):
                    raise TypeError("Each raster selection must be a dictionary.")

                output_columns = [
                    f"{str(selection.get('variable', '')).strip()}_{str(selection.get('time', '')).strip()}"
                    for selection in selected_variable_dict
                ]
                if any(
                    column == "_" or column.startswith("_") or column.endswith("_")
                    for column in output_columns
                ):
                    raise ValueError(
                        "Each raster selection must have a non-empty variable name and timestamp."
                    )
                if len(output_columns) != len(set(output_columns)):
                    raise ValueError("Each variable and timestamp combination must be unique.")

                total_start = perf_counter()
                linked_gdf = points_dataframe.copy()
                failures = []
                for variable_dict in selected_variable_dict:
                    variable_name = str(variable_dict["variable"]).strip()
                    timestamp = str(variable_dict["time"]).strip()
                    output_column = f"{variable_name}_{timestamp}"
                    try:
                        if progress_callback:
                            progress_callback("started", output_column)
                        extracted_values, tile_failures = link_to_raster(
                            variable_dict,
                            linked_gdf,
                            progress_callback=progress_callback,
                            return_failures=True,
                        )
                        linked_gdf[output_column] = extracted_values[output_column]
                        failures.extend(tile_failures)
                        if progress_callback:
                            progress_callback("completed", output_column)
                    except Exception as error:
                        linked_gdf[output_column] = [None] * len(linked_gdf)
                        failures.append({"variable": output_column, "error": str(error)})
                        if progress_callback:
                            progress_callback("failed", output_column)
                if return_failures:
                    return linked_gdf, failures
                return linked_gdf
                '''
            )
