"""
MODULE 2: Prétraitement (preprocessing.py)
Nettoyage et normalisation des signaux I/Q
"""

import numpy as np
from scipy import signal
from typing import Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalPreprocessor:
    """
    Classe pour le prétraitement des signaux I/Q
    """

    def __init__(self, sample_rate: float = 25e6):
        """
        Initialise le préprocesseur

        Args:
            sample_rate: Taux d'échantillonnage en Hz
        """
        self.sample_rate = sample_rate
        logger.info(f"Préprocesseur initialisé avec fs={sample_rate/1e6:.2f} MS/s")

    def remove_dc_offset(self, iq_samples: np.ndarray) -> np.ndarray:
        """
        Supprime le DC offset (offset continu) du signal I/Q

        Args:
            iq_samples: Échantillons I/Q complexes

        Returns:
            Signal corrigé
        """
        # Calcul de la moyenne (DC offset)
        dc_offset = np.mean(iq_samples)

        # Soustraction du DC offset
        corrected = iq_samples - dc_offset

        logger.debug(f"DC offset supprimé: {np.abs(dc_offset):.6f}")

        return corrected

    def correct_iq_imbalance(self, iq_samples: np.ndarray) -> np.ndarray:
        """
        Corrige les déséquilibres I/Q (amplitude et phase)

        Args:
            iq_samples: Échantillons I/Q complexes

        Returns:
            Signal corrigé
        """
        # Extraction des composantes I et Q
        i_component = np.real(iq_samples)
        q_component = np.imag(iq_samples)

        # Correction d'amplitude: normalisation des variances
        i_std = np.std(i_component)
        q_std = np.std(q_component)

        if q_std > 0:
            gain_correction = i_std / q_std
            q_component = q_component * gain_correction
        else:
            gain_correction = 1.0

        # Correction de phase: orthogonalisation par Gram-Schmidt
        correlation = np.mean(i_component * q_component)
        i_variance = np.var(i_component)

        if i_variance > 0:
            phase_correction = correlation / i_variance
            q_component = q_component - phase_correction * i_component
        else:
            phase_correction = 0

        corrected = i_component + 1j * q_component

        logger.debug(f"IQ correction - Gain: {gain_correction:.4f}, Phase: {phase_correction:.6f}")

        return corrected

    def bandpass_filter(self,
                       iq_samples: np.ndarray,
                       low_freq: float,
                       high_freq: float,
                       order: int = 6) -> np.ndarray:
        """
        Applique un filtre passe-bande Butterworth

        Args:
            iq_samples: Échantillons I/Q complexes
            low_freq: Fréquence basse de coupure (Hz)
            high_freq: Fréquence haute de coupure (Hz)
            order: Ordre du filtre

        Returns:
            Signal filtré
        """
        # Normalisation des fréquences par rapport à la fréquence de Nyquist
        nyquist = self.sample_rate / 2.0
        low = low_freq / nyquist
        high = high_freq / nyquist

        # Vérification des bornes
        if low <= 0 or high >= 1:
            logger.warning(f"Fréquences de coupure invalides: {low_freq/1e6:.2f}-{high_freq/1e6:.2f} MHz")
            return iq_samples

        # Création du filtre Butterworth
        sos = signal.butter(order, [low, high], btype='band', output='sos')

        # Application du filtre (traitement séparé de I et Q)
        i_filtered = signal.sosfilt(sos, np.real(iq_samples))
        q_filtered = signal.sosfilt(sos, np.imag(iq_samples))

        filtered = i_filtered + 1j * q_filtered

        logger.debug(f"Filtre passe-bande appliqué: {low_freq/1e6:.2f}-{high_freq/1e6:.2f} MHz, ordre {order}")

        return filtered

    def lowpass_filter(self,
                      iq_samples: np.ndarray,
                      cutoff_freq: float,
                      order: int = 6) -> np.ndarray:
        """
        Applique un filtre passe-bas Butterworth

        Args:
            iq_samples: Échantillons I/Q complexes
            cutoff_freq: Fréquence de coupure (Hz)
            order: Ordre du filtre

        Returns:
            Signal filtré
        """
        # Normalisation de la fréquence
        nyquist = self.sample_rate / 2.0
        normalized_cutoff = cutoff_freq / nyquist

        if normalized_cutoff >= 1:
            logger.warning(f"Fréquence de coupure invalide: {cutoff_freq/1e6:.2f} MHz")
            return iq_samples

        # Création du filtre
        sos = signal.butter(order, normalized_cutoff, btype='low', output='sos')

        # Application
        i_filtered = signal.sosfilt(sos, np.real(iq_samples))
        q_filtered = signal.sosfilt(sos, np.imag(iq_samples))

        filtered = i_filtered + 1j * q_filtered

        logger.debug(f"Filtre passe-bas appliqué: {cutoff_freq/1e6:.2f} MHz, ordre {order}")

        return filtered

    def normalize_signal(self,
                        iq_samples: np.ndarray,
                        method: str = 'rms') -> np.ndarray:
        """
        Normalise le signal

        Args:
            iq_samples: Échantillons I/Q complexes
            method: Méthode de normalisation ('rms', 'peak', 'minmax')

        Returns:
            Signal normalisé
        """
        if method == 'rms':
            # Normalisation RMS (Root Mean Square)
            rms_value = np.sqrt(np.mean(np.abs(iq_samples)**2))
            if rms_value > 0:
                normalized = iq_samples / rms_value
            else:
                normalized = iq_samples
                logger.warning("RMS value is zero, skipping normalization")

        elif method == 'peak':
            # Normalisation par le maximum
            peak_value = np.max(np.abs(iq_samples))
            if peak_value > 0:
                normalized = iq_samples / peak_value
            else:
                normalized = iq_samples
                logger.warning("Peak value is zero, skipping normalization")

        elif method == 'minmax':
            # Normalisation min-max [-1, 1]
            abs_max = np.max(np.abs(iq_samples))
            if abs_max > 0:
                normalized = iq_samples / abs_max
            else:
                normalized = iq_samples
                logger.warning("Max absolute value is zero, skipping normalization")

        else:
            logger.warning(f"Méthode de normalisation inconnue: {method}")
            normalized = iq_samples

        logger.debug(f"Signal normalisé avec méthode '{method}'")

        return normalized

    def decimate(self,
                iq_samples: np.ndarray,
                decimation_factor: int) -> np.ndarray:
        """
        Décime le signal (réduction du taux d'échantillonnage)

        Args:
            iq_samples: Échantillons I/Q complexes
            decimation_factor: Facteur de décimation

        Returns:
            Signal décimé
        """
        if decimation_factor <= 1:
            return iq_samples

        # Décimation avec filtre anti-repliement
        decimated = signal.decimate(iq_samples, decimation_factor, ftype='iir', zero_phase=True)

        new_rate = self.sample_rate / decimation_factor
        logger.debug(f"Signal décimé par {decimation_factor}: "
                    f"{self.sample_rate/1e6:.2f} MS/s -> {new_rate/1e6:.2f} MS/s")

        return decimated

    def process(self,
               iq_samples: np.ndarray,
               enable_dc_removal: bool = True,
               enable_iq_correction: bool = True,
               bandpass_range: Optional[Tuple[float, float]] = None,
               normalize_method: str = 'rms') -> np.ndarray:
        """
        Pipeline complet de prétraitement

        Args:
            iq_samples: Échantillons I/Q bruts
            enable_dc_removal: Activer la suppression du DC offset
            enable_iq_correction: Activer la correction I/Q
            bandpass_range: Tuple (freq_low, freq_high) pour le filtre passe-bande
            normalize_method: Méthode de normalisation

        Returns:
            Signal prétraité
        """
        logger.info(f"Démarrage du prétraitement ({len(iq_samples)} échantillons)")

        processed = iq_samples.copy()

        # 1. Suppression DC offset
        if enable_dc_removal:
            processed = self.remove_dc_offset(processed)

        # 2. Correction I/Q
        if enable_iq_correction:
            processed = self.correct_iq_imbalance(processed)

        # 3. Filtrage passe-bande
        if bandpass_range is not None:
            low_freq, high_freq = bandpass_range
            processed = self.bandpass_filter(processed, low_freq, high_freq)

        # 4. Normalisation
        processed = self.normalize_signal(processed, method=normalize_method)

        logger.info("Prétraitement terminé")

        return processed

    def compute_snr(self,
                   iq_samples: np.ndarray,
                   signal_range: Optional[Tuple[int, int]] = None) -> float:
        """
        Calcule le rapport signal/bruit (SNR)

        Args:
            iq_samples: Échantillons I/Q
            signal_range: Tuple (start_idx, end_idx) pour la portion de signal

        Returns:
            SNR en dB
        """
        if signal_range is not None:
            start, end = signal_range
            signal_power = np.mean(np.abs(iq_samples[start:end])**2)

            # Bruit = tout sauf le signal
            noise_samples = np.concatenate([iq_samples[:start], iq_samples[end:]])
            noise_power = np.mean(np.abs(noise_samples)**2)
        else:
            # Estimation simple: on considère que le signal est dans la moitié centrale
            mid = len(iq_samples) // 2
            quarter = len(iq_samples) // 4

            signal_power = np.mean(np.abs(iq_samples[mid-quarter:mid+quarter])**2)
            noise_power = np.mean(np.abs(np.concatenate([
                iq_samples[:quarter],
                iq_samples[-quarter:]
            ]))**2)

        if noise_power > 0:
            snr_db = 10 * np.log10(signal_power / noise_power)
        else:
            snr_db = float('inf')

        logger.debug(f"SNR estimé: {snr_db:.2f} dB")

        return snr_db


