# TerraClimateDownloader QGIS Plugin

## 🌍 Overview
**TerraClimateDownloader** is a QGIS plugin that allows you to directly download and clip **TerraClimate** datasets (monthly climate & water balance variables, 1958–2024) via **OPeNDAP**.  

It connects to the **TerraClimate THREDDS server**, extracts a bounding-box subset using [xarray](https://xarray.dev) and [rioxarray](https://corteva.github.io/rioxarray/), saves a temporary GeoTIFF, and then clips it to any polygon boundary in your QGIS project using GDAL.

- 📅 Supports **any year 1958–2024**
- 🌡️ Supports **all TerraClimate variables** (ppt, tmax, tmin, vap, vpd, aet, etc.)
- 🗺️ Clips raster outputs to any vector boundary
- ⚡ Adds the result automatically to your QGIS project
- 🔍 Available in **Processing Toolbox** and **Plugins menu**

---

## 📦 Installation

1. Download the latest release ZIP:  
   [TerraClimateDownloader.zip](https://github.com/yourusername/TerraClimateDownloader/releases)

2. In QGIS:  
   - Go to **Plugins → Manage and Install Plugins → Install from ZIP**  
   - Select `TerraClimateDownloader.zip`  
   - Enable the plugin  

3. Access it from:  
   - **Processing Toolbox** → *TerraClimateDownloader → Clip TerraClimate (OPeNDAP) to Layer (GDAL)*  
   - **Plugins Menu / Toolbar** → *TerraClimate Downloader*  

---

## ⚙️ Requirements

This plugin requires the following Python packages installed into your **QGIS Python environment**:

- `xarray`
- `rioxarray`
- `numpy`

Optional (recommended for performance):  
- `netCDF4`
- `dask`

### Installation

On **Windows (OSGeo4W Shell / QGIS Python env):**
```bash
python -m pip install --upgrade pip
python -m pip install xarray rioxarray numpy netCDF4 dask
````

On **Linux/macOS:**

```bash
pip3 install --user xarray rioxarray numpy netCDF4 dask
```

---

## 🚀 Usage

1. Load a polygon boundary layer into QGIS (e.g., a country shapefile).
2. Run **TerraClimate Downloader** (Processing Toolbox or Plugins menu).
3. Configure:

   * Input polygon layer
   * Variable (ppt, tmax, tmin, etc.)
   * Year (1958–2024)
   * TIME_INDEX = `-1` for all months (multiband), or `1–12` for a single month
4. Click **Run** → A clipped GeoTIFF is downloaded, processed, and added to the map.

---

## 📖 Data Source

**TerraClimate Dataset:**
Abatzoglou, J.T., S.Z. Dobrowski, S.A. Parks, K.C. Hegewisch (2018).
*TerraClimate, a high-resolution global dataset of monthly climate and climatic water balance from 1958–2015*.
*Scientific Data*, 5:170191. [DOI:10.1038/sdata.2017.191](https://doi.org/10.1038/sdata.2017.191)

---

## 🎨 Credits

* **Plugin Author:** Hemed Lungo
* **Icon:** by Fusion5085 (licensed for free use)
* **Dataset:** TerraClimate, Abatzoglou et al. (2018)

---

## 📜 License

This plugin is released under the **MIT License**.
See [LICENSE](LICENSE) for details.

---

## 🙌 Acknowledgements

Thanks to the **QGIS community** and **GDAL/xarray developers** for the tools that make this plugin possible.
