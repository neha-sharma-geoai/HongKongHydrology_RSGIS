import os
import datetime
import numpy as np
import geopandas as gpd
import pandas as pd
import rasterio
import glob
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
from whitebox.whitebox_tools import WhiteboxTools
from shapely.geometry import mapping
from rasterio import features
from shapely.geometry import shape
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from rasterstats import zonal_stats
import argparse




timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")

def reproject_and_clip_dem(dem_path, aoi_path, out_folder, target_crs="EPSG:2326"):

    os.makedirs(out_folder, exist_ok=True)

    print("✅ Clipping DEM")

    base_name = f"clipped_dem_2326_{timestamp}.tif"
    reprojected_name = f"reprojected_temp_{timestamp}.tif"

    out_path = os.path.join(out_folder, base_name)
    reprojected_path = os.path.join(out_folder, reprojected_name)

    aoi = gpd.read_file(aoi_path).to_crs(target_crs)
    geometries = [mapping(geom) for geom in aoi.geometry]

    with rasterio.open(dem_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds
        )
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(reprojected_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.bilinear
                )

    with rasterio.open(reprojected_path) as reproj_src:
        out_image, out_transform = mask(reproj_src, geometries, crop=True)
        out_meta = reproj_src.meta.copy()
        out_meta.update({
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })

        with rasterio.open(out_path, "w", **out_meta) as dest:
            dest.write(out_image)

    os.remove(reprojected_path)
    print(f"✅ Clipped DEM saved to: {out_path}")
    return out_path


def run_hydrology_whitebox(dem_path, out_folder):
    os.makedirs(out_folder, exist_ok=True)
    wbt = WhiteboxTools()
    wbt.set_working_dir(out_folder)

    # Create output filenames with timestamp
    dem_filled = os.path.join(out_folder, f"dem_filled_{timestamp}.tif")
    flow_acc = os.path.join(out_folder, f"flow_acc_{timestamp}.tif")
    slope = os.path.join(out_folder, f"slope_{timestamp}.tif")

    print("🕳️ Filling depressions...")
    wbt.fill_depressions(dem_path, dem_filled)

    print("🌊 Computing flow accumulation...")
    wbt.d8_flow_accumulation(dem_filled, flow_acc, out_type='cells')

    print("📐 Calculating slope...")
    wbt.slope(dem_filled, slope)

    print("✅ Whitebox hydrological layers saved in:", out_folder)
    return {
        "filled_dem": dem_filled,
        "slope": slope,
        "flow_acc": flow_acc
    }

def extract_flood_zones(slope_path, flow_acc_path, out_folder, slope_thresh=5, flow_thresh=1500):
    os.makedirs(out_folder, exist_ok=True)
    flood_zone_path = os.path.join(out_folder, f"flood_zones_{timestamp}.tif")

    with rasterio.open(slope_path) as slope_src, rasterio.open(flow_acc_path) as flow_src:
        # Read arrays
        slope = slope_src.read(1)
        flow_acc = flow_src.read(1)

        # Create mask: flow > threshold and slope < threshold
        flood_mask = (flow_acc > flow_thresh) & (slope < slope_thresh)

        # Convert boolean to 0 and 1
        flood_array = flood_mask.astype(np.uint8)

        out_meta = slope_src.meta.copy()
        out_meta.update({
            "dtype": 'uint8',
            "count": 1,
            "nodata": 255  # FIXED: valid for uint8
        })

        with rasterio.open(flood_zone_path, 'w', **out_meta) as dst:
            dst.write(flood_array, 1)

    print(f"✅ Flood zone raster saved: {flood_zone_path}")
    return flood_zone_path

