# Fix Rapide - Overflows USRP B210

## 🔴 Problème
Vous avez des overflows massifs avec votre commande actuelle :
```bash
python3 main_gnuradio_wifi.py \
  --freq 2.442e9 \
  --scan-channels "" \
  --gain 38 \
  --sample-rate 20000000 \
  --uhd-args "type=b200"
```

**Résultat :** `OOOOusrp_source :error: In the last 784 ms, 4 overflows occurred.`

---

## ✅ Solution Immédiate

### Option 1 : Script Automatique (RECOMMANDÉ)

```bash
# Lancer avec paramètres optimisés
./run_optimized.sh
```

### Option 2 : Commande Manuelle

```bash
python3 main_gnuradio_wifi.py \
  --freq 2.437e9 \
  --gain 40 \
  --sample-rate 10000000 \
  --scan-channels "" \
  --uhd-args "type=b200,num_recv_frames=1024,recv_frame_size=32768"
```

---

## 🔧 Changements Clés

| Paramètre | Avant | Après | Raison |
|-----------|-------|-------|--------|
| `--sample-rate` | 20000000 (20 MS/s) | **10000000 (10 MS/s)** | ⚠️ 20 MS/s trop élevé pour USB 3.0 |
| `--gain` | 38 | **40** | Gain optimal |
| `--uhd-args` | `type=b200` | **`type=b200,num_recv_frames=1024,recv_frame_size=32768`** | Buffers 4× plus grands |

---

## 📊 Résultat Attendu

**Avant (20 MS/s) :**
```
OOOOusrp_source :error: In the last 784 ms, 4 overflows occurred.
OOOOOusrp_source :error: In the last 802 ms, 5 overflows occurred.
[...] 50+ overflows par minute
```

**Après (10 MS/s) :**
```
2025-11-17 00:48:48,114 - __main__ - INFO - 🚀 Système actif
[...] 0-2 overflows par minute (acceptable)
```

---

## 🚀 Optimisations Système (Optionnel)

### 1. Augmenter mémoire USB (nécessite sudo)
```bash
sudo sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb'
```

### 2. Mode Performance CPU (nécessite sudo)
```bash
sudo cpupower frequency-set -g performance
```

### 3. Vérifier diagnostic complet
```bash
./optimize_usrp_performance.sh
```

---

## 📖 Documentation Complète

- **Guide détaillé :** `TROUBLESHOOTING_OVERFLOWS.md`
- **Script diagnostic :** `optimize_usrp_performance.sh`
- **Script optimisé :** `run_optimized.sh`

---

## ❓ FAQ

### Q: Pourquoi 10 MS/s au lieu de 20 MS/s ?
**R:** 20 MS/s = 80 MB/s sur USB 3.0, trop proche de la limite (300-400 MB/s réels). 10 MS/s = 40 MB/s, marge confortable.

### Q: Est-ce que 10 MS/s suffit pour détecter Remote ID ?
**R:** Oui ! 10 MS/s = 10 MHz de bande passante, couvre 2 canaux WiFi. Remote ID utilise 1 canal (20 MHz nominal mais 10 MHz suffisent).

### Q: Puis-je utiliser 5 MS/s ?
**R:** Oui, encore plus stable (20 MB/s). Commande :
```bash
python3 main_gnuradio_wifi.py --sample-rate 5000000 --freq 2.437e9
```

### Q: Les overflows persistent avec 10 MS/s ?
**R:** Vérifier :
1. Connexion USB 3.0 (pas 2.0) : `lsusb -t | grep -i b210`
2. Fermer applications gourmandes
3. Appliquer optimisations système (sudo)

---

## 🎯 Test Rapide

```bash
# Test 2 minutes avec 10 MS/s
timeout 120 python3 main_gnuradio_wifi.py \
  --sample-rate 10000000 \
  --scan-channels ""

# Compter overflows
grep "overflows occurred" drone_detection_gnuradio.log | tail -20
```

**Objectif :** < 5 overflows en 2 minutes

---

## 📞 Besoin d'Aide ?

Si overflows persistent après ces changements :
1. Lancer `./optimize_usrp_performance.sh > diagnostic.txt`
2. Partager `diagnostic.txt` et les logs
3. Vérifier câble USB 3.0 et port USB 3.0 (bleu)
