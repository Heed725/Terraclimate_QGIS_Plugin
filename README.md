# TerraClimate Downloader for QGIS

**Version 0.0.8**

**Compatibility:** QGIS 3.16-4.99 with Qt5/Qt6 compatibility updates.  
**Checked on:** Jul 24, 2026, 09:19 PM GMT+3
**Qt6 validation:** All 27 reported scoped-enum/API issues were corrected while keeping version 0.0.8.

Download and clip TerraClimate climate data directly in QGIS. Select your area of interest, choose a climate variable, and download either a single year or a multi-year stack.

## Easy Installation

### Method 1: Install from ZIP

1. Download the `TerraClimateDownloader-0.0.8.zip` file.
2. In QGIS, go to **Plugins > Manage and Install Plugins**.
3. Click **Install from ZIP**.
4. Select the ZIP file and click **Install Plugin**.
5. Open **Plugins > TerraClimate Downloader > Install Dependencies**.
6. Click **Install Required Packages** and wait for completion.
7. Restart QGIS.

### Method 2: Manual Installation

1. Extract the ZIP file.
2. Copy the `TerraClimateDownloader` folder to your QGIS plugins directory.
3. Restart QGIS.
4. Enable the plugin in **Plugins > Manage and Install Plugins**.
5. Install dependencies as described below.

## Installing Python Dependencies

### Automatic

1. Open **Plugins > TerraClimate Downloader > Install Dependencies**.
2. Click **Install Required Packages**.
3. Restart QGIS after installation.

### Manual

Run this command with the same Python executable that QGIS uses:

```bash
python -m pip install --user --upgrade-strategy only-if-needed "numpy>=1.24,<2" xarray rioxarray netCDF4 dask
```

## How to Use

1. Load a polygon layer representing your area of interest.
2. Open the tool from **Plugins > TerraClimate Downloader** or the **Processing Toolbox**.
3. Choose a climate variable.
4. Choose a year mode:
   - `Single year`: select one year and either one month or all 12 months.
   - `Year range`: select a start year and end year; the tool downloads all months automatically.
5. Set the output file location and run.

Examples:
- `2024` in single-year mode with month `-1` gives a 12-band raster.
- `2023-2024` in year-range mode gives a 24-band raster.
- `2021-2025` in year-range mode gives a 60-band raster.

## Available Climate Variables

| Variable | Description | Units |
|----------|-------------|-------|
| aet | Actual Evapotranspiration | mm |
| def | Climatic Water Deficit | mm |
| pdsi | Palmer Drought Severity Index | - |
| pet | Potential Evapotranspiration | mm |
| ppt | Precipitation | mm |
| q | Runoff | mm |
| soil | Soil Moisture | mm |
| srad | Downward Shortwave Radiation | W/m² |
| swe | Snow Water Equivalent | mm |
| tmax | Maximum Temperature | °C |
| tmin | Minimum Temperature | °C |
| vap | Vapor Pressure | kPa |
| vpd | Vapor Pressure Deficit | kPa |
| ws | Wind Speed | m/s |

## Notes

- Supported years: `1958-2025`
- All-month downloads are combined into one multiband raster.
- Large year ranges can create large raster files and take longer to download.

## Troubleshooting

### Missing Python packages

- Use the built-in dependency installer: **Plugins > TerraClimate Downloader > Install Dependencies**
- Restart QGIS after installing packages

### Connection timeout

- Check your internet connection
- The TerraClimate server may be temporarily unavailable
- Increase the **Connection retries** parameter

### Large downloads are slow

- TerraClimate data is downloaded over the internet
- Large areas or long year ranges will take longer
- Try a smaller region first if you want to test the workflow

## Credits

- **Author:** Hemed Lungo (Hemedlungo@gmail.com)
- **Icon:** Fusion5085
- **TerraClimate Dataset:** Abatzoglou, J.T., S.Z. Dobrowski, S.A. Parks, K.C. Hegewisch (2018), Scientific Data

## Links

- [GitHub Repository](https://github.com/Heed725/Terraclimate_QGIS_Plugin/)
- [TerraClimate Website](https://www.climatologylab.org/terraclimate.html)
- [Report Issues](https://github.com/Heed725/Terraclimate_QGIS_Plugin/issues)

## License

See `LICENSE`.


### 0.0.8 Security hardening

- Resolved 17 Bandit findings.
- Removed silent exception swallowing from processing and installer paths.
- Replaced `subprocess.Popen` with validated Qt `QProcess` launches.
- Restricted process execution to absolute executable paths and fixed installer arguments.