def polygonize_flood_raster(flood_raster_path, out_folder):
    os.makedirs(out_folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    vector_path = os.path.join(out_folder, f"flood_zones_{timestamp}.geojson")

    with rasterio.open(flood_raster_path) as src:
        mask = src.read(1) == 1  # Only keep flood-prone pixels (value = 1)
        transform = src.transform

        shapes_gen = features.shapes(src.read(1), mask=mask, transform=transform)

        records = [{
            "geometry": shape(geom),
            "properties": {"value": val}
        } for geom, val in shapes_gen if val == 1]

        gdf = gpd.GeoDataFrame.from_records(records)
        gdf = gdf.set_geometry("geometry")
        gdf.set_crs(src.crs, inplace=True)

    gdf.to_file(vector_path, driver="GeoJSON")
    print(f"✅ Flood polygons saved to: {vector_path}")
    return vector_path

import geopandas as gpd
import os

def compute_railway_flood_exposure(rail_path, flood_polygon_path):
    # Load railway and flood zone data
    rail = gpd.read_file(rail_path)
    flood = gpd.read_file(flood_polygon_path)

    # Ensure same CRS
    rail = rail.to_crs(flood.crs)

    # Calculate total railway length (in km)
    rail["length_km"] = rail.geometry.length / 1000
    total_length = rail["length_km"].sum()

    # Spatial intersection
    intersect = gpd.overlay(rail, flood, how='intersection')
    intersect["impacted_km"] = intersect.geometry.length / 1000
    impacted_length = intersect["impacted_km"].sum()

    # Percent impacted
    percent_impacted = (impacted_length / total_length) * 100 if total_length else 0

    intersect.to_file(os.path.join(out_folder, "railway_flood_impacted.geojson"), driver="GeoJSON")

    # Print summary
    print("✅ Flood Exposure Summary for Railway Lines")
    print("Impacted Length (km):", round(impacted_length, 3))
    print("Total Length (km):", round(total_length, 3))
    print("Percent Impacted:", round(percent_impacted, 2), "%")

    # Optional: return as dict or DataFrame
    return {
        "Impacted Length (km)": round(impacted_length, 3),
        "Total Length (km)": round(total_length, 3),
        "% Impacted": round(percent_impacted, 2)
    }


def clip_and_mosaic_tiles(tile_folder, aoi_path, out_folder, target_crs="EPSG:2326"):
    os.makedirs(out_folder, exist_ok=True)

    s2_ls_out_path = os.path.join(out_folder, f"mosaic_clipped_{target_crs.split(':')[-1]}_{timestamp}.tif")
    temp_clipped_folder = os.path.join(out_folder, f"temp_clipped_{timestamp}")
    os.makedirs(temp_clipped_folder, exist_ok=True)

    aoi = gpd.read_file(aoi_path).to_crs(target_crs)
    tile_paths = glob.glob(os.path.join(tile_folder, "*.tif"))

    clipped_paths = []

    for tile_path in tile_paths:
        with rasterio.open(tile_path) as src:
            # Reproject AOI to tile CRS for clipping
            aoi_proj = aoi.to_crs(src.crs)
            geom = [mapping(geom) for geom in aoi_proj.geometry]
            try:
                out_image, out_transform = mask(src, shapes=geom, crop=True)
            except ValueError:
                continue  # Skip if tile doesn't intersect AOI

            # Step 1: Save the clipped image temporarily
            temp_path = os.path.join(temp_clipped_folder, f"clipped_{os.path.basename(tile_path)}")
            out_meta = src.meta.copy()
            out_meta.update({
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform
            })

            with rasterio.open(temp_path, "w", **out_meta) as dst:
                dst.write(out_image)

        # Step 2: Reproject clipped tile to target CRS
        reprojected_path = temp_path.replace("clipped_", "reproj_")

        # ✅ Ensure directory for reprojected file exists
        reprojected_dir = os.path.dirname(reprojected_path)
        os.makedirs(reprojected_dir, exist_ok=True)

        with rasterio.open(temp_path) as src:
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )
            kwargs = src.meta.copy()
            kwargs.update({
                "crs": target_crs,
                "transform": transform,
                "width": width,
                "height": height
            })

            with rasterio.open(reprojected_path, "w", **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=Resampling.nearest
                    )

        clipped_paths.append(reprojected_path)

    if not clipped_paths:
        raise RuntimeError("❌ No tiles intersect the AOI. Mosaic cannot be created.")

    print(f"🧩 Mosaicking {len(clipped_paths)} reprojected and clipped tiles...")
    src_files = [rasterio.open(p) for p in clipped_paths]
    mosaic, out_transform = merge(src_files)

    out_meta = src_files[0].meta.copy()
    out_meta.update({
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_transform,
        "count": mosaic.shape[0]
    })

    with rasterio.open(s2_ls_out_path, "w", **out_meta) as dst:
        dst.write(mosaic)

    print(f"✅ Mosaic clipped and reprojected saved to: {s2_ls_out_path}")
    return s2_ls_out_path

