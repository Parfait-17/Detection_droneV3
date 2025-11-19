#!/bin/bash
# Configuration des permissions USRP B210
# À exécuter avec sudo

echo "=========================================="
echo "Configuration Permissions USRP B210"
echo "=========================================="

# Créer règle udev pour USRP B210
echo "Création de la règle udev..."
cat > /tmp/uhd-usrp.rules << 'EOF'
# USRP B200/B210
SUBSYSTEMS=="usb", ATTRS{idVendor}=="2500", ATTRS{idProduct}=="0020", MODE:="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="2500", ATTRS{idProduct}=="0021", MODE:="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="2500", ATTRS{idProduct}=="0022", MODE:="0666"

# USRP B200mini/B205mini
SUBSYSTEMS=="usb", ATTRS{idVendor}=="2500", ATTRS{idProduct}=="0030", MODE:="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="2500", ATTRS{idProduct}=="0031", MODE:="0666"
EOF

sudo cp /tmp/uhd-usrp.rules /etc/udev/rules.d/10-uhd-usrp.rules
sudo chmod 644 /etc/udev/rules.d/10-uhd-usrp.rules

echo "✓ Règle udev créée: /etc/udev/rules.d/10-uhd-usrp.rules"

# Recharger udev
echo "Rechargement des règles udev..."
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "✓ Règles udev rechargées"

# Créer groupe usrp si nécessaire
if ! getent group usrp > /dev/null 2>&1; then
    echo "Création du groupe 'usrp'..."
    sudo groupadd usrp
    echo "✓ Groupe 'usrp' créé"
fi

# Ajouter utilisateur au groupe usrp
echo "Ajout de l'utilisateur au groupe 'usrp'..."
sudo usermod -a -G usrp $USER

echo ""
echo "=========================================="
echo "✓ Configuration terminée"
echo "=========================================="
echo ""
echo "IMPORTANT:"
echo "1. Débrancher et rebrancher le USRP B210"
echo "2. Ou redémarrer l'ordinateur"
echo "3. Puis tester: uhd_find_devices"
echo ""
