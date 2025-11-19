"""
Détecteur WiFi pour Remote ID
Utilise les caractéristiques spectrales pour détecter les signaux WiFi
"""

import numpy as np
from typing import Optional, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WiFiDetector:
    """
    Détecteur de signaux WiFi basé sur l'analyse spectrale
    """

    # Caractéristiques WiFi 2.4 GHz
    WIFI_2G4_CHANNELS = {
        1: 2.412e9,
        2: 2.417e9,
        3: 2.422e9,
        4: 2.427e9,
        5: 2.432e9,
        6: 2.437e9,  # Canal le plus courant
        7: 2.442e9,
        8: 2.447e9,
        9: 2.452e9,
        10: 2.457e9,
        11: 2.462e9,
    }

    # Caractéristiques WiFi 802.11
    WIFI_BANDWIDTH_20MHZ = 20e6
    WIFI_BANDWIDTH_40MHZ = 40e6

    def __init__(self):
        """
        Initialise le détecteur WiFi
        """
        logger.info("Détecteur WiFi initialisé")

    def is_wifi_signal(self, features: Dict, center_freq: float) -> tuple:
        """
        Détermine si un signal est WiFi basé sur ses caractéristiques

        Args:
            features: Features spectrales du signal
            center_freq: Fréquence centrale

        Returns:
            Tuple (is_wifi: bool, confidence: float, wifi_channel: Optional[int])
        """
        confidence = 0.0
        wifi_channel = None

        # 1. Vérification de la fréquence (canal WiFi)
        channel, freq_confidence = self._check_wifi_frequency(center_freq)
        if channel:
            confidence += freq_confidence * 0.4
            wifi_channel = channel

        # 2. Vérification de la bande passante
        bandwidth = features.get('spectral_features', {}).get('bandwidth', 0)
        bw_confidence = self._check_wifi_bandwidth(bandwidth)
        confidence += bw_confidence * 0.3

        # 3. Vérification de la structure OFDM
        ofdm_confidence = self._check_ofdm_structure(features)
        confidence += ofdm_confidence * 0.3

        is_wifi = confidence >= 0.6

        if is_wifi:
            logger.info(f"Signal WiFi détecté (confiance: {confidence:.2%}, canal: {wifi_channel})")
        else:
            logger.debug(f"Signal non-WiFi (confiance WiFi: {confidence:.2%})")

        return is_wifi, confidence, wifi_channel

    def _check_wifi_frequency(self, freq: float) -> tuple:
        """
        Vérifie si la fréquence correspond à un canal WiFi

        Args:
            freq: Fréquence en Hz

        Returns:
            Tuple (channel, confidence)
        """
        tolerance = 5e6  # ±5 MHz

        for channel, channel_freq in self.WIFI_2G4_CHANNELS.items():
            if abs(freq - channel_freq) < tolerance:
                # Plus on est proche, plus la confiance est élevée
                distance = abs(freq - channel_freq)
                confidence = 1.0 - (distance / tolerance)
                return channel, confidence

        return None, 0.0

    def _check_wifi_bandwidth(self, bandwidth: float) -> float:
        """
        Vérifie si la bande passante correspond à WiFi

        Args:
            bandwidth: Bande passante en Hz

        Returns:
            Confiance (0-1)
        """
        # WiFi 20 MHz (802.11n/ac)
        if 18e6 <= bandwidth <= 22e6:
            return 1.0

        # WiFi 40 MHz (802.11n/ac)
        if 38e6 <= bandwidth <= 42e6:
            return 1.0

        # WiFi 802.11b/g (11 Mbps, ~22 MHz)
        if 10e6 <= bandwidth <= 25e6:
            return 0.7

        return 0.0

    def _check_ofdm_structure(self, features: Dict) -> float:
        """
        Vérifie la structure OFDM typique du WiFi

        Args:
            features: Features du signal

        Returns:
            Confiance (0-1)
        """
        spectral = features.get('spectral_features', {})

        # WiFi OFDM a une structure plate caractéristique
        flatness = spectral.get('spectral_flatness', 0)

        # OFDM WiFi: flatness entre 0.3 et 0.7
        if 0.3 <= flatness <= 0.7:
            return 1.0
        elif 0.2 <= flatness <= 0.8:
            return 0.5

        return 0.0

    def detect_beacon_frames(self, features: Dict) -> bool:
        """
        Détecte les caractéristiques de trames Beacon WiFi

        Args:
            features: Features du signal

        Returns:
            True si des Beacons sont probablement présents
        """
        # Les Beacon frames sont envoyées périodiquement (~100ms)
        bursts = features.get('bursts', {})
        burst_list = bursts.get('bursts_list', [])

        if len(burst_list) < 2:
            return False

        # Calcul de la période entre bursts
        sample_rate = features.get('sample_rate', 25e6)
        intervals = []

        for i in range(1, len(burst_list)):
            prev_end = burst_list[i-1][1]
            curr_start = burst_list[i][0]
            interval = (curr_start - prev_end) / sample_rate
            intervals.append(interval)

        if not intervals:
            return False

        avg_interval = np.mean(intervals)

        # Beacon interval typique: 100ms (TU = 102.4ms)
        # Remote ID: peut être 100ms, 200ms, etc.
        beacon_intervals = [0.1, 0.102, 0.2, 0.204]

        for expected in beacon_intervals:
            if abs(avg_interval - expected) < 0.02:  # ±20ms
                logger.info(f"Beacon frames détectés (période: {avg_interval*1000:.1f}ms)")
                return True

        return False


def test_wifi_detector():
    """
    Test du détecteur WiFi
    """
    logger.info("=== Test du détecteur WiFi ===")

    detector = WiFiDetector()

    # Test 1: Signal WiFi typique (canal 6, 2.437 GHz)
    logger.info("\n--- Test 1: Signal WiFi canal 6 ---")

    features_wifi = {
        'spectral_features': {
            'bandwidth': 20e6,
            'spectral_flatness': 0.5
        },
        'bursts': {
            'bursts_list': [
                (0, 1000, 0.0001, 0.5),
                (2550000, 2551000, 0.0001, 0.5),  # ~102ms après
                (5100000, 5101000, 0.0001, 0.5)   # ~204ms depuis début
            ]
        },
        'sample_rate': 25e6
    }

    is_wifi, confidence, channel = detector.is_wifi_signal(features_wifi, 2.437e9)

    logger.info(f"Résultat: WiFi={is_wifi}, Confiance={confidence:.2%}, Canal={channel}")

    beacon_detected = detector.detect_beacon_frames(features_wifi)
    logger.info(f"Beacon frames détectés: {beacon_detected}")

    # Test 2: Signal non-WiFi (OcuSync DJI)
    logger.info("\n--- Test 2: Signal OcuSync (non-WiFi) ---")

    features_ocusync = {
        'spectral_features': {
            'bandwidth': 15e6,
            'spectral_flatness': 0.2
        },
        'bursts': {
            'bursts_list': [
                (0, 10000, 0.0004, 0.5),
                (16000000, 16010000, 0.0004, 0.5)  # 640ms
            ]
        },
        'sample_rate': 25e6
    }

    is_wifi2, confidence2, channel2 = detector.is_wifi_signal(features_ocusync, 2.445e9)

    logger.info(f"Résultat: WiFi={is_wifi2}, Confiance={confidence2:.2%}, Canal={channel2}")

    logger.info("\nTest terminé")


if __name__ == "__main__":
    test_wifi_detector()
