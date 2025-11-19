#!/usr/bin/env python3
"""
Test de Présence de Signal WiFi
Vérifie si l'USRP B210 détecte du WiFi 2.4 GHz
"""

import logging
import numpy as np
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_signal_strength():
    """
    Test la force du signal sur plusieurs canaux WiFi
    """
    logger.info("="*70)
    logger.info("TEST DE PRÉSENCE SIGNAL WiFi 2.4 GHz")
    logger.info("="*70)

    try:
        from src.uhd_acquisition import UHDAcquisition
        from src.preprocessing import SignalPreprocessor
    except ImportError as e:
        logger.error(f"Erreur import: {e}")
        return False

    # Canaux WiFi 2.4 GHz à scanner
    wifi_channels = {
        1: 2.412e9,
        6: 2.437e9,  # Canal par défaut
        11: 2.462e9,
    }

    # Initialiser USRP
    logger.info("\n--- Initialisation USRP B210 ---")
    usrp = UHDAcquisition(
        device_args="type=b200",
        sample_rate=20e6,
        rx_freq_2g4=2.437e9,
        rx_gain=50.0
    )

    if not usrp.initialize():
        logger.error("❌ USRP B210 non disponible")
        return False

    logger.info("✅ USRP B210 initialisé")

    preprocessor = SignalPreprocessor(sample_rate=20e6)

    # Scanner chaque canal
    results = []

    for channel, freq in wifi_channels.items():
        logger.info(f"\n--- Test Canal {channel} ({freq/1e9:.3f} GHz) ---")

        # Configurer la fréquence
        usrp.usrp.set_rx_freq(freq, 0)

        # Capturer
        samples = usrp.acquire_samples(num_samples=200000, channel=0)

        if samples is None:
            logger.warning(f"❌ Échec acquisition canal {channel}")
            continue

        # Prétraiter
        processed = preprocessor.process(
            samples,
            enable_dc_removal=True,
            enable_iq_correction=True,
            bandpass_range=(1e6, 9e6),  # < Nyquist (10 MHz pour 20 MS/s)
            normalize_method='rms'
        )

        # Calculer SNR
        snr = preprocessor.compute_snr(processed)

        # Calculer puissance moyenne
        power_dbm = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-12)

        logger.info(f"  SNR: {snr:.2f} dB")
        logger.info(f"  Puissance: {power_dbm:.2f} dBm")

        results.append({
            'channel': channel,
            'freq_ghz': freq / 1e9,
            'snr_db': snr,
            'power_dbm': power_dbm
        })

        # Verdict
        if snr > 15:
            logger.info(f"  ✅ SIGNAL FORT DÉTECTÉ (SNR > 15 dB)")
        elif snr > 5:
            logger.info(f"  ⚠️  Signal faible (SNR 5-15 dB)")
        else:
            logger.info(f"  ❌ Bruit uniquement (SNR < 5 dB)")

    # Fermer USRP
    usrp.close()

    # Résumé
    logger.info("\n" + "="*70)
    logger.info("RÉSUMÉ DU SCAN")
    logger.info("="*70)

    logger.info(f"\n{'Canal':<8} {'Fréquence':<15} {'SNR (dB)':<12} {'Puissance (dBm)':<18} {'Statut'}")
    logger.info("-" * 70)

    max_snr = -999
    best_channel = None

    for r in results:
        status = "✅ FORT" if r['snr_db'] > 15 else "⚠️  FAIBLE" if r['snr_db'] > 5 else "❌ BRUIT"
        logger.info(f"{r['channel']:<8} {r['freq_ghz']:.3f} GHz{'':<6} {r['snr_db']:>6.2f}{'':<6} {r['power_dbm']:>10.2f}{'':<8} {status}")

        if r['snr_db'] > max_snr:
            max_snr = r['snr_db']
            best_channel = r['channel']

    logger.info("\n" + "="*70)

    if max_snr > 15:
        logger.info(f"✅ Signal WiFi détecté sur canal {best_channel} (SNR: {max_snr:.2f} dB)")
        logger.info(f"\n📝 Recommandation: Utiliser canal {best_channel} dans config.yaml:")
        freq_best = wifi_channels[best_channel]
        logger.info(f"   rx_freq_2g4: {int(freq_best)}")
        return True
    elif max_snr > 5:
        logger.info(f"⚠️  Signal WiFi faible sur canal {best_channel} (SNR: {max_snr:.2f} dB)")
        logger.info("\n📝 Solutions:")
        logger.info("   1. Augmenter le gain: rx_gain: 60.0 ou 70.0")
        logger.info("   2. Rapprocher l'antenne du point d'accès WiFi")
        logger.info("   3. Réduire le seuil temporairement: detection_threshold_snr: 5.0")
        return False
    else:
        logger.info(f"❌ Aucun signal WiFi détecté (SNR max: {max_snr:.2f} dB)")
        logger.info("\n📝 Causes possibles:")
        logger.info("   1. Aucun WiFi actif dans l'environnement")
        logger.info("   2. Antenne mal connectée ou défectueuse")
        logger.info("   3. USRP B210 mal configuré")
        logger.info("   4. Distance trop grande du point d'accès WiFi")
        logger.info("\n📝 Tests à faire:")
        logger.info("   1. Vérifier connexion antenne sur port RX1")
        logger.info("   2. Activer un hotspot WiFi sur smartphone (proche de l'antenne)")
        logger.info("   3. Vérifier avec: uhd_fft -f 2.437e9 -s 20e6 -g 50")
        return False


if __name__ == "__main__":
    try:
        success = test_signal_strength()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nInterruption utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur: {e}", exc_info=True)
        sys.exit(1)
