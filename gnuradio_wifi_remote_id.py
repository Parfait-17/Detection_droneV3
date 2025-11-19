#!/usr/bin/env python3
"""
GNU Radio WiFi Remote ID Decoder
Utilise gr-ieee802-11 pour démodulation WiFi robuste

Installation requise:
    sudo apt-get install gnuradio
    # Puis installer gr-ieee802-11 (voir OPTION2B_GNU_RADIO.md)
"""

import logging
import time
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Vérifie que GNU Radio et gr-ieee802-11 sont installés"""
    missing = []

    try:
        from gnuradio import gr
        logger.info("✓ GNU Radio installé")
    except ImportError:
        missing.append("gnuradio")
        logger.error("✗ GNU Radio non installé")

    try:
        from gnuradio import uhd
        logger.info("✓ UHD (USRP) installé")
    except ImportError:
        missing.append("gnuradio-uhd")
        logger.error("✗ UHD non installé")

    try:
        import ieee802_11
        logger.info("✓ gr-ieee802-11 installé")
    except ImportError:
        missing.append("gr-ieee802-11")
        logger.error("✗ gr-ieee802-11 non installé")

    if missing:
        logger.error(f"\nDépendances manquantes: {', '.join(missing)}")
        logger.info("\nInstallation:")
        logger.info("  sudo apt-get install gnuradio gnuradio-dev")
        logger.info("  # Puis installer gr-ieee802-11 (voir OPTION2B_GNU_RADIO.md)")
        return False

    return True


class WiFiRemoteIDReceiver:
    """
    Récepteur WiFi Remote ID utilisant GNU Radio
    """

    def __init__(self, freq=2.437e9, gain=50, sample_rate=20e6):
        """
        Initialise le récepteur

        Args:
            freq: Fréquence centrale (Hz)
            gain: Gain USRP (dB)
            sample_rate: Taux d'échantillonnage (Hz)
        """
        from gnuradio import gr, blocks, uhd
        try:
            import ieee802_11
        except ImportError:
            raise ImportError("gr-ieee802-11 non installé. Voir OPTION2B_GNU_RADIO.md")

        from src.remote_id_decoder import WiFiRemoteIDDecoder
        from src.mqtt_publisher import MQTTPublisher

        logger.info("="*70)
        logger.info("GNU Radio WiFi Remote ID Receiver")
        logger.info("="*70)

        self.freq = freq
        self.gain = gain
        self.sample_rate = sample_rate

        # Décodeur Remote ID
        self.decoder = WiFiRemoteIDDecoder()

        # MQTT Publisher
        self.mqtt_publisher = MQTTPublisher(
            broker_host='localhost',
            broker_port=1883,
            client_id='gnuradio_remote_id'
        )

        self.detection_count = 0

        logger.info(f"\nConfiguration:")
        logger.info(f"  Fréquence: {freq/1e9:.3f} GHz")
        logger.info(f"  Gain: {gain} dB")
        logger.info(f"  Sample rate: {sample_rate/1e6:.1f} MS/s")

    def packet_callback(self, packet_bytes):
        """
        Callback appelé pour chaque paquet WiFi décodé

        Args:
            packet_bytes: Paquet WiFi (bytes)
        """
        logger.debug(f"Paquet WiFi reçu: {len(packet_bytes)} octets")

        # Parser trame Beacon
        beacon_info = self.decoder.parse_beacon_frame(packet_bytes)

        if beacon_info is None:
            logger.debug("Pas une trame Beacon")
            return

        logger.info("✓ Trame Beacon détectée")

        # Extraire Remote ID
        remote_id = self.decoder.extract_remote_id(beacon_info)

        if remote_id and remote_id.uas_id:
            self.detection_count += 1

            logger.info("\n" + "="*70)
            logger.info("🎉 REMOTE ID DÉTECTÉ via GNU Radio")
            logger.info("="*70)
            logger.info(f"\n🆔 UAS ID: {remote_id.uas_id}")
            logger.info(f"   Type: {remote_id.uas_id_type}")

            if remote_id.latitude and remote_id.longitude:
                logger.info(f"\n📍 Position:")
                logger.info(f"   Lat/Lon: ({remote_id.latitude:.6f}°, {remote_id.longitude:.6f}°)")
                logger.info(f"   Altitude MSL: {remote_id.altitude_msl:.1f} m")
                logger.info(f"   Hauteur AGL: {remote_id.height:.1f} m")

            if remote_id.speed is not None:
                logger.info(f"\n🚁 Mouvement:")
                logger.info(f"   Vitesse: {remote_id.speed:.1f} m/s ({remote_id.speed*3.6:.1f} km/h)")
                logger.info(f"   Direction: {remote_id.direction}°")

            logger.info(f"\n📊 Détections totales: {self.detection_count}")
            logger.info("="*70 + "\n")

            # Publier MQTT
            if self.mqtt_publisher.connected:
                detection_data = {
                    'remote_id': remote_id.to_dict(),
                    'timestamp': time.time(),
                    'method': 'gnuradio_gr_ieee802_11',
                    'frequency_hz': self.freq,
                    'gain_db': self.gain
                }
                self.mqtt_publisher.publish_detection(detection_data)

    def start(self):
        """Démarre la réception"""
        logger.error("\n❌ Implémentation GNU Radio nécessaire")
        logger.info("\nPour une implémentation complète avec gr-ieee802-11:")
        logger.info("1. Installer gr-ieee802-11 (voir OPTION2B_GNU_RADIO.md)")
        logger.info("2. Créer un flowgraph GNU Radio Companion (.grc)")
        logger.info("3. Connecter à ce script Python via message passing")
        logger.info("\nAlternativement:")
        logger.info("- Utilisez main_sdr_wifi.py (OPTION 2 - Python pur)")
        logger.info("- Ou attendez implémentation OPTION 2B complète")

        return False


def main():
    """Point d'entrée"""
    parser = argparse.ArgumentParser(
        description="GNU Radio WiFi Remote ID Receiver"
    )
    parser.add_argument(
        '-f', '--freq',
        type=float,
        default=2.437e9,
        help='Fréquence centrale (Hz)'
    )
    parser.add_argument(
        '-g', '--gain',
        type=float,
        default=50,
        help='Gain USRP (dB)'
    )
    parser.add_argument(
        '-s', '--sample-rate',
        type=float,
        default=20e6,
        help='Taux échantillonnage (Hz)'
    )

    args = parser.parse_args()

    # Vérifier dépendances
    logger.info("Vérification des dépendances...\n")
    if not check_dependencies():
        logger.error("\n❌ Dépendances manquantes")
        logger.info("\nPour installer:")
        logger.info("  Voir OPTION2B_GNU_RADIO.md pour instructions complètes")
        return 1

    logger.info("\n✓ Toutes les dépendances sont installées")

    # Créer récepteur
    receiver = WiFiRemoteIDReceiver(
        freq=args.freq,
        gain=args.gain,
        sample_rate=args.sample_rate
    )

    # Démarrer
    try:
        receiver.start()
    except KeyboardInterrupt:
        logger.info("\n\nArrêt utilisateur")
    except Exception as e:
        logger.error(f"Erreur: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
