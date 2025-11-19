#!/usr/bin/env python3
"""
Exemple Complet: Détection Remote ID Hybride
Combine SDR (détection) + WiFi (capture) pour Remote ID optimal
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from src.uhd_acquisition import UHDAcquisition
from src.preprocessing import SignalPreprocessor
from src.spectrogram import SpectralAnalyzer
from src.wifi_detector import WiFiDetector
from src.wifi_capture import WiFiMonitorCapture
from src.remote_id_decoder import WiFiRemoteIDDecoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridRemoteIDDetector:
    """
    Détecteur Remote ID hybride SDR + WiFi
    """

    def __init__(self):
        """
        Initialise le système hybride
        """
        logger.info("="*70)
        logger.info("Détecteur Remote ID Hybride")
        logger.info("="*70)

        # SDR pour détection
        self.sdr = UHDAcquisition(
            sample_rate=25e6,
            rx_freq_2g4=2.437e9,
            rx_gain=40.0
        )

        # Modules de traitement
        self.preprocessor = SignalPreprocessor(sample_rate=25e6)
        self.analyzer = SpectralAnalyzer(sample_rate=25e6)
        self.wifi_detector = WiFiDetector()

        # WiFi capture
        self.wifi_capture = WiFiMonitorCapture(interface="wlan1")

        # Remote ID decoder
        self.remote_id_decoder = WiFiRemoteIDDecoder()

        self.detection_count = 0

    def run(self, duration: int = 60):
        """
        Lance la détection pendant une durée donnée

        Args:
            duration: Durée en secondes
        """
        logger.info(f"\nDémarrage de la détection pour {duration}s...")

        # 1. Initialiser SDR
        if not self.sdr.initialize():
            logger.error("Impossible d'initialiser le SDR")
            return

        # 2. Activer mode monitor WiFi
        logger.info("\nActivation du mode monitor WiFi...")
        if not self.wifi_capture.enable_monitor_mode():
            logger.warning("Mode monitor non disponible - détection WiFi désactivée")
            wifi_available = False
        else:
            wifi_available = True

        # 3. Boucle de détection
        start_time = time.time()
        snr_threshold = 10.0

        try:
            while (time.time() - start_time) < duration:
                # ÉTAPE 1: Acquisition SDR
                logger.debug("\n--- Acquisition SDR ---")
                samples = self.sdr.acquire_samples(num_samples=100000, channel=0)

                if samples is None:
                    time.sleep(0.1)
                    continue

                # ÉTAPE 2: Prétraitement
                logger.debug("Prétraitement...")
                processed = self.preprocessor.process(
                    samples,
                    enable_dc_removal=True,
                    enable_iq_correction=True,
                    bandpass_range=(4e6, 20e6),
                    normalize_method='rms'
                )

                # ÉTAPE 3: Calcul SNR
                snr = self.preprocessor.compute_snr(processed)

                if snr < snr_threshold:
                    logger.debug(f"SNR trop faible: {snr:.1f} dB")
                    time.sleep(0.1)
                    continue

                logger.info(f"\n🎯 Signal détecté! SNR: {snr:.1f} dB")

                # ÉTAPE 4: Analyse spectrale
                logger.debug("Analyse spectrale...")
                features = self.analyzer.analyze_signal(processed, compute_spectrogram=False)
                features['snr'] = snr
                features['sample_rate'] = 25e6

                # ÉTAPE 5: Détection WiFi
                logger.debug("Vérification si signal WiFi...")
                is_wifi, wifi_confidence, wifi_channel = self.wifi_detector.is_wifi_signal(
                    features,
                    center_freq=2.437e9
                )

                if not is_wifi:
                    logger.info(f"Signal non-WiFi (confiance WiFi: {wifi_confidence:.1%})")
                    time.sleep(0.1)
                    continue

                logger.info(f"✅ Signal WiFi détecté! Canal: {wifi_channel}, Confiance: {wifi_confidence:.1%}")

                # ÉTAPE 6: Capture WiFi si disponible
                if wifi_available:
                    logger.info("📡 Capture des trames WiFi...")

                    # Changer de canal si nécessaire
                    if wifi_channel:
                        logger.info(f"Passage au canal {wifi_channel}")
                        # TODO: Changer le canal de l'adaptateur WiFi

                    # Capturer des trames
                    frames = self.wifi_capture.capture_with_scapy(count=20)

                    if not frames:
                        logger.warning("Aucune trame capturée")
                        continue

                    logger.info(f"✅ {len(frames)} trames Beacon capturées")

                    # ÉTAPE 7: Parser pour Remote ID
                    logger.info("🔍 Recherche de Remote ID...")
                    remote_id_found = False

                    for i, frame in enumerate(frames, 1):
                        try:
                            # Parser la trame
                            beacon_info = self.remote_id_decoder.parse_beacon_frame(
                                frame.frame_data
                            )

                            if beacon_info:
                                # Extraire Remote ID
                                remote_id = self.remote_id_decoder.extract_remote_id(
                                    beacon_info
                                )

                                if remote_id and remote_id.uas_id:
                                    self._display_remote_id(remote_id, frame)
                                    remote_id_found = True
                                    self.detection_count += 1
                                    break

                        except Exception as e:
                            logger.debug(f"Erreur parsing frame {i}: {e}")
                            continue

                    if not remote_id_found:
                        logger.warning("Aucun Remote ID trouvé dans les trames")

                else:
                    logger.warning("Mode WiFi non disponible - utiliser capture SDR (limitée)")

                # Pause avant prochaine détection
                time.sleep(0.5)

        except KeyboardInterrupt:
            logger.info("\nInterruption par l'utilisateur")

        finally:
            # Nettoyage
            logger.info("\nNettoyage...")
            self.sdr.close()
            if wifi_available:
                self.wifi_capture.disable_monitor_mode()

            logger.info(f"\n📊 Statistiques:")
            logger.info(f"   Remote IDs détectés: {self.detection_count}")

    def _display_remote_id(self, remote_id, frame):
        """
        Affiche les informations Remote ID

        Args:
            remote_id: Objet RemoteIDData
            frame: WiFiFrame source
        """
        logger.info("\n" + "="*70)
        logger.info("🎯 REMOTE ID DÉTECTÉ")
        logger.info("="*70)

        logger.info(f"\n📡 Informations Radio:")
        logger.info(f"   Source MAC: {frame.src_mac}")
        logger.info(f"   Signal: {frame.signal_strength} dBm")
        logger.info(f"   Fréquence: {frame.frequency/1e6:.0f} MHz")

        logger.info(f"\n🆔 Identifiant:")
        logger.info(f"   UAS ID: {remote_id.uas_id}")
        logger.info(f"   Type: {remote_id.uas_id_type}")

        if remote_id.latitude and remote_id.longitude:
            logger.info(f"\n📍 Position Drone:")
            logger.info(f"   Latitude: {remote_id.latitude:.6f}°")
            logger.info(f"   Longitude: {remote_id.longitude:.6f}°")
            logger.info(f"   Altitude MSL: {remote_id.altitude_msl:.1f} m")
            logger.info(f"   Hauteur AGL: {remote_id.height:.1f} m")

        if remote_id.speed is not None:
            logger.info(f"\n🚁 Vélocité:")
            logger.info(f"   Vitesse: {remote_id.speed:.1f} m/s ({remote_id.speed*3.6:.1f} km/h)")
            logger.info(f"   Direction: {remote_id.direction}°")
            logger.info(f"   Vitesse verticale: {remote_id.vertical_speed:.1f} m/s")

        if remote_id.operator_latitude and remote_id.operator_longitude:
            logger.info(f"\n👤 Opérateur:")
            logger.info(f"   Position: ({remote_id.operator_latitude:.6f}°, {remote_id.operator_longitude:.6f}°)")
            if remote_id.operator_id:
                logger.info(f"   ID: {remote_id.operator_id}")

        logger.info(f"\n📊 Statut: {remote_id.status}")
        logger.info("="*70 + "\n")


def main():
    """
    Point d'entrée
    """
    logger.info("\n" + "="*70)
    logger.info("EXEMPLE: Détection Remote ID Hybride SDR + WiFi")
    logger.info("="*70)

    logger.info("\n⚠️  Prérequis:")
    logger.info("   1. LibreSDR B210mini connecté")
    logger.info("   2. Adaptateur WiFi en mode monitor")
    logger.info("   3. Scapy installé: pip install scapy")
    logger.info("   4. Droits sudo pour mode monitor")

    input("\nAppuyez sur Entrée pour continuer (Ctrl+C pour annuler)...")

    detector = HybridRemoteIDDetector()
    detector.run(duration=60)


if __name__ == "__main__":
    main()
