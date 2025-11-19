#!/bin/bash
# Script de lancement optimisé pour éviter les overflows USRP

echo "======================================================================="
echo "Lancement GNU Radio WiFi Remote ID - Configuration Optimisée"
echo "======================================================================="
echo ""

# Vérifier si USRP est connecté
if ! lsusb | grep -q "2500:0020"; then
    echo "❌ ERREUR: USRP B210 non détecté"
    echo "   Vérifier la connexion USB"
    exit 1
fi

echo "✓ USRP B210 détecté"
echo ""

# Paramètres optimisés
FREQ="${FREQ:-2.437e9}"           # Canal 6 WiFi (2.437 GHz)
GAIN="${GAIN:-40}"                # Gain modéré (40 dB)
SAMPLE_RATE="${SAMPLE_RATE:-10000000}"  # 10 MS/s (stable)
SCAN_CHANNELS="${SCAN_CHANNELS:-}"      # Pas de scan par défaut
UHD_ARGS="type=b200,num_recv_frames=1024,recv_frame_size=32768"

echo "Configuration:"
echo "  • Fréquence: $(echo "scale=3; $FREQ/1e9" | bc) GHz"
echo "  • Gain: $GAIN dB"
echo "  • Sample rate: $(echo "scale=1; $SAMPLE_RATE/1e6" | bc) MS/s"
echo "  • Channel hopping: $([ -z "$SCAN_CHANNELS" ] && echo "Désactivé" || echo "$SCAN_CHANNELS")"
echo "  • Buffers UHD: 1024 frames × 32 KB"
echo ""

# Vérifier optimisations système
echo "Vérifications système:"

# Mémoire USB
usb_mem=$(cat /sys/module/usbcore/parameters/usbfs_memory_mb 2>/dev/null || echo "?")
if [ "$usb_mem" -lt 1000 ] 2>/dev/null; then
    echo "  ⚠️  Mémoire USB: ${usb_mem} MB (recommandé: 1000 MB)"
    echo "     → sudo sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb'"
else
    echo "  ✓ Mémoire USB: ${usb_mem} MB"
fi

# CPU Governor
cpu_gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "?")
if [ "$cpu_gov" != "performance" ]; then
    echo "  ⚠️  CPU Governor: $cpu_gov (recommandé: performance)"
    echo "     → sudo cpupower frequency-set -g performance"
else
    echo "  ✓ CPU Governor: $cpu_gov"
fi

echo ""
echo "======================================================================="
echo "Démarrage dans 3 secondes... (Ctrl+C pour annuler)"
echo "======================================================================="
sleep 3

# Lancer le système
python3 main_gnuradio_wifi.py \
    --freq "$FREQ" \
    --gain "$GAIN" \
    --sample-rate "$SAMPLE_RATE" \
    --scan-channels "$SCAN_CHANNELS" \
    --uhd-args "$UHD_ARGS"
