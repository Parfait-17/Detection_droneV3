"""
Système de Détection et Identification de Drones
Package principal
"""

__version__ = "1.0.0"
__author__ = "Drone Detection System"

from .uhd_acquisition import UHDAcquisition
from .preprocessing import SignalPreprocessor
from .spectrogram import SpectralAnalyzer
from .remote_id_decoder import WiFiRemoteIDDecoder, RemoteIDData
from .data_fusion import DataFusion
from .mqtt_publisher import MQTTPublisher

__all__ = [
    'UHDAcquisition',
    'SignalPreprocessor',
    'SpectralAnalyzer',
    'WiFiRemoteIDDecoder',
    'RemoteIDData',
    'DataFusion',
    'MQTTPublisher'
]
