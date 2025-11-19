"""
MODULE 4B: Décodage Remote ID (remote_id_decoder.py)
Démodulation WiFi 802.11 et extraction des informations Remote ID (ASTM F3411)
"""

import numpy as np
from typing import Optional, Dict, List, Tuple
import struct
import logging
from dataclasses import dataclass
from datetime import datetime
import string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RemoteIDData:
    """
    Structure pour les données Remote ID
    """
    # Basic ID
    uas_id: Optional[str] = None  # ID de l'UAS
    uas_id_type: Optional[str] = None  # Type d'ID (Serial, CAA, UUID, etc.)

    # Location/Vector
    latitude: Optional[float] = None  # Latitude du drone (degrés)
    longitude: Optional[float] = None  # Longitude du drone (degrés)
    altitude_msl: Optional[float] = None  # Altitude MSL (m)
    altitude_agl: Optional[float] = None  # Altitude AGL (m)
    height: Optional[float] = None  # Hauteur (m)
    speed: Optional[float] = None  # Vitesse (m/s)
    direction: Optional[float] = None  # Direction (degrés)
    vertical_speed: Optional[float] = None  # Vitesse verticale (m/s)

    # Operator Location
    operator_latitude: Optional[float] = None
    operator_longitude: Optional[float] = None
    operator_altitude: Optional[float] = None
    operator_id: Optional[str] = None

    # System info
    timestamp: Optional[float] = None
    status: Optional[str] = None
    classification: Optional[str] = None

    # Self ID
    self_id_text: Optional[str] = None

    # Authentication (single-page capture)
    auth_type: Optional[int] = None
    auth_page_index: Optional[int] = None
    auth_last_page_index: Optional[int] = None
    auth_payload: Optional[bytes] = None

    # System fields (minimal)
    system_category: Optional[int] = None
    system_eu_class: Optional[int] = None
    system_operator_location_type: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            'uas_id': self.uas_id,
            'uas_id_type': self.uas_id_type,
            'position': {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'altitude_msl': self.altitude_msl,
                'altitude_agl': self.altitude_agl,
                'height': self.height
            },
            'velocity': {
                'speed': self.speed,
                'direction': self.direction,
                'vertical_speed': self.vertical_speed
            },
            'operator': {
                'latitude': self.operator_latitude,
                'longitude': self.operator_longitude,
                'altitude': self.operator_altitude,
                'id': self.operator_id
            },
            'timestamp': self.timestamp,
            'status': self.status,
            'classification': self.classification,
            'self_id': self.self_id_text,
            'auth': {
                'type': self.auth_type,
                'page_index': self.auth_page_index,
                'last_page_index': self.auth_last_page_index,
                'payload_hex': self.auth_payload.hex().upper() if isinstance(self.auth_payload, (bytes, bytearray)) else None
            },
            'system': {
                'category': self.system_category,
                'eu_class': self.system_eu_class,
                'operator_location_type': self.system_operator_location_type
            }
        }


