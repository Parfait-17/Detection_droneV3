#!/usr/bin/env python3
"""
Test de détection de patterns Remote ID
Vérifie que le système peut détecter des patterns DJI et ASTM dans des données brutes
"""

import sys
sys.path.insert(0, '/home/parfait/Bureau/drone_detection_projectV2')

from src.remote_id_decoder import WiFiRemoteIDDecoder

def test_dji_pattern():
    """Test détection pattern DJI"""
    print("=" * 60)
    print("TEST 1: Détection Pattern DJI")
    print("=" * 60)
    
    decoder = WiFiRemoteIDDecoder()
    
    # Créer des données avec un pattern DJI
    test_data = b'\x00' * 50 + b'DJI-RID-MAVIC3PRO-12345' + b'\x00' * 50
    
    print(f"Données test: {len(test_data)} bytes")
    print(f"Pattern: DJI-RID-MAVIC3PRO-12345")
    
    # Recherche de pattern
    result = decoder.search_patterns_in_bytes(test_data)
    
    if result:
        print(f"✅ SUCCÈS - Pattern détecté!")
        print(f"   Type: {result['pattern_type']}")
        print(f"   Offset: {result['offset']}")
        if 'uas_id' in result:
            print(f"   UAS ID: {result['uas_id']}")
    else:
        print(f"❌ ÉCHEC - Aucun pattern détecté")
    
    # Test decode_from_raw_bytes
    print("\nTest decode_from_raw_bytes:")
    remote_id = decoder.decode_from_raw_bytes(test_data)
    
    if remote_id and remote_id.uas_id:
        print(f"✅ Remote ID décodé!")
        print(f"   UAS ID: {remote_id.uas_id}")
        print(f"   Type: {remote_id.uas_id_type}")
    else:
        print(f"❌ Pas de Remote ID décodé")
    
    print()

def test_astm_pattern():
    """Test détection pattern ASTM"""
    print("=" * 60)
    print("TEST 2: Détection Pattern ASTM F3411")
    print("=" * 60)
    
    decoder = WiFiRemoteIDDecoder()
    
    # Créer des données avec header ASTM
    test_data = b'\x00' * 30 + b'\x0D\x00' + b'ASTM_DATA_HERE' + b'\x00' * 30
    
    print(f"Données test: {len(test_data)} bytes")
    print(f"Pattern: ASTM header \\x0D\\x00")
    
    result = decoder.search_patterns_in_bytes(test_data)
    
    if result:
        print(f"✅ SUCCÈS - Pattern détecté!")
        print(f"   Type: {result['pattern_type']}")
        print(f"   Pattern hex: {result['pattern']}")
        print(f"   Offset: {result['offset']}")
    else:
        print(f"❌ ÉCHEC - Aucun pattern détecté")
    
    print()

def test_opendroneid_oui():
    """Test détection OUI OpenDroneID"""
    print("=" * 60)
    print("TEST 3: Détection OUI OpenDroneID")
    print("=" * 60)
    
    decoder = WiFiRemoteIDDecoder()
    
    # Créer des données avec OUI OpenDroneID
    test_data = b'\x00' * 40 + bytes([0xFA, 0x0B, 0xBC]) + b'REMOTE_ID_DATA' + b'\x00' * 40
    
    print(f"Données test: {len(test_data)} bytes")
    print(f"Pattern: OUI FA-0B-BC (OpenDroneID)")
    
    result = decoder.search_patterns_in_bytes(test_data)
    
    if result:
        print(f"✅ SUCCÈS - OUI détecté!")
        print(f"   Type: {result['pattern_type']}")
        print(f"   Pattern hex: {result['pattern']}")
        print(f"   Offset: {result['offset']}")
    else:
        print(f"❌ ÉCHEC - OUI non détecté")
    
    print()

def test_mavic_pattern():
    """Test détection simple MAVIC"""
    print("=" * 60)
    print("TEST 4: Détection Pattern MAVIC")
    print("=" * 60)
    
    decoder = WiFiRemoteIDDecoder()
    
    # Données avec juste MAVIC
    test_data = b'\xFF' * 25 + b'MAVIC' + b'\x00' * 25
    
    print(f"Données test: {len(test_data)} bytes")
    print(f"Pattern: MAVIC")
    
    result = decoder.search_patterns_in_bytes(test_data)
    
    if result:
        print(f"✅ SUCCÈS - Pattern MAVIC détecté!")
        print(f"   Type: {result['pattern_type']}")
    else:
        print(f"❌ ÉCHEC - Pattern non détecté")
    
    print()

def test_no_pattern():
    """Test données sans pattern (doit échouer)"""
    print("=" * 60)
    print("TEST 5: Données sans pattern (contrôle négatif)")
    print("=" * 60)
    
    decoder = WiFiRemoteIDDecoder()
    
    # Données aléatoires sans pattern
    test_data = b'RANDOM_DATA_WITHOUT_REMOTE_ID_PATTERNS_HERE'
    
    print(f"Données test: {len(test_data)} bytes")
    print(f"Attendu: Aucun pattern détecté")
    
    result = decoder.search_patterns_in_bytes(test_data)
    
    if result:
        print(f"❌ ÉCHEC - Pattern détecté alors qu'il ne devrait pas!")
        print(f"   Type: {result['pattern_type']}")
    else:
        print(f"✅ SUCCÈS - Aucun pattern détecté (correct)")
    
    print()

def main():
    print("\n" + "=" * 60)
    print("🧪 TESTS DE DÉTECTION DE PATTERNS REMOTE ID")
    print("=" * 60)
    print()
    
    # Exécuter tous les tests
    test_dji_pattern()
    test_astm_pattern()
    test_opendroneid_oui()
    test_mavic_pattern()
    test_no_pattern()
    
    print("=" * 60)
    print("✅ Tous les tests terminés!")
    print("=" * 60)
    print()
    print("📝 NOTES:")
    print("   • Le système peut maintenant détecter des patterns Remote ID")
    print("   • Ceci complète la détection basée sur OUI WiFi")
    print("   • Utile si Remote ID non-conforme aux standards IE")
    print()

if __name__ == "__main__":
    main()
