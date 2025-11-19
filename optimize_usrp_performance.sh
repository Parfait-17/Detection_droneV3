#!/bin/bash
# Script d'optimisation pour réduire les overflows USRP B210
# À exécuter avant de lancer main_gnuradio_wifi.py

echo "======================================================================="
echo "Optimisation système pour USRP B210 - Réduction des overflows"
echo "======================================================================="
echo ""

# 1. Augmenter la priorité du thread USB
echo "[1/6] Configuration priorité thread USB..."
if [ -f /sys/module/usbcore/parameters/usbfs_memory_mb ]; then
    current=$(cat /sys/module/usbcore/parameters/usbfs_memory_mb)
    echo "   Mémoire USB actuelle: ${current} MB"
    if [ "$current" -lt 1000 ]; then
        echo "   ⚠️  Augmentation recommandée à 1000 MB"
        echo "   Commande: sudo sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb'"
    else
        echo "   ✓ Mémoire USB suffisante"
    fi
else
    echo "   ⚠️  Paramètre usbfs_memory_mb non trouvé"
fi
echo ""

# 2. Vérifier la connexion USB 3.0
echo "[2/6] Vérification connexion USB..."
lsusb -d 2500:0020 -v 2>/dev/null | grep -i "bcdUSB" | head -1
usb_speed=$(lsusb -t | grep -i "b210\|2500:0020" | grep -o "480M\|5000M" | head -1)
if [ "$usb_speed" = "5000M" ]; then
    echo "   ✓ USB 3.0 détecté (5 Gbps)"
elif [ "$usb_speed" = "480M" ]; then
    echo "   ⚠️  USB 2.0 détecté (480 Mbps) - OVERFLOWS ATTENDUS"
    echo "   → Brancher sur port USB 3.0 (bleu)"
else
    echo "   ? Vitesse USB non détectée"
fi
echo ""

# 3. Désactiver CPU frequency scaling (performance maximale)
echo "[3/6] Configuration CPU governor..."
current_governor=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)
if [ -n "$current_governor" ]; then
    echo "   Governor actuel: $current_governor"
    if [ "$current_governor" != "performance" ]; then
        echo "   ⚠️  Recommandation: mode 'performance'"
        echo "   Commande: sudo cpupower frequency-set -g performance"
    else
        echo "   ✓ Mode performance activé"
    fi
else
    echo "   ⚠️  CPU governor non accessible"
fi
echo ""

# 4. Vérifier les processus gourmands
echo "[4/6] Vérification charge CPU..."
cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
echo "   Load average: $cpu_load"
if (( $(echo "$cpu_load > 2.0" | bc -l 2>/dev/null || echo 0) )); then
    echo "   ⚠️  Charge CPU élevée - fermer applications inutiles"
else
    echo "   ✓ Charge CPU acceptable"
fi
echo ""

# 5. Recommandations sample rate
echo "[5/6] Recommandations sample rate..."
echo "   • 5 MS/s  : Très stable, bande passante limitée (1 canal WiFi)"
echo "   • 10 MS/s : Stable, bon compromis (RECOMMANDÉ)"
echo "   • 20 MS/s : Instable sur USB 3.0, overflows fréquents"
echo "   • 40 MS/s : Nécessite PCIe, impossible sur USB"
echo ""

# 6. Test de latence USB
echo "[6/6] Test latence USB (si uhd_usrp_probe disponible)..."
if command -v uhd_usrp_probe &> /dev/null; then
    echo "   Exécution uhd_usrp_probe --args='type=b200'..."
    timeout 5 uhd_usrp_probe --args="type=b200" 2>&1 | grep -i "usb\|b210" | head -3
else
    echo "   ⚠️  uhd_usrp_probe non trouvé (paquet uhd-host)"
fi
echo ""

# Résumé
echo "======================================================================="
echo "RÉSUMÉ DES OPTIMISATIONS"
echo "======================================================================="
echo ""
echo "✓ Paramètres recommandés pour main_gnuradio_wifi.py:"
echo ""
echo "  python3 main_gnuradio_wifi.py \\"
echo "    --freq 2.437e9 \\"
echo "    --gain 40 \\"
echo "    --sample-rate 10000000 \\"
echo "    --scan-channels \"\" \\"
echo "    --uhd-args \"type=b200,num_recv_frames=1024,recv_frame_size=32768\""
echo ""
echo "📝 Notes:"
echo "  • Sample rate réduit à 10 MS/s (au lieu de 20 MS/s)"
echo "  • Buffers UHD augmentés (1024 frames × 32 KB)"
echo "  • Gain réduit à 40 dB (moins de bruit)"
echo "  • Scan désactivé (--scan-channels \"\") pour stabilité"
echo ""
echo "🔧 Optimisations système (nécessitent sudo):"
echo "  sudo sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb'"
echo "  sudo cpupower frequency-set -g performance"
echo ""
echo "======================================================================="