def classify_lulc_kmeans(band_paths, out_folder, n_classes=5):
    os.makedirs(out_folder, exist_ok=True)
    lulc_path = os.path.join(out_folder, f"lulc_kmeans_{n_classes}class_{timestamp}.tif")

    # Read and stack bands
    band_arrays = []
    for path in band_paths:
        with rasterio.open(path) as src:
            for b in range(1, src.count + 1):  # <-- NEW: Read all bands
                band_arrays.append(src.read(b))
            profile = src.profile
            transform = src.transform
            crs = src.crs

    # Stack to 3D array: (bands, rows, cols) → (rows*cols, bands)
    stacked = np.stack(band_arrays, axis=0)
    rows, cols = stacked.shape[1], stacked.shape[2]
    reshaped = stacked.reshape(len(band_arrays), -1).T

    # Mask out zero or nodata pixels
    valid_mask = ~np.any(reshaped == 0, axis=1)
    reshaped_valid = reshaped[valid_mask]

    # KMeans Classification
    print("🧠 Running KMeans classification...")
    kmeans = KMeans(n_clusters=n_classes, n_init='auto', random_state=42)
    labels = np.full(reshaped.shape[0], fill_value=-1)
    labels[valid_mask] = kmeans.fit_predict(reshaped_valid)

    # Reshape to raster
    classified = labels.reshape(rows, cols).astype(np.uint8)

    # Save LULC classified raster
    profile.update(dtype='uint8', count=1, nodata=255)
    with rasterio.open(lulc_path, 'w', **profile) as dst:
        dst.write(classified, 1)

    print(f"✅ LULC classified raster saved: {lulc_path}")
    return lulc_path

def classify_supervised_with_report(mosaic_raster_path, training_shapefile, out_folder, test_size=0.2):
    os.makedirs(out_folder, exist_ok=True)
    output_path = os.path.join(out_folder, f"lulc_supervised_{timestamp}.tif")

    print("🧭 Reading training samples...")
    gdf = gpd.read_file(training_shapefile)
    if 'class_id' not in gdf.columns:
        raise ValueError("Training shapefile must contain a 'class_id' column.")

    with rasterio.open(mosaic_raster_path) as src:
        img = src.read()
        profile = src.profile

        X = []
        y = []

        for idx, row in gdf.iterrows():
            geom = [row["geometry"]]
            class_val = row["class_id"]
            try:
                out_image, _ = mask(src, geom, crop=True)
                pixels = out_image.reshape(out_image.shape[0], -1).T
                valid_pixels = pixels[~np.any(pixels == 0, axis=1)]
                if len(valid_pixels) > 0:
                    X.extend(valid_pixels)
                    y.extend([class_val] * len(valid_pixels))
            except Exception as e:
                print(f"⚠️ Skipping geometry {idx} due to error: {e}")

    print(f"🧠 Training Random Forest on {len(X)} pixels...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, stratify=y, random_state=42)
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)

    print("📊 Generating classification report...")
    y_pred = clf.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred)

    print("📋 Classification Report:")
    print(classification_report(y_test, y_pred))

    print("🗺️ Classifying full image...")
    rows, cols = img.shape[1], img.shape[2]
    flat_pixels = img.reshape(img.shape[0], -1).T
    valid_mask = ~np.any(flat_pixels == 0, axis=1)
    predictions = np.full(flat_pixels.shape[0], fill_value=255, dtype=np.uint8)

    if np.any(valid_mask):
        predictions[valid_mask] = clf.predict(flat_pixels[valid_mask])

    classified = predictions.reshape(rows, cols)

    profile.update(dtype='uint8', count=1, nodata=255)
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(classified, 1)

    print(f"✅ Supervised LULC classification saved: {output_path}")

    # Plot confusion matrix
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=np.unique(y), yticklabels=np.unique(y))
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    cm_path = os.path.join(out_folder, f"confusion_matrix_{timestamp}.png")
    plt.savefig(cm_path)
    plt.close()
    print(f"📊 Confusion matrix saved: {cm_path}")

    return output_path, report, cm_path

def compute_zonal_stats(raster_path, zones_path, out_path):
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs

    gdf = gpd.read_file(zones_path)
    gdf = gdf.to_crs(raster_crs)  # Ensure CRS match

    stats = zonal_stats(gdf, raster_path, stats=["mean", "majority", "min", "max"], nodata=255)
    gdf_stats = gdf.copy()
    for key in stats[0].keys():
        gdf_stats[key] = [s[key] for s in stats]

    gdf_stats.to_file(out_path, driver="GeoJSON")
    print(f"✅ Zonal statistics saved to: {out_path}")



