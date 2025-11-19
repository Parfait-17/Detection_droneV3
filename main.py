#!/usr/bin/env python3
"""
Main - Système de Détection et Identification de Drones
Orchestration de tous les modules pour la détection en temps réel
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
from src.remote_id_decoder import WiFiRemoteIDDecoder
from src.data_fusion import DataFusion
from src.mqtt_publisher import MQTTPublisher

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('drone_detection.log')
    ]
)

logger = logging.getLogger(__name__)


class DroneDetectionSystem:
    """
    Système complet de détection et identification de drones
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialise le système

        Args:
            config_path: Chemin vers le fichier de configuration
        """
        logger.info("="*70)
        logger.info("Initialisation du Système de Détection de Drones")
        logger.info("="*70)

        # Chargement de la configuration
        self.config = self.load_config(config_path)
        self._configure_logging()

        # Initialisation des modules
        self.acquisition = None
        self.preprocessor = None
        self.analyzer = None
        self.remote_id_decoder = None
        self.fusion = None
        self.mqtt_publisher = None

        # État du système
        self.running = False
        self.detection_count = 0

        self._initialize_modules()

    def load_config(self, config_path: str) -> dict:
        """
        Charge la configuration depuis un fichier YAML

        Args:
            config_path: Chemin du fichier de configuration

        Returns:
            Dictionnaire de configuration
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration chargée: {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Fichier de configuration non trouvé: {config_path}")
            logger.info("Utilisation de la configuration par défaut")
            return self._default_config()

    def _default_config(self) -> dict:
        """
        Retourne une configuration par défaut

        Returns:
            Dictionnaire de configuration par défaut
        """
        return {
            'acquisition': {
                'device_args': 'type=b200',
                'sample_rate': 20e6,
                'rx_freq_2g4': 2.437e9,
                'rx_freq_5g8': 5.8e9,
                'rx_gain': 50.0,
                'num_samples': 200000
            },
            'preprocessing': {
                'enable_dc_removal': True,
                'enable_iq_correction': True,
                'bandpass_low': 1e6,
                'bandpass_high': 9e6,
                'normalize_method': 'rms',
                'filter_order': 6
            },
            'mqtt': {
                'broker_host': 'localhost',
                'broker_port': 1883,
                'client_id': 'drone_detector',
                'use_tls': False,
                'username': None,
                'password': None,
                'topics': {
                    'detection': 'drone/detection',
                    'position': 'drone/position',
                    'classification': 'drone/classification',
                    'alert': 'drone/alert',
                    'health': 'system/health'
                },
                'qos': {
                    'detection': 1,
                    'position': 1,
                    'alert': 2,
                    'health': 0
                },
                'retain': False
            },
            'system': {
                'heartbeat_interval': 60,
                'detection_threshold_snr': 15.0,
                'log_level': 'INFO',
                'log_file': 'drone_detection.log'
            },
            'data_fusion': {
                'restricted_zones': [],
                'threat_assessment': {
                    'altitude_agl_limit_m': 120,
                    'speed_limit_mps': 20,
                    'operator_distance_limit_m': 5000
                }
            }
        }

    def _configure_logging(self):
        lvl = str(self.config.get('system', {}).get('log_level', 'INFO')).upper()
        level = getattr(logging, lvl, logging.INFO)
        log_file = self.config.get('system', {}).get('log_file', 'drone_detection.log')
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)
        handlers = [logging.StreamHandler(), logging.FileHandler(log_file)]
        logging.basicConfig(level=level,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            handlers=handlers)
        logging.getLogger().setLevel(level)

    def _initialize_modules(self):
        """
        Initialise tous les modules du système
        """
        logger.info("\n--- Initialisation des modules ---")

        # Module 1: Acquisition RF
        logger.info("1. Initialisation de l'acquisition RF...")
        acq_config = self.config['acquisition']
        self.acquisition = UHDAcquisition(
            device_args=acq_config['device_args'],
            sample_rate=acq_config['sample_rate'],
            rx_freq_2g4=acq_config['rx_freq_2g4'],
            rx_freq_5g8=acq_config['rx_freq_5g8'],
            rx_gain=acq_config['rx_gain']
        )

        # Module 2: Prétraitement
        logger.info("2. Initialisation du prétraitement...")
        self.preprocessor = SignalPreprocessor(
            sample_rate=acq_config['sample_rate']
        )

        # Module 3: Analyse spectrale
        logger.info("3. Initialisation de l'analyse spectrale...")
        self.analyzer = SpectralAnalyzer(
            sample_rate=acq_config['sample_rate']
        )

        # Module 4B: Décodeur Remote ID
        logger.info("4. Initialisation du décodeur Remote ID...")
        self.remote_id_decoder = WiFiRemoteIDDecoder(
            sample_rate=acq_config['sample_rate']
        )

        # Module 5: Fusion de données
        logger.info("5. Initialisation de la fusion de données...")
        self.fusion = DataFusion(config=self.config)

        # Module 6: Publisher MQTT
        logger.info("6. Initialisation du publisher MQTT...")
        mqtt_config = self.config['mqtt']
        self.mqtt_publisher = MQTTPublisher(
            broker_host=mqtt_config['broker_host'],
            broker_port=mqtt_config['broker_port'],
            client_id=mqtt_config['client_id'],
            username=mqtt_config.get('username'),
            password=mqtt_config.get('password'),
            use_tls=mqtt_config.get('use_tls', False),
            topics=mqtt_config.get('topics'),
            qos=mqtt_config.get('qos'),
            retain=mqtt_config.get('retain', False)
        )

        logger.info("\n✓ Tous les modules initialisés avec succès")

    def start(self):
        """
        Démarre le système de détection
        """
        logger.info("\n" + "="*70)
        logger.info("DÉMARRAGE DU SYSTÈME DE DÉTECTION")
        logger.info("="*70 + "\n")

        # Connexion MQTT
        logger.info("Connexion au broker MQTT...")
        if not self.mqtt_publisher.connect():
            logger.error("Impossible de se connecter au broker MQTT")
            logger.warning("Le système continuera sans publication MQTT")

        # Initialisation USRP
        logger.info("Initialisation du périphérique USRP...")
        if not self.acquisition.initialize():
            logger.error("Impossible d'initialiser l'USRP")
            logger.error("Vérifiez que le LibreSDR B210mini est connecté")
            return

        # Configuration de l'arrêt propre
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Démarrage de la boucle de détection
        self.running = True
        logger.info("\n🚀 Système de détection actif - Appuyez sur Ctrl+C pour arrêter\n")

        self._detection_loop()

    def _detection_loop(self):
        """
        Boucle principale de détection
        """
        last_heartbeat = time.time()
        heartbeat_interval = self.config['system']['heartbeat_interval']
        detection_threshold = self.config['system']['detection_threshold_snr']

        acq_config = self.config['acquisition']
        preproc_config = self.config['preprocessing']

        while self.running:
            try:
                # Heartbeat
                if time.time() - last_heartbeat > heartbeat_interval:
                    self.mqtt_publisher.publish_heartbeat()
                    logger.info(f"📊 Statistiques: {self.detection_count} détections")
                    last_heartbeat = time.time()

                # Acquisition de données
                logger.debug("Acquisition d'échantillons RF...")
                samples = self.acquisition.acquire_samples(
                    num_samples=acq_config['num_samples'],
                    channel=0  # Canal 2.4 GHz
                )

                if samples is None:
                    logger.warning("Échec de l'acquisition, nouvelle tentative...")
                    time.sleep(0.1)
                    continue

                # Prétraitement
                logger.debug("Prétraitement du signal...")
                nyq = acq_config['sample_rate'] / 2.0
                bp_low = max(0.0, float(preproc_config['bandpass_low']))
                bp_high = min(float(preproc_config['bandpass_high']), nyq * 0.9)
                if bp_low >= bp_high:
                    bp_low = 0.1 * nyq
                    bp_high = 0.9 * nyq
                processed = self.preprocessor.process(
                    samples,
                    enable_dc_removal=preproc_config['enable_dc_removal'],
                    enable_iq_correction=preproc_config['enable_iq_correction'],
                    bandpass_range=(bp_low, bp_high),
                    normalize_method=preproc_config['normalize_method']
                )

                # Calcul du SNR
                snr = self.preprocessor.compute_snr(processed)

                # Vérification du seuil de détection
                if snr < detection_threshold:
                    logger.debug(f"SNR trop faible: {snr:.1f} dB < {detection_threshold} dB")
                    time.sleep(0.1)
                    continue

                logger.info(f"🎯 Signal détecté! SNR: {snr:.1f} dB")

                # Analyse spectrale
                logger.debug("Analyse spectrale...")
                features = self.analyzer.analyze_signal(processed, compute_spectrogram=False)
                features['snr'] = snr
                features['sample_rate'] = acq_config['sample_rate']

                # Décodage Remote ID
                logger.debug("Tentative de décodage Remote ID...")
                remote_id_data = None
                remote_id = self.remote_id_decoder.detect_and_decode_remote_id(processed)
                if remote_id:
                    remote_id_data = remote_id.to_dict()
                    logger.info(f"📡 Remote ID décodé: {remote_id.uas_id}")

                # Création d'une classification simple basée sur Remote ID
                classification = {
                    'brand': 'Unknown',
                    'model': 'Unknown',
                    'protocol': 'Unknown',
                    'confidence': 0.0,
                    'method': 'remote_id_only',
                    'is_valid': remote_id is not None
                }

                # Fusion des données
                logger.debug("Fusion des données...")
                fused_data = self.fusion.fuse_detection_data(
                    features,
                    classification,
                    remote_id_data,
                    center_freq=acq_config['rx_freq_2g4']
                )

                # Publication MQTT
                if self.mqtt_publisher.connected:
                    logger.debug("Publication MQTT...")
                    self.mqtt_publisher.publish_detection(fused_data)

                # Affichage du résumé
                self._display_detection_summary(fused_data)

                self.detection_count += 1

                # Petite pause pour éviter la saturation
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Erreur dans la boucle de détection: {e}", exc_info=True)
                time.sleep(1)

    def _display_detection_summary(self, detection_data: dict):
        """
        Affiche un résumé de la détection

        Args:
            detection_data: Données de détection fusionnées
        """
        logger.info("\n" + "="*70)
        logger.info("DÉTECTION #{}".format(self.detection_count + 1))
        logger.info("="*70)

        # Information de détection
        cls = detection_data['classification']
        if cls.get('brand') != 'Unknown' or cls.get('model') != 'Unknown':
            logger.info(f"Type: {cls['brand']} {cls.get('model', 'Unknown')}")
            logger.info(f"Protocole: {cls['protocol']}")
            logger.info(f"Confiance: {cls['confidence']:.1%}")
        else:
            logger.info(f"Type: Détection basée sur Remote ID uniquement")

        # Détection RF
        det = detection_data['detection']
        logger.info(f"Fréquence: {det['frequency_mhz']:.1f} MHz")
        logger.info(f"Bande passante: {det['bandwidth_mhz']:.1f} MHz")
        logger.info(f"SNR: {det['snr']:.1f} dB")
        logger.info(f"RSSI: {det['rssi_dbm']:.1f} dBm")

        # Remote ID
        if detection_data['metadata']['has_position']:
            pos = detection_data['remote_id']['position']
            logger.info(f"\n📍 Position: ({pos['latitude']:.6f}°, {pos['longitude']:.6f}°)")
            logger.info(f"   Altitude: {pos['altitude_agl']:.1f} m AGL")

            if detection_data['metadata']['has_operator_info']:
                op = detection_data['remote_id']['operator']
                logger.info(f"👤 Opérateur: {op.get('id', 'N/A')}")
                logger.info(f"   Distance: {op.get('distance_to_uas_m', 0):.0f} m")

        # Menace
        threat = detection_data['threat_assessment']
        logger.info(f"\n⚠️  Niveau de menace: {threat['level']}")
        logger.info(f"   Raisons: {', '.join(threat['reasons'])}")

        logger.info("="*70 + "\n")

    def _signal_handler(self, signum, frame):
        """
        Gère les signaux d'arrêt (Ctrl+C, etc.)
        """
        logger.info("\n\nSignal d'arrêt reçu...")
        self.stop()

    def stop(self):
        """
        Arrête proprement le système
        """
        logger.info("\n" + "="*70)
        logger.info("ARRÊT DU SYSTÈME")
        logger.info("="*70)

        self.running = False

        # Arrêt de l'acquisition
        if self.acquisition:
            logger.info("Fermeture de l'acquisition RF...")
            self.acquisition.close()

        # Déconnexion MQTT
        if self.mqtt_publisher and self.mqtt_publisher.connected:
            logger.info("Déconnexion MQTT...")
            self.mqtt_publisher.disconnect()

        logger.info(f"\n📊 Statistiques finales:")
        logger.info(f"   Détections totales: {self.detection_count}")

        logger.info("\n✓ Système arrêté proprement")
        logger.info("="*70 + "\n")


def main():
    """
    Point d'entrée principal
    """
    parser = argparse.ArgumentParser(
        description="Système de Détection et Identification de Drones"
    )
    parser.add_argument(
        '-c', '--config',
        default='config/config.yaml',
        help='Chemin vers le fichier de configuration (défaut: config/config.yaml)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Mode verbeux (debug)'
    )

    args = parser.parse_args()

    # Configuration du niveau de log
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Création et démarrage du système
    try:
        system = DroneDetectionSystem(config_path=args.config)
        system.start()
    except KeyboardInterrupt:
        logger.info("\nInterruption par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
