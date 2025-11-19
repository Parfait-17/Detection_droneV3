"""
MODULE 6: Fusion de Données (data_fusion.py)
Fusion des résultats de détection, classification et Remote ID
"""

import numpy as np
from typing import Dict, Optional, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFusion:
    """
    Classe pour la fusion de données multi-sources:
    - Détection RF (spectrale)
    - Classification (brand/model)
    - Remote ID (position, vitesse, opérateur)
    """

    # Zones restreintes (exemple: coordonnées Burkina Faso)
    RESTRICTED_ZONES = [
        {
            'name': 'Zone militaire exemple',
            'center_lat': 12.3714,
            'center_lon': -1.5197,
            'radius_km': 5.0
        },
        {
            'name': 'Aéroport Ouagadougou',
            'center_lat': 12.3532,
            'center_lon': -1.5124,
            'radius_km': 10.0
        }
    ]

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialise le module de fusion de données
        """
        logger.info("Module de fusion de données initialisé")
        df_cfg = (config or {}).get('data_fusion', {})
        self.restricted_zones = df_cfg.get('restricted_zones', self.RESTRICTED_ZONES)
        ta = df_cfg.get('threat_assessment', {})
        # Support both naming schemes from config.yaml
        alt_limit = ta.get('altitude_agl_limit_m', ta.get('high_altitude_m', 120))
        spd_limit = ta.get('speed_limit_mps', ta.get('high_speed_ms', 20))
        op_dist_limit = ta.get('operator_distance_limit_m', ta.get('max_operator_distance_m', 5000))
        self.threat_thresholds = {
            'altitude_agl_limit_m': alt_limit,
            'speed_limit_mps': spd_limit,
            'operator_distance_limit_m': op_dist_limit
        }

    def fuse_detection_data(self,
                          detection_features: Dict,
                          classification_result: Dict,
                          remote_id_data: Optional[Dict] = None,
                          center_freq: float = 2.437e9) -> Dict:
        """
        Fusionne toutes les données de détection

        Args:
            detection_features: Features de détection RF
            classification_result: Résultat de classification
            remote_id_data: Données Remote ID (optionnel)
            center_freq: Fréquence centrale de détection

        Returns:
            Dictionnaire fusionné avec toutes les informations
        """
        logger.info("Fusion des données de détection")

        # Structure de base
        fusion_result = {
            'timestamp': datetime.now().isoformat(),
            'timestamp_unix': datetime.now().timestamp(),
            'detection': {},
            'classification': {},
            'remote_id': {},
            'threat_assessment': {},
            'metadata': {}
        }

        # === SECTION DETECTION ===
        spectral = detection_features.get('spectral_features', {})
        temporal = detection_features.get('temporal_features', {})

        fusion_result['detection'] = {
            'frequency': float(center_freq),
            'frequency_mhz': float(center_freq / 1e6),
            'bandwidth': float(spectral.get('bandwidth', 0)),
            'bandwidth_mhz': float(spectral.get('bandwidth', 0) / 1e6),
            'snr': float(detection_features.get('snr', 0)),
            'rssi_dbm': self._estimate_rssi(
                spectral.get('peak_power_db', -100),
                detection_features.get('snr', 0)
            ),
            'peak_power_db': float(spectral.get('peak_power_db', -100)),
            'signal_quality': self._assess_signal_quality(detection_features),
            'duration_ms': float(detection_features.get('duration', 0) * 1000)
        }

        # Informations sur les rafales
        bursts = detection_features.get('bursts', {})
        if bursts.get('count', 0) > 0:
            bursts_list = bursts.get('bursts_list', [])
            if bursts_list:
                intervals = self._compute_burst_intervals(
                    bursts_list,
                    detection_features.get('sample_rate', 25e6)
                )

                fusion_result['detection']['burst_info'] = {
                    'count': bursts['count'],
                    'avg_period_ms': float(np.mean(intervals) * 1000) if intervals else 0,
                    'std_period_ms': float(np.std(intervals) * 1000) if len(intervals) > 1 else 0
                }

        # === SECTION CLASSIFICATION ===
        fusion_result['classification'] = {
            'brand': classification_result.get('brand', 'Unknown'),
            'model': classification_result.get('model', 'Unknown'),
            'protocol': classification_result.get('protocol', 'Unknown'),
            'confidence': float(classification_result.get('confidence', 0)),
            'method': classification_result.get('method', 'unknown'),
            'is_valid': classification_result.get('is_valid', False)
        }

        # Top prédictions si disponibles
        if classification_result.get('top_predictions'):
            fusion_result['classification']['top_predictions'] = [
                {'model': m, 'confidence': float(c)}
                for m, c in classification_result['top_predictions']
            ]

        # === SECTION REMOTE ID ===
        if remote_id_data:
            # Position du drone
            position = remote_id_data.get('position', {})
            fusion_result['remote_id']['uas_id'] = remote_id_data.get('uas_id')
            fusion_result['remote_id']['uas_id_type'] = remote_id_data.get('uas_id_type')

            if position.get('latitude') and position.get('longitude'):
                fusion_result['remote_id']['position'] = {
                    'latitude': float(position['latitude']),
                    'longitude': float(position['longitude']),
                    'altitude_msl': float(position.get('altitude_msl', 0)),
                    'altitude_agl': float(position.get('altitude_agl', 0)),
                    'height': float(position.get('height', 0))
                }

            # Vélocité
            velocity = remote_id_data.get('velocity', {})
            if velocity.get('speed') is not None:
                fusion_result['remote_id']['velocity'] = {
                    'speed': float(velocity['speed']),
                    'speed_kmh': float(velocity['speed'] * 3.6),
                    'direction': float(velocity.get('direction', 0)),
                    'vertical_speed': float(velocity.get('vertical_speed', 0))
                }

            # Opérateur
            operator = remote_id_data.get('operator', {})
            if operator.get('latitude') and operator.get('longitude'):
                fusion_result['remote_id']['operator'] = {
                    'latitude': float(operator['latitude']),
                    'longitude': float(operator['longitude']),
                    'altitude': float(operator.get('altitude', 0)),
                    'id': operator.get('id')
                }

                # Calcul de la distance drone-opérateur
                drone_pos = fusion_result['remote_id']['position']
                op_pos = fusion_result['remote_id']['operator']

                distance = self._calculate_distance(
                    drone_pos['latitude'], drone_pos['longitude'],
                    op_pos['latitude'], op_pos['longitude']
                )

                fusion_result['remote_id']['operator']['distance_to_uas_m'] = float(distance)

            fusion_result['remote_id']['status'] = remote_id_data.get('status')

        # === SECTION THREAT ASSESSMENT ===
        threat_level, threat_reasons = self._assess_threat(
            fusion_result['remote_id'],
            fusion_result['classification']
        )

        fusion_result['threat_assessment'] = {
            'level': threat_level,
            'reasons': threat_reasons,
            'in_restricted_zone': self._check_restricted_zone(
                fusion_result['remote_id'].get('position')
            )
        }

        # === METADATA ===
        fusion_result['metadata'] = {
            'has_remote_id': bool(remote_id_data),
            'has_position': bool(fusion_result['remote_id'].get('position')),
            'has_operator_info': bool(fusion_result['remote_id'].get('operator')),
            'detection_confidence': float(classification_result.get('confidence', 0)),
            'overall_quality': self._compute_overall_quality(fusion_result)
        }

        logger.info(f"Fusion complète: {fusion_result['classification']['brand']} "
                   f"{fusion_result['classification']['model']}, "
                   f"Menace: {threat_level}")

        return fusion_result

    def _estimate_rssi(self, peak_power_db: float, snr: float) -> float:
        """
        Estime le RSSI (Received Signal Strength Indicator)

        Args:
            peak_power_db: Puissance de crête (dB)
            snr: SNR (dB)

        Returns:
            RSSI estimé (dBm)
        """
        # Estimation simplifiée: RSSI ≈ puissance - gain + pertes
        # Valeur typique pour récepteur SDR
        noise_floor = -90  # dBm (typique pour SDR)
        rssi = noise_floor + snr

        return float(rssi)

    def _assess_signal_quality(self, features: Dict) -> str:
        """
        Évalue la qualité du signal détecté

        Args:
            features: Features de détection

        Returns:
            'excellent', 'good', 'fair', 'poor'
        """
        snr = features.get('snr', 0)

        if snr >= 20:
            return 'excellent'
        elif snr >= 15:
            return 'good'
        elif snr >= 10:
            return 'fair'
        else:
            return 'poor'

    def _compute_burst_intervals(self, bursts_list: list, sample_rate: float) -> list:
        """
        Calcule les intervalles entre rafales

        Args:
            bursts_list: Liste des rafales [(start, end, duration, power), ...]
            sample_rate: Taux d'échantillonnage

        Returns:
            Liste des intervalles (secondes)
        """
        intervals = []

        for i in range(1, len(bursts_list)):
            prev_end = bursts_list[i-1][1]
            curr_start = bursts_list[i][0]
            interval = (curr_start - prev_end) / sample_rate
            intervals.append(interval)

        return intervals

    def _calculate_distance(self, lat1: float, lon1: float,
                          lat2: float, lon2: float) -> float:
        """
        Calcule la distance entre deux points GPS (formule haversine)

        Args:
            lat1, lon1: Coordonnées point 1 (degrés)
            lat2, lon2: Coordonnées point 2 (degrés)

        Returns:
            Distance en mètres
        """
        R = 6371000  # Rayon de la Terre en mètres

        # Conversion en radians
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)

        # Formule haversine
        a = (np.sin(dlat/2)**2 +
             np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

        distance = R * c

        return distance

    def _assess_threat(self, remote_id: Dict, classification: Dict) -> tuple:
        """
        Évalue le niveau de menace

        Args:
            remote_id: Données Remote ID
            classification: Résultat de classification

        Returns:
            Tuple (level, reasons) où level = 'LOW'|'MEDIUM'|'HIGH'
        """
        reasons = []
        score = 0

        # Pas de Remote ID = menace plus élevée
        if not remote_id:
            score += 20
            reasons.append("Aucune donnée Remote ID")
        else:
            # Remote ID présent = bon signe
            if remote_id.get('uas_id'):
                score -= 10
                reasons.append("Remote ID disponible")

        # Position dans zone restreinte
        position = remote_id.get('position')
        if position and self._check_restricted_zone(position):
            score += 50
            reasons.append("Drone dans zone restreinte")

        # Altitude élevée
        if position and position.get('altitude_agl', 0) > self.threat_thresholds.get('altitude_agl_limit_m', 120):
            score += 20
            reasons.append(f"Altitude élevée ({position['altitude_agl']:.0f}m AGL)")

        # Vitesse élevée
        velocity = remote_id.get('velocity', {})
        if velocity.get('speed', 0) > self.threat_thresholds.get('speed_limit_mps', 20):
            score += 10
            reasons.append(f"Vitesse élevée ({velocity['speed']:.1f} m/s)")

        # Distance opérateur élevée
        operator = remote_id.get('operator', {})
        if operator.get('distance_to_uas_m', 0) > self.threat_thresholds.get('operator_distance_limit_m', 5000):
            score += 15
            reasons.append("Distance opérateur > 5km")

        # Classification non valide
        if not classification.get('is_valid'):
            score += 10
            reasons.append("Classification incertaine")

        # Détermination du niveau
        if score >= 50:
            level = 'HIGH'
        elif score >= 20:
            level = 'MEDIUM'
        else:
            level = 'LOW'

        if not reasons:
            reasons.append("Aucune anomalie détectée")

        return level, reasons

    def _check_restricted_zone(self, position: Optional[Dict]) -> bool:
        """
        Vérifie si une position est dans une zone restreinte

        Args:
            position: Dictionnaire avec latitude, longitude

        Returns:
            True si dans zone restreinte
        """
        if not position or not position.get('latitude') or not position.get('longitude'):
            return False

        lat = position['latitude']
        lon = position['longitude']

        for zone in self.restricted_zones:
            distance = self._calculate_distance(
                lat, lon,
                zone['center_lat'], zone['center_lon']
            )

            if distance <= zone['radius_km'] * 1000:
                logger.warning(f"Drone dans zone restreinte: {zone['name']}")
                return True

        return False

    def _compute_overall_quality(self, fusion_result: Dict) -> float:
        """
        Calcule la qualité globale de la détection (0-1)

        Args:
            fusion_result: Résultat de fusion

        Returns:
            Score de qualité (0-1)
        """
        quality = 0.0

        # Confiance de classification (40%)
        quality += fusion_result['classification']['confidence'] * 0.4

        # SNR (30%)
        snr = fusion_result['detection']['snr']
        snr_score = min(1.0, max(0, (snr - 5) / 20))  # Normalisé entre 5 et 25 dB
        quality += snr_score * 0.3

        # Présence Remote ID (20%)
        if fusion_result['metadata']['has_remote_id']:
            quality += 0.2

        # Validation (10%)
        if fusion_result['classification']['is_valid']:
            quality += 0.1

        return float(quality)


def test_data_fusion():
    """
    Fonction de test pour la fusion de données
    """
    logger.info("=== Test de la fusion de données ===")

    fusion = DataFusion()

    # Données de test
    detection_features = {
        'spectral_features': {
            'bandwidth': 15.2e6,
            'center_frequency': 2.437e9,
            'peak_power_db': -52.3,
            'spectral_centroid': 2.437e9,
            'spectral_spread': 4.6e6,
            'spectral_flatness': 0.42,
            'mean_psd_db': -65.1,
            'max_psd_db': -50.2,
            'std_psd_db': 7.8
        },
        'temporal_features': {
            'mean_amplitude': 0.52,
            'std_amplitude': 0.12,
            'crest_factor': 2.02,
            'kurtosis': 2.95
        },
        'bursts': {
            'count': 5,
            'bursts_list': [
                (0, 10000, 0.0004, 0.52),
                (160000, 170000, 0.0004, 0.51),
                (320000, 330000, 0.0004, 0.53)
            ]
        },
        'snr': 18.5,
        'sample_rate': 25e6,
        'duration': 0.01
    }

    classification_result = {
        'brand': 'DJI',
        'model': 'Mavic 3',
        'protocol': 'OcuSync 3.0',
        'confidence': 0.94,
        'method': 'hybrid',
        'is_valid': True,
        'top_predictions': [
            ('Mavic 3', 0.94),
            ('Air 2S', 0.04),
            ('Mini 3 Pro', 0.02)
        ]
    }

    remote_id_data = {
        'uas_id': '1FFJX8K3QH000001',
        'uas_id_type': 'Serial Number',
        'position': {
            'latitude': 12.3585,
            'longitude': -1.5352,
            'altitude_msl': 120.5,
            'altitude_agl': 45.2,
            'height': 45.2
        },
        'velocity': {
            'speed': 12.3,
            'direction': 87,
            'vertical_speed': 2.5
        },
        'operator': {
            'latitude': 12.3580,
            'longitude': -1.5348,
            'altitude': 280.0,
            'id': 'BFA-OP-12345'
        },
        'status': 'Airborne'
    }

    # Test de fusion
    result = fusion.fuse_detection_data(
        detection_features,
        classification_result,
        remote_id_data,
        center_freq=2.437e9
    )

    # Affichage du résultat
    import json
    print("\n" + "="*70)
    print("RÉSULTAT DE LA FUSION DE DONNÉES")
    print("="*70)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("="*70)

    logger.info("\nTest terminé")


if __name__ == "__main__":
    test_data_fusion()
