# 🌊 Flood Risk Zoning and LULC Classification using Remote Sensing and GIS in Hong Kong
This project integrates geospatial analysis, remote sensing, and GIS-based cartography to assess flood risk zones and land use/land cover (LULC) patterns in Hong Kong. It combines automated Python scripting with manual mapping using QGIS, and documents the results in a structured report.

---

## 📁 Project Folder Structure
📂 Project_Root/
├── 📁 Data/ # All input spatial datasets (DEM, S2, AOI, Railway, Training)
├── 📁 PythonScripts/ # Python pipeline for automated processing
├── 📁 Maps/ # Final maps exported from QGIS (PDF/PNG)
├── 📁 QGISProject/ # QGIS project file (.qgz), layer styles, templates
├── 📁 Report/ # Final written report (DOCX, PDF), charts, figures
└── 📄 README.md # Project overview and usage instructions

---

## 🧰 Tools & Technologies Used

| Type                  | Tool / Library                      |
|-----------------------|--------------------------------------|
| GIS Desktop           | QGIS 3.x                             |
| Programming           | Python 3.10+, Conda environment      |
| Python Libraries      | Rasterio, GeoPandas, WhiteboxTools, scikit-learn, matplotlib |
| Remote Sensing Data   | Sentinel-2 (multispectral), ASTER/COP DEM |
| Infrastructure Data   | OpenStreetMap Railway Lines         |
| Reporting & Cartography | MS Word, QGIS Composer             |

---

## 🔄 Project Workflow

### 1. **Preprocessing (Python Scripts)**
- Reproject and clip DEM
- Perform hydrological modeling (flow accumulation, slope)
- Extract flood-prone zones based on terrain criteria
- Assess infrastructure (railway) exposure
- Conduct LULC classification (KMeans & Random Forest)
- Generate zonal statistics

### 2. **Visualization & Cartographic Mapping (QGIS)**
- Load outputs: classified rasters, flood zones, exposure maps
- Apply custom symbology (legend, colors, labels)
- Prepare cartographic layouts using QGIS Print Layout
- Export high-resolution maps

### 3. **Reporting (MS Word)**
- Structure report into methodology, results, and conclusion
- Includes:
  - Flood zone maps
  - Historical flood risk analysis
  - LULC classification results (unsupervised + supervised)
  - Exposure summary tables
  - Screenshots and flowcharts of the pipeline

---

## ⚙️ Setting Up the Environment

You can use `conda` to create an isolated environment with all required dependencies.

```bash
# Create conda env
conda create -n flood-lulc python=3.10

# Activate environment
conda activate flood-lulc

# Install dependencies
pip install -r requirements.txt
```

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
