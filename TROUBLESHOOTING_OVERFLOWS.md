# Guide de Dépannage - Overflows USRP B210

## Symptômes

```
OOOOusrp_source :error: In the last 784 ms, 4 overflows occurred.
OOOOOusrp_source :error: In the last 802 ms, 5 overflows occurred.
```

Les "O" indiquent des **pertes de données** : le PC ne traite pas assez vite les échantillons reçus de l'USRP.

---

## Causes Principales

### 1. **Sample Rate Trop Élevé** ⚠️
- **20 MS/s** = 80 MB/s de données (complexes float32)
- USB 3.0 théorique : 5 Gbps = 625 MB/s
- USB 3.0 réel : ~300-400 MB/s (overhead protocole)
- **Verdict** : 20 MS/s est à la limite, instable

### 2. **Buffers USB Insuffisants**
- Par défaut : `num_recv_frames=512`, `recv_frame_size=16384`
- Total buffer : 512 × 16 KB = 8 MB
- **Insuffisant** pour absorber les pics de latence

### 3. **CPU Surchargé**
- GNU Radio + gr-ieee802-11 = traitement intensif
- FFT 64 points + égalisation + décodage MAC
- Si CPU < 100% disponible → overflows

### 4. **USB 2.0 au lieu de 3.0**
- USB 2.0 : 480 Mbps = 60 MB/s
- **Impossible** de tenir 20 MS/s (80 MB/s)

---

## Solutions (par ordre d'efficacité)

### ✅ Solution 1 : Réduire le Sample Rate (CRITIQUE)

**Recommandation : 10 MS/s**

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 40 \
  --sample-rate 10000000 \
  --scan-channels ""
```

**Pourquoi ça marche :**
- 10 MS/s = 40 MB/s (divisé par 2)
- Marge confortable sur USB 3.0
- Bande passante : 10 MHz (couvre 2 canaux WiFi)

**Comparaison :**
| Sample Rate | Débit USB | Stabilité | Bande passante |
|-------------|-----------|-----------|----------------|
| 5 MS/s      | 20 MB/s   | ✅ Excellent | 5 MHz (1 canal) |
| 10 MS/s     | 40 MB/s   | ✅ Bon       | 10 MHz (2 canaux) |
| 20 MS/s     | 80 MB/s   | ⚠️ Instable  | 20 MHz (4 canaux) |
| 40 MS/s     | 160 MB/s  | ❌ Impossible USB | 40 MHz |

---

### ✅ Solution 2 : Augmenter les Buffers UHD

**Déjà implémenté dans le code mis à jour :**

```python
uhd_device_args="type=b200,num_recv_frames=1024,recv_frame_size=32768"
```

**Avant :**
- 512 frames × 16 KB = 8 MB buffer

**Après :**
- 1024 frames × 32 KB = 32 MB buffer
- **4× plus de marge** pour absorber les pics

---

### ✅ Solution 3 : Optimisations Système

#### A. Augmenter la mémoire USB

```bash
# Vérifier valeur actuelle
cat /sys/module/usbcore/parameters/usbfs_memory_mb

# Augmenter à 1000 MB (nécessite sudo)
sudo sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb'
```

#### B. Mode Performance CPU

```bash
# Installer cpupower
sudo apt install linux-tools-common linux-tools-generic

# Activer mode performance
sudo cpupower frequency-set -g performance

# Vérifier
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

#### C. Vérifier connexion USB 3.0

```bash
# Lister périphériques USB
lsusb -t | grep -i b210

# Doit afficher "5000M" (USB 3.0), pas "480M" (USB 2.0)
```

**Si USB 2.0 détecté :**
- Brancher sur port USB 3.0 (souvent bleu)
- Vérifier câble USB 3.0 (marqué SS)
- Tester autre port USB

---

### ✅ Solution 4 : Désactiver le Channel Hopping

**Le hopping change la fréquence toutes les 2 secondes :**
- Perturbe la réception
- Augmente la charge CPU

```bash
# Désactiver le scan (rester sur canal 6)
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --scan-channels ""
```

---

### ✅ Solution 5 : Réduire le Gain

**Gain élevé = plus de bruit = plus de traitements**

```bash
# Tester avec gain 40 dB au lieu de 50
python3 main_gnuradio_wifi.py \
  --gain 40 \
  --sample-rate 10000000
```

