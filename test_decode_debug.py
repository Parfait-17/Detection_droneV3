#!/usr/bin/env python3
"""
Debug pour comprendre pourquoi decode_from_raw_bytes ne retourne pas l'ID du pattern
"""

import sys
sys.path.insert(0, '/home/parfait/Bureau/drone_detection_projectV2')

from src.remote_id_decoder import WiFiRemoteIDDecoder

decoder = WiFiRemoteIDDecoder()

# Créer des données avec un pattern DJI
test_data = b'\x00' * 50 + b'DJI-RID-MAVIC3PRO-12345' + b'\x00' * 50

print("Test data créé")
print(f"Longueur: {len(test_data)}")

# Test decode_from_raw_bytes
remote_id = decoder.decode_from_raw_bytes(test_data)

print(f"\nRemote ID object créé")
print(f"  uas_id: {repr(remote_id.uas_id)}")
print(f"  uas_id_type: {repr(remote_id.uas_id_type)}")
print(f"  latitude: {remote_id.latitude}")

# Test is_valid_id logic
uas_id = remote_id.uas_id
if uas_id:
    print(f"\nAnalyse uas_id:")
    print(f"  Length: {len(uas_id)}")
    print(f"  Repr: {repr(uas_id)}")
    cleaned = uas_id.replace('\x00', '').replace(' ', '').strip()
    print(f"  Cleaned: {repr(cleaned)}")
    print(f"  Cleaned length: {len(cleaned)}")
    print(f"  Is valid? {len(cleaned) > 0}")
