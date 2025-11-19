#!/usr/bin/env python3
"""
Moniteur MQTT - Affiche tous les messages de détection en temps réel
"""

import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def on_connect(client, userdata, flags, rc):
    """Callback connexion"""
    if rc == 0:
        logger.info("="*70)
        logger.info("📡 MONITEUR MQTT ACTIF")
        logger.info("="*70)
        logger.info("En attente de messages...\n")

        # S'abonner à tous les topics drone
        client.subscribe("drone/#")
        client.subscribe("system/#")
        logger.info("✅ Abonné aux topics: drone/# et system/#\n")
    else:
        logger.error(f"❌ Échec connexion MQTT (code: {rc})")


def on_message(client, userdata, msg):
    """Callback réception message"""
    topic = msg.topic
    timestamp = datetime.now().strftime("%H:%M:%S")

    try:
        payload = json.loads(msg.payload.decode())
        payload_str = json.dumps(payload, indent=2, ensure_ascii=False)
    except:
        payload_str = msg.payload.decode()

    # Affichage selon le topic
    if topic == "system/health":
        # Heartbeat - affichage compact
        logger.info(f"[{timestamp}] 💓 Heartbeat: {payload.get('status', 'unknown')}")

    elif topic == "drone/detection":
        # DÉTECTION REMOTE ID - affichage détaillé
        logger.info("\n" + "="*70)
        logger.info(f"🎯 REMOTE ID DÉTECTÉ [{timestamp}]")
        logger.info("="*70)

        # Extraire infos importantes
        remote_id = payload.get('remote_id', {})
        rf_features = payload.get('rf_features', {})

        logger.info(f"\n📡 Radio:")
        logger.info(f"   Fréquence: {payload.get('center_frequency_mhz', 'N/A')} MHz")
        logger.info(f"   SNR: {rf_features.get('snr', 'N/A')} dB")
        logger.info(f"   Bande: {rf_features.get('bandwidth_mhz', 'N/A')} MHz")

        logger.info(f"\n🆔 Remote ID:")
        logger.info(f"   UAS ID: {remote_id.get('uas_id', 'N/A')}")
        logger.info(f"   Type: {remote_id.get('uas_id_type', 'N/A')}")

        if remote_id.get('latitude') and remote_id.get('longitude'):
            logger.info(f"\n📍 Position Drone:")
            logger.info(f"   Lat/Lon: {remote_id['latitude']:.6f}°, {remote_id['longitude']:.6f}°")
            logger.info(f"   Altitude: {remote_id.get('altitude_msl', 'N/A')} m MSL")
            logger.info(f"   Hauteur: {remote_id.get('height', 'N/A')} m AGL")

        if remote_id.get('speed') is not None:
            logger.info(f"\n🚁 Mouvement:")
            logger.info(f"   Vitesse: {remote_id['speed']:.1f} m/s ({remote_id['speed']*3.6:.1f} km/h)")
            logger.info(f"   Direction: {remote_id.get('direction', 'N/A')}°")

        logger.info("\n" + "="*70 + "\n")

    elif topic == "drone/position":
        # Position update
        logger.info(f"\n[{timestamp}] 📍 Position Update:")
        logger.info(f"   Lat/Lon: {payload.get('latitude', 'N/A')}, {payload.get('longitude', 'N/A')}")
        logger.info(f"   Altitude: {payload.get('altitude_msl', 'N/A')} m")

    elif topic == "drone/alert":
        # Alerte
        logger.info("\n" + "!"*70)
        logger.info(f"⚠️  ALERTE [{timestamp}]")
        logger.info("!"*70)
        logger.info(f"   Niveau: {payload.get('threat_level', 'N/A')}")
        logger.info(f"   Raison: {payload.get('reason', 'N/A')}")
        logger.info("!"*70 + "\n")

    else:
        # Autre topic
        logger.info(f"\n[{timestamp}] Topic: {topic}")
        logger.info(payload_str)


def main():
    """Lance le moniteur MQTT"""
    # Configuration
    broker_host = "localhost"
    broker_port = 1883

    # Client MQTT
    client = mqtt.Client(client_id="mqtt_monitor")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        logger.info(f"Connexion au broker MQTT {broker_host}:{broker_port}...")
        client.connect(broker_host, broker_port, 60)

        # Boucle d'écoute
        client.loop_forever()

    except KeyboardInterrupt:
        logger.info("\n\nArrêt du moniteur...")
        client.disconnect()

    except Exception as e:
        logger.error(f"Erreur: {e}")


if __name__ == "__main__":
    main()
