# TerraClimateDownloader QGIS Plugin

![Version](https://img.shields.io/badge/version-0.0.3-green?style=flat-square&logo=qgis)
![QGIS](https://img.shields.io/badge/QGIS-3.16--3.99-blue?style=flat-square&logo=qgis)
![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)

## 🌍 Overview

**TerraClimateDownloader** is a QGIS plugin that allows you to directly download and clip **TerraClimate** datasets (monthly climate & water balance variables, 1958–2025) via **OPeNDAP**.
It connects to the **TerraClimate THREDDS server**, extracts a bounding-box subset using [xarray](https://xarray.dev) and [rioxarray](https://corteva.github.io/rioxarray/), saves a temporary GeoTIFF, and then clips it to any polygon boundary in your QGIS project using GDAL.

- 📅 Supports **any year from 1958–2025**
- 🌡️ Supports **all 14 TerraClimate variables** (ppt, tmax, tmin, vap, vpd, aet, def, pdsi, pet, q, soil, srad, swe, ws)
- 📆 **Single year** or **year range** mode for multi-year downloads
- 🎨 **Automatic pseudocolor styling** with variable-appropriate color ramps
- 🗺️ Clips raster outputs to any vector boundary
- ✂️ **Split Raster Bands** tool to export multiband outputs as individual monthly or yearly files
- ⚡ Adds the result automatically to your QGIS project
- 📦 **One-click dependency installer** via OSGeo4W Shell
- 🔍 Available in **Processing Toolbox** and **Plugins menu**

---

## 📦 Installation

1. Download the latest release ZIP:
   [TerraClimateDownloader.zip](https://github.com/Heed725/Terraclimate_QGIS_Plugin/releases)

2. In QGIS:
   - Go to **Plugins → Manage and Install Plugins → Install from ZIP**
   - Select `TerraClimateDownloader.zip`
   - Enable the plugin

3. Install dependencies (first time only):
   - Go to **Plugins → TerraClimate Downloader → Install Dependencies**
   - Click **"Install Dependencies (OSGeo4W Shell)"**
   - Wait for the installation to finish in the shell window
   - Restart QGIS

4. Access the plugin from:
   - **Processing Toolbox** → *TerraClimate Downloader → Download TerraClimate Data*
   - **Processing Toolbox** → *TerraClimate Downloader → Split Raster Bands*
   - **Plugins Menu / Toolbar** → *TerraClimate Downloader*

---

## ⚙️ Requirements

This plugin requires the following Python packages installed into your **QGIS Python environment**:

| Package | Status | Minimum Version |
|---------|--------|-----------------|
| `xarray` | Required | 2023.1.0 |
| `rioxarray` | Required | 0.15.0 |
| `numpy` | Required | 1.24 |
| `netCDF4` | Required | 1.6.0 |
| `dask` | Optional | — |

### Automatic Installation (Recommended)

Use the built-in installer: **Plugins → TerraClimate Downloader → Install Dependencies**. It opens an OSGeo4W Shell and runs the install command for you.

### Manual Installation

On **Windows (OSGeo4W Shell):**

```bash
python -m pip install xarray rioxarray "numpy>=1.24" netCDF4 dask
```

On **Linux/macOS:**

```bash
pip3 install --user xarray rioxarray "numpy>=1.24" netCDF4 dask
```

---

## 🚀 Usage

### Download TerraClimate Data

1. Load a polygon boundary layer into QGIS (e.g., a country or district shapefile).
2. Run **Download TerraClimate Data** from the Processing Toolbox or Plugins menu.
3. Configure:
   - **Input polygon layer** — your area of interest
   - **Climate variable** — choose from 14 variables (temperature, precipitation, etc.)
   - **Year mode** — Single year or Year range
   - **Year / End year** — select your time period (1958–2025)
   - **Month** — `-1` for all months (multiband), or `1–12` for a specific month
   - **Buffer** — extra area around your boundary in degrees
4. Click **Run** → a clipped GeoTIFF is downloaded, styled, and added to the map.

### Split Raster Bands

Use this tool to break apart multiband rasters (from year range downloads) into separate files:

- **Monthly mode** — each band becomes its own GeoTIFF (e.g., `tmax_01_Jan_2023.tif`)
- **Yearly mode** — every 12 bands are grouped into one file per year (e.g., `tmax_2023.tif`)

---

## 🎨 Automatic Styling

Downloaded rasters are automatically styled with color ramps suited to each variable:

| Variable Type | Color Ramp |
|---------------|------------|
| Temperature (tmax, tmin) | Blue → White → Red |
| Precipitation (ppt, q) | Yellow → Green → Blue |
| Drought Index (pdsi) | Red → White → Blue (centered on zero) |
| Moisture (aet, pet, soil, vap) | Brown → Teal |
| Water Deficit (def, vpd) | Green → Yellow → Red |
| Radiation (srad) | Purple → Yellow → White |
| Snow (swe) | Light Blue → Dark Blue |
| Wind Speed (ws) | Yellow → Dark Green |

For multiband outputs, min/max is calculated across all bands so colors remain consistent when switching between months.

---

## 🎬 Video Tutorial

[![Video Tutorial](https://img.shields.io/badge/YouTube-Tutorial-red?style=flat-square&logo=youtube)](https://youtu.be/IqF5fW00lWU?si=TjLjWCiLSusx5QcQ)

---

## 📖 Data Source

**TerraClimate Dataset:**
Abatzoglou, J.T., S.Z. Dobrowski, S.A. Parks, K.C. Hegewisch (2018).
*TerraClimate, a high-resolution global dataset of monthly climate and climatic water balance from 1958–2015*.
*Scientific Data*, 5:170191. [DOI:10.1038/sdata.2017.191](https://doi.org/10.1038/sdata.2017.191)

---

## 🎨 Credits

- **Plugin Author:** Hemed Lungo ([Hemedlungo@gmail.com](mailto:Hemedlungo@gmail.com))
- **Icon:** by Fusion5085 (licensed for free use)
- **Dataset:** TerraClimate, Abatzoglou et al. (2018)

---

## 📜 License

This plugin is released under the **MIT License**.
See [LICENSE](LICENSE) for details.

---

## 🙌 Acknowledgements

Thanks to the **QGIS community** and **GDAL/xarray developers** for the tools that make this plugin possible.
