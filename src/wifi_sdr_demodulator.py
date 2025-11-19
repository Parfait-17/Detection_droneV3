"""
Démodulateur WiFi pour SDR (OPTION 2)
Implémentation de la démodulation WiFi 802.11 OFDM via USRP B210
"""

import numpy as np
from scipy import signal as sp_signal
from typing import Optional, Tuple, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WiFiSDRDemodulator:
    """
    Démodulateur WiFi 802.11 pour SDR
    Implémente OFDM démodulation pour extraction de trames Beacon
    """

    # Paramètres WiFi 802.11g/n OFDM
    FFT_SIZE = 64
    CYCLIC_PREFIX = 16
    OFDM_SYMBOL_DURATION = 4e-6  # 4 µs
    SHORT_PREAMBLE_DURATION = 8e-6  # 8 µs
    LONG_PREAMBLE_DURATION = 8e-6   # 8 µs

    # Sous-porteuses OFDM
    DATA_SUBCARRIERS = 48
    PILOT_SUBCARRIERS = 4
    NULL_SUBCARRIERS = 12

    # Préambule court WiFi (connu)
    SHORT_PREAMBLE_FREQ = np.array([
        0, 0, 0, 0, 0, 0, 0, 0, 1+1j, 0, 0, 0,
        -1-1j, 0, 0, 0, 1+1j, 0, 0, 0, -1-1j, 0, 0, 0,
        -1-1j, 0, 0, 0, 1+1j, 0, 0, 0, 0, 0, 0, 0,
        -1-1j, 0, 0, 0, -1-1j, 0, 0, 0, 1+1j, 0, 0, 0,
        1+1j, 0, 0, 0, 1+1j, 0, 0, 0, 1+1j, 0, 0, 0
    ])

    def __init__(self, sample_rate: float = 20e6):
        """
        Initialise le démodulateur WiFi

        Args:
            sample_rate: Taux d'échantillonnage (20 MS/s pour WiFi 20 MHz)
        """
        self.sample_rate = sample_rate

        # Générer le préambule court en temps
        self.short_preamble = np.fft.ifft(self.SHORT_PREAMBLE_FREQ, n=64)
        self.short_preamble = np.tile(self.short_preamble, 10)  # 10 répétitions

        logger.info(f"Démodulateur WiFi SDR initialisé (fs={sample_rate/1e6:.1f} MS/s)")

    def detect_preamble(self, iq_samples: np.ndarray) -> Optional[int]:
        """
        Détecte le préambule WiFi dans le signal

        Args:
            iq_samples: Échantillons I/Q complexes

        Returns:
            Index de début du paquet ou None
        """
        # Corrélation avec préambule court
        correlation = np.correlate(iq_samples, self.short_preamble, mode='valid')

        # Détection de pic de corrélation
        correlation_power = np.abs(correlation)**2
        threshold = np.mean(correlation_power) + 5 * np.std(correlation_power)

        peaks = np.where(correlation_power > threshold)[0]

        if len(peaks) > 0:
            # Premier pic significatif
            preamble_idx = peaks[0]
            logger.debug(f"Préambule détecté à l'index {preamble_idx}")
            return int(preamble_idx)

        return None

    def estimate_cfo(self, iq_samples: np.ndarray, preamble_idx: int) -> float:
        """
        Estime le décalage de fréquence porteuse (CFO)

        Args:
            iq_samples: Échantillons I/Q
            preamble_idx: Index du début du préambule

        Returns:
            CFO estimé (Hz)
        """
        # Utiliser les répétitions du préambule court
        short_preamble_samples = 16  # 16 échantillons par répétition

        start_idx = preamble_idx
        samples1 = iq_samples[start_idx:start_idx + short_preamble_samples]
        samples2 = iq_samples[start_idx + short_preamble_samples:
                             start_idx + 2*short_preamble_samples]

        # Phase entre deux répétitions
        phase_diff = np.angle(np.sum(np.conj(samples1) * samples2))

        # CFO = phase_diff / (2π * T)
        cfo = phase_diff * self.sample_rate / (2 * np.pi * short_preamble_samples)

        logger.debug(f"CFO estimé: {cfo/1e3:.2f} kHz")

        return cfo

    def correct_cfo(self, iq_samples: np.ndarray, cfo: float) -> np.ndarray:
        """
        Corrige le décalage de fréquence

        Args:
            iq_samples: Échantillons I/Q
            cfo: CFO à corriger (Hz)

        Returns:
            Signal corrigé
        """
        t = np.arange(len(iq_samples)) / self.sample_rate
        correction = np.exp(-1j * 2 * np.pi * cfo * t)

        return iq_samples * correction

    def extract_ofdm_symbols(self,
                            iq_samples: np.ndarray,
                            start_idx: int,
                            num_symbols: int = 10) -> List[np.ndarray]:
        """
        Extrait les symboles OFDM du signal

        Args:
            iq_samples: Signal I/Q
            start_idx: Index de début (après préambule)
            num_symbols: Nombre de symboles à extraire

        Returns:
            Liste de symboles OFDM (domaine fréquentiel)
        """
        symbols = []

        # Taille symbole = CP + FFT
        symbol_size = self.CYCLIC_PREFIX + self.FFT_SIZE

        for i in range(num_symbols):
            sym_start = start_idx + i * symbol_size
            sym_end = sym_start + symbol_size

            if sym_end > len(iq_samples):
                break

            # Récupérer le symbole
            ofdm_symbol_time = iq_samples[sym_start:sym_end]

            # Supprimer le préfixe cyclique
            ofdm_symbol_time = ofdm_symbol_time[self.CYCLIC_PREFIX:]

            # FFT pour passer en fréquentiel
            ofdm_symbol_freq = np.fft.fft(ofdm_symbol_time, n=self.FFT_SIZE)
            ofdm_symbol_freq = np.fft.fftshift(ofdm_symbol_freq)

            symbols.append(ofdm_symbol_freq)

        logger.debug(f"{len(symbols)} symboles OFDM extraits")

        return symbols

    def estimate_channel(self,
                        long_preamble_samples: np.ndarray) -> np.ndarray:
        """
        Estime la réponse en fréquence du canal

        Args:
            long_preamble_samples: Échantillons du préambule long

        Returns:
            Estimation du canal (H)
        """
        # Préambule long connu (simplifié)
        # Dans WiFi réel, c'est une séquence BPSK connue

        # FFT du préambule reçu
        received_fft = np.fft.fft(long_preamble_samples, n=self.FFT_SIZE)
        received_fft = np.fft.fftshift(received_fft)

        # Préambule long connu (simplifié - devrait être la vraie séquence WiFi)
        known_preamble = np.ones(self.FFT_SIZE, dtype=complex)

        # Estimation: H = Y / X
        channel_estimate = received_fft / (known_preamble + 1e-10)

        return channel_estimate

    def equalize_symbols(self,
                        symbols: List[np.ndarray],
                        channel_estimate: np.ndarray) -> List[np.ndarray]:
        """
        Égalise les symboles OFDM

        Args:
            symbols: Symboles OFDM en fréquentiel
            channel_estimate: Estimation du canal

        Returns:
            Symboles égalisés
        """
        equalized = []

        for symbol in symbols:
            # Égalisation: Y_eq = Y / H
            eq_symbol = symbol / (channel_estimate + 1e-10)
            equalized.append(eq_symbol)

        return equalized

    def demodulate_bpsk(self, symbols: List[np.ndarray]) -> np.ndarray:
        """
        Démodule BPSK (utilisé pour headers WiFi)

        Args:
            symbols: Symboles OFDM égalisés

        Returns:
            Bits démodulés
        """
        bits = []

        for symbol in symbols:
            # Extraire les sous-porteuses de données
            # WiFi: indices -26 à -1 et 1 à 26 (centré à 0)
            data_carriers = np.concatenate([
                symbol[6:32],   # -26 à -1
                symbol[33:59]   # 1 à 26
            ])

            # Démodulation BPSK: bit = 1 si real > 0, sinon 0
            symbol_bits = (np.real(data_carriers) > 0).astype(int)
            bits.extend(symbol_bits)

        return np.array(bits)

    def demodulate_qpsk(self, symbols: List[np.ndarray]) -> np.ndarray:
        """
        Démodule QPSK

        Args:
            symbols: Symboles OFDM égalisés

        Returns:
            Bits démodulés
        """
        bits = []

        for symbol in symbols:
            data_carriers = np.concatenate([
                symbol[6:32],
                symbol[33:59]
            ])

            # QPSK: 2 bits par symbole
            for carrier in data_carriers:
                # Bit 0: signe de real
                bits.append(1 if np.real(carrier) > 0 else 0)
                # Bit 1: signe de imag
                bits.append(1 if np.imag(carrier) > 0 else 0)

        return np.array(bits)

    def bits_to_bytes(self, bits: np.ndarray) -> bytes:
        """
        Convertit les bits en octets

        Args:
            bits: Array de bits

        Returns:
            Octets
        """
        # Padding pour avoir un multiple de 8
        padding = (8 - len(bits) % 8) % 8
        bits = np.append(bits, np.zeros(padding, dtype=int))

        # Regrouper par 8 bits
        bytes_array = []
        for i in range(0, len(bits), 8):
            byte_bits = bits[i:i+8]
            byte_value = 0
            for j, bit in enumerate(byte_bits):
                byte_value |= (int(bit) << (7-j))
            bytes_array.append(byte_value)

        return bytes(bytes_array)

    def demodulate_wifi_packet(self, iq_samples: np.ndarray) -> Optional[bytes]:
        """
        Démodule un paquet WiFi complet

        Args:
            iq_samples: Signal I/Q contenant un paquet WiFi

        Returns:
            Octets du paquet démodulé ou None
        """
        logger.info("Démodulation paquet WiFi...")

        # 1. Détection du préambule
        preamble_idx = self.detect_preamble(iq_samples)

        if preamble_idx is None:
            logger.warning("Aucun préambule WiFi détecté")
            return None

        logger.info(f"✓ Préambule détecté à l'index {preamble_idx}")

        # 2. Estimation et correction CFO
        cfo = self.estimate_cfo(iq_samples, preamble_idx)
        iq_corrected = self.correct_cfo(iq_samples, cfo)

        # 3. Extraction du préambule long pour estimation de canal
        long_preamble_start = preamble_idx + int(self.SHORT_PREAMBLE_DURATION * self.sample_rate)
        long_preamble_samples = iq_corrected[
            long_preamble_start:long_preamble_start + self.FFT_SIZE
        ]

        channel_estimate = self.estimate_channel(long_preamble_samples)

        # 4. Extraction des symboles OFDM (données)
        data_start = long_preamble_start + 2 * self.FFT_SIZE  # Après préambules
        ofdm_symbols = self.extract_ofdm_symbols(iq_corrected, data_start, num_symbols=20)

        if not ofdm_symbols:
            logger.warning("Aucun symbole OFDM extrait")
            return None

        logger.info(f"✓ {len(ofdm_symbols)} symboles OFDM extraits")

        # 5. Égalisation
        equalized_symbols = self.equalize_symbols(ofdm_symbols, channel_estimate)

        # 6. Démodulation (BPSK pour le header, QPSK/QAM pour data)
        # Simplifié: on utilise BPSK
        bits = self.demodulate_bpsk(equalized_symbols)

        logger.info(f"✓ {len(bits)} bits démodulés")

        # 7. Conversion en octets
        packet_bytes = self.bits_to_bytes(bits)

        logger.info(f"✓ Paquet démodulé: {len(packet_bytes)} octets")

        return packet_bytes


