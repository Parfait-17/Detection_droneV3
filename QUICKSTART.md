# Guide de Démarrage Rapide

## Installation en 5 minutes

### 1. Prérequis système

```bash
# Installation UHD et dépendances
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev libuhd-dev uhd-host python3-uhd
sudo uhd_images_downloader
```

### 2. Installation Python

```bash
# Environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Dépendances
pip install -r requirements.txt
```

### 3. Test du matériel

```bash
# Vérifier que l'USRP B210mini est détecté
uhd_find_devices

# Test de communication
uhd_usrp_probe
```

### 4. Configuration MQTT (optionnel)

```bash
# Installer Mosquitto
sudo apt-get install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

### 5. Lancement

```bash
# Mode normal
python3 main.py

# Mode debug
python3 main.py --verbose
```

## Test des modules individuels

```bash
# Activer l'environnement
source venv/bin/activate

# Tester chaque module
python3 -m src.remote_id_decoder  # Test Remote ID
python3 -m src.classifier         # Test classification
python3 -m src.data_fusion        # Test fusion
python3 -m src.mqtt_publisher     # Test MQTT
```

## Configuration minimale

Éditez `config/config.yaml` :

```yaml
acquisition:
  rx_gain: 40.0  # Ajuster selon votre environnement

mqtt:
  broker_host: "localhost"  # Votre broker MQTT

system:
  detection_threshold_snr: 10.0  # Seuil de détection
```

## Résolution de problèmes

### Erreur: "No UHD devices found"
```bash
# Vérifier les permissions USB
sudo usermod -a -G usb $USER
# Redémarrer la session
```

### Erreur: "Connection refused" (MQTT)
```bash
# Vérifier que Mosquitto fonctionne
sudo systemctl status mosquitto
sudo systemctl start mosquitto
```

### SNR trop faible
- Augmenter `rx_gain` dans config.yaml (max 76 dB pour B210)
- Vérifier l'antenne
- Se rapprocher d'un drone en vol

## Prochaines étapes

1. **Entraîner le modèle ML** avec vos propres données
2. **Configurer les zones restreintes** dans config.yaml
3. **Adapter les seuils** de détection selon votre environnement
4. **Visualiser les détections** via un client MQTT (ex: MQTT Explorer)

## Support

- Logs: `drone_detection.log`
- Mode verbose: `python3 main.py --verbose`
- Test unitaires: `pytest tests/`