# dem_path=r"D:\KorrAI\DEM_rasters_COP30\rasters_COP30\output_hh.tif"
# out_folder=r"D:\KorrAI\PythonScripts\Outputs"
# aoi_path=r"D:\KorrAI\HongKongAdmBoundary.shp"
# tile_folder=r"D:\KorrAI\Sen2Data\S2_layerstacks"
# rail_path=r"D:\KorrAI\InfraData\hotosm_hkg_railways_lines_shp\hotosm_hkg_railways_lines_shp.shp"
# training_shapefile = r"D:\KorrAI\Sen2Data\TrainingSamples.shp"


# # Step 1: Clip DEM and get path
# clipped_dem = reproject_and_clip_dem(
#     dem_path=dem_path,
#     aoi_path=aoi_path,
#     out_folder=out_folder
# )

# # Step 2: Run hydrology using returned DEM path
# hydro_outputs = run_hydrology_whitebox(
#     dem_path=clipped_dem,
#     out_folder=out_folder
# )

# # Step 3: Flood Zone Analysis
# flood_zone_raster = extract_flood_zones(
#     slope_path=hydro_outputs["slope"],
#     flow_acc_path=hydro_outputs["flow_acc"],
#     out_folder=out_folder,
#     slope_thresh=5,
#     flow_thresh=1500
# )

# # Step 4: Polygonize Raster
# flood_vector = polygonize_flood_raster(
#     flood_raster_path=flood_zone_raster,
#     out_folder=out_folder
# )

# # Step 4: Compute Railway Flood Exposure
# exposure_summary = compute_railway_flood_exposure(
#     rail_path=rail_path,
#     flood_polygon_path=flood_vector
# )

# # Step 5: Mosaic and Clip Sentinel 2 Data
# mosaic_clipped_path = clip_and_mosaic_tiles(
#     tile_folder=tile_folder,
#     aoi_path=aoi_path,
#     out_folder=out_folder
# )

# # Step 6: Perform Unsupervised Classification
# lulc_raster = classify_lulc_kmeans(
#     band_paths=[mosaic_clipped_path],  # If you want to read bands 1-4 from it
#     out_folder=os.path.join(out_folder, "lulc"),
#     n_classes=5
# )

# # Step 7: Run supervised classification
# supervised_output, report, cm_path = classify_supervised_with_report(
#     mosaic_raster_path=mosaic_clipped_path,
#     training_shapefile=training_shapefile,
#     out_folder=out_folder
# )

# # Step 8: Perform Zonal Statistics
# zonal_stats_path = compute_zonal_stats(
#     zones_path=flood_vector,
#     raster_path=supervised_output,
#     out_path=os.path.join(out_folder, f"zonal_stats_flood_supervised_{timestamp}.geojson")
# )

if __name__ == "__main__":
    # CLI Argument Parsing
    parser = argparse.ArgumentParser(description="Run Flood Risk Zoning and LULC Classification Pipeline")

    parser.add_argument('--dem', type=str, required=True, help='Path to input DEM file (Raw)')
    parser.add_argument('--aoi', type=str, required=True, help='Path to administrative boundary shapefile')
    parser.add_argument('--tiles', type=str, required=True, help='Folder containing Sentinel-2 layer stacked tiles. Folder should only contain those tif files which are to be mosaiced together.')
    parser.add_argument('--rail', type=str, required=True, help='Path to railway shapefile')
    parser.add_argument('--training', type=str, required=True, help='Path to training shapefile for supervised classification in shapefile format')
    parser.add_argument('--out', type=str, required=True, help='Output folder for results')

    args = parser.parse_args()

    dem_path = args.dem
    aoi_path = args.aoi
    tile_folder = args.tiles
    rail_path = args.rail
    training_shapefile = args.training
    out_folder = args.out

    # Workflow
    clipped_dem = reproject_and_clip_dem(dem_path, aoi_path, out_folder)
    hydro_outputs = run_hydrology_whitebox(clipped_dem, out_folder)
    flood_zone_raster = extract_flood_zones(hydro_outputs["slope"], hydro_outputs["flow_acc"], out_folder)
    flood_vector = polygonize_flood_raster(flood_zone_raster, out_folder)
    exposure_summary = compute_railway_flood_exposure(rail_path, flood_vector)
    mosaic_clipped_path = clip_and_mosaic_tiles(tile_folder, aoi_path, out_folder)
    lulc_raster = classify_lulc_kmeans([mosaic_clipped_path], os.path.join(out_folder, "lulc"))
    supervised_output, report, cm_path = classify_supervised_with_report(mosaic_clipped_path, training_shapefile, out_folder)
    zonal_stats_path = compute_zonal_stats(supervised_output, flood_vector, os.path.join(out_folder, f"zonal_stats_flood_supervised_{timestamp}.geojson"))