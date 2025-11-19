# Guide de Détection Remote ID

## 🎯 Problème Actuel

L'implémentation actuelle a **3 problèmes majeurs** :

1. ❌ **Pas de détection WiFi préalable** - On tente de décoder Remote ID sur tous les signaux
2. ❌ **Démodulation WiFi manquante** - `demodulate_wifi_beacon()` retourne `None`
3. ❌ **Approche incorrecte** - Impossible de décoder WiFi directement depuis I/Q bruts sans démodulation OFDM complète

## ✅ Solutions Recommandées

### **OPTION 1: Capture WiFi Directe (⭐ RECOMMANDÉE)**

**Avantages:**
- ✅ Simple et fiable
- ✅ Pas besoin de démodulation complexe
- ✅ Performance élevée
- ✅ Faible latence

**Matériel requis:**
- Adaptateur WiFi USB compatible mode monitor (ex: **Alfa AWUS036ACH**)
- OU utiliser WiFi intégré si compatible

**Implémentation:**

```python
# Utiliser src/wifi_capture.py
from src.wifi_capture import WiFiMonitorCapture
from src.remote_id_decoder import WiFiRemoteIDDecoder

# 1. Capturer les trames WiFi
capture = WiFiMonitorCapture(interface="wlan0")
capture.enable_monitor_mode()
frames = capture.capture_with_scapy(count=100)

# 2. Parser chaque trame pour Remote ID
decoder = WiFiRemoteIDDecoder()
for frame in frames:
    beacon_info = decoder.parse_beacon_frame(frame.frame_data)
    if beacon_info:
        remote_id = decoder.extract_remote_id(beacon_info)
        if remote_id:
            print(f"Drone détecté: {remote_id.uas_id}")
```

**Coût:** ~30-50€ (adaptateur WiFi)

---

### **OPTION 2: SDR + Détection WiFi + GNU Radio (Avancé)**

**Avantages:**
- ✅ Détection RF complète
- ✅ Peut détecter autres protocoles (OcuSync, etc.)
- ✅ Analyse spectrale riche

**Inconvénients:**
- ❌ Très complexe
- ❌ Nécessite GNU Radio
- ❌ Performance moyenne
- ❌ Latence élevée

**Implémentation:**

```python
# 1. Détecter si signal WiFi
from src.wifi_detector import WiFiDetector
detector = WiFiDetector()

is_wifi, confidence, channel = detector.is_wifi_signal(features, center_freq)

if is_wifi:
    # 2. Démodulation avec GNU Radio
    # (Nécessite flowgraph GNU Radio complexe)
    # 3. Parser les trames
    pass
```

**Coût:** LibreSDR B210mini déjà disponible + temps de développement

---

### **OPTION 3: Hybride SDR + WiFi (⭐ OPTIMAL)**

**Meilleure approche:**

```
┌─────────────────┐
│  LibreSDR B210  │ → Détection RF large bande
│  (2.4 + 5.8 GHz)│    Analyse spectrale
└────────┬────────┘    Détection de signaux
         │
         ↓
    ┌────────┐
    │ WiFi   │ ← Si signal WiFi détecté →
    │ USB    │   Capture précise des trames
    └────────┘   Décodage Remote ID
```

**Workflow:**
1. **SDR** : Scan large bande, détection de signaux
2. **WiFi Detector** : Identifie les signaux WiFi
3. **WiFi Monitor** : Capture les trames sur canal détecté
4. **Remote ID Decoder** : Parse les informations

## 📋 Implémentation Recommandée

### Installation

```bash
# 1. Installer les outils WiFi
sudo apt-get install aircrack-ng iw

# 2. Installer Scapy
pip install scapy

# 3. Vérifier l'adaptateur WiFi
iw list  # Doit afficher "monitor mode"
```

### Mise à jour de main.py

