"""
Capture WiFi pour Remote ID (Approche Recommandée)
Utilise un adaptateur WiFi en mode monitor pour capturer directement les trames
"""

import logging
from typing import Optional, List
from dataclasses import dataclass
import subprocess
import struct

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WiFiFrame:
    """
    Trame WiFi capturée
    """
    timestamp: float
    frequency: int
    signal_strength: int  # dBm
    src_mac: str
    dst_mac: str
    frame_type: str
    frame_data: bytes


class WiFiMonitorCapture:
    """
    Capture de trames WiFi en mode monitor
    APPROCHE RECOMMANDÉE pour Remote ID

    Cette approche est beaucoup plus simple et efficace que la démodulation SDR :
    1. Utilise un adaptateur WiFi USB en mode monitor
    2. Capture directement les trames Beacon
    3. Parse les IE Remote ID

    Matériel requis:
    - Adaptateur WiFi compatible mode monitor (ex: Alfa AWUS036ACH)
    - OU utiliser l'interface WiFi intégrée si supportée
    """

    def __init__(self, interface: str = "wlan0"):
        """
        Initialise la capture WiFi

        Args:
            interface: Interface WiFi (ex: wlan0, wlan1)
        """
        self.interface = interface
        self.monitor_interface = f"{interface}mon"
        logger.info(f"WiFi Monitor Capture initialisé sur {interface}")

    def enable_monitor_mode(self) -> bool:
        """
        Active le mode monitor sur l'interface WiFi

        Returns:
            True si succès
        """
        try:
            # Arrêt de l'interface
            subprocess.run(['sudo', 'ip', 'link', 'set', self.interface, 'down'],
                         check=True, capture_output=True)

            # Mode monitor avec airmon-ng (si disponible)
            try:
                subprocess.run(['sudo', 'airmon-ng', 'start', self.interface],
                             check=True, capture_output=True)
                logger.info(f"Mode monitor activé via airmon-ng")
                return True
            except FileNotFoundError:
                # Alternative: iw
                subprocess.run(['sudo', 'iw', self.interface, 'set', 'monitor', 'none'],
                             check=True, capture_output=True)
                logger.info(f"Mode monitor activé via iw")

            # Redémarrage de l'interface
            subprocess.run(['sudo', 'ip', 'link', 'set', self.monitor_interface, 'up'],
                         check=True, capture_output=True)

            # Définir le canal (exemple: canal 6)
            subprocess.run(['sudo', 'iw', self.monitor_interface, 'set', 'channel', '6'],
                         check=True, capture_output=True)

            logger.info(f"✓ Mode monitor activé sur {self.monitor_interface}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de l'activation du mode monitor: {e}")
            return False

    def disable_monitor_mode(self):
        """
        Désactive le mode monitor
        """
        try:
            subprocess.run(['sudo', 'airmon-ng', 'stop', self.monitor_interface],
                         capture_output=True)
            logger.info("Mode monitor désactivé")
        except Exception as e:
            logger.error(f"Erreur lors de la désactivation: {e}")

    def capture_with_tcpdump(self, duration: int = 10) -> List[str]:
        """
        Capture des trames avec tcpdump

        Args:
            duration: Durée de capture en secondes

        Returns:
            Liste de chemins vers fichiers pcap
        """
        pcap_file = f"/tmp/wifi_capture_{duration}s.pcap"

        try:
            # Capture avec tcpdump (beacon frames uniquement)
            cmd = [
                'sudo', 'tcpdump',
                '-i', self.monitor_interface,
                '-w', pcap_file,
                '-G', str(duration),
                '-W', '1',
                'type mgt subtype beacon'
            ]

            logger.info(f"Capture en cours pendant {duration}s...")
            subprocess.run(cmd, check=True, timeout=duration + 5)

            logger.info(f"✓ Capture terminée: {pcap_file}")
            return [pcap_file]

        except Exception as e:
            logger.error(f"Erreur lors de la capture: {e}")
            return []

    def capture_with_scapy(self, count: int = 100) -> List[WiFiFrame]:
        """
        Capture des trames avec Scapy (Python)

        Args:
            count: Nombre de trames à capturer

        Returns:
            Liste de WiFiFrame
        """
        try:
            from scapy.all import sniff, Dot11, Dot11Beacon

            logger.info(f"Capture de {count} trames beacon avec Scapy...")

            frames = []

            def packet_handler(pkt):
                if pkt.haslayer(Dot11Beacon):
                    # Extraction des informations
                    src_mac = pkt[Dot11].addr2
                    dst_mac = pkt[Dot11].addr1
                    signal = pkt.dBm_AntSignal if hasattr(pkt, 'dBm_AntSignal') else -100

                    frame = WiFiFrame(
                        timestamp=pkt.time,
                        frequency=2437,  # Canal 6 par défaut
                        signal_strength=signal,
                        src_mac=src_mac,
                        dst_mac=dst_mac,
                        frame_type='Beacon',
                        frame_data=bytes(pkt)
                    )
                    frames.append(frame)

            # Capture
            sniff(iface=self.monitor_interface,
                  prn=packet_handler,
                  count=count,
                  timeout=30,
                  filter="type mgt subtype beacon")

            logger.info(f"✓ {len(frames)} trames beacon capturées")
            return frames

        except ImportError:
            logger.error("Scapy n'est pas installé. Installez avec: pip install scapy")
            return []
        except Exception as e:
            logger.error(f"Erreur lors de la capture Scapy: {e}")
            return []


def test_wifi_capture():
    """
    Test de la capture WiFi
    """
    logger.info("=== Test de la capture WiFi ===")

    capture = WiFiMonitorCapture(interface="wlan0")

    logger.info("\n⚠️  ATTENTION: Ce test nécessite:")
    logger.info("  1. Un adaptateur WiFi compatible mode monitor")
    logger.info("  2. Les droits sudo")
    logger.info("  3. airmon-ng ou iw installé")
    logger.info("  4. Scapy installé (pip install scapy)")

    # Activation du mode monitor
    logger.info("\n--- Activation du mode monitor ---")
    # Décommentez si vous voulez tester réellement:
    # if capture.enable_monitor_mode():
    #     logger.info("✓ Mode monitor activé")
    #
    #     # Capture de trames
    #     logger.info("\n--- Capture de trames ---")
    #     frames = capture.capture_with_scapy(count=10)
    #
    #     for i, frame in enumerate(frames, 1):
    #         logger.info(f"Frame {i}: {frame.src_mac} @ {frame.signal_strength} dBm")
    #
    #     # Désactivation
    #     capture.disable_monitor_mode()
    # else:
    #     logger.error("Impossible d'activer le mode monitor")

    logger.info("\n📝 Pour utiliser ce module:")
    logger.info("1. Installez les outils: sudo apt-get install aircrack-ng")
    logger.info("2. Installez Scapy: pip install scapy")
    logger.info("3. Décommentez le code de test ci-dessus")
    logger.info("4. Exécutez avec: sudo python3 -m src.wifi_capture")

    logger.info("\nTest terminé")


if __name__ == "__main__":
    test_wifi_capture()