**Recommandations gain :**
- **30-40 dB** : Environnement urbain (drone proche)
- **40-50 dB** : Environnement rural
- **50-60 dB** : Longue distance (risque overflows)

---

## Configuration Optimale Testée

```bash
# Lancer le script d'optimisation
chmod +x optimize_usrp_performance.sh
./optimize_usrp_performance.sh

# Lancer avec paramètres optimisés
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 40 \
  --sample-rate 10000000 \
  --scan-channels "" \
  --uhd-args "type=b200,num_recv_frames=1024,recv_frame_size=32768"
```

**Résultat attendu :**
- ✅ Overflows < 1 par minute (acceptable)
- ✅ Trames WiFi décodées correctement
- ✅ CPU < 80%

---

## Diagnostic des Overflows

### Overflows Occasionnels (< 5/min)
**Cause :** Pics de charge CPU normaux  
**Action :** ✅ Acceptable, continuer

### Overflows Fréquents (> 10/min)
**Cause :** Sample rate trop élevé  
**Action :** ⚠️ Réduire à 10 MS/s ou 5 MS/s

### Overflows Massifs (> 50/min)
**Cause :** USB 2.0 ou CPU surchargé  
**Action :** ❌ Vérifier connexion USB 3.0, fermer applications

---

## Vérification Post-Optimisation

### 1. Tester la stabilité

```bash
# Lancer pendant 5 minutes
timeout 300 python3 main_gnuradio_wifi.py \
  --sample-rate 10000000 \
  --scan-channels ""

# Compter les overflows
grep "overflows occurred" drone_detection_gnuradio.log | wc -l
```

**Objectif :** < 10 overflows en 5 minutes

### 2. Monitorer les ressources

```bash
# Terminal 1 : Lancer le système
python3 main_gnuradio_wifi.py --sample-rate 10000000

# Terminal 2 : Monitorer CPU
watch -n 1 'ps aux | grep python3 | grep -v grep'
```

**Objectif :** CPU < 80%

---

## Alternatives si Overflows Persistent

### Option A : Réduire à 5 MS/s

```bash
python3 main_gnuradio_wifi.py \
  --sample-rate 5000000 \
  --freq 2.437e9
```

**Avantages :**
- ✅ Très stable (20 MB/s)
- ✅ Pas d'overflows

**Inconvénients :**
- ⚠️ Bande passante : 5 MHz (1 seul canal WiFi)

### Option B : Utiliser un PC plus puissant

**Requis minimum :**
- CPU : 4 cœurs @ 2.5 GHz
- RAM : 4 GB
- USB 3.0 natif (pas via hub)

### Option C : Passer à USRP N210 (Ethernet)

**Si budget disponible :**
- USRP N210 : Connexion Gigabit Ethernet
- Pas de limitation USB
- Sample rate jusqu'à 25 MS/s stable

---

## Commandes de Diagnostic

```bash
# 1. Vérifier USRP détecté
uhd_find_devices

# 2. Tester connexion
uhd_usrp_probe --args="type=b200"

# 3. Vérifier mémoire USB
cat /sys/module/usbcore/parameters/usbfs_memory_mb

# 4. Vérifier CPU governor
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 5. Monitorer overflows en temps réel
tail -f drone_detection_gnuradio.log | grep --line-buffered "overflow"
```

---

## Résumé Rapide

| Problème | Solution | Priorité |
|----------|----------|----------|
| Overflows massifs | Réduire sample rate à 10 MS/s | 🔴 Critique |
| USB 2.0 | Brancher sur port USB 3.0 | 🔴 Critique |
| Buffers petits | Augmenter num_recv_frames=1024 | 🟡 Important |
| CPU lent | Mode performance governor | 🟡 Important |
| Mémoire USB faible | Augmenter usbfs_memory_mb | 🟢 Optionnel |

---

## Support

Si les overflows persistent après toutes ces optimisations :

1. **Partager les logs :**
   ```bash
   tail -100 drone_detection_gnuradio.log
   ```

2. **Informations système :**
   ```bash
   ./optimize_usrp_performance.sh > system_info.txt
   ```

3. **Configuration testée :**
   ```bash
   # Quelle commande exacte avez-vous lancée ?
   ```