```python
# Remplacer la section détection Remote ID par:

# 1. Détecter si WiFi (via SDR)
from src.wifi_detector import WiFiDetector
wifi_detector = WiFiDetector()

is_wifi, wifi_confidence, channel = wifi_detector.is_wifi_signal(
    features,
    acq_config['rx_freq_2g4']
)

# 2. Si WiFi détecté, capturer avec adaptateur
if is_wifi and channel:
    logger.info(f"Signal WiFi détecté sur canal {channel}")

    from src.wifi_capture import WiFiMonitorCapture
    wifi_capture = WiFiMonitorCapture()

    # Capturer des trames sur ce canal
    frames = wifi_capture.capture_with_scapy(count=10)

    # 3. Décoder Remote ID
    for frame in frames:
        beacon_info = remote_id_decoder.parse_beacon_frame(frame.frame_data)
        if beacon_info:
            remote_id = remote_id_decoder.extract_remote_id(beacon_info)
            if remote_id:
                remote_id_data = remote_id.to_dict()
                logger.info(f"📡 Remote ID: {remote_id.uas_id}")
                break
```

## 🔧 Configuration Matérielle

### Adaptateurs WiFi Recommandés

| Modèle | Prix | Bandes | Mode Monitor |
|--------|------|--------|--------------|
| **Alfa AWUS036ACH** | ~40€ | 2.4 + 5 GHz | ✅ Oui |
| **TP-Link TL-WN722N v1** | ~15€ | 2.4 GHz | ✅ Oui (v1 uniquement) |
| **Alfa AWUS036NHA** | ~35€ | 2.4 GHz | ✅ Oui |

⚠️ **IMPORTANT:** La version du chipset est critique. Vérifiez avant achat.

### Test de l'Adaptateur

```bash
# Vérifier le chipset
lsusb
dmesg | grep -i wifi

# Tester le mode monitor
sudo airmon-ng start wlan0
sudo airodump-ng wlan0mon

# Si vous voyez des trames → OK ✅
```

## 📊 Comparaison des Approches

| Critère | WiFi Direct | SDR + GNU Radio | Hybride |
|---------|-------------|-----------------|---------|
| **Complexité** | ⭐ Faible | ⭐⭐⭐⭐⭐ Très élevée | ⭐⭐⭐ Moyenne |
| **Coût** | 30-50€ | 0€ (SDR déjà là) | 30-50€ |
| **Fiabilité** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Détection autres protocoles** | ❌ | ✅ | ✅ |

## 🎯 Recommandation Finale

### Pour Démarrer Rapidement
👉 **Utilisez l'OPTION 1 (WiFi Direct)**
- Achetez un Alfa AWUS036ACH (~40€)
- Utilisez `src/wifi_capture.py`
- Simple, fiable, performant

### Pour Projet Complet
👉 **Utilisez l'OPTION 3 (Hybride)**
- SDR pour détection large bande
- WiFi pour capture précise Remote ID
- Meilleure approche technique

### À Éviter
❌ **Démodulation WiFi pure avec SDR**
- Trop complexe
- Résultats médiocres
- Pas recommandé

## 📝 Exemple Complet

Voir le fichier `examples/remote_id_detection_complete.py` pour un exemple complet utilisant l'approche hybride.

## 🔗 Ressources

- [ASTM F3411 Standard](https://www.astm.org/f3411-22a.html)
- [OpenDroneID](https://github.com/opendroneid)
- [Scapy WiFi Tutorial](https://scapy.readthedocs.io/en/latest/layers/dot11.html)
- [Aircrack-ng Suite](https://www.aircrack-ng.org/)

## ⚠️ Notes Légales

La capture de trames WiFi doit être effectuée dans le respect des lois locales :
- ✅ Capture de trames Beacon (public) : Généralement autorisé
- ❌ Déchiffrement de communications : Interdit
- ✅ Détection Remote ID : Autorisé (c'est son but)

**Consultez les lois locales avant déploiement.**