def test_wifi_sdr_demodulator():
    """
    Test du démodulateur WiFi SDR
    """
    logger.info("=== Test du démodulateur WiFi SDR ===")

    demodulator = WiFiSDRDemodulator(sample_rate=20e6)

    # Génération d'un signal WiFi simulé pour test
    logger.info("\n--- Test avec signal WiFi simulé ---")

    # Créer un signal de test avec préambule
    num_samples = 100000
    signal_test = np.random.randn(num_samples) + 1j * np.random.randn(num_samples)
    signal_test *= 0.1

    # Ajouter le préambule à l'index 1000
    preamble_idx = 1000
    signal_test[preamble_idx:preamble_idx + len(demodulator.short_preamble)] = \
        demodulator.short_preamble * 2.0

    # Test détection
    detected_idx = demodulator.detect_preamble(signal_test)

    if detected_idx is not None:
        logger.info(f"✓ Préambule détecté à l'index {detected_idx} (attendu: ~{preamble_idx})")
    else:
        logger.warning("✗ Préambule non détecté")

    logger.info("\n📝 Pour tester avec de vrais signaux WiFi:")
    logger.info("1. Utilisez uhd_acquisition.py pour capturer du WiFi 2.4 GHz")
    logger.info("2. Passez les échantillons à demodulate_wifi_packet()")
    logger.info("3. Les octets démodulés peuvent être parsés par remote_id_decoder.py")

    logger.info("\nTest terminé")


if __name__ == "__main__":
    test_wifi_sdr_demodulator()
