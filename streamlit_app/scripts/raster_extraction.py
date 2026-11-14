import asyncio
from time import perf_counter

import aiohttp
import geopandas as gpd
import pandas as pd

WMS_URL = "https://exposome.uu.nl/geoserver/wms"
WMS_WORKSPACE = "EXPANSE_map"
TARGET_CRS = "EPSG:3857"
WMS_TIMEOUT = 60
MAX_REQUESTS = 3000
MAX_CONCURRENT_REQUESTS = 10


def _format_wms_time(timestamp):
    """Format date-only selections as the UTC instants used by daily layers."""
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
        # print(
        #     f"[link_to_raster] Point {position + 1}/{total_points}: "
        #     f"original index={original_index}"
        # )
        # print(f"[link_to_raster] Request parameters: {params}")
        request_start = perf_counter()
        try:
            async with session.get(WMS_URL, params=params) as response:
                # print(
                #     f"[link_to_raster] Response for point {position + 1}: "
                #     f"status={response.status}, "
                #     f"content-type={response.headers.get('Content-Type')}, "
                #     f"elapsed={perf_counter() - request_start:.3f}s"
                # )
                response.raise_for_status()
                data = await response.json(content_type=None)
                features = data.get("features", [])
                # print(f"[link_to_raster] Features returned: {len(features)}")
                if features:
                    properties = features[0].get("properties", {})
                    # print(f"[link_to_raster] Properties: {properties}")
                    value = properties.get("GRAY_INDEX")
                    # print(
                    #     f"[link_to_raster] Gray Index for point {position + 1}: {value}"
                    # )
                    return position, value, None
                print(f"[link_to_raster] No feature returned for point {position + 1}.")
                return position, None, None
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError, AttributeError) as error:
            print(
                f"[link_to_raster] Request failed for point {position + 1}: "
                f"{type(error).__name__}: {error}"
            )
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


def _clean_linked_columns(dataframe, columns):
    """Normalize linked exposure values and remove invalid raster values."""
    for column in columns:
        values = pd.to_numeric(dataframe[column], errors="coerce")
        values = values.replace([float("inf"), float("-inf")], pd.NA)
        dataframe[column] = values.mask(values < -1).round(4)


def link_to_raster(selected_variable_dict, points_dataframe, progress_callback=None, return_failures=False):
    total_start = perf_counter()
    validation_start = perf_counter()
    print("[link_to_raster] Starting raster link.")
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

    output_column = f"{variable_name}_{timestamp}".replace(".", "_")
    wms_timestamp = _format_wms_time(timestamp)
    # print(
    #     f"[link_to_raster] Raster: variable={variable_name}, "
    #     f"GeoServer name={geoserver_name}, time={timestamp}, pixel size={pixel_size}"
    # )
    points_in_wms_crs = points_dataframe.to_crs(TARGET_CRS)
    layer_name = f"{WMS_WORKSPACE}:{geoserver_name}"
    values = [None] * len(points_dataframe)
    failures = []
    # print(f"Timing: validation = {perf_counter() - validation_start:.3f}s")

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
        # print(
        #     f"[link_to_raster] Limiting requests from {len(requests_to_make)} "
        #     f"to {MAX_REQUESTS}."
        # )
        requests_to_make = requests_to_make[:MAX_REQUESTS]
    # print(
    #     f"[link_to_raster] Sending {len(requests_to_make)} request(s) asynchronously "
    #     f"with a maximum of {MAX_CONCURRENT_REQUESTS} concurrent request(s)."
    # )
    requested_values, request_failures = asyncio.run(
        _fetch_raster_values(requests_to_make, output_column, progress_callback)
    )
    values[: len(requested_values)] = requested_values
    failures.extend(request_failures)

    # print(
    #     f"[link_to_raster] Finished requests: values={sum(value is not None for value in values)}, "
    #     f"missing={sum(value is None for value in values)}, failures={len(failures)}"
    # )
    linked_points = points_dataframe.copy()
    linked_points[output_column] = values
    _clean_linked_columns(linked_points, [output_column])
    print(f"Timing: total link_to_raster = {perf_counter() - total_start:.3f}s")
    if return_failures:
        return linked_points, failures
    return linked_points


def create_linked_dataframe(
    selected_variable_dict,
    points_dataframe,
    return_failures=False,
    progress_callback=None,
):
    """Add one sampled exposure column for every selected raster/time.

    Failed layers are added as null columns and recorded in the optional
    failure report instead of stopping the remaining layers.
    """
    if not isinstance(selected_variable_dict, list) or not selected_variable_dict:
        raise ValueError("selected_variable_dict must be a non-empty list.")

    if not all(isinstance(selection, dict) for selection in selected_variable_dict):
        raise TypeError("Each raster selection must be a dictionary.")

    output_columns = [
        f"{str(selection.get('variable', '')).strip()}_{str(selection.get('time', '')).strip()}"
        .replace(".", "_")
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
    # print(
    #     f"[create_linked_dataframe] Starting link for {len(selected_variable_dict)} "
    #     f"raster selection(s) and {len(points_dataframe)} point(s)."
    # )
    # print(f"[create_linked_dataframe] Output columns: {output_columns}")
    linked_gdf = points_dataframe.copy()
    failures = []
    for variable_dict in selected_variable_dict:
        variable_name = str(variable_dict["variable"]).strip()
        timestamp = str(variable_dict["time"]).strip()
        output_column = f"{variable_name}_{timestamp}".replace(".", "_")
        try:
            # print(
            #     f"[create_linked_dataframe] Starting {output_column} "
            #     f"({selected_variable_dict.index(variable_dict) + 1}/{len(selected_variable_dict)})."
            # )
            if progress_callback:
                progress_callback("started", output_column)
            # print(f"Extracting values from raster: {variable_dict['geoserver_name']}")
            extracted_values, tile_failures = link_to_raster(
                variable_dict,
                linked_gdf,
                progress_callback=progress_callback,
                return_failures=True,
            )
            linked_gdf[output_column] = extracted_values[output_column]
            failures.extend(tile_failures)
            # print(
            #     f"[create_linked_dataframe] Completed {output_column}; "
            #     f"failures so far={len(failures)}."
            # )
            if progress_callback:
                progress_callback("completed", output_column)
        except Exception as error:
            print(f"Failed to link {output_column}: {error}")
            linked_gdf[output_column] = [None] * len(linked_gdf)
            failures.append({"variable": output_column, "error": str(error)})
            print(
                f"[create_linked_dataframe] Added null column for {output_column}; "
                f"failures so far={len(failures)}."
            )
            if progress_callback:
                progress_callback("failed", output_column)

    print(
        f"Timing: total create_linked_dataframe = {perf_counter() - total_start:.3f}s"
    )
    print(
        f"[create_linked_dataframe] Finished. Shape={linked_gdf.shape}, "
        f"total failures={len(failures)}."
    )
    _clean_linked_columns(linked_gdf, output_columns)
    if return_failures:
        return linked_gdf, failures
    return linked_gdf