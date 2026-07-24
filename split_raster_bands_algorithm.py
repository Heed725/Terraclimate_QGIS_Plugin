# -*- coding: utf-8 -*-
"""
Split Raster Bands - Processing algorithm to separate a multi-band raster
into individual single-band rasters (monthly) or yearly multi-band rasters.
"""
import os

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.core import (
    Qgis,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputMultipleLayers,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
    QgsProject,
    QgsRasterBandStats,
    QgsRasterLayer,
    QgsRasterShader,
    QgsColorRampShader,
    QgsSingleBandPseudoColorRenderer,
)

import processing


try:
    PROCESSING_NUMBER_INTEGER = QgsProcessingParameterNumber.Type.Integer
except AttributeError:
    PROCESSING_NUMBER_INTEGER = getattr(QgsProcessingParameterNumber, "Integer")

try:
    RASTER_STAT_MIN = QgsRasterBandStats.Stats.Min
    RASTER_STAT_MAX = QgsRasterBandStats.Stats.Max
except AttributeError:
    RASTER_STAT_MIN = getattr(QgsRasterBandStats, "Min")
    RASTER_STAT_MAX = getattr(QgsRasterBandStats, "Max")

try:
    SHADER_INTERPOLATED = QgsColorRampShader.Type.Interpolated
except AttributeError:
    SHADER_INTERPOLATED = getattr(QgsColorRampShader, "Interpolated")

try:
    SHADER_CONTINUOUS = QgsColorRampShader.ClassificationMode.Continuous
except AttributeError:
    SHADER_CONTINUOUS = getattr(QgsColorRampShader, "Continuous")