class WiFiRemoteIDDecoder:
    """
    Décodeur WiFi Remote ID pour drones
    Implémente le standard ASTM F3411 (Remote ID)
    """

    # Wi-Fi Alliance OpenDroneID OUI (ASTM F3411 / ASD-STAN)
    ODID_OUI = bytes([0xFA, 0x0B, 0xBC])
    
    # Patterns Remote ID authentiques pour recherche brute
    AUTHENTIC_PATTERNS = {
        'dji_remote_id': [
            b'DJI-RID-',     # DJI Remote ID officiel
            b'MAVIC',         # Mavic series
            b'MINI',          # Mini series
            b'AIR',           # Air series
            b'FPV'            # FPV series
        ],
        'astm_f3411': [
            b'\x0D\x00',     # ASTM F3411 Remote ID header
            b'\x25\x00',     # OpenDroneID header
            b'\x1A\x00'      # Autre variante ASTM
        ],
        'opendroneid': [
            bytes([0xFA, 0x0B, 0xBC]),  # OpenDroneID OUI
        ]
    }
    
    # Message types ASTM F3411
    MSG_TYPE_BASIC_ID = 0x0
    MSG_TYPE_LOCATION = 0x1
    MSG_TYPE_AUTH = 0x2
    MSG_TYPE_SELF_ID = 0x3
    MSG_TYPE_SYSTEM = 0x4
    MSG_TYPE_OPERATOR_ID = 0x5

    # UAS ID Types
    ID_TYPES = {
        0: "None",
        1: "Serial Number",
        2: "CAA Registration ID",
        3: "UTM UUID",
        4: "Specific Session ID"
    }

    def __init__(self, sample_rate: float = 25e6):
        """
        Initialise le décodeur Remote ID

        Args:
            sample_rate: Taux d'échantillonnage
        """
        self.sample_rate = sample_rate
        logger.info("Décodeur WiFi Remote ID initialisé")

    def _decode_printable(self, b: bytes) -> str:
        s = b.decode('utf-8', errors='ignore').rstrip('\x00')
        printable = ''.join(ch for ch in s if 32 <= ord(ch) <= 126)
        if len(printable) >= max(6, len(s) // 2):
            return printable
        return b.hex().upper()

    def demodulate_wifi_beacon(self, iq_samples: np.ndarray) -> Optional[bytes]:
        """
        Démodule un signal WiFi 802.11 Beacon Frame

        Args:
            iq_samples: Échantillons I/Q du signal WiFi

        Returns:
            Octets bruts de la trame ou None
        """
        # Note: Cette implémentation est simplifiée
        # Une vraie démodulation WiFi nécessiterait:
        # 1. Synchronisation temporelle (détection du préambule)
        # 2. Estimation et correction du CFO (Carrier Frequency Offset)
        # 3. Estimation du canal
        # 4. Égalisation OFDM
        # 5. Décodage des symboles OFDM (QAM)
        # 6. Désentrelacement et décodage convolutionnel

        logger.debug("Démodulation WiFi beacon (implémentation simplifiée)")

        # Pour cette implémentation, nous simulons la détection
        # Dans un cas réel, on utiliserait une bibliothèque comme GNU Radio
        # ou une implémentation SDR complète

        # Placeholder: retourne None car la vraie démodulation est complexe
        return None

    def parse_beacon_frame(self, frame_bytes: bytes) -> Optional[Dict]:
        """
        Parse une trame Beacon 802.11

        Args:
            frame_bytes: Octets de la trame

        Returns:
            Dictionnaire avec les informations de la trame
        """
        if len(frame_bytes) < 36:  # Taille minimale d'un beacon
            return None

        try:
            # En-tête 802.11
            # 0-1: Frame Control
            # 2-3: Duration
            # 4-9: Destination Address (broadcast FF:FF:FF:FF:FF:FF)
            # 10-15: Source Address (adresse du drone)
            # 16-21: BSSID
            # 22-23: Sequence Control

            frame_control = struct.unpack('<H', frame_bytes[0:2])[0]
            src_addr = ':'.join([f'{b:02x}' for b in frame_bytes[10:16]])
            bssid = ':'.join([f'{b:02x}' for b in frame_bytes[16:22]])

            # Beacon frame body commence à l'offset 24
            # 24-31: Timestamp
            # 32-33: Beacon interval
            # 34-35: Capability info

            timestamp = struct.unpack('<Q', frame_bytes[24:32])[0]
            beacon_interval = struct.unpack('<H', frame_bytes[32:34])[0]
            capability = struct.unpack('<H', frame_bytes[34:36])[0]

            result = {
                'frame_control': frame_control,
                'src_addr': src_addr,
                'bssid': bssid,
                'timestamp': timestamp,
                'beacon_interval': beacon_interval,
                'capability': capability
            }

            # Parsing des Information Elements (IE)
            ies = self._parse_information_elements(frame_bytes[36:])
            result['information_elements'] = ies

            return result

        except Exception as e:
            logger.error(f"Erreur lors du parsing de la trame beacon: {e}")
            return None

    def parse_beacon_body(self, body_bytes: bytes) -> Optional[Dict]:
        if len(body_bytes) < 12:
            return None
        try:
            timestamp = struct.unpack('<Q', body_bytes[0:8])[0]
            beacon_interval = struct.unpack('<H', body_bytes[8:10])[0]
            capability = struct.unpack('<H', body_bytes[10:12])[0]
            ies = self._parse_information_elements(body_bytes[12:])
            return {
                'timestamp': timestamp,
                'beacon_interval': beacon_interval,
                'capability': capability,
                'information_elements': ies
            }
        except Exception:
            return None

    def _parse_information_elements(self, ie_data: bytes) -> List[Dict]:
        """
        Parse les Information Elements d'une trame beacon

        Args:
            ie_data: Données des IEs

        Returns:
            Liste de dictionnaires pour chaque IE
        """
        ies = []
        offset = 0

        while offset < len(ie_data) - 2:
            ie_id = ie_data[offset]
            ie_len = ie_data[offset + 1]

            if offset + 2 + ie_len > len(ie_data):
                break

            ie_content = ie_data[offset + 2:offset + 2 + ie_len]

            ies.append({
                'id': ie_id,
                'length': ie_len,
                'data': ie_content
            })

            offset += 2 + ie_len

        return ies

    def extract_remote_id(self, beacon_info: Dict) -> Optional[RemoteIDData]:
        """
        Extrait les informations Remote ID d'une trame beacon

        Args:
            beacon_info: Informations de la trame beacon

        Returns:
            Objet RemoteIDData ou None
        """
        if 'information_elements' not in beacon_info:
            return None

        # Recherche du Vendor Specific IE pour Remote ID
        # IE ID 221 (0xDD) = Vendor Specific
        # OUI pour Remote ID: FA-0B-BC (Wi-Fi Alliance OpenDroneID)

        remote_id_data = RemoteIDData()
        remote_id_data.timestamp = datetime.now().timestamp()

        for ie in beacon_info['information_elements']:
            if ie['id'] == 0xDD:  # Vendor Specific IE
                # Vérifier si c'est du Remote ID
                data = ie['data']

                if len(data) < 4:
                    continue

                # OUI (3 octets) + Type (1 octet)
                oui = data[0:3]
                vendor_type = data[3]
                try:
                    logger.debug(f"Vendor IE: OUI={oui.hex('-')}, type={vendor_type}, len={len(data)}")
                except Exception:
                    pass

                # Filtrer uniquement les IEs avec l'OUI OpenDroneID
                if oui != self.ODID_OUI:
                    continue
                    
                logger.info(f"✓ Remote ID Vendor IE détecté (OUI={oui.hex('-')})")

                # Parsing du contenu Remote ID
                if len(data) > 4:
                    self._parse_remote_id_messages(data[4:], remote_id_data)

        if remote_id_data.uas_id or remote_id_data.latitude:
            return remote_id_data

        return None

    def _parse_remote_id_messages(self, data: bytes, remote_id: RemoteIDData):
        """
        Parse les messages Remote ID contenus dans le Vendor IE

        Args:
            data: Données du message
            remote_id: Objet RemoteIDData à remplir
        """
        offset = 0

        while offset < len(data):
            if offset + 1 >= len(data):
                break

            msg_type = data[offset]
            offset += 1

            # Basic ID Message (Type 0)
            if msg_type == self.MSG_TYPE_BASIC_ID:
                remaining = len(data) - offset
                if remaining >= 21:
                    id_type = data[offset]
                    uas_id_bytes = data[offset + 1:offset + 21]
                    remote_id.uas_id_type = self.ID_TYPES.get(id_type, "Unknown")
                    remote_id.uas_id = self._decode_printable(uas_id_bytes)
                    adv = 21
                    if remaining >= 23 and data[offset + 21] == 0x00 and data[offset + 22] == 0x00:
                        adv = 23
                    offset += adv

            # Location/Vector Message (Type 1)
            elif msg_type == self.MSG_TYPE_LOCATION:
                if offset + 23 <= len(data):
                    # Status (1 byte)
                    status = data[offset]

                    # Direction (1 byte, 0-360 degrés)
                    direction = data[offset + 1]

                    # Speed (1 byte, 0.25 m/s resolution)
                    speed_encoded = data[offset + 2]

                    # Vertical speed (1 byte, 0.5 m/s resolution, signed)
                    vspeed_encoded = struct.unpack('b', bytes([data[offset + 3]]))[0]

                    # Latitude (4 bytes, 1e-7 degrés)
                    lat_encoded = struct.unpack('<i', data[offset + 4:offset + 8])[0]

                    # Longitude (4 bytes, 1e-7 degrés)
                    lon_encoded = struct.unpack('<i', data[offset + 8:offset + 12])[0]

                    # Altitude (2 bytes, 0.5m resolution)
                    alt_encoded = struct.unpack('<h', data[offset + 12:offset + 14])[0]

                    # Height (2 bytes, 0.5m resolution)
                    height_encoded = struct.unpack('<h', data[offset + 14:offset + 16])[0]

                    # Décodage
                    remote_id.status = "Airborne" if status & 0x0F else "Ground"
                    remote_id.direction = float(direction) if direction != 0xFF else None
                    remote_id.speed = float(speed_encoded) * 0.25 if speed_encoded != 0xFF else None
                    remote_id.vertical_speed = float(vspeed_encoded) * 0.5 if vspeed_encoded != 0x7F else None

                    if lat_encoded != 0:
                        remote_id.latitude = lat_encoded * 1e-7

                    if lon_encoded != 0:
                        remote_id.longitude = lon_encoded * 1e-7

                    if alt_encoded != -1000:
                        remote_id.altitude_msl = alt_encoded * 0.5

                    if height_encoded != -1000:
                        remote_id.height = height_encoded * 0.5

                    offset += 23

            # Authentication (Type 2)
            elif msg_type == self.MSG_TYPE_AUTH:
                if offset + 4 <= len(data):
                    a_type = data[offset]
                    a_page = data[offset + 1]
                    a_last = data[offset + 2]
                    a_len = data[offset + 3]
                    offset += 4
                    if offset + a_len <= len(data):
                        a_payload = data[offset:offset + a_len]
                        remote_id.auth_type = int(a_type)
                        remote_id.auth_page_index = int(a_page)
                        remote_id.auth_last_page_index = int(a_last)
                        remote_id.auth_payload = bytes(a_payload)
                        offset += a_len
                    else:
                        break

            # Self ID (Type 3)
            elif msg_type == self.MSG_TYPE_SELF_ID:
                if offset + 24 <= len(data):
                    d_type = data[offset]
                    text_bytes = data[offset + 1:offset + 24]
                    remote_id.self_id_text = self._decode_printable(text_bytes)
                    offset += 24
                else:
                    break

            # System (Type 4)
            elif msg_type == self.MSG_TYPE_SYSTEM:
                if offset + 3 <= len(data):
                    op_loc = data[offset]
                    eu_cls = data[offset + 1]
                    cat = data[offset + 2]
                    remote_id.system_operator_location_type = int(op_loc)
                    remote_id.system_eu_class = int(eu_cls)
                    remote_id.system_category = int(cat)
                    offset += 3
                else:
                    break

            # Operator ID Message (Type 5)
            elif msg_type == self.MSG_TYPE_OPERATOR_ID:
                if offset + 21 <= len(data):
                    op_id_type = data[offset]
                    op_id_bytes = data[offset + 1:offset + 21]
                    remote_id.operator_id = self._decode_printable(op_id_bytes)
                    offset += 21
            else:
                # Message type inconnu, passer au suivant
                offset += 1

    def detect_and_decode_remote_id(self, iq_samples: np.ndarray) -> Optional[RemoteIDData]:
        """
        Détecte et décode les informations Remote ID d'un signal

        Args:
            iq_samples: Échantillons I/Q

        Returns:
            RemoteIDData ou None
        """
        logger.info("Détection et décodage Remote ID")

        # Étape 1: Démodulation WiFi
        frame_bytes = self.demodulate_wifi_beacon(iq_samples)

        if frame_bytes is None:
            logger.debug("Aucune trame WiFi détectée")
            return None

        # Étape 2: Parsing de la trame beacon
        beacon_info = self.parse_beacon_frame(frame_bytes)

        if beacon_info is None:
            logger.debug("Impossible de parser la trame beacon")
            return None

        # Étape 3: Extraction Remote ID
        remote_id = self.extract_remote_id(beacon_info)

        if remote_id:
            logger.info(f"Remote ID décodé: UAS ID={remote_id.uas_id}, "
                       f"Position=({remote_id.latitude}, {remote_id.longitude})")

        return remote_id

    def search_patterns_in_bytes(self, data: bytes) -> Optional[Dict]:
        """
        Recherche de patterns Remote ID authentiques dans des données brutes
        Méthode complémentaire pour détecter Remote ID non-conformes
        
        Args:
            data: Données brutes à analyser
            
        Returns:
            Dict avec infos si pattern trouvé, None sinon
        """
        for pattern_type, patterns in self.AUTHENTIC_PATTERNS.items():
            for pattern in patterns:
                # Recherche du pattern
                offset = data.find(pattern)
                if offset != -1:
                    # Pattern trouvé!
                    logger.info(f"✓ Pattern {pattern_type} détecté à offset {offset}")
                    logger.debug(f"  Pattern bytes: {pattern.hex()}")
                    
                    # Essayer de parser depuis cette position
                    remaining = data[offset:]
                    
                    # Pour DJI, extraire l'ID si possible
                    if pattern_type == 'dji_remote_id' and len(remaining) >= 20:
                        try:
                            # L'ID DJI suit généralement le pattern
                            id_end = remaining.find(b'\x00')  # Chercher null terminator
                            if id_end > len(pattern):
                                uas_id = remaining[:id_end].decode('ascii', errors='ignore')
                                return {
                                    'pattern_type': pattern_type,
                                    'pattern': pattern.hex(),
                                    'offset': offset,
                                    'uas_id': uas_id,
                                    'confidence': 'pattern_match'
                                }
                        except:
                            pass
                    
                    return {
                        'pattern_type': pattern_type,
                        'pattern': pattern.hex(),
                        'offset': offset,
                        'confidence': 'pattern_match'
                    }
        
        return None
    
    def decode_from_raw_bytes(self, raw_data: bytes) -> Optional[RemoteIDData]:
        """
        Décode directement depuis des octets bruts (utile pour les tests)
        Maintenant avec recherche de patterns en fallback

        Args:
            raw_data: Données brutes contenant le Remote ID

        Returns:
            RemoteIDData ou None
        """
        remote_id = RemoteIDData()
        remote_id.timestamp = datetime.now().timestamp()

        # Méthode 1: Parsing ASTM structuré
        self._parse_remote_id_messages(raw_data, remote_id)
        
        # Vérifier si l'ID est valide (pas juste des zéros/espaces)
        def is_valid_id(uas_id: Optional[str]) -> bool:
            if not uas_id:
                return False
            # Enlever les null bytes, zéros ASCII, espaces, et tirets
            cleaned = uas_id.replace('\x00', '').replace('0', '').replace(' ', '').replace('-', '').strip()
            # Un ID valide doit contenir au moins quelques caractères significatifs
            return len(cleaned) >= 3
        
        # Si pas de résultat valide, essayer la recherche de patterns
        if not is_valid_id(remote_id.uas_id) and not remote_id.latitude:
            pattern_info = self.search_patterns_in_bytes(raw_data)
            if pattern_info:
                # Remplir les données depuis le pattern
                remote_id.uas_id = pattern_info.get('uas_id', f"PATTERN_{pattern_info['pattern_type']}")
                remote_id.uas_id_type = f"Pattern Detection ({pattern_info['pattern_type']})"
                logger.info(f"Remote ID détecté via pattern: {remote_id.uas_id}")

        return remote_id

    def create_test_remote_id_packet(self) -> bytes:
        """
        Crée un paquet Remote ID de test

        Returns:
            Octets d'un message Remote ID de test
        """
        packet = bytearray()

        # Basic ID Message
        packet.append(self.MSG_TYPE_BASIC_ID)  # Type
        packet.append(1)  # ID Type: Serial Number

        # UAS ID: "DJI-TEST-001" (20 bytes)
        uas_id = b"DJI-TEST-001".ljust(20, b'\x00')
        packet.extend(uas_id)

        packet.append(0)  # Reserved
        packet.append(0)  # Reserved

        # Location Message
        packet.append(self.MSG_TYPE_LOCATION)  # Type
        packet.append(0x01)  # Status: Airborne

        packet.append(87)  # Direction: 87 degrés
        packet.append(int(12.3 / 0.25))  # Speed: 12.3 m/s

        packet.append(int(2.5 / 0.5))  # Vertical speed: 2.5 m/s

        # Latitude: 12.3585° → 123585000
        lat_encoded = int(12.3585 * 1e7)
        packet.extend(struct.pack('<i', lat_encoded))

        # Longitude: -1.5352° → -15352000
        lon_encoded = int(-1.5352 * 1e7)
        packet.extend(struct.pack('<i', lon_encoded))

        # Altitude MSL: 120.5m → 241
        alt_encoded = int(120.5 / 0.5)
        packet.extend(struct.pack('<h', alt_encoded))

        # Height AGL: 45.2m → 90
        height_encoded = int(45.2 / 0.5)
        packet.extend(struct.pack('<h', height_encoded))

        # Timestamp, etc.
        packet.extend(b'\x00' * 5)

        return bytes(packet)


def test_remote_id_decoder():
    """
    Fonction de test pour le décodeur Remote ID
    """
    logger.info("=== Test du décodeur Remote ID ===")

    decoder = WiFiRemoteIDDecoder()

    # Test 1: Création et décodage d'un paquet de test
    logger.info("\n--- Test 1: Paquet de test ---")
    test_packet = decoder.create_test_remote_id_packet()
    logger.info(f"Paquet de test créé: {len(test_packet)} octets")

    remote_id = decoder.decode_from_raw_bytes(test_packet)

    if remote_id:
        logger.info("\nInformations Remote ID décodées:")
        logger.info(f"  UAS ID: {remote_id.uas_id} (Type: {remote_id.uas_id_type})")
        logger.info(f"  Position: ({remote_id.latitude:.6f}°, {remote_id.longitude:.6f}°)")
        logger.info(f"  Altitude MSL: {remote_id.altitude_msl:.1f} m")
        logger.info(f"  Hauteur AGL: {remote_id.height:.1f} m")
        logger.info(f"  Vitesse: {remote_id.speed:.1f} m/s")
        logger.info(f"  Direction: {remote_id.direction}°")
        logger.info(f"  Vitesse verticale: {remote_id.vertical_speed:.1f} m/s")
        logger.info(f"  Status: {remote_id.status}")

        # Conversion en dictionnaire
        data_dict = remote_id.to_dict()
        logger.info(f"\nDonnées sous forme de dictionnaire:")
        import json
        logger.info(json.dumps(data_dict, indent=2))
    else:
        logger.warning("Échec du décodage")

    logger.info("\nTest terminé")


if __name__ == "__main__":
    test_remote_id_decoder()
