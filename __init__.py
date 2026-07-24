# -*- coding: utf-8 -*-
"""
TerraClimate Downloader - QGIS Plugin
Download and clip TerraClimate climate data via OPeNDAP

Version: 0.0.4
Author: Hemed Lungo
"""


def classFactory(iface):
    """Load the plugin class.
    
    Args:
        iface: A QGIS interface instance
        
    Returns:
        TerraClimateProviderPlugin instance
    """
    from .terraclimate_provider import TerraClimateProviderPlugin
    return TerraClimateProviderPlugin(iface)
