"""
MODULE 3: Analyse Spectrale (spectrogram.py)
Génération de spectrogrammes et extraction de features temporelles/fréquentielles
"""

import numpy as np
from scipy import signal
from typing import Tuple, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpectralAnalyzer:
    """
    Classe pour l'analyse spectrale des signaux I/Q
    """

    def __init__(self, sample_rate: float = 25e6):
        """
        Initialise l'analyseur spectral

        Args:
            sample_rate: Taux d'échantillonnage en Hz
        """
        self.sample_rate = sample_rate
        logger.info(f"Analyseur spectral initialisé avec fs={sample_rate/1e6:.2f} MS/s")

    def compute_spectrogram(self,
                          iq_samples: np.ndarray,
                          nperseg: int = 2048,
                          noverlap: Optional[int] = None,
                          window: str = 'hann') -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calcule le spectrogramme du signal

        Args:
            iq_samples: Échantillons I/Q complexes
            nperseg: Longueur de chaque segment pour la STFT
            noverlap: Nombre d'échantillons de recouvrement entre segments
            window: Type de fenêtre ('hann', 'hamming', 'blackman', etc.)

        Returns:
            Tuple (fréquences, temps, spectrogramme) où:
                - fréquences: array des fréquences (Hz)
                - temps: array des temps (s)
                - spectrogramme: matrice complexe [freq × temps]
        """
        if noverlap is None:
            noverlap = nperseg // 2

        # Calcul de la STFT (Short-Time Fourier Transform)
        f, t, Zxx = signal.stft(
            iq_samples,
            fs=self.sample_rate,
            window=window,
            nperseg=nperseg,
            noverlap=noverlap,
            return_onesided=False,
            boundary=None
        )

        # Réorganisation des fréquences pour centrer à 0
        f = np.fft.fftshift(f)
        Zxx = np.fft.fftshift(Zxx, axes=0)

        logger.debug(f"Spectrogramme calculé: {Zxx.shape[0]} freq × {Zxx.shape[1]} temps")

        return f, t, Zxx

    def compute_psd(self,
                   iq_samples: np.ndarray,
                   nperseg: int = 2048,
                   window: str = 'hann') -> Tuple[np.ndarray, np.ndarray]:
        """
        Calcule la densité spectrale de puissance (PSD)

        Args:
            iq_samples: Échantillons I/Q complexes
            nperseg: Longueur de chaque segment
            window: Type de fenêtre

        Returns:
            Tuple (fréquences, psd) où:
                - fréquences: array des fréquences (Hz)
                - psd: densité spectrale de puissance (en échelle linéaire)
        """
        f, psd = signal.welch(
            iq_samples,
            fs=self.sample_rate,
            window=window,
            nperseg=nperseg,
            return_onesided=False,
            scaling='density'
        )

        # Réorganisation pour centrer à 0
        f = np.fft.fftshift(f)
        psd = np.fft.fftshift(psd)

        logger.debug(f"PSD calculée: {len(f)} points fréquentiels")

        return f, psd

    def estimate_bandwidth(self,
                         iq_samples: np.ndarray,
                         threshold_db: float = -10.0) -> Tuple[float, float, float]:
        """
        Estime la bande passante du signal

        Args:
            iq_samples: Échantillons I/Q complexes
            threshold_db: Seuil en dB par rapport au pic pour définir la bande

        Returns:
            Tuple (bandwidth, center_freq, peak_power_db)
        """
        # Calcul de la PSD
        f, psd = self.compute_psd(iq_samples)

        # Conversion en dB
        psd_db = 10 * np.log10(psd + 1e-12)

        # Recherche du pic
        peak_idx = np.argmax(psd_db)
        peak_power = psd_db[peak_idx]
        center_freq = f[peak_idx]

        # Seuil pour la bande passante
        threshold = peak_power + threshold_db

        # Recherche des limites de la bande
        above_threshold = psd_db > threshold
        indices = np.where(above_threshold)[0]

        if len(indices) > 0:
            freq_low = f[indices[0]]
            freq_high = f[indices[-1]]
            bandwidth = freq_high - freq_low
        else:
            bandwidth = 0
            logger.warning("Impossible d'estimer la bande passante")

        logger.debug(f"Bande passante estimée: {bandwidth/1e6:.2f} MHz "
                    f"(centre: {center_freq/1e6:.2f} MHz, pic: {peak_power:.2f} dB)")

        return bandwidth, center_freq, peak_power

    def detect_bursts(self,
                     iq_samples: np.ndarray,
                     threshold_factor: float = 3.0,
                     min_burst_duration: float = 1e-3) -> list:
        """
        Détecte les rafales (bursts) dans le signal

        Args:
            iq_samples: Échantillons I/Q complexes
            threshold_factor: Facteur multiplicatif du bruit pour le seuil
            min_burst_duration: Durée minimale d'une rafale (secondes)

        Returns:
            Liste de tuples (start_idx, end_idx, duration, power) pour chaque rafale
        """
        # Calcul de l'enveloppe (puissance instantanée)
        power = np.abs(iq_samples)**2

        # Estimation du niveau de bruit (percentile 25%)
        noise_level = np.percentile(power, 25)

        # Seuil de détection
        threshold = noise_level * threshold_factor

        # Détection des échantillons au-dessus du seuil
        above_threshold = power > threshold

        # Identification des rafales
        bursts = []
        in_burst = False
        burst_start = 0

        min_samples = int(min_burst_duration * self.sample_rate)

        for i, is_above in enumerate(above_threshold):
            if is_above and not in_burst:
                # Début d'une rafale
                in_burst = True
                burst_start = i
            elif not is_above and in_burst:
                # Fin d'une rafale
                burst_end = i
                burst_length = burst_end - burst_start

                if burst_length >= min_samples:
                    burst_duration = burst_length / self.sample_rate
                    burst_power = np.mean(power[burst_start:burst_end])
                    bursts.append((burst_start, burst_end, burst_duration, burst_power))

                in_burst = False

        # Dernière rafale si le signal se termine pendant une rafale
        if in_burst:
            burst_end = len(above_threshold)
            burst_length = burst_end - burst_start
            if burst_length >= min_samples:
                burst_duration = burst_length / self.sample_rate
                burst_power = np.mean(power[burst_start:burst_end])
                bursts.append((burst_start, burst_end, burst_duration, burst_power))

        logger.info(f"{len(bursts)} rafales détectées")

        return bursts

    def extract_temporal_features(self, iq_samples: np.ndarray) -> Dict[str, float]:
        """
        Extrait les caractéristiques temporelles du signal

        Args:
            iq_samples: Échantillons I/Q complexes

        Returns:
            Dictionnaire de features
        """
        # Calcul de l'enveloppe
        envelope = np.abs(iq_samples)
        power = envelope**2

        # Calcul de la phase instantanée
        phase = np.angle(iq_samples)
        phase_diff = np.diff(np.unwrap(phase))

        features = {
            # Statistiques d'amplitude
            'mean_amplitude': float(np.mean(envelope)),
            'std_amplitude': float(np.std(envelope)),
            'max_amplitude': float(np.max(envelope)),
            'min_amplitude': float(np.min(envelope)),

            # Statistiques de puissance
            'mean_power': float(np.mean(power)),
            'std_power': float(np.std(power)),
            'peak_to_average_ratio': float(np.max(power) / (np.mean(power) + 1e-12)),

            # Statistiques de phase
            'mean_phase_derivative': float(np.mean(phase_diff)),
            'std_phase_derivative': float(np.std(phase_diff)),

            # Facteur de crête
            'crest_factor': float(np.max(envelope) / (np.sqrt(np.mean(power)) + 1e-12)),

            # Kurtosis (indicateur de non-gaussianité)
            'kurtosis': float(np.mean((envelope - np.mean(envelope))**4) /
                            (np.std(envelope)**4 + 1e-12))
        }

        logger.debug(f"Features temporelles extraites: {len(features)} valeurs")

        return features

    def extract_spectral_features(self,
                                 iq_samples: np.ndarray,
                                 nperseg: int = 2048) -> Dict[str, float]:
        """
        Extrait les caractéristiques spectrales du signal

        Args:
            iq_samples: Échantillons I/Q complexes
            nperseg: Longueur de segment pour l'analyse spectrale

        Returns:
            Dictionnaire de features
        """
        # Calcul de la PSD
        f, psd = self.compute_psd(iq_samples, nperseg=nperseg)
        psd_db = 10 * np.log10(psd + 1e-12)

        # Estimation de la bande passante
        bandwidth, center_freq, peak_power = self.estimate_bandwidth(iq_samples)

        # Calcul du centroïde spectral
        spectral_centroid = np.sum(f * psd) / (np.sum(psd) + 1e-12)

        # Calcul de la largeur spectrale (spread)
        spectral_spread = np.sqrt(np.sum(((f - spectral_centroid)**2) * psd) /
                                 (np.sum(psd) + 1e-12))

        # Flatness spectrale (mesure de tonalité vs bruit)
        geometric_mean = np.exp(np.mean(np.log(psd + 1e-12)))
        arithmetic_mean = np.mean(psd)
        spectral_flatness = geometric_mean / (arithmetic_mean + 1e-12)

        features = {
            'bandwidth': float(bandwidth),
            'center_frequency': float(center_freq),
            'peak_power_db': float(peak_power),
            'spectral_centroid': float(spectral_centroid),
            'spectral_spread': float(spectral_spread),
            'spectral_flatness': float(spectral_flatness),
            'mean_psd_db': float(np.mean(psd_db)),
            'max_psd_db': float(np.max(psd_db)),
            'std_psd_db': float(np.std(psd_db))
        }

        logger.debug(f"Features spectrales extraites: {len(features)} valeurs")

        return features

    def analyze_signal(self,
                      iq_samples: np.ndarray,
                      compute_spectrogram: bool = True) -> Dict:
        """
        Analyse complète du signal

        Args:
            iq_samples: Échantillons I/Q complexes
            compute_spectrogram: Si True, calcule également le spectrogramme

        Returns:
            Dictionnaire contenant toutes les analyses
        """
        logger.info(f"Analyse du signal ({len(iq_samples)} échantillons)")

        results = {
            'num_samples': len(iq_samples),
            'duration': len(iq_samples) / self.sample_rate
        }

        # Features temporelles
        results['temporal_features'] = self.extract_temporal_features(iq_samples)

        # Features spectrales
        results['spectral_features'] = self.extract_spectral_features(iq_samples)

        # Détection de rafales
        bursts = self.detect_bursts(iq_samples)
        results['bursts'] = {
            'count': len(bursts),
            'bursts_list': bursts
        }

        # Spectrogramme (optionnel)
        if compute_spectrogram:
            f, t, Zxx = self.compute_spectrogram(iq_samples)
            results['spectrogram'] = {
                'frequencies': f,
                'times': t,
                'data': Zxx,
                'shape': Zxx.shape
            }

        logger.info("Analyse complète terminée")

        return results


def test_spectral_analysis():
    """
    Fonction de test pour l'analyse spectrale
    """
    logger.info("=== Test de l'analyse spectrale ===")

    # Génération d'un signal de test
    fs = 25e6
    duration = 0.01  # 10 ms
    num_samples = int(fs * duration)

    t = np.arange(num_samples) / fs

    # Signal composite: plusieurs porteuses + rafales
    signal_test = np.zeros(num_samples, dtype=np.complex64)

    # Porteuse 1 à 3 MHz (continue)
    signal_test += 0.5 * np.exp(2j * np.pi * 3e6 * t)

    # Porteuse 2 à -5 MHz (continue, plus faible)
    signal_test += 0.3 * np.exp(2j * np.pi * (-5e6) * t)

    # Rafale à 0 MHz (burst de 2ms)
    burst_start = int(0.003 * fs)
    burst_end = int(0.005 * fs)
    signal_test[burst_start:burst_end] += 1.0 * np.exp(2j * np.pi * 0 * t[burst_start:burst_end])

    # Ajout de bruit
    noise = 0.1 * (np.random.randn(num_samples) + 1j * np.random.randn(num_samples))
    signal_test += noise

    logger.info(f"Signal de test généré: {num_samples} échantillons, durée {duration*1000:.1f} ms")

    # Analyse spectrale
    analyzer = SpectralAnalyzer(sample_rate=fs)

    results = analyzer.analyze_signal(signal_test, compute_spectrogram=True)

    # Affichage des résultats
    logger.info(f"\n--- Résultats de l'analyse ---")
    logger.info(f"Durée: {results['duration']*1000:.2f} ms")

    logger.info("\nFeatures temporelles:")
    for key, value in results['temporal_features'].items():
        logger.info(f"  {key}: {value:.6f}")

    logger.info("\nFeatures spectrales:")
    for key, value in results['spectral_features'].items():
        if 'frequency' in key or 'bandwidth' in key:
            logger.info(f"  {key}: {value/1e6:.3f} MHz")
        else:
            logger.info(f"  {key}: {value:.6f}")

    logger.info(f"\nRafales détectées: {results['bursts']['count']}")
    for i, (start, end, duration, power) in enumerate(results['bursts']['bursts_list']):
        logger.info(f"  Burst {i+1}: {duration*1000:.2f} ms, puissance {10*np.log10(power):.2f} dB")

    if 'spectrogram' in results:
        logger.info(f"\nSpectrogramme: {results['spectrogram']['shape']}")

    logger.info("\nTest terminé")


if __name__ == "__main__":
    test_spectral_analysis()
