#!/usr/bin/env python3
"""
Test du système sans USRP - Mode Simulation
Génère des signaux WiFi simulés pour tester le décodeur Remote ID
"""

import logging
import time
import numpy as np
from src.remote_id_decoder import WiFiRemoteIDDecoder, RemoteIDData
from src.mqtt_publisher import MQTTPublisher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def simulate_remote_id_data():
    """Simule des données Remote ID pour test"""
    return RemoteIDData(
        uas_id="SIM-DRONE-001",
        uas_id_type="Serial Number",
        latitude=12.3585,
        longitude=-1.5352,
        altitude_msl=150.0,
        height=45.0,
        speed=12.5,
        direction=87,
        timestamp=time.time(),
        operator_latitude=12.3580,
        operator_longitude=-1.5348,
        operator_id="BFA-OP-SIM-001",
        status="Airborne"
    )


def main():
    """Mode simulation sans USRP"""
    logger.info("="*70)
    logger.info("MODE SIMULATION - Test sans USRP B210")
    logger.info("="*70)
    
    # Initialiser MQTT
    logger.info("\nInitialisation MQTT...")
    mqtt = MQTTPublisher(
        broker_host='localhost',
        broker_port=1883,
        client_id='simulation_test'
    )
    
    if mqtt.connect():
        logger.info("✓ MQTT connecté")
    else:
        logger.warning("⚠ MQTT non disponible - Mode autonome")
    
    # Initialiser décodeur
    logger.info("Initialisation décodeur Remote ID...")
    decoder = WiFiRemoteIDDecoder()
    
    logger.info("\n🚀 Simulation démarrée - Génération de détections simulées\n")
    
    detection_count = 0
    
    try:
        while True:
            detection_count += 1
            
            # Simuler Remote ID
            remote_id = simulate_remote_id_data()
            
            # Varier légèrement la position
            remote_id.latitude += np.random.uniform(-0.001, 0.001)
            remote_id.longitude += np.random.uniform(-0.001, 0.001)
            remote_id.height += np.random.uniform(-5, 5)
            remote_id.speed += np.random.uniform(-2, 2)
            
            # Afficher détection
            logger.info("="*70)
            logger.info(f"🎯 DÉTECTION SIMULÉE #{detection_count}")
            logger.info("="*70)
            logger.info(f"\n🆔 Identifiant:")
            logger.info(f"   UAS ID: {remote_id.uas_id}")
            logger.info(f"   Type: {remote_id.uas_id_type}")
            logger.info(f"\n📍 Position Drone:")
            logger.info(f"   Latitude: {remote_id.latitude:.6f}°")
            logger.info(f"   Longitude: {remote_id.longitude:.6f}°")
            logger.info(f"   Altitude MSL: {remote_id.altitude_msl:.1f} m")
            logger.info(f"   Hauteur AGL: {remote_id.height:.1f} m")
            logger.info(f"\n🚁 Vélocité:")
            logger.info(f"   Vitesse: {remote_id.speed:.1f} m/s ({remote_id.speed*3.6:.1f} km/h)")
            logger.info(f"   Direction: {remote_id.direction}°")
            logger.info(f"\n👤 Opérateur:")
            logger.info(f"   ID: {remote_id.operator_id}")
            logger.info(f"   Position: ({remote_id.operator_latitude:.6f}°, {remote_id.operator_longitude:.6f}°)")
            logger.info("="*70 + "\n")
            
            # Publier MQTT
            if mqtt.connected:
                detection_data = {
                    'remote_id': remote_id.to_dict(),
                    'timestamp': time.time(),
                    'method': 'simulation',
                    'detection_number': detection_count
                }
                mqtt.publish_detection(detection_data)
            
            # Attendre 5 secondes
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("\n\nArrêt simulation...")
        if mqtt.connected:
            mqtt.disconnect()
        logger.info(f"✓ {detection_count} détections simulées")


if __name__ == "__main__":
    main()
