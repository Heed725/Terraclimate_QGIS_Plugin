# -*- coding: utf-8 -*-
"""
Resample Raster to Reference - Processing algorithm to resample a raster
(single- or multi-band) to match the resolution, extent, and CRS of a
reference raster such as a DEM.
"""
import os

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    Qgis,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsRasterLayer,
    QgsProject,
)

import processing


try:
    PROCESSING_NUMBER_DOUBLE = QgsProcessingParameterNumber.Type.Double
except AttributeError:
    PROCESSING_NUMBER_DOUBLE = getattr(QgsProcessingParameterNumber, "Double")


class ResampleRasterToReference(QgsProcessingAlgorithm):
    """
    Resample a raster to match the resolution, extent, and CRS of a
    reference raster.  All bands are preserved.

    Typical use-case: you downloaded a TerraClimate multi-band raster at
    ~4 km and need it resampled to the grid of a 30 m DEM for further
    analysis (e.g. temperature lapse-rate correction).
    """

    INPUT_RASTER = "INPUT_RASTER"
    REFERENCE_RASTER = "REFERENCE_RASTER"
    RESAMPLING = "RESAMPLING"
    NODATA = "NODATA"
    OUTPUT = "OUTPUT"

    RESAMPLING_OPTIONS = [
        "Nearest Neighbour",
        "Bilinear",
        "Cubic",
        "Cubic Spline",
        "Lanczos",
        "Average",
        "Mode",
    ]

    # Maps the enum index to the GDAL resampling code used by gdal:warpreproject
    RESAMPLING_GDAL_CODES = {
        0: 0,   # Nearest Neighbour
        1: 1,   # Bilinear
        2: 2,   # Cubic
        3: 3,   # Cubic Spline
        4: 4,   # Lanczos
        5: 5,   # Average
        6: 6,   # Mode
    }

    def tr(self, text):
        return QCoreApplication.translate("ResampleRasterToReference", text)

    def createInstance(self):
        return ResampleRasterToReference()

    def name(self):
        return "resamplerastertoref"

    def displayName(self):
        return self.tr("Resample Raster to Reference")

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.svg"))

    def group(self):
        return ""

    def groupId(self):
        return ""

    def shortHelpString(self):
        return self.tr(
            "<h3>Resample Raster to Reference</h3>"
            "<p>Resamples a raster so that it matches the resolution, extent, "
            "and coordinate system of a reference raster (e.g. a DEM). "
            "All bands are preserved.</p>"

            "<h4>Parameters</h4>"
            "<ul>"
            "<li><b>Input raster:</b> The raster to resample (single- or multi-band)</li>"
            "<li><b>Reference raster:</b> The raster whose grid to match (e.g. a DEM)</li>"
            "<li><b>Resampling method:</b> Interpolation algorithm. "
            "Bilinear or Cubic recommended for continuous data such as temperature; "
            "Nearest Neighbour for categorical data</li>"
            "<li><b>NoData override:</b> Optional custom NoData value. "
            "Leave as 0 to keep the original NoData</li>"
            "<li><b>Output raster:</b> Path for the resampled GeoTIFF</li>"
            "</ul>"

            "<h4>How it works</h4>"
            "<p>Uses GDAL Warp under the hood.  The reference raster defines "
            "the target extent, pixel size, and CRS.  The input raster is "
            "reprojected and resampled in a single pass with multithreading "
            "enabled.  Output is always Float32 to avoid precision loss.</p>"

            "<h4>Typical workflow</h4>"
            "<ol>"
            "<li>Download TerraClimate data with <i>Download TerraClimate Data</i></li>"
            "<li>Optionally split it with <i>Split Raster Bands</i></li>"
            "<li>Use this tool to resample the result onto your DEM grid</li>"
            "</ol>"
        )

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_RASTER,
                self.tr("Input raster to resample"),
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.REFERENCE_RASTER,
                self.tr("Reference raster (target grid, e.g. a DEM)"),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.RESAMPLING,
                self.tr("Resampling method"),
                options=self.RESAMPLING_OPTIONS,
                defaultValue=1,  # Bilinear — good default for temperature
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.NODATA,
                self.tr("NoData value override (0 = keep original)"),
                type=PROCESSING_NUMBER_DOUBLE,
                defaultValue=0,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
                self.tr("Resampled raster"),
            )
        )

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def processAlgorithm(self, parameters, context, feedback):
        input_layer = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        ref_layer = self.parameterAsRasterLayer(parameters, self.REFERENCE_RASTER, context)
        resampling_idx = self.parameterAsEnum(parameters, self.RESAMPLING, context)
        nodata_override = self.parameterAsDouble(parameters, self.NODATA, context)

        if input_layer is None or not input_layer.isValid():
            raise QgsProcessingException(self.tr("Invalid input raster."))
        if ref_layer is None or not ref_layer.isValid():
            raise QgsProcessingException(self.tr("Invalid reference raster."))

        ref_extent = ref_layer.extent()
        ref_crs = ref_layer.crs()
        ref_res_x = ref_layer.rasterUnitsPerPixelX()
        ref_res_y = ref_layer.rasterUnitsPerPixelY()

        feedback.pushInfo("=" * 60)
        feedback.pushInfo("Resample Raster to Reference")
        feedback.pushInfo("=" * 60)
        feedback.pushInfo(f"Input raster : {input_layer.source()}")
        feedback.pushInfo(f"  Bands      : {input_layer.bandCount()}")
        feedback.pushInfo(f"  CRS        : {input_layer.crs().authid()}")
        feedback.pushInfo(f"  Resolution : {input_layer.rasterUnitsPerPixelX():.6f} x "
                          f"{input_layer.rasterUnitsPerPixelY():.6f}")
        feedback.pushInfo(f"Reference    : {ref_layer.source()}")
        feedback.pushInfo(f"  CRS        : {ref_crs.authid()}")
        feedback.pushInfo(f"  Resolution : {ref_res_x:.6f} x {ref_res_y:.6f}")
        feedback.pushInfo(f"  Extent     : {ref_extent.toString()}")
        feedback.pushInfo(f"Resampling   : {self.RESAMPLING_OPTIONS[resampling_idx]}")
        feedback.pushInfo("")

        # Determine NoData: honour override, otherwise let GDAL keep original
        use_nodata = None
        if nodata_override != 0:
            use_nodata = nodata_override
            feedback.pushInfo(f"NoData override: {use_nodata}")

        warp_params = {
            "INPUT": input_layer,
            "SOURCE_CRS": input_layer.crs(),
            "TARGET_CRS": ref_crs,
            "RESAMPLING": self.RESAMPLING_GDAL_CODES[resampling_idx],
            "NODATA": use_nodata,
            "TARGET_RESOLUTION": ref_res_x,
            "TARGET_EXTENT": ref_extent,
            "TARGET_EXTENT_CRS": ref_crs,
            "DATA_TYPE": 6,       # Float32
            "MULTITHREADING": True,
            "OPTIONS": "COMPRESS=LZW",
            "EXTRA": "",
            "OUTPUT": parameters[self.OUTPUT],
        }

        feedback.pushInfo("Running GDAL Warp...")
        result = processing.run(
            "gdal:warpreproject",
            warp_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        out_path = result["OUTPUT"]
        feedback.pushInfo("")
        feedback.pushInfo(f"Resampling complete: {out_path}")

        # Load into map
        layer_name = os.path.basename(out_path)
        out_layer = QgsRasterLayer(out_path, layer_name)
        if out_layer.isValid():
            QgsProject.instance().addMapLayer(out_layer)
            feedback.pushInfo(f"Added layer: {layer_name}  ({out_layer.bandCount()} bands)")
        else:
            feedback.reportError("Warning: output saved but could not be loaded in QGIS.")

        feedback.pushInfo("")
        feedback.pushInfo("=" * 60)
        feedback.pushInfo("COMPLETE!")
        feedback.pushInfo("=" * 60)

        return {self.OUTPUT: out_path}
