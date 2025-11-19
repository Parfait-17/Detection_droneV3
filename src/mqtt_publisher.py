"""
MODULE 7: Publication MQTT (mqtt_publisher.py)
Publication des détections vers un broker MQTT
"""

import paho.mqtt.client as mqtt
import json
import logging
from typing import Dict, Optional, Callable
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MQTTPublisher:
    """
    Classe pour publier les détections de drones vers un broker MQTT
    """

    # Topics MQTT par défaut
    TOPICS = {
        'detection': 'drone/detection',
        'position': 'drone/position',
        'classification': 'drone/classification',
        'alert': 'drone/alert',
        'health': 'system/health'
    }

    # QoS levels
    QOS_DETECTION = 1  # At least once
    QOS_POSITION = 1   # At least once
    QOS_ALERT = 2      # Exactly once
    QOS_HEALTH = 0     # At most once

    def __init__(self,
                 broker_host: str = "localhost",
                 broker_port: int = 1883,
                 client_id: str = "drone_detector",
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 use_tls: bool = False,
                 topics: Optional[Dict] = None,
                 qos: Optional[Dict] = None,
                 retain: bool = False):
        """
        Initialise le publisher MQTT

        Args:
            broker_host: Adresse du broker MQTT
            broker_port: Port du broker (1883 standard, 8883 pour TLS)
            client_id: ID du client MQTT
            username: Nom d'utilisateur (optionnel)
            password: Mot de passe (optionnel)
            use_tls: Utiliser TLS/SSL
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.topics = topics or self.TOPICS
        self.qos = qos or {
            'detection': 1,
            'position': 1,
            'alert': 2,
            'health': 0
        }
        self.retain = retain

        # Création du client MQTT
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

        # Configuration des callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish

        # État de connexion
        self.connected = False
        self.last_publish_time = None

        logger.info(f"MQTT Publisher initialisé: {broker_host}:{broker_port}")

    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback appelé lors de la connexion au broker
        """
        if rc == 0:
            self.connected = True
            logger.info(f"Connecté au broker MQTT: {self.broker_host}:{self.broker_port}")

            # Publication d'un message de statut
            self._publish_health_status("connected")
        else:
            self.connected = False
            logger.error(f"Échec de connexion au broker MQTT, code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """
        Callback appelé lors de la déconnexion du broker
        """
        self.connected = False
        if rc != 0:
            logger.warning(f"Déconnexion inattendue du broker MQTT, code: {rc}")
        else:
            logger.info("Déconnecté du broker MQTT")

    def _on_publish(self, client, userdata, mid):
        """
        Callback appelé après publication d'un message
        """
        logger.debug(f"Message publié, ID: {mid}")
        self.last_publish_time = time.time()

    def connect(self) -> bool:
        """
        Connecte au broker MQTT

        Returns:
            True si la connexion réussit
        """
        try:
            # Configuration de l'authentification
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            # Configuration TLS
            if self.use_tls:
                self.client.tls_set()

            # Connexion
            logger.info(f"Connexion au broker MQTT {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)

            # Démarrage de la boucle réseau (non-bloquante)
            self.client.loop_start()

            # Attente de la connexion (max 5 secondes)
            timeout = 5
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            return self.connected

        except Exception as e:
            logger.error(f"Erreur lors de la connexion MQTT: {e}")
            return False

    def disconnect(self):
        """
        Déconnecte du broker MQTT
        """
        if self.connected:
            # Basculer l'état avant de publier pour refléter correctement 'connected: false'
            self.connected = False
            self._publish_health_status("disconnected")
            time.sleep(0.5)  # Laisser le temps au message de partir

        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Déconnexion MQTT effectuée")

    def publish_detection(self, detection_data: Dict) -> bool:
        """
        Publie une détection complète

        Args:
            detection_data: Données de détection fusionnées

        Returns:
            True si la publication réussit
        """
        if not self.connected:
            logger.warning("Non connecté au broker MQTT")
            return False

        try:
            # Publication de la détection complète
            topic = self.topics['detection']
            payload = json.dumps(detection_data, ensure_ascii=False)

            result = self.client.publish(topic, payload, qos=self.qos.get('detection', 1), retain=self.retain)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Détection publiée sur {topic}")

                # Publication des données spécifiques
                self._publish_position(detection_data)
                self._publish_classification(detection_data)

                # Alertes si menace élevée
                threat_level = detection_data.get('threat_assessment', {}).get('level')
                if threat_level in ['HIGH', 'MEDIUM']:
                    self._publish_alert(detection_data)

                return True
            else:
                logger.error(f"Échec de publication, code: {result.rc}")
                return False

        except Exception as e:
            logger.error(f"Erreur lors de la publication: {e}")
            return False

    def _publish_position(self, detection_data: Dict):
        """
        Publie les données de position

        Args:
            detection_data: Données de détection
        """
        remote_id = detection_data.get('remote_id', {})
        position = remote_id.get('position')

        if not position:
            return

        position_data = {
            'timestamp': detection_data['timestamp'],
            'uas_id': remote_id.get('uas_id'),
            'latitude': position.get('latitude'),
            'longitude': position.get('longitude'),
            'altitude_msl': position.get('altitude_msl'),
            'altitude_agl': position.get('altitude_agl'),
            'velocity': remote_id.get('velocity', {}),
            'threat_level': detection_data.get('threat_assessment', {}).get('level')
        }

        topic = self.topics['position']
        payload = json.dumps(position_data, ensure_ascii=False)

        self.client.publish(topic, payload, qos=self.qos.get('position', 1), retain=self.retain)
        logger.debug(f"Position publiée sur {topic}")

    def _publish_classification(self, detection_data: Dict):
        """
        Publie les données de classification

        Args:
            detection_data: Données de détection
        """
        classification = detection_data.get('classification', {})

        classification_data = {
            'timestamp': detection_data['timestamp'],
            'brand': classification.get('brand'),
            'model': classification.get('model'),
            'protocol': classification.get('protocol'),
            'confidence': classification.get('confidence'),
            'method': classification.get('method'),
            'top_predictions': classification.get('top_predictions', [])
        }

        topic = self.topics['classification']
        payload = json.dumps(classification_data, ensure_ascii=False)

        self.client.publish(topic, payload, qos=self.qos.get('detection', 1), retain=self.retain)
        logger.debug(f"Classification publiée sur {topic}")

    def _publish_alert(self, detection_data: Dict):
        """
        Publie une alerte

        Args:
            detection_data: Données de détection
        """
        threat = detection_data.get('threat_assessment', {})
        remote_id = detection_data.get('remote_id', {})
        classification = detection_data.get('classification', {})

        alert_data = {
            'timestamp': detection_data['timestamp'],
            'alert_level': threat.get('level'),
            'reasons': threat.get('reasons', []),
            'in_restricted_zone': threat.get('in_restricted_zone', False),
            'drone_info': {
                'brand': classification.get('brand'),
                'model': classification.get('model'),
                'uas_id': remote_id.get('uas_id')
            },
            'position': remote_id.get('position'),
            'detection_frequency_mhz': detection_data.get('detection', {}).get('frequency_mhz')
        }

        topic = self.topics['alert']
        payload = json.dumps(alert_data, ensure_ascii=False)

        self.client.publish(topic, payload, qos=self.qos.get('alert', 2), retain=self.retain)
        logger.warning(f"ALERTE publiée: {threat.get('level')} - {', '.join(threat.get('reasons', []))}")

    def _publish_health_status(self, status: str):
        """
        Publie le statut de santé du système

        Args:
            status: Statut ('connected', 'disconnected', 'running', etc.)
        """
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'client_id': self.client_id,
            'connected': self.connected,
            'last_publish': self.last_publish_time
        }

        topic = self.topics['health']
        payload = json.dumps(health_data)

        self.client.publish(topic, payload, qos=self.qos.get('health', 0), retain=self.retain)
        logger.debug(f"Health status publié: {status}")

    def publish_heartbeat(self):
        """
        Publie un heartbeat pour indiquer que le système fonctionne
        """
        self._publish_health_status("running")

    def set_will(self):
        """
        Configure le Last Will and Testament (message en cas de déconnexion inattendue)
        """
        will_payload = json.dumps({
            'timestamp': datetime.now().isoformat(),
            'status': 'disconnected_unexpectedly',
            'client_id': self.client_id
        })

        self.client.will_set(
            self.topics['health'],
            will_payload,
            qos=self.qos.get('health', 0),
            retain=self.retain
        )

        logger.info("Last Will configuré")


def test_mqtt_publisher():
    """
    Fonction de test pour le publisher MQTT
    """
    logger.info("=== Test du publisher MQTT ===")

    # Configuration
    publisher = MQTTPublisher(
        broker_host="localhost",
        broker_port=1883,
        client_id="drone_detector_test"
    )

    # Configuration du Last Will
    publisher.set_will()

    # Connexion
    logger.info("\n--- Test de connexion ---")
    if publisher.connect():
        logger.info("✓ Connexion réussie")
    else:
        logger.error("✗ Connexion échouée")
        return

    time.sleep(1)

    # Données de test
    test_detection = {
        'timestamp': datetime.now().isoformat(),
        'timestamp_unix': datetime.now().timestamp(),
        'detection': {
            'frequency': 2437000000.0,
            'frequency_mhz': 2437.0,
            'bandwidth': 15200000.0,
            'bandwidth_mhz': 15.2,
            'snr': 18.5,
            'rssi_dbm': -65,
            'peak_power_db': -52.3,
            'signal_quality': 'good'
        },
        'classification': {
            'brand': 'DJI',
            'model': 'Mavic 3',
            'protocol': 'OcuSync 3.0',
            'confidence': 0.94,
            'method': 'hybrid',
            'is_valid': True
        },
        'remote_id': {
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
                'speed_kmh': 44.28,
                'direction': 87,
                'vertical_speed': 2.5
            },
            'operator': {
                'latitude': 12.3580,
                'longitude': -1.5348,
                'id': 'BFA-OP-12345'
            }
        },
        'threat_assessment': {
            'level': 'LOW',
            'reasons': ['Remote ID disponible'],
            'in_restricted_zone': False
        },
        'metadata': {
            'has_remote_id': True,
            'has_position': True,
            'overall_quality': 0.87
        }
    }

    # Test de publication
    logger.info("\n--- Test de publication ---")
    if publisher.publish_detection(test_detection):
        logger.info("✓ Publication réussie")
    else:
        logger.error("✗ Publication échouée")

    time.sleep(1)

    # Test heartbeat
    logger.info("\n--- Test heartbeat ---")
    publisher.publish_heartbeat()
    logger.info("✓ Heartbeat envoyé")

    time.sleep(1)

    # Simulation d'une alerte
    logger.info("\n--- Test alerte ---")
    test_detection['threat_assessment']['level'] = 'HIGH'
    test_detection['threat_assessment']['reasons'] = ['Drone dans zone restreinte', 'Altitude élevée']
    test_detection['threat_assessment']['in_restricted_zone'] = True

    if publisher.publish_detection(test_detection):
        logger.info("✓ Alerte publiée")

    time.sleep(1)

    # Déconnexion
    logger.info("\n--- Test de déconnexion ---")
    publisher.disconnect()
    logger.info("✓ Déconnexion effectuée")

    logger.info("\nTest terminé")


if __name__ == "__main__":
    test_mqtt_publisher()
