# Exemples de Commandes - GNU Radio WiFi Remote ID

## 🚀 Configurations Recommandées

### 1. Configuration Stable (RECOMMANDÉE)

**Usage :** Production, détection fiable, overflows minimaux

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 40 \
  --sample-rate 10000000 \
  --scan-channels "" \
  --uhd-args "type=b200,num_recv_frames=1024,recv_frame_size=32768"
```

**Caractéristiques :**
- ✅ Sample rate : 10 MS/s (stable)
- ✅ Gain : 40 dB (bon compromis)
- ✅ Canal fixe : 6 (2.437 GHz)
- ✅ Buffers : 32 MB
- ✅ Overflows : < 2/min

---

### 2. Configuration Ultra-Stable

**Usage :** PC ancien, USB instable, overflows persistants

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 40 \
  --sample-rate 5000000 \
  --scan-channels "" \
  --uhd-args "type=b200,num_recv_frames=1024,recv_frame_size=32768"
```

**Caractéristiques :**
- ✅ Sample rate : 5 MS/s (très stable)
- ✅ Débit USB : 20 MB/s (minimal)
- ✅ Overflows : 0/min
- ⚠️ Bande passante : 5 MHz (1 canal WiFi)

---

### 3. Configuration Haute Performance

**Usage :** PC puissant, USB 3.0 natif, optimisations système appliquées

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 50 \
  --sample-rate 20000000 \
  --scan-channels "" \
  --uhd-args "type=b200,num_recv_frames=2048,recv_frame_size=32768"
```

**Caractéristiques :**
- ⚠️ Sample rate : 20 MS/s (limite USB 3.0)
- ✅ Gain : 50 dB (longue portée)
- ✅ Buffers : 64 MB (doublés)
- ⚠️ Overflows : 5-10/min (acceptable si CPU puissant)

**Prérequis :**
```bash
# Optimisations système obligatoires
sudo sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb'
sudo cpupower frequency-set -g performance
```

---

### 4. Configuration Scan Multi-Canaux

**Usage :** Recherche de drones sur plusieurs canaux WiFi

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 40 \
  --sample-rate 10000000 \
  --scan-channels "1,6,11" \
  --hop-interval 3.0 \
  --uhd-args "type=b200,num_recv_frames=1024,recv_frame_size=32768"
```

**Caractéristiques :**
- ✅ Canaux : 1, 6, 11 (2.4 GHz)
- ✅ Hop interval : 3 secondes par canal
- ⚠️ Moins de temps par canal (détection plus lente)

---

### 5. Configuration 5 GHz (Expérimental)

**Usage :** Drones WiFi 5 GHz (rare)

```bash
python3 main_gnuradio_wifi.py \
  --freq 5.180e9 \
  --gain 50 \
  --sample-rate 10000000 \
  --scan-channels "36,40,44,48" \
  --include-5ghz \
  --uhd-args "type=b200,num_recv_frames=1024,recv_frame_size=32768"
```

**Caractéristiques :**
- ✅ Fréquence : 5.18 GHz (canal 36)
- ✅ Scan : Canaux 36, 40, 44, 48
- ⚠️ Remote ID 5 GHz très rare

---

## 🎯 Scénarios d'Utilisation

### Scénario 1 : Détection en Environnement Urbain

**Contexte :** Ville, beaucoup de WiFi, drone proche (< 500m)

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 35 \
  --sample-rate 10000000 \
  --scan-channels ""
```

**Raison :**
- Gain réduit (35 dB) : Éviter saturation par WiFi environnant
- Canal fixe : Meilleure réception continue

---

### Scénario 2 : Détection en Environnement Rural

**Contexte :** Campagne, peu de WiFi, drone lointain (> 1 km)

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 55 \
  --sample-rate 10000000 \
  --scan-channels "1,6,11" \
  --hop-interval 5.0
```

**Raison :**
- Gain élevé (55 dB) : Longue portée
- Scan multi-canaux : Recherche active
- Hop interval long (5s) : Plus de temps par canal

---

### Scénario 3 : Test avec Drone Connu

**Contexte :** Drone DJI à proximité, canal WiFi connu (ex: canal 6)

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 40 \
  --sample-rate 10000000 \
  --scan-channels "" \
  --verbose
```

**Raison :**
- Canal fixe : Réception optimale
- Verbose : Voir tous les paquets WiFi décodés

---

### Scénario 4 : Monitoring Longue Durée

**Contexte :** Surveillance 24/7, stabilité critique

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 40 \
  --sample-rate 5000000 \
  --scan-channels "" \
  --uhd-args "type=b200,num_recv_frames=2048,recv_frame_size=32768"
```

**Raison :**
- Sample rate minimal (5 MS/s) : Stabilité maximale
- Buffers doublés : Tolérance aux pics
- Pas de scan : Moins de perturbations

---

## 🔧 Ajustements par Gain

### Gain 30 dB : Très Proche (< 100m)

```bash
python3 main_gnuradio_wifi.py --gain 30 --sample-rate 10000000
```