class SplitRasterBands(QgsProcessingAlgorithm):
    """
    Split a multi-band raster into separate rasters by month or by year.
    """

    INPUT_RASTER = "INPUT_RASTER"
    OUTPUT_FOLDER = "OUTPUT_FOLDER"
    PREFIX = "PREFIX"
    START_YEAR = "START_YEAR"
    SPLIT_MODE = "SPLIT_MODE"
    ADD_TO_MAP = "ADD_TO_MAP"
    OUTPUT_LAYERS = "OUTPUT_LAYERS"

    SPLIT_MODE_OPTIONS = [
        "Monthly (one band per file)",
        "Yearly (12 bands per file)",
    ]

    MONTH_NAMES = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    def tr(self, string):
        return QCoreApplication.translate("SplitRasterBands", string)

    def createInstance(self):
        return SplitRasterBands()

    def name(self):
        return "splitrasterbands"

    def displayName(self):
        return self.tr("Split Raster Bands")

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.svg"))

    def group(self):
        return ''

    def groupId(self):
        return ''

    def shortHelpString(self):
        return self.tr(
            "Splits a multi-band raster into separate files with automatic month/year labelling.\n\n"
            "Two split modes:\n\n"
            "MONTHLY - each band becomes its own single-band GeoTIFF:\n"
            "  24 bands + start 2023 = 24 files (Jan_2023 ... Dec_2024)\n\n"
            "YEARLY - every 12 bands are grouped into one file per year:\n"
            "  24 bands + start 2023 = 2 files (2023.tif with 12 bands, 2024.tif with 12 bands)\n\n"
            "Works with any multiple of 12 bands. If the band count is not a multiple "
            "of 12, only Monthly mode with numeric labels is used."
        )

    def _apply_singleband_pseudocolor(self, raster_layer, feedback=None):
        """Apply a Singleband Pseudocolor renderer using band 1."""
        try:
            provider = raster_layer.dataProvider()
            band_count = raster_layer.bandCount()

            if band_count > 1:
                global_min = float("inf")
                global_max = float("-inf")
                for band_num in range(1, band_count + 1):
                    stats = provider.bandStatistics(
                        band_num,
                        RASTER_STAT_MIN | RASTER_STAT_MAX,
                        raster_layer.extent(),
                        0,
                    )
                    if stats.minimumValue != -9999.0 and stats.minimumValue < global_min:
                        global_min = stats.minimumValue
                    if stats.maximumValue != -9999.0 and stats.maximumValue > global_max:
                        global_max = stats.maximumValue
                min_val = global_min
                max_val = global_max
            else:
                stats = provider.bandStatistics(
                    1,
                    RASTER_STAT_MIN | RASTER_STAT_MAX,
                    raster_layer.extent(),
                    0,
                )
                min_val = stats.minimumValue
                max_val = stats.maximumValue

            if min_val == float("inf") or max_val == float("-inf"):
                return False
            if min_val == max_val:
                max_val = min_val + 1

            shader = QgsRasterShader()
            color_ramp = QgsColorRampShader()
            color_ramp.setColorRampType(SHADER_INTERPOLATED)
            color_ramp.setMinimumValue(min_val)
            color_ramp.setMaximumValue(max_val)
            color_ramp.setClassificationMode(SHADER_CONTINUOUS)
            color_ramp.setColorRampItemList([
                QgsColorRampShader.ColorRampItem(min_val, QColor(68, 1, 84), f"{min_val:.1f}"),
                QgsColorRampShader.ColorRampItem(min_val + (max_val - min_val) * 0.25, QColor(59, 82, 139), ""),
                QgsColorRampShader.ColorRampItem(min_val + (max_val - min_val) * 0.5, QColor(33, 145, 140), ""),
                QgsColorRampShader.ColorRampItem(min_val + (max_val - min_val) * 0.75, QColor(94, 201, 98), ""),
                QgsColorRampShader.ColorRampItem(max_val, QColor(253, 231, 37), f"{max_val:.1f}"),
            ])
            shader.setRasterShaderFunction(color_ramp)

            renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
            renderer.setClassificationMin(min_val)
            renderer.setClassificationMax(max_val)
            raster_layer.setRenderer(renderer)
            raster_layer.triggerRepaint()

            if feedback:
                feedback.pushInfo(
                    f"    Applied Singleband Pseudocolor styling (range: {min_val:.2f} to {max_val:.2f})"
                )
            return True
        except Exception as exc:
            if feedback:
                feedback.reportError(f"    Warning: Could not apply pseudocolor style: {exc}")
            return False

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_RASTER,
                self.tr("Input multi-band raster"),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.PREFIX,
                self.tr("Output filename prefix (e.g. tmax, ppt)"),
                defaultValue="band",
                optional=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.START_YEAR,
                self.tr("Start year (first band = January of this year)"),
                type=PROCESSING_NUMBER_INTEGER,
                defaultValue=2024,
                minValue=1958,
                maxValue=2100,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.SPLIT_MODE,
                self.tr("Split mode"),
                options=self.SPLIT_MODE_OPTIONS,
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ADD_TO_MAP,
                self.tr("Add output layers to map"),
                defaultValue=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_FOLDER,
                self.tr("Output folder"),
            )
        )
        self.addOutput(
            QgsProcessingOutputMultipleLayers(
                self.OUTPUT_LAYERS,
                self.tr("Output layers"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        raster_layer = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        output_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        prefix = self.parameterAsString(parameters, self.PREFIX, context)
        start_year = self.parameterAsInt(parameters, self.START_YEAR, context)
        split_mode = self.parameterAsEnum(parameters, self.SPLIT_MODE, context)
        add_to_map = self.parameterAsBool(parameters, self.ADD_TO_MAP, context)

        if raster_layer is None:
            raise QgsProcessingException(self.tr("Invalid input raster."))

        band_count = raster_layer.bandCount()
        if band_count < 2:
            raise QgsProcessingException(self.tr("Input raster has only 1 band - nothing to split."))

        is_multiple_of_12 = band_count % 12 == 0
        if split_mode == 1 and not is_multiple_of_12:
            raise QgsProcessingException(
                self.tr(
                    f"Yearly mode requires a band count that is a multiple of 12. "
                    f"This raster has {band_count} bands. Use Monthly mode instead."
                )
            )

        os.makedirs(output_folder, exist_ok=True)
        source_path = raster_layer.source()

        num_years = band_count // 12 if is_multiple_of_12 else 0
        end_year = start_year + num_years - 1 if num_years else start_year
        mode_label = self.SPLIT_MODE_OPTIONS[split_mode]

        feedback.pushInfo("=" * 60)
        feedback.pushInfo("Split Raster Bands")
        feedback.pushInfo("=" * 60)
        feedback.pushInfo(f"Input: {source_path}")
        feedback.pushInfo(f"Total bands: {band_count}")
        feedback.pushInfo(f"Split mode: {mode_label}")
        if is_multiple_of_12:
            feedback.pushInfo(f"Year span: {start_year} - {end_year} ({num_years} year(s))")
        else:
            feedback.pushInfo("Band count is not a multiple of 12 - using numeric labels.")
        feedback.pushInfo(f"Prefix: {prefix}")
        feedback.pushInfo(f"Output folder: {output_folder}")
        feedback.pushInfo("")

        output_paths = []

        if split_mode == 0:
            for band_num in range(1, band_count + 1):
                if feedback.isCanceled():
                    break

                if is_multiple_of_12:
                    month_index = (band_num - 1) % 12
                    year = start_year + (band_num - 1) // 12
                    month_name = self.MONTH_NAMES[month_index]
                    label = f"{band_num:02d}_{month_name}_{year}"
                else:
                    label = f"{band_num:02d}"

                out_filename = f"{prefix}_{label}.tif"
                out_path = os.path.join(output_folder, out_filename)
                feedback.pushInfo(f"  [{band_num}/{band_count}] -> {out_filename}")

                result = processing.run(
                    "gdal:translate",
                    {
                        "INPUT": source_path,
                        "TARGET_CRS": None,
                        "NODATA": None,
                        "COPY_SUBDATASETS": False,
                        "OPTIONS": "COMPRESS=LZW",
                        "EXTRA": f"-b {band_num}",
                        "DATA_TYPE": 0,
                        "OUTPUT": out_path,
                    },
                    context=context,
                    feedback=feedback,
                    is_child_algorithm=True,
                )

                output_paths.append(result["OUTPUT"])

                if add_to_map:
                    layer_name = f"{prefix}_{label}"
                    new_layer = QgsRasterLayer(result["OUTPUT"], layer_name)
                    if new_layer.isValid():
                        QgsProject.instance().addMapLayer(new_layer)

                feedback.setProgress(int((band_num / band_count) * 100))

        elif split_mode == 1:
            for year_idx in range(num_years):
                if feedback.isCanceled():
                    break

                year = start_year + year_idx
                first_band = year_idx * 12 + 1
                last_band = first_band + 11

                out_filename = f"{prefix}_{year}.tif"
                out_path = os.path.join(output_folder, out_filename)
                feedback.pushInfo(
                    f"  [{year_idx + 1}/{num_years}] -> {out_filename} "
                    f"(bands {first_band}-{last_band})"
                )

                band_flags = " ".join(f"-b {band}" for band in range(first_band, last_band + 1))

                result = processing.run(
                    "gdal:translate",
                    {
                        "INPUT": source_path,
                        "TARGET_CRS": None,
                        "NODATA": None,
                        "COPY_SUBDATASETS": False,
                        "OPTIONS": "COMPRESS=LZW",
                        "EXTRA": band_flags,
                        "DATA_TYPE": 0,
                        "OUTPUT": out_path,
                    },
                    context=context,
                    feedback=feedback,
                    is_child_algorithm=True,
                )

                output_paths.append(result["OUTPUT"])

                if add_to_map:
                    layer_name = f"{prefix}_{year}"
                    new_layer = QgsRasterLayer(result["OUTPUT"], layer_name)
                    if new_layer.isValid():
                        QgsProject.instance().addMapLayer(new_layer)
                        self._apply_singleband_pseudocolor(new_layer, feedback=feedback)

                feedback.setProgress(int(((year_idx + 1) / num_years) * 100))

        feedback.pushInfo("")
        feedback.pushInfo("=" * 60)
        feedback.pushInfo(f"COMPLETE - {len(output_paths)} file(s) exported.")
        feedback.pushInfo("=" * 60)

        return {self.OUTPUT_LAYERS: output_paths}
