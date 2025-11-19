#!/bin/bash
# Installation GNU Radio et gr-ieee802-11 pour Remote ID
# Ubuntu 22.04 LTS

set -e

echo "========================================================================"
echo "Installation GNU Radio + gr-ieee802-11"
echo "Pour USRP B210 Remote ID Detection"
echo "========================================================================"
echo ""

# Vérifier Ubuntu version
if ! command -v lsb_release &> /dev/null; then
    echo "❌ Impossible de détecter la version Ubuntu"
    exit 1
fi

UBUNTU_VERSION=$(lsb_release -rs)
echo "✓ Ubuntu version: $UBUNTU_VERSION"

# 1. Installer GNU Radio
echo ""
echo "=== Étape 1/5: Installation GNU Radio ==="
echo ""

sudo apt-get update
sudo apt-get install -y \
    gnuradio \
    gnuradio-dev \
    gr-osmosdr \
    libuhd-dev \
    uhd-host

echo "✓ GNU Radio installé"

# Vérifier version GNU Radio
GR_VERSION=$(gnuradio-config-info --version)
echo "  Version GNU Radio: $GR_VERSION"

# 2. Installer dépendances gr-ieee802-11
echo ""
echo "=== Étape 2/5: Installation dépendances gr-ieee802-11 ==="
echo ""

sudo apt-get install -y \
    git \
    cmake \
    build-essential \
    libboost-all-dev \
    libcppunit-dev \
    liblog4cpp5-dev \
    swig \
    python3-dev

echo "✓ Dépendances installées"

# 3. Cloner gr-ieee802-11
echo ""
echo "=== Étape 3/5: Téléchargement gr-ieee802-11 ==="
echo ""

cd ~
if [ -d "gr-ieee802-11" ]; then
    echo "  Dossier gr-ieee802-11 existe déjà"
    cd gr-ieee802-11
    git pull
else
    git clone https://github.com/bastibl/gr-ieee802-11.git
    cd gr-ieee802-11
fi

echo "✓ gr-ieee802-11 téléchargé"

# 4. Compiler gr-ieee802-11
echo ""
echo "=== Étape 4/5: Compilation gr-ieee802-11 ==="
echo "  (Cela peut prendre 5-10 minutes...)"
echo ""

mkdir -p build
cd build
cmake ..
make -j$(nproc)
sudo make install
sudo ldconfig

echo "✓ gr-ieee802-11 compilé et installé"

# 5. Vérification
echo ""
echo "=== Étape 5/5: Vérification installation ==="
echo ""

# Test import Python
if python3 -c "import ieee802_11" 2>/dev/null; then
    echo "✓ gr-ieee802-11 importable en Python"
else
    echo "❌ Erreur: gr-ieee802-11 non importable"
    echo "   Essayez: export PYTHONPATH=/usr/local/lib/python3/dist-packages:$PYTHONPATH"
    exit 1
fi

# Test GNU Radio
if python3 -c "from gnuradio import gr" 2>/dev/null; then
    echo "✓ GNU Radio importable en Python"
else
    echo "❌ Erreur: GNU Radio non importable"
    exit 1
fi

# Test UHD (USRP)
if python3 -c "from gnuradio import uhd" 2>/dev/null; then
    echo "✓ UHD (USRP) importable en Python"
else
    echo "❌ Erreur: UHD non importable"
    exit 1
fi

echo ""
echo "========================================================================"
echo "✅ INSTALLATION RÉUSSIE"
echo "========================================================================"
echo ""
echo "Prochaines étapes:"
echo "  1. Tester: python3 gnuradio_wifi_remote_id.py"
echo "  2. Faire voler votre drone avec Remote ID activé"
echo "  3. Lancer: python3 main_gnuradio_wifi.py"
echo ""
echo "Documentation:"
echo "  - OPTION2B_GNU_RADIO.md"
echo "  - https://github.com/bastibl/gr-ieee802-11"
echo ""