def test_preprocessing():
    """
    Fonction de test pour le prétraitement
    """
    logger.info("=== Test du prétraitement ===")

    # Génération d'un signal de test
    fs = 25e6  # 25 MS/s
    duration = 0.01  # 10 ms
    num_samples = int(fs * duration)

    # Signal: porteuse à 5 MHz + bruit + DC offset
    t = np.arange(num_samples) / fs
    carrier_freq = 5e6
    signal_test = np.exp(2j * np.pi * carrier_freq * t)

    # Ajout de bruit
    noise = 0.1 * (np.random.randn(num_samples) + 1j * np.random.randn(num_samples))
    signal_test += noise

    # Ajout DC offset
    signal_test += 0.5 + 0.3j

    # Ajout déséquilibre I/Q
    signal_test = np.real(signal_test) + 1j * 1.2 * np.imag(signal_test)

    logger.info(f"Signal de test généré: {num_samples} échantillons")

    # Prétraitement
    preprocessor = SignalPreprocessor(sample_rate=fs)

    processed = preprocessor.process(
        signal_test,
        enable_dc_removal=True,
        enable_iq_correction=True,
        bandpass_range=(4e6, 6e6),
        normalize_method='rms'
    )

    logger.info(f"Signal prétraité: {len(processed)} échantillons")
    logger.info(f"Puissance originale: {10*np.log10(np.mean(np.abs(signal_test)**2)):.2f} dB")
    logger.info(f"Puissance traitée: {10*np.log10(np.mean(np.abs(processed)**2)):.2f} dB")

    # Calcul SNR
    snr = preprocessor.compute_snr(processed)
    logger.info(f"SNR: {snr:.2f} dB")

    logger.info("Test terminé")


if __name__ == "__main__":
    test_preprocessing()
