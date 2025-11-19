# Exemples de Détection Remote ID

## 📁 Fichiers Disponibles

### [remote_id_detection_complete.py](remote_id_detection_complete.py)
Exemple complet de détection Remote ID avec approche **hybride SDR + WiFi**.

**Utilisation:**
```bash
# Installation des dépendances
pip install scapy
sudo apt-get install aircrack-ng

# Exécution (nécessite sudo pour mode monitor)
sudo python3 examples/remote_id_detection_complete.py
```

## 🎯 Approches Implémentées

### 1. Détection WiFi Pure
```python
from src.wifi_capture import WiFiMonitorCapture
from src.remote_id_decoder import WiFiRemoteIDDecoder

capture = WiFiMonitorCapture(interface="wlan1")
capture.enable_monitor_mode()

frames = capture.capture_with_scapy(count=100)
decoder = WiFiRemoteIDDecoder()

for frame in frames:
    beacon = decoder.parse_beacon_frame(frame.frame_data)
    if beacon:
        remote_id = decoder.extract_remote_id(beacon)
        if remote_id:
            print(f"Drone: {remote_id.uas_id}")
```

### 2. Détection Hybride (Recommandé)
```python
# 1. SDR détecte signal WiFi
is_wifi, confidence, channel = wifi_detector.is_wifi_signal(features, freq)

# 2. Si WiFi → Capture avec adaptateur
if is_wifi:
    frames = wifi_capture.capture_with_scapy(count=20)

    # 3. Parse Remote ID
    for frame in frames:
        remote_id = decoder.extract_remote_id(frame)
```

## 🔧 Configuration

### Adaptateur WiFi
```bash
# Vérifier compatibilité mode monitor
iw list | grep monitor

# Activer mode monitor
sudo airmon-ng start wlan1

# Tester
sudo airodump-ng wlan1mon
```

### LibreSDR B210
```bash
# Vérifier connexion
uhd_find_devices

# Test
uhd_usrp_probe
```

## 📊 Résultats Attendus

```
🎯 Signal détecté! SNR: 18.5 dB
✅ Signal WiFi détecté! Canal: 6, Confiance: 85%
📡 Capture des trames WiFi...
✅ 15 trames Beacon capturées
🔍 Recherche de Remote ID...

========================================================================
🎯 REMOTE ID DÉTECTÉ
========================================================================

📡 Informations Radio:
   Source MAC: aa:bb:cc:dd:ee:ff
   Signal: -65 dBm
   Fréquence: 2437 MHz

🆔 Identifiant:
   UAS ID: 1FFJX8K3QH000001
   Type: Serial Number

📍 Position Drone:
   Latitude: 12.358500°
   Longitude: -1.535200°
   Altitude MSL: 120.5 m
   Hauteur AGL: 45.2 m

🚁 Vélocité:
   Vitesse: 12.3 m/s (44.3 km/h)
   Direction: 87°
   Vitesse verticale: 2.5 m/s

👤 Opérateur:
   Position: (12.358000°, -1.534800°)
   ID: BFA-OP-12345

📊 Statut: Airborne
========================================================================
```

## ⚠️ Notes Importantes

1. **Permissions** : Mode monitor nécessite `sudo`
2. **Chipset WiFi** : Vérifiez compatibilité avant achat
3. **Légalité** : Capture Remote ID autorisée, respectez les lois locales
4. **Performance** : Approche hybride = meilleurs résultats

## 🔗 Ressources

- [Guide complet](../REMOTE_ID_GUIDE.md)
- [Documentation Remote ID](../README.md)
