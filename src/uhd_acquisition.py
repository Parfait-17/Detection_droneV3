"""
MODULE 1: Acquisition RF (uhd_acquisition.py)
Gestion de l'acquisition des signaux RF via LibreSDR B210mini
"""

import uhd
import numpy as np
import logging
from typing import Optional, Tuple
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UHDAcquisition:
    """
    Classe pour gérer l'acquisition RF avec le LibreSDR B210mini (USRP)
    """

    def __init__(self,
                 device_args: str = "type=b200",
                 sample_rate: float = 25e6,
                 rx_freq_2g4: float = 2.4e9,
                 rx_freq_5g8: float = 5.8e9,
                 rx_gain: float = 40.0):
        """
        Initialise le récepteur USRP

        Args:
            device_args: Arguments pour identifier le device USRP
            sample_rate: Taux d'échantillonnage (25 MS/s par défaut)
            rx_freq_2g4: Fréquence RX1 pour 2.4 GHz
            rx_freq_5g8: Fréquence RX2 pour 5.8 GHz
            rx_gain: Gain en dB
        """
        self.device_args = device_args
        self.sample_rate = sample_rate
        self.rx_freq_2g4 = rx_freq_2g4
        self.rx_freq_5g8 = rx_freq_5g8
        self.rx_gain = rx_gain
        self.usrp: Optional[uhd.usrp.MultiUSRP] = None
        self.is_running = False
        self.data_queue = queue.Queue(maxsize=10)

    def initialize(self) -> bool:
        """
        Initialise et configure le périphérique USRP

        Returns:
            True si l'initialisation réussit, False sinon
        """
        try:
            logger.info(f"Initialisation USRP avec {self.device_args}")
            self.usrp = uhd.usrp.MultiUSRP(self.device_args)

            # Configuration RX1 (2.4 GHz - OcuSync + WiFi Remote ID)
            logger.info("Configuration RX1 (2.4 GHz)")
            self.usrp.set_rx_rate(self.sample_rate, 0)
            self.usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(self.rx_freq_2g4), 0)
            self.usrp.set_rx_gain(self.rx_gain, 0)
            self.usrp.set_rx_antenna("RX2", 0)

            # Configuration RX2 (5.8 GHz - OcuSync HD, WiFi 5 GHz)
            logger.info("Configuration RX2 (5.8 GHz)")
            self.usrp.set_rx_rate(self.sample_rate, 1)
            self.usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(self.rx_freq_5g8), 1)
            self.usrp.set_rx_gain(self.rx_gain, 1)
            self.usrp.set_rx_antenna("RX2", 1)

            # Vérification de la configuration
            actual_rate_ch0 = self.usrp.get_rx_rate(0)
            actual_freq_ch0 = self.usrp.get_rx_freq(0)
            actual_gain_ch0 = self.usrp.get_rx_gain(0)

            logger.info(f"RX1 configuré: {actual_rate_ch0/1e6:.2f} MS/s, "
                       f"{actual_freq_ch0/1e9:.3f} GHz, {actual_gain_ch0} dB")

            actual_rate_ch1 = self.usrp.get_rx_rate(1)
            actual_freq_ch1 = self.usrp.get_rx_freq(1)
            actual_gain_ch1 = self.usrp.get_rx_gain(1)

            logger.info(f"RX2 configuré: {actual_rate_ch1/1e6:.2f} MS/s, "
                       f"{actual_freq_ch1/1e9:.3f} GHz, {actual_gain_ch1} dB")

            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation USRP: {e}")
            return False

    def acquire_samples(self,
                       num_samples: int = 100000,
                       channel: int = 0) -> Optional[np.ndarray]:
        """
        Acquiert un nombre spécifique d'échantillons I/Q

        Args:
            num_samples: Nombre d'échantillons à acquérir
            channel: Canal à utiliser (0 pour 2.4GHz, 1 pour 5.8GHz)

        Returns:
            Array numpy de samples complexes (complex64) ou None si erreur
        """
        if self.usrp is None:
            logger.error("USRP non initialisé")
            return None

        try:
            # Création du stream
            st_args = uhd.usrp.StreamArgs("fc32", "sc16")
            st_args.channels = [channel]
            rx_streamer = self.usrp.get_rx_stream(st_args)

            # Buffer pour recevoir les échantillons
            recv_buffer = np.zeros(num_samples, dtype=np.complex64)

            # Metadata pour les informations de streaming
            metadata = uhd.types.RXMetadata()

            # Configuration du streaming
            stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.num_done)
            stream_cmd.num_samps = num_samples
            stream_cmd.stream_now = True
            rx_streamer.issue_stream_cmd(stream_cmd)

            # Réception des échantillons
            samples_received = 0
            timeout = 3.0  # Timeout de 3 secondes

            while samples_received < num_samples:
                samps = rx_streamer.recv(recv_buffer[samples_received:], metadata, timeout)

                if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
                    logger.warning(f"Erreur de réception: {metadata.error_code}")
                    break

                samples_received += samps

            logger.debug(f"Reçu {samples_received}/{num_samples} échantillons du canal {channel}")

            return recv_buffer[:samples_received]

        except Exception as e:
            logger.error(f"Erreur lors de l'acquisition: {e}")
            return None

    def start_continuous_acquisition(self,
                                    num_samples_per_buffer: int = 100000,
                                    channel: int = 0):
        """
        Démarre l'acquisition continue en arrière-plan

        Args:
            num_samples_per_buffer: Taille des buffers à acquérir
            channel: Canal à utiliser
        """
        if self.is_running:
            logger.warning("L'acquisition est déjà en cours")
            return

        self.is_running = True

        def acquisition_thread():
            logger.info(f"Démarrage de l'acquisition continue sur le canal {channel}")
            while self.is_running:
                samples = self.acquire_samples(num_samples_per_buffer, channel)
                if samples is not None:
                    try:
                        self.data_queue.put(samples, timeout=1.0)
                    except queue.Full:
                        logger.warning("Queue pleine, échantillons perdus")

        self.acquisition_thread = threading.Thread(target=acquisition_thread, daemon=True)
        self.acquisition_thread.start()
        logger.info("Acquisition continue démarrée")

    def get_samples(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        Récupère les échantillons de la queue (mode continu)

        Args:
            timeout: Timeout en secondes

        Returns:
            Array d'échantillons ou None
        """
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop_continuous_acquisition(self):
        """
        Arrête l'acquisition continue
        """
        if self.is_running:
            logger.info("Arrêt de l'acquisition continue")
            self.is_running = False
            if hasattr(self, 'acquisition_thread'):
                self.acquisition_thread.join(timeout=5.0)
            logger.info("Acquisition continue arrêtée")

    def scan_frequencies(self,
                        freq_start: float,
                        freq_stop: float,
                        freq_step: float = 1e6,
                        num_samples: int = 10000) -> dict:
        """
        Scan un range de fréquences

        Args:
            freq_start: Fréquence de départ (Hz)
            freq_stop: Fréquence de fin (Hz)
            freq_step: Pas de fréquence (Hz)
            num_samples: Nombre d'échantillons par fréquence

        Returns:
            Dictionnaire {fréquence: puissance moyenne}
        """
        results = {}
        freqs = np.arange(freq_start, freq_stop, freq_step)

        logger.info(f"Scan de {freq_start/1e9:.3f} GHz à {freq_stop/1e9:.3f} GHz "
                   f"avec un pas de {freq_step/1e6:.1f} MHz")

        for freq in freqs:
            # Changer la fréquence
            self.usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(freq), 0)

            # Acquérir des échantillons
            samples = self.acquire_samples(num_samples, channel=0)

            if samples is not None:
                # Calculer la puissance moyenne
                power = np.mean(np.abs(samples)**2)
                results[freq] = 10 * np.log10(power + 1e-12)  # Conversion en dB

        logger.info(f"Scan terminé: {len(results)} fréquences balayées")
        return results

    def close(self):
        """
        Ferme proprement le périphérique USRP
        """
        self.stop_continuous_acquisition()
        if self.usrp is not None:
            logger.info("Fermeture de l'USRP")
            self.usrp = None


# Fonction utilitaire pour tester le module
def test_acquisition():
    """
    Fonction de test pour vérifier l'acquisition
    """
    logger.info("=== Test d'acquisition UHD ===")

    # Initialisation
    acq = UHDAcquisition()

    if not acq.initialize():
        logger.error("Échec de l'initialisation")
        return

    # Test acquisition simple
    logger.info("Test d'acquisition de 100k échantillons sur 2.4 GHz")
    samples = acq.acquire_samples(num_samples=100000, channel=0)

    if samples is not None:
        logger.info(f"Échantillons reçus: {len(samples)}")
        logger.info(f"Type: {samples.dtype}")
        logger.info(f"Puissance moyenne: {10*np.log10(np.mean(np.abs(samples)**2)):.2f} dB")
        logger.info(f"Min: {np.min(np.abs(samples)):.6f}, Max: {np.max(np.abs(samples)):.6f}")

    # Fermeture
    acq.close()
    logger.info("Test terminé")


if __name__ == "__main__":
    test_acquisition()
