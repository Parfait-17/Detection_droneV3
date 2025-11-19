# Alternatives Sans USRP B210

## 🎯 Situation Actuelle

Votre USRP B210 n'est **pas connecté** ou **pas disponible**.

Voici les alternatives pour continuer à développer/tester votre système.

---

## ✅ Option 1 : Mode Simulation (Recommandé pour Tests)

**Avantages** :
- ✅ Aucun matériel requis
- ✅ Teste toute la chaîne MQTT/Fusion/Alertes
- ✅ Données réalistes

**Utilisation** :
```bash
# Lancer la simulation
python3 test_without_usrp.py

# Dans un autre terminal, monitorer MQTT
mosquitto_sub -h localhost -t "drone/#" -v
```

**Résultat** : Génère des détections Remote ID simulées toutes les 5 secondes.

---

## ✅ Option 2 : Adaptateur WiFi Mode Monitor

**Matériel requis** :
- Adaptateur WiFi interne (`wlo1` détecté) OU
- Adaptateur USB externe compatible (~40€)

**Avantages** :
- ✅ Détection WiFi Remote ID **réelle**
- ✅ Pas cher (si adaptateur interne compatible)
- ✅ Fiabilité 95%+

**Installation** :
```bash
# Installer outils WiFi
sudo apt install iw aircrack-ng

# Tester mode monitor
sudo ip link set wlo1 down
sudo iw dev wlo1 set monitor none
sudo ip link set wlo1 up

# Vérifier
iwconfig wlo1
```

**Script de test** :
```bash
# Créer script WiFi direct
python3 test_wifi_basic.py
```

---

## ✅ Option 3 : Fichiers IQ Pré-enregistrés

**Principe** : Utiliser des captures IQ de drones réels.

**Avantages** :
- ✅ Teste démodulation complète
- ✅ Reproductible
- ✅ Pas de matériel

**Utilisation** :
```bash
# Télécharger échantillons (si disponibles)
wget https://example.com/drone_samples.iq

# Rejouer avec GNU Radio
python3 replay_iq_samples.py --file drone_samples.iq
```

---

## ✅ Option 4 : RTL-SDR (~25€)

**Matériel** : Clé USB RTL-SDR (DVB-T)

**Avantages** :
- ✅ Très bon marché (~25€)
- ✅ Détection WiFi 2.4 GHz possible
- ✅ Large communauté

**Limitations** :
- ⚠️ RX uniquement (pas TX)
- ⚠️ Bande passante limitée (2.4 MHz)
- ⚠️ Moins performant que B210

**Installation** :
```bash
sudo apt install rtl-sdr gr-osmosdr
rtl_test
```

---

## 📊 Comparaison

| Option | Coût | Détection Réelle | Difficulté |
|--------|------|------------------|------------|
| **Simulation** | 0€ | ❌ Non | ⭐ Facile |
| **WiFi Monitor** | 0-40€ | ✅ Oui | ⭐⭐ Moyen |
| **Fichiers IQ** | 0€ | ✅ Oui (replay) | ⭐⭐ Moyen |
| **RTL-SDR** | 25€ | ✅ Oui | ⭐⭐⭐ Avancé |
| **USRP B210** | 700€ | ✅ Oui | ⭐⭐⭐⭐ Expert |

---

## 🎯 Recommandation Immédiate

### Court Terme (Aujourd'hui)
```bash
# Tester le système complet en simulation
python3 test_without_usrp.py
```

### Moyen Terme (Cette Semaine)
1. **Si vous avez le USRP B210** :
   - Brancher sur USB 3.0
   - Exécuter : `bash setup_usrp_permissions.sh`
   - Tester : `uhd_find_devices`

2. **Si vous n'avez PAS le USRP** :
   - Tester adaptateur WiFi interne (`wlo1`)
   - Ou acheter adaptateur WiFi USB (~40€)
   - Ou acheter RTL-SDR (~25€)

---

## 📝 Prochaines Étapes

1. **Confirmer disponibilité USRP B210** :
   - Avez-vous le matériel physiquement ?
   - Est-il fonctionnel ?

2. **Choisir alternative** si pas de USRP :
   - WiFi Monitor (recommandé)
   - RTL-SDR (bon compromis)
   - Simulation (développement)

3. **Continuer développement** :
   - Tests unitaires
   - Dashboard MQTT
   - Sécurisation

---

**Date** : 16 Novembre 2025  
**Statut USRP** : ❌ Non détecté  
**Alternatives** : ✅ Disponibles