**Usage :** Tests en intérieur, drone très proche

---

### Gain 40 dB : Proche (100-500m)

```bash
python3 main_gnuradio_wifi.py --gain 40 --sample-rate 10000000
```

**Usage :** Environnement urbain, détection standard

---

### Gain 50 dB : Moyen (500m-1km)

```bash
python3 main_gnuradio_wifi.py --gain 50 --sample-rate 10000000
```

**Usage :** Environnement rural, portée moyenne

---

### Gain 60 dB : Lointain (> 1km)

```bash
python3 main_gnuradio_wifi.py --gain 60 --sample-rate 5000000
```

**Usage :** Longue portée, environnement dégagé

⚠️ **Attention :** Gain élevé = plus de bruit = plus de CPU = risque overflows

---

## 📊 Ajustements par Sample Rate

### 5 MS/s : Ultra-Stable

```bash
python3 main_gnuradio_wifi.py --sample-rate 5000000
```

**Avantages :**
- ✅ Débit USB : 20 MB/s (minimal)
- ✅ Overflows : 0/min
- ✅ CPU : ~40%

**Inconvénients :**
- ⚠️ Bande passante : 5 MHz (1 canal WiFi)

---

### 10 MS/s : Stable (RECOMMANDÉ)

```bash
python3 main_gnuradio_wifi.py --sample-rate 10000000
```

**Avantages :**
- ✅ Débit USB : 40 MB/s (confortable)
- ✅ Overflows : < 2/min
- ✅ Bande passante : 10 MHz (2 canaux WiFi)
- ✅ CPU : ~60%

---

### 20 MS/s : Limite USB 3.0

```bash
python3 main_gnuradio_wifi.py --sample-rate 20000000
```

**Avantages :**
- ✅ Bande passante : 20 MHz (4 canaux WiFi)

**Inconvénients :**
- ⚠️ Débit USB : 80 MB/s (limite)
- ⚠️ Overflows : 5-10/min
- ⚠️ CPU : ~80%

**Prérequis :**
- USB 3.0 natif (pas hub)
- Optimisations système appliquées

---

## 🧪 Commandes de Test

### Test 1 : Vérifier USRP

```bash
# Détecter USRP
uhd_find_devices

# Tester connexion
uhd_usrp_probe --args="type=b200"
```

---

### Test 2 : Test Court (2 minutes)

```bash
# Lancer 2 minutes
timeout 120 python3 main_gnuradio_wifi.py \
  --sample-rate 10000000 \
  --scan-channels ""

# Compter overflows
grep "overflows occurred" drone_detection_gnuradio.log | wc -l
```

**Objectif :** < 5 overflows

---

### Test 3 : Monitorer CPU

```bash
# Terminal 1
python3 main_gnuradio_wifi.py --sample-rate 10000000

# Terminal 2
watch -n 1 'ps aux | grep python3 | grep main_gnuradio | grep -v grep'
```

**Objectif :** CPU < 80%

---

### Test 4 : Vérifier Réception WiFi

```bash
# Lancer avec verbose
python3 main_gnuradio_wifi.py \
  --sample-rate 10000000 \
  --verbose

# Doit afficher des trames WiFi décodées
```

---

## 🔍 Commandes de Diagnostic

### Vérifier Connexion USB

```bash
# Lister périphériques USB
lsusb | grep "2500:0020"

# Vérifier vitesse USB
lsusb -t | grep -i b210
# Doit afficher "5000M" (USB 3.0)
```

---

### Vérifier Mémoire USB

```bash
# Voir valeur actuelle
cat /sys/module/usbcore/parameters/usbfs_memory_mb

# Augmenter (nécessite sudo)
sudo sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb'
```

---

### Vérifier CPU Governor

```bash
# Voir governor actuel
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Passer en performance (nécessite sudo)
sudo cpupower frequency-set -g performance
```

---

### Monitorer Overflows en Temps Réel

```bash
# Terminal 1
python3 main_gnuradio_wifi.py --sample-rate 10000000

# Terminal 2
tail -f drone_detection_gnuradio.log | grep --line-buffered "overflow"
```

---

## 📝 Variables d'Environnement

### Personnaliser via Variables

```bash
# Définir paramètres
export FREQ=2.437e9
export GAIN=40
export SAMPLE_RATE=10000000

# Lancer script optimisé
./run_optimized.sh
```

---

## 🎯 Commande Finale Recommandée

**Pour la plupart des cas d'usage :**

```bash
./run_optimized.sh
```

**Ou manuellement :**

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 40 \
  --sample-rate 10000000 \
  --scan-channels "" \
  --uhd-args "type=b200,num_recv_frames=1024,recv_frame_size=32768"
```

---

## 📚 Références

- **Guide rapide :** `QUICK_FIX_OVERFLOWS.md`
- **Dépannage :** `TROUBLESHOOTING_OVERFLOWS.md`
- **Diagnostic :** `./optimize_usrp_performance.sh`
- **README :** `README_OVERFLOWS_FIX.md`
