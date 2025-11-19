#!/usr/bin/env python3
"""
Main SDR WiFi - Détection Remote ID via Démodulation SDR (OPTION 2)
Utilise USRP B210 pour démoduler directement les signaux WiFi
"""

import logging
import argparse
import yaml
import time
import signal
import sys
from pathlib import Path

from src.uhd_acquisition import UHDAcquisition
from src.preprocessing import SignalPreprocessor
from src.spectrogram import SpectralAnalyzer
from src.wifi_detector import WiFiDetector
from src.wifi_sdr_demodulator import WiFiSDRDemodulator
from src.remote_id_decoder import WiFiRemoteIDDecoder
from src.data_fusion import DataFusion
from src.mqtt_publisher import MQTTPublisher

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('drone_detection_sdr.log')
    ]
)

logger = logging.getLogger(__name__)


class SDRWiFiRemoteIDSystem:
    """
    Système de détection Remote ID via SDR WiFi
    Approche: SDR → Démodulation WiFi → Remote ID
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialise le système

        Args:
            config_path: Chemin vers le fichier de configuration
        """
        logger.info("="*70)
        logger.info("Système de Détection Remote ID - SDR WiFi Démodulation")
        logger.info("USRP B210 → WiFi OFDM → Remote ID")
        logger.info("="*70)

        # Chargement configuration
        self.config = self._load_config(config_path)

        # Initialisation modules
        self.acquisition = None
        self.preprocessor = None
        self.analyzer = None
        self.wifi_detector = None
        self.wifi_demodulator = None
        self.remote_id_decoder = None
        self.fusion = None
        self.mqtt_publisher = None

        self.running = False
        self.detection_count = 0

        self._initialize_modules()

    def _load_config(self, config_path: str) -> dict:
        """Charge la configuration"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except:
            logger.warning("Config non trouvée, utilisation par défaut")
            return {
                'acquisition': {
                    'sample_rate': 20e6,  # 20 MS/s pour WiFi 20 MHz
                    'rx_freq_2g4': 2.437e9,
                    'rx_gain': 50.0,
                    'num_samples': 200000  # Plus d'échantillons pour WiFi
                },
                'mqtt': {'broker_host': 'localhost', 'broker_port': 1883},
                'system': {'heartbeat_interval': 60, 'detection_threshold_snr': 15.0}
            }

    def _initialize_modules(self):
        """Initialise tous les modules"""
        logger.info("\n--- Initialisation des modules ---")

        acq_config = self.config['acquisition']

        # Module 1: Acquisition USRP B210
        logger.info("1. Initialisation USRP B210...")
        self.acquisition = UHDAcquisition(
            device_args="type=b200",
            sample_rate=acq_config['sample_rate'],
            rx_freq_2g4=acq_config['rx_freq_2g4'],
            rx_gain=acq_config['rx_gain']
        )

        # Module 2: Prétraitement
        logger.info("2. Initialisation prétraitement...")
        self.preprocessor = SignalPreprocessor(
            sample_rate=acq_config['sample_rate']
        )

        # Module 3: Analyse spectrale
        logger.info("3. Initialisation analyse spectrale...")
        self.analyzer = SpectralAnalyzer(
            sample_rate=acq_config['sample_rate']
        )

        # Module 4a: Détecteur WiFi
        logger.info("4a. Initialisation détecteur WiFi...")
        self.wifi_detector = WiFiDetector()

        # Module 4b: Démodulateur WiFi SDR
        logger.info("4b. Initialisation démodulateur WiFi SDR...")
        self.wifi_demodulator = WiFiSDRDemodulator(
            sample_rate=acq_config['sample_rate']
        )

        # Module 4c: Décodeur Remote ID
        logger.info("4c. Initialisation décodeur Remote ID...")
        self.remote_id_decoder = WiFiRemoteIDDecoder()

        # Module 5: Fusion
        logger.info("5. Initialisation fusion de données...")
        self.fusion = DataFusion()

        # Module 6: MQTT
        logger.info("6. Initialisation MQTT...")
        mqtt_config = self.config.get('mqtt', {})
        self.mqtt_publisher = MQTTPublisher(
            broker_host=mqtt_config.get('broker_host', 'localhost'),
            broker_port=mqtt_config.get('broker_port', 1883),
            client_id='drone_detector_sdr'
        )

        logger.info("\n✓ Tous les modules initialisés")

    def start(self):
        """Démarre le système"""
        logger.info("\n" + "="*70)
        logger.info("DÉMARRAGE DU SYSTÈME SDR WiFi")
        logger.info("="*70 + "\n")

        # Connexion MQTT
        logger.info("Connexion MQTT...")
        if not self.mqtt_publisher.connect():
            logger.warning("MQTT non connecté - Mode autonome")

        # Initialisation USRP
        logger.info("Initialisation USRP B210...")
        if not self.acquisition.initialize():
            logger.error("❌ Impossible d'initialiser l'USRP B210")
            logger.error("Vérifiez la connexion USB 3.0")
            return

        # Handlers d'arrêt
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Lancement
        self.running = True
        logger.info("\n🚀 Système actif - Appuyez sur Ctrl+C pour arrêter\n")

        self._detection_loop()

    def _detection_loop(self):
        """Boucle principale de détection"""
        last_heartbeat = time.time()
        heartbeat_interval = self.config['system']['heartbeat_interval']
        snr_threshold = self.config['system']['detection_threshold_snr']

        acq_config = self.config['acquisition']

        while self.running:
            try:
                # Heartbeat
                if time.time() - last_heartbeat > heartbeat_interval:
                    self.mqtt_publisher.publish_heartbeat()
                    logger.info(f"📊 Remote IDs détectés: {self.detection_count}")
                    last_heartbeat = time.time()

                # ═══════════════════════════════════════════════════════
                # ÉTAPE 1: ACQUISITION SDR
                # ═══════════════════════════════════════════════════════
                logger.debug("\n--- Acquisition USRP B210 ---")
                samples = self.acquisition.acquire_samples(
                    num_samples=acq_config['num_samples'],
                    channel=0  # RX1: 2.4 GHz
                )

                if samples is None:
                    logger.warning("Échec acquisition")
                    time.sleep(0.1)
                    continue

                # ═══════════════════════════════════════════════════════
                # ÉTAPE 2: PRÉTRAITEMENT
                # ═══════════════════════════════════════════════════════
                logger.debug("Prétraitement...")
                processed = self.preprocessor.process(
                    samples,
                    enable_dc_removal=True,
                    enable_iq_correction=True,
                    bandpass_range=(1e6, 9e6),  # Bande WiFi 2.4 GHz (< Nyquist 10 MHz)
                    normalize_method='rms'
                )

                # ═══════════════════════════════════════════════════════
                # ÉTAPE 3: VÉRIFICATION SNR
                # ═══════════════════════════════════════════════════════
                snr = self.preprocessor.compute_snr(processed)

                if snr < snr_threshold:
                    logger.debug(f"SNR trop faible: {snr:.1f} dB")
                    time.sleep(0.1)
                    continue

                logger.info(f"\n🎯 Signal détecté! SNR: {snr:.1f} dB")

                # ═══════════════════════════════════════════════════════
                # ÉTAPE 4: ANALYSE SPECTRALE
                # ═══════════════════════════════════════════════════════
                logger.debug("Analyse spectrale...")
                features = self.analyzer.analyze_signal(
                    processed,
                    compute_spectrogram=False
                )
                features['snr'] = snr
                features['sample_rate'] = acq_config['sample_rate']

                # ═══════════════════════════════════════════════════════
                # ÉTAPE 5: DÉTECTION WiFi
                # ═══════════════════════════════════════════════════════
                logger.debug("Vérification si signal WiFi...")
                is_wifi, wifi_conf, wifi_channel = self.wifi_detector.is_wifi_signal(
                    features,
                    acq_config['rx_freq_2g4']
                )

                if not is_wifi:
                    logger.info(f"❌ Signal non-WiFi (conf: {wifi_conf:.1%})")
                    time.sleep(0.1)
                    continue

                logger.info(f"✅ Signal WiFi détecté! (Canal: {wifi_channel}, Conf: {wifi_conf:.1%})")

                # Vérifier présence de Beacon frames
                has_beacons = self.wifi_detector.detect_beacon_frames(features)

                if not has_beacons:
                    logger.info("⚠️  Pas de Beacon frames détectés")
                    time.sleep(0.1)
                    continue

                logger.info("✅ Beacon frames détectés!")

                # ═══════════════════════════════════════════════════════
                # ÉTAPE 6: DÉMODULATION WiFi OFDM
                # ═══════════════════════════════════════════════════════
                logger.info("🔧 Démodulation WiFi OFDM...")
                wifi_packet = self.wifi_demodulator.demodulate_wifi_packet(processed)

                if wifi_packet is None:
                    logger.warning("❌ Échec démodulation WiFi")
                    time.sleep(0.5)
                    continue

                logger.info(f"✅ Paquet WiFi démodulé: {len(wifi_packet)} octets")

                # ═══════════════════════════════════════════════════════
                # ÉTAPE 7: PARSING BEACON & REMOTE ID
                # ═══════════════════════════════════════════════════════
                logger.info("🔍 Recherche Remote ID dans la trame...")

                # Parser la trame Beacon
                beacon_info = self.remote_id_decoder.parse_beacon_frame(wifi_packet)

                if beacon_info is None:
                    logger.warning("❌ Trame Beacon invalide")
                    time.sleep(0.5)
                    continue

                logger.info("✅ Trame Beacon parsée")

                # Extraire Remote ID
                remote_id = self.remote_id_decoder.extract_remote_id(beacon_info)

                remote_id_data = None
                if remote_id and remote_id.uas_id:
                    logger.info(f"🎉 REMOTE ID DÉTECTÉ: {remote_id.uas_id}")
                    remote_id_data = remote_id.to_dict()
                    self._display_remote_id(remote_id, snr, wifi_channel)
                    self.detection_count += 1
                else:
                    logger.info("⚠️  Pas de Remote ID dans cette trame")

                # ═══════════════════════════════════════════════════════
                # ÉTAPE 8: FUSION & PUBLICATION
                # ═══════════════════════════════════════════════════════
                if remote_id_data:
                    classification = {
                        'brand': 'WiFi Remote ID',
                        'model': 'Unknown',
                        'protocol': f'WiFi 802.11 CH{wifi_channel}',
                        'confidence': wifi_conf,
                        'method': 'sdr_wifi_demod',
                        'is_valid': True
                    }

                    fused_data = self.fusion.fuse_detection_data(
                        features,
                        classification,
                        remote_id_data,
                        center_freq=acq_config['rx_freq_2g4']
                    )

                    # Publication MQTT
                    if self.mqtt_publisher.connected:
                        self.mqtt_publisher.publish_detection(fused_data)

                # Pause
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Erreur dans la boucle: {e}", exc_info=True)
                time.sleep(1)

    def _display_remote_id(self, remote_id, snr: float, wifi_channel: int):
        """Affiche les informations Remote ID"""
        logger.info("\n" + "="*70)
        logger.info("🎯 REMOTE ID DÉTECTÉ VIA SDR WiFi")
        logger.info("="*70)

        logger.info(f"\n📡 Informations Radio:")
        logger.info(f"   Canal WiFi: {wifi_channel}")
        logger.info(f"   SNR: {snr:.1f} dB")
        logger.info(f"   Méthode: Démodulation OFDM via USRP B210")

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

        if remote_id.operator_latitude and remote_id.operator_longitude:
            logger.info(f"\n👤 Opérateur:")
            logger.info(f"   Position: ({remote_id.operator_latitude:.6f}°, "
                       f"{remote_id.operator_longitude:.6f}°)")

        logger.info(f"\n📊 Statut: {remote_id.status}")
        logger.info("="*70 + "\n")

    def _signal_handler(self, signum, frame):
        """Gère Ctrl+C"""
        logger.info("\nSignal d'arrêt reçu...")
        self.stop()

    def stop(self):
        """Arrête le système"""
        logger.info("\n" + "="*70)
        logger.info("ARRÊT DU SYSTÈME")
        logger.info("="*70)

        self.running = False

        if self.acquisition:
            logger.info("Fermeture USRP...")
            self.acquisition.close()

        if self.mqtt_publisher and self.mqtt_publisher.connected:
            logger.info("Déconnexion MQTT...")
            self.mqtt_publisher.disconnect()

        logger.info(f"\n📊 Statistiques:")
        logger.info(f"   Remote IDs détectés: {self.detection_count}")

        logger.info("\n✓ Système arrêté")
        logger.info("="*70 + "\n")


def main():
    """Point d'entrée"""
    parser = argparse.ArgumentParser(
        description="Détection Remote ID via SDR WiFi - USRP B210"
    )
    parser.add_argument(
        '-c', '--config',
        default='config/config.yaml',
        help='Fichier de configuration'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Mode verbeux (debug)'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Lancement
    try:
        system = SDRWiFiRemoteIDSystem(config_path=args.config)
        system.start()
    except KeyboardInterrupt:
        logger.info("\nInterruption utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
