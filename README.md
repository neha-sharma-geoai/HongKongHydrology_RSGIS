# 🌊 Flood Risk Zoning and LULC Classification using Remote Sensing and GIS in Hong Kong
This project integrates geospatial analysis, remote sensing, and GIS-based cartography to assess flood risk zones and land use/land cover (LULC) patterns in Hong Kong. It combines automated Python scripting with manual mapping using QGIS, and documents the results in a structured report.

---

## 📁 Project Folder Structure
```
📂 Project_Root/
├── 📁 Data/ # All input spatial datasets (DEM, S2, AOI, Railway, Training)
├── 📁 PythonScripts/ # Python pipeline for automated processing
├── 📁 Maps/ # Final maps exported from QGIS (PNG)
├── 📁 QGISProject/ # QGIS project file (.qgz), layer styles, templates
├── 📁 Report/ # Final written report (DOCX, PDF), charts, figures
└── 📄 README.md # Project overview and usage instructions
```

---

## 🧰 Tools & Technologies Used

| Type                  | Tool / Library                      |
|-----------------------|--------------------------------------|
| GIS Desktop           | QGIS 3.x                             |
| Programming           | Python 3.10+, Conda environment      |
| Python Libraries      | Rasterio, GeoPandas, WhiteboxTools, scikit-learn, matplotlib |
| Remote Sensing Data   | Sentinel-2 (multispectral), ASTER |
| Infrastructure Data   | OpenStreetMap         |
| Reporting & Cartography | MS Word             |

---

## 🔄 Python Script Workflow

### **Preprocessing (Python Scripts)**
- Reproject and clip DEM
- Perform hydrological modeling (flow accumulation, slope)
- Extract flood-prone zones based on terrain criteria
- Assess infrastructure (railway) exposure
- Conduct LULC classification (KMeans & Random Forest)
- Generate zonal statistics

---

## ⚙️ Setting Up the Environment

You can use `conda` to create an isolated environment with all required dependencies.
Run the following commands in the command prompt to create your conda environment.

```bash
# Create conda env
conda create -n flood-lulc python=3.10

# Activate environment
conda activate flood-lulc

# Install dependencies
pip install -r requirements.txt # .txt file is given in the repo.
```
Once the environment is set up, set the current directory to the root folder where the Python script is present.
You can simply run the command below in the CLI with the correct paths to the required datasets. It will save the outputs in the '--out' path.

## ▶️ Running the Python Pipeline

### 🖥️ Example (Windows)

```cmd
python flood_lulc_pipeline.py ^
  --dem "D:\Data\ProcessedData\DEM_rasters_COP30\Aster\aster_mosaic.tiff" ^
  --aoi "D:\Data\RawData\HongKongAdmBoundary.shp" ^
  --tiles "D:\Data\RawData\Sen2Data\S2_layerstacks" ^
  --rail "D:\Data\RawData\InfraData\hotosm_hkg_railways_lines_shp\hotosm_hkg_railways_lines_shp.shp" ^
  --training "D:\Data\RawData\Sen2Data\TrainingSamples.shp" ^
  --out "D:\PythonScripts\Outputs"
```
### Required Paths Details -

- '--dem', type=str, required=True, help='Path to input DEM file (Raw), only a single input file can be given. It will be reprojected and clipped to the Hong Kong region.'
- '--aoi', type=str, required=True, help='Path to administrative boundary shapefile'
- '--tiles', type=str, required=True, help='Folder containing Sentinel-2 layer stacked tiles. The folder should only contain those TIF files which are to be mosaiced together.'
- '--rail', type=str, required=True, help='Path to railway shapefile'
- '--training', type=str, required=True, help='Path to training shapefile for supervised classification in shapefile format'
- '--out', type=str, required=True, help='Output folder for results'

### 📊 Outputs
- clipped_dem_2326_*.tif
- flow_acc_*.tif, slope_*.tif
- flood_zones_*.tif + polygonized shp
- Flood-impacted railway lines
- lulc_kmeans_*.tif, lulc_supervised_*.tif
- confusion_matrix_*.png
- zonal_stats_flood_supervised_*.geojson

Thank you for reading!
