# Système de Détection et Identification de Drones

Système complet de détection RF, classification et décodage Remote ID pour drones, basé sur LibreSDR B210mini.

## 📋 Table des matières

- [Caractéristiques](#caractéristiques)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Modules](#modules)
- [Structure du projet](#structure-du-projet)

## ✨ Caractéristiques

- **Détection RF multi-bandes** : 2.4 GHz et 5.8 GHz simultanées
- **Décodage Remote ID** : Extraction des informations WiFi Beacon (ASTM F3411)
- **Évaluation de menace** : Détection de zones restreintes, altitudes anormales
- **Publication MQTT** : Streaming temps réel des détections
- **Traitement temps réel** : Pipeline optimisé pour détection continue

## 🏗️ Architecture

```
┌─────────────────────┐
│  LibreSDR B210mini  │  (Dual RX: 2.4 GHz + 5.8 GHz)
└──────────┬──────────┘
           │ USB 3.0
           ↓
┌─────────────────────────────────────────────────────┐
│  MODULE 1: Acquisition RF (uhd_acquisition.py)      │
│  • Taux: 25 MS/s                                    │
│  • Échantillons I/Q complexes                       │
└──────────┬──────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────┐
│  MODULE 2: Prétraitement (preprocessing.py)         │
│  • Suppression DC offset                            │
│  • Correction I/Q                                   │
│  • Filtrage passe-bande                             │
└──────────┬──────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────┐
│  MODULE 3: Analyse Spectrale (spectrogram.py)       │
│  • Spectrogramme (STFT)                             │
│  • Extraction de features (50 dimensions)           │
│  • Détection de rafales                             │
└──────────┬──────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────┐
│  MODULE 4B: Décodage Remote ID (remote_id_decoder.py)│
│  • Démodulation WiFi 802.11                         │
│  • Parsing Beacon Frames                            │
│  • Extraction position, vitesse, opérateur          │
└──────────┬──────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────┐
│  MODULE 5: Fusion de Données (data_fusion.py)       │
│  • Agrégation RF + Remote ID                        │
│  • Évaluation de menace (LOW/MEDIUM/HIGH)           │
│  • Vérification zones restreintes                   │
└──────────┬──────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────┐
│  MODULE 6: Publication MQTT (mqtt_publisher.py)     │
│  • Topics: drone/detection, drone/position, etc.    │
│  • QoS 1 (détections), QoS 2 (alertes)              │
└─────────────────────────────────────────────────────┘
```

## 🔧 Prérequis

### Matériel
- **LibreSDR B210mini** (Ettus Research USRP B210)
- **PC Linux** (Ubuntu 22.04 LTS recommandé) ou **Raspberry Pi 4/5**
- **Port USB 3.0** disponible
- **RAM** : Minimum 4 GB (8 GB recommandé)

### Logiciels
- **Python** : 3.10 ou supérieur
- **UHD** (USRP Hardware Driver) : 4.6 ou supérieur
- **Broker MQTT** : Mosquitto, HiveMQ, ou autre (optionnel)

## 📦 Installation

### 1. Installation des dépendances système

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    libuhd-dev \
    uhd-host \
    python3-uhd

# Téléchargement des images FPGA pour USRP
sudo uhd_images_downloader
```

### 2. Clonage du projet

```bash
git clone <url-du-repo>
cd drone_detection_projectV2
```

### 3. Installation des dépendances Python

```bash
# Création d'un environnement virtuel (recommandé)
python3 -m venv venv
source venv/bin/activate

# Installation des dépendances
pip install -r requirements.txt
```

### 4. Vérification de l'USRP

```bash
# Test de détection du périphérique
uhd_find_devices

# Test de communication
uhd_usrp_probe
```

### 5. Installation du broker MQTT (optionnel)

```bash
# Mosquitto
sudo apt-get install mosquitto mosquitto-clients

# Démarrage du service
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

## ⚙️ Configuration

Éditez le fichier `config/config.yaml` pour adapter le système :

```yaml
acquisition:
  device_args: "type=b200"
  sample_rate: 25000000
  rx_freq_2g4: 2437000000  # 2.437 GHz
  rx_gain: 40.0

mqtt:
  broker_host: "localhost"
  broker_port: 1883
  client_id: "drone_detector_001"

system:
  detection_threshold_snr: 10.0
```

## 🚀 Utilisation

### Mode normal

```bash
python3 main.py
```

### Mode verbose (debug)

```bash
python3 main.py --verbose
```

### Configuration personnalisée

```bash
python3 main.py --config /chemin/vers/config.yaml
```

### Arrêt du système

Appuyez sur `Ctrl+C` pour arrêter proprement le système.

## 📚 Modules

### MODULE 1: Acquisition RF ([uhd_acquisition.py](src/uhd_acquisition.py))
- Gère la communication avec le LibreSDR B210mini
- Acquisition dual-channel (2.4 GHz + 5.8 GHz)
- Mode continu ou par rafale

### MODULE 2: Prétraitement ([preprocessing.py](src/preprocessing.py))
- Correction DC offset
- Correction déséquilibres I/Q
- Filtrage passe-bande Butterworth
- Normalisation du signal

### MODULE 3: Analyse Spectrale ([spectrogram.py](src/spectrogram.py))
- Calcul du spectrogramme (STFT)
- Extraction de 50 features (temporelles + spectrales)
- Détection de rafales (burst detection)
- Estimation de bande passante

### MODULE 4B: Décodage Remote ID ([remote_id_decoder.py](src/remote_id_decoder.py))
- **PRIORITÉ** : Focus sur Remote ID
- Démodulation WiFi 802.11 (OFDM)
- Parsing IEEE Beacon Frames
- Extraction informations ASTM F3411:
  - UAS ID (identifiant drone)
  - Position GPS (lat, lon, altitude)
  - Vitesse et direction
  - Position opérateur

### MODULE 5: Fusion de Données ([data_fusion.py](src/data_fusion.py))
- Agrégation de toutes les sources
- Calcul RSSI, qualité signal
- Évaluation de menace (LOW/MEDIUM/HIGH)
- Vérification zones restreintes

### MODULE 6: Publication MQTT ([mqtt_publisher.py](src/mqtt_publisher.py))
- Publication temps réel vers broker MQTT
- Topics : `drone/detection`, `drone/position`, `drone/alert`, etc.
- QoS configurables
- Heartbeat système

## 📁 Structure du projet

```
drone_detection_projectV2/
├── src/                          # Code source
│   ├── __init__.py
│   ├── uhd_acquisition.py        # MODULE 1
│   ├── preprocessing.py          # MODULE 2
│   ├── spectrogram.py            # MODULE 3
│   ├── remote_id_decoder.py      # MODULE 4B (PRIORITÉ)
│   ├── data_fusion.py            # MODULE 5
│   └── mqtt_publisher.py         # MODULE 6
├── config/                       # Configuration
│   └── config.yaml
├── models/                       # Modèles ML (optionnel)
├── tests/                        # Tests unitaires
├── main.py                       # Point d'entrée
├── requirements.txt              # Dépendances Python
└── README.md                     # Ce fichier
```

## 🔍 Exemple de détection

```
======================================================================
DÉTECTION #1
======================================================================
Type: DJI Mavic 3
Protocole: OcuSync 3.0
Confiance: 94.0%
Fréquence: 2437.0 MHz
Bande passante: 15.2 MHz
SNR: 18.5 dB
RSSI: -65.0 dBm

📍 Position: (12.358500°, -1.535200°)
   Altitude: 45.2 m AGL
👤 Opérateur: BFA-OP-12345
   Distance: 350 m

⚠️  Niveau de menace: LOW
   Raisons: Remote ID disponible
======================================================================
```

## 📊 Topics MQTT

### `drone/detection`
Détection complète (toutes les informations fusionnées)

### `drone/position`
Position GPS temps réel du drone

### `drone/classification`
Résultats de classification (brand, model, protocole)

### `drone/alert`
Alertes pour menaces MEDIUM/HIGH

### `system/health`
Heartbeat et statut du système

## 🛠️ Tests des modules

Chaque module peut être testé individuellement :

```bash
# Test acquisition
python3 -m src.uhd_acquisition

# Test prétraitement
python3 -m src.preprocessing

# Test analyse spectrale
python3 -m src.spectrogram

# Test Remote ID
python3 -m src.remote_id_decoder

# Test classification
python3 -m src.classifier

# Test fusion
python3 -m src.data_fusion

# Test MQTT
python3 -m src.mqtt_publisher
```

## ⚠️ Notes importantes

1. **MODULE 4A (Détection NPAQM)** : Non implémenté selon les spécifications
2. **MODULE 5 (Classification)** : Supprimé - Détection basée uniquement sur Remote ID
3. **Remote ID** : La démodulation WiFi complète nécessite GNU Radio ou bibliothèque similaire pour un déploiement réel
4. **Zones restreintes** : À configurer selon votre localisation dans `config/config.yaml`

## 📝 License

Tous droits réservés.

## 👥 Auteur

Système de Détection de Drones - Version 1.0.0
# Detection_droneV3
