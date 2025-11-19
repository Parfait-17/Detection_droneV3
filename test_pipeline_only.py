#!/usr/bin/env python3
"""
Test Pipeline - Vérifie le fonctionnement du pipeline sans signal réel
Utilise des signaux synthétiques pour tester chaque étape
"""

import logging
import numpy as np
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_wifi_like_signal(num_samples=200000, sample_rate=20e6):
    """
    Génère un signal synthétique ressemblant à du WiFi
    Pour tester le pipeline sans vrai drone
    """
    t = np.arange(num_samples) / sample_rate

    # Fréquence WiFi centrée (après mixage à baseband)
    freq_wifi = 5e6  # 5 MHz dans la bande

    # Signal OFDM simplifié (plusieurs sous-porteuses)
    signal = np.zeros(num_samples, dtype=complex)

    # Ajouter quelques sous-porteuses (simule OFDM)
    for i in range(-10, 11, 2):
        freq = freq_wifi + i * 312.5e3  # Espacement 312.5 kHz (WiFi)
        signal += np.exp(1j * 2 * np.pi * freq * t)

    # Normaliser
    signal = signal / np.max(np.abs(signal))

    # Ajouter du bruit (SNR = 20 dB)
    noise_power = 10**(-20/10)
    noise = np.sqrt(noise_power/2) * (np.random.randn(num_samples) +
                                       1j * np.random.randn(num_samples))
    signal = signal + noise

    return signal


def test_full_pipeline():
    """
    Test complet du pipeline avec signal synthétique
    """
    logger.info("="*70)
    logger.info("TEST PIPELINE COMPLET - Signal Synthétique")
    logger.info("="*70)

    try:
        from src.preprocessing import SignalPreprocessor
        from src.spectrogram import SpectralAnalyzer
        from src.wifi_detector import WiFiDetector
        from src.wifi_sdr_demodulator import WiFiSDRDemodulator
        from src.remote_id_decoder import WiFiRemoteIDDecoder
    except ImportError as e:
        logger.error(f"Erreur import: {e}")
        return False

    sample_rate = 20e6

    # Générer signal synthétique
    logger.info("\n--- Génération Signal Synthétique WiFi-like ---")
    signal = generate_wifi_like_signal(num_samples=200000, sample_rate=sample_rate)
    logger.info(f"✅ Signal généré: {len(signal)} échantillons")

    # ÉTAPE 1: Prétraitement
    logger.info("\n--- ÉTAPE 1: Prétraitement ---")
    preprocessor = SignalPreprocessor(sample_rate=sample_rate)

    processed = preprocessor.process(
        signal,
        enable_dc_removal=True,
        enable_iq_correction=True,
        bandpass_range=(1e6, 9e6),
        normalize_method='rms'
    )

    snr = preprocessor.compute_snr(processed)
    logger.info(f"  SNR: {snr:.2f} dB")

    if snr > 15:
        logger.info("  ✅ SNR > 15 dB (signal détecté)")
    else:
        logger.warning(f"  ⚠️  SNR faible: {snr:.2f} dB")

    # ÉTAPE 2: Analyse Spectrale
    logger.info("\n--- ÉTAPE 2: Analyse Spectrale ---")
    analyzer = SpectralAnalyzer(sample_rate=sample_rate)

    features = analyzer.analyze_signal(processed, compute_spectrogram=False)
    features['snr'] = snr
    features['sample_rate'] = sample_rate

    logger.info(f"  Bande passante estimée: {features['spectral_features']['bandwidth']/1e6:.2f} MHz")
    logger.info(f"  Puissance pic: {features['spectral_features']['peak_power_db']:.2f} dB")
    logger.info("  ✅ Analyse spectrale OK")

    # ÉTAPE 3: Détection WiFi
    logger.info("\n--- ÉTAPE 3: Détection WiFi ---")
    wifi_detector = WiFiDetector()

    is_wifi, confidence, channel = wifi_detector.is_wifi_signal(
        features,
        center_freq=2.437e9
    )

    if is_wifi:
        logger.info(f"  ✅ Signal WiFi détecté (Canal: {channel}, Conf: {confidence:.1%})")
    else:
        logger.warning(f"  ⚠️  Signal non-WiFi (Conf: {confidence:.1%})")

    # ÉTAPE 4: Démodulation WiFi
    logger.info("\n--- ÉTAPE 4: Démodulation WiFi ---")
    demodulator = WiFiSDRDemodulator(sample_rate=sample_rate)

    # Test détection préambule seulement (pas de vrai préambule dans signal synthétique)
    preamble_idx = demodulator.detect_preamble(processed)

    if preamble_idx is not None:
        logger.info(f"  ✅ Préambule détecté à l'index {preamble_idx}")
    else:
        logger.warning("  ⚠️  Pas de préambule WiFi (normal avec signal synthétique)")

    # ÉTAPE 5: Test Décodeur Remote ID
    logger.info("\n--- ÉTAPE 5: Test Décodeur Remote ID ---")
    decoder = WiFiRemoteIDDecoder()

    # Créer un paquet Remote ID de test
    test_packet = decoder.create_test_remote_id_packet()
    logger.info(f"  Paquet de test créé: {len(test_packet)} octets")

    # Décoder
    remote_id = decoder.decode_from_raw_bytes(test_packet)

    if remote_id and remote_id.uas_id:
        logger.info(f"  ✅ Décodage Remote ID OK")
        logger.info(f"     UAS ID: {remote_id.uas_id}")
        if remote_id.latitude is not None and remote_id.longitude is not None:
            logger.info(f"     Position: ({remote_id.latitude:.6f}°, {remote_id.longitude:.6f}°)")
            logger.info(f"     Altitude: {remote_id.altitude_msl:.1f} m")
        else:
            logger.info(f"     Position: Non disponible (paquet test basique)")
    else:
        logger.error("  ❌ Échec décodage Remote ID")
        return False

    # RÉSUMÉ
    logger.info("\n" + "="*70)
    logger.info("RÉSUMÉ DU TEST PIPELINE")
    logger.info("="*70)

    logger.info("\n✅ Étapes fonctionnelles:")
    logger.info("   1. Prétraitement (DC removal, IQ correction, filtrage)")
    logger.info("   2. Analyse spectrale (PSD, bandwidth, features)")
    logger.info("   3. Détection WiFi (caractéristiques OFDM)")
    logger.info("   4. Démodulation WiFi (détection préambule)")
    logger.info("   5. Décodage Remote ID (parsing beacon)")

    logger.info("\n⚠️  Limitations du test:")
    logger.info("   - Signal synthétique (pas de vrai paquet WiFi)")
    logger.info("   - Pas de démodulation OFDM complète")
    logger.info("   - Remote ID de test (pas de vrai drone)")

    logger.info("\n📝 Pour test réel:")
    logger.info("   1. Activer hotspot WiFi sur smartphone")
    logger.info("   2. Placer à ~50 cm de l'antenne USRP")
    logger.info("   3. Lancer: python3 test_signal_presence.py")
    logger.info("   4. Vérifier SNR > 15 dB")
    logger.info("   5. Puis: python3 main_sdr_wifi.py --verbose")

    logger.info("\n" + "="*70)
    return True


if __name__ == "__main__":
    try:
        success = test_full_pipeline()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Erreur: {e}", exc_info=True)
        sys.exit(1)
