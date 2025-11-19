#!/usr/bin/env python3
"""
Main GNU Radio WiFi Remote ID
Système complet avec gr-ieee802-11 pour démodulation WiFi robuste
"""

import logging
import time
import signal
import sys
import threading
from queue import Queue
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('drone_detection_gnuradio.log')
    ]
)

logger = logging.getLogger(__name__)


class GNURadioWiFiRemoteIDSystem:
    """
    Système de détection Remote ID avec GNU Radio + gr-ieee802-11
    """

    def __init__(self, freq=2.437e9, gain=50, sample_rate=20e6,
                 channels=None, hop_interval=2.0, include_5ghz=False,
                 uhd_device_args="type=b200,master_clock_rate=32e6,num_recv_frames=256,recv_frame_size=16384",
                 mqtt_publisher=None):
        """
        Initialise le système

        Args:
            freq: Fréquence centrale (Hz)
            gain: Gain USRP (dB)
            sample_rate: Taux d'échantillonnage (Hz)
        """
        logger.info("="*70)
        logger.info("Système de Détection Remote ID - GNU Radio WiFi")
        logger.info("USRP B210 → gr-ieee802-11 → Remote ID Decoder")
        logger.info("="*70)

        self.freq = freq
        self.gain = gain
        self.sample_rate = sample_rate
        self.running = False
        self.detection_count = 0
        self.uhd_device_args = uhd_device_args
        self.mqtt_publisher = mqtt_publisher

        # Balayage de canaux
        self.channels = channels if channels is not None else [2412e6, 2437e6, 2462e6]
        if include_5ghz:
            self.channels += [5180e6, 5200e6]  # ch36/ch40 (optionnel)
        self.hop_interval = hop_interval
        self._hopper_thread = None

        # Compteurs de trames pour valider le format d'émission
        self.frame_counts = {
            'mgmt_beacon': 0,
            'mgmt_action': 0,
            'mgmt_probe_resp': 0,
            'ctrl': 0,
            'data': 0,
            'other': 0
        }

        # File de messages
        self.packet_queue = Queue()

        # Vérifier dépendances
        self._check_dependencies()

        # Initialiser modules
        self._initialize_modules()

    def _check_dependencies(self):
        """Vérifie que toutes les dépendances sont installées"""
        logger.info("\nVérification des dépendances...")

        try:
            from gnuradio import gr
            logger.info("  ✓ GNU Radio")
        except ImportError:
            logger.error("  ✗ GNU Radio non installé")
            logger.error("  → Lancer: ./INSTALL_GNURADIO.sh")
            sys.exit(1)

        try:
            from gnuradio import uhd
            logger.info("  ✓ UHD (USRP)")
        except ImportError:
            logger.error("  ✗ UHD non installé")
            raise RuntimeError("GNU Radio UHD module not installed")

        try:
            import ieee802_11
            logger.info("  ✓ gr-ieee802-11")
        except ImportError:
            logger.error("  ✗ gr-ieee802-11 non installé")
            logger.error("  → Lancer: ./INSTALL_GNURADIO.sh")
            raise RuntimeError("gr-ieee802-11 module not installed")

        logger.info("✓ Toutes les dépendances sont installées\n")

    def _initialize_modules(self):
        """Initialise tous les modules"""
        from src.remote_id_decoder import WiFiRemoteIDDecoder
        from src.mqtt_publisher import MQTTPublisher

        logger.info("--- Initialisation des modules ---")

        # Décodeur Remote ID
        logger.info("1. Initialisation décodeur Remote ID...")
        self.decoder = WiFiRemoteIDDecoder()

        # MQTT Publisher
        logger.info("2. Initialisation MQTT...")
        if not self.mqtt_publisher:
            self.mqtt_publisher = MQTTPublisher(
                broker_host='localhost',
                broker_port=1883,
                client_id='gnuradio_remote_id'
            )

        # GNU Radio Flowgraph (sera créé au start)
        self.tb = None

        logger.info("\n✓ Modules initialisés")

    def _create_flowgraph(self):
        """Crée le flowgraph GNU Radio"""
        from gnuradio import gr, blocks, uhd, fft
        from gnuradio.fft import window
        import ieee802_11
        import pmt

        logger.info("\n--- Création du flowgraph GNU Radio ---")

        # Top block
        tb = gr.top_block("WiFi Remote ID Receiver")

        # USRP Source
        logger.info("1. Configuration USRP B210...")
        usrp_source = uhd.usrp_source(
            ",".join((self.uhd_device_args, "")),
            uhd.stream_args(
                cpu_format="fc32",
                channels=[0],
            ),
        )
        # Source d'horloge explicite pour B210
        try:
            usrp_source.set_clock_source('internal')
        except Exception:
            pass
        usrp_source.set_samp_rate(self.sample_rate)
        usrp_source.set_center_freq(self.freq, 0)
        usrp_source.set_gain(self.gain, 0)
        usrp_source.set_antenna('RX2', 0)
        try:
            usrp_source.set_min_output_buffer(1 << 18)
        except Exception:
            pass

        # Conserver une référence pour le channel hopping
        self.usrp_source = usrp_source

        logger.info(f"   Fréquence: {self.freq/1e9:.3f} GHz")
        logger.info(f"   Gain: {self.gain} dB")
        logger.info(f"   Sample rate: {self.sample_rate/1e6:.1f} MS/s")

        # IEEE 802.11 Receiver Chain
        logger.info("2. Configuration chaîne récepteur WiFi...")

        # Paramètres WiFi
        sync_length = 320  # Longueur sync pour BPSK
        window_size = 48   # Taille fenêtre corrélation

        # === Blocs de corrélation pour Sync Short ===
        # Delay de 16 échantillons (durée d'une séquence courte WiFi)
        delay_16 = blocks.delay(gr.sizeof_gr_complex, 16)

        # Conjugué du signal retardé
        conjugate = blocks.conjugate_cc()

        # Multiplication pour autocorrélation
        multiply = blocks.multiply_vcc(1)

        # Moyennes mobiles
        moving_avg_corr = blocks.moving_average_cc(window_size, 1, 4000, 1)
        moving_avg_power = blocks.moving_average_ff(window_size + 16, 1, 4000, 1)

        # Magnitude
        complex_to_mag = blocks.complex_to_mag(1)
        complex_to_mag_sq = blocks.complex_to_mag_squared(1)

        # Division pour normalisation
        divide = blocks.divide_ff(1)

        # Sync Short - Détection préambule court
        sync_short = ieee802_11.sync_short(0.56, 2, False, False)

        # Delay pour sync_long
        delay_sync = blocks.delay(gr.sizeof_gr_complex, sync_length)

        # Sync Long - Détection préambule long
        sync_long = ieee802_11.sync_long(sync_length, False, False)

        # Stream to Vector (OFDM symbols = 64 subcarriers)
        stream_to_vec = blocks.stream_to_vector(gr.sizeof_gr_complex, 64)

        # FFT (OFDM demodulation)
        fft_block = fft.fft_vcc(64, True, window.rectangular(64), True, 1)

        # Frame Equalizer - Égalisation canal
        frame_eq = ieee802_11.frame_equalizer(
            ieee802_11.COMB,  # Equalizer algorithm
            self.freq,        # Center frequency
            self.sample_rate, # Bandwidth
            False,            # log
            False             # debug
        )

        # Decode MAC - Décodage trame MAC
        decode_mac = ieee802_11.decode_mac(False, False)

        # Message Debug (pour capturer les paquets)
        msg_debug = blocks.message_debug()

        # Connections de la chaîne WiFi
        logger.info("3. Connexion flowgraph...")

        # === Branch 1: Signal retardé pour sync_short ===
        tb.connect((usrp_source, 0), (delay_16, 0))
        tb.connect((delay_16, 0), (conjugate, 0))
        tb.connect((delay_16, 0), (sync_short, 0))  # Input 0: signal retardé

        # === Branch 2: Autocorrélation pour sync_short ===
        tb.connect((usrp_source, 0), (multiply, 0))
        tb.connect((conjugate, 0), (multiply, 1))
        tb.connect((multiply, 0), (moving_avg_corr, 0))
        tb.connect((moving_avg_corr, 0), (complex_to_mag, 0))
        tb.connect((moving_avg_corr, 0), (sync_short, 1))  # Input 1: autocorrélation

        # === Branch 3: Puissance/Seuil pour sync_short ===
        tb.connect((usrp_source, 0), (complex_to_mag_sq, 0))
        tb.connect((complex_to_mag_sq, 0), (moving_avg_power, 0))
        tb.connect((complex_to_mag, 0), (divide, 0))
        tb.connect((moving_avg_power, 0), (divide, 1))
        tb.connect((divide, 0), (sync_short, 2))  # Input 2: seuil normalisé

        # === Sync Short → Sync Long ===
        tb.connect((sync_short, 0), (sync_long, 0))
        tb.connect((sync_short, 0), (delay_sync, 0))
        tb.connect((delay_sync, 0), (sync_long, 1))

        # === Sync Long → FFT → Frame EQ → Decode MAC ===
        tb.connect((sync_long, 0), (stream_to_vec, 0))
        tb.connect((stream_to_vec, 0), (fft_block, 0))
        tb.connect((fft_block, 0), (frame_eq, 0))
        tb.connect((frame_eq, 0), (decode_mac, 0))

        # Message connection (paquets MAC décodés)
        tb.msg_connect((decode_mac, 'out'), (msg_debug, 'store'))

        logger.info("✓ Flowgraph créé")

        return tb, msg_debug

    def _process_packets_thread(self, msg_debug):
        """Thread qui traite les paquets WiFi reçus"""
        import pmt

        logger.info("Thread de traitement des paquets démarré")

        last_check = time.time()
        check_interval = 0.05  # Vérifier toutes les 50ms (plus réactif)
        last_processed = 0  # index du dernier message traité

        while self.running:
            try:
                # Vérifier périodiquement
                if time.time() - last_check < check_interval:
                    time.sleep(0.005)  # Sleep plus court pour réactivité
                    continue

                last_check = time.time()

                # Récupérer nombre de messages
                num_messages = msg_debug.num_messages()

                if num_messages <= last_processed:
                    continue

                # Traiter uniquement les nouveaux messages
                for i in range(last_processed, num_messages):
                    msg = msg_debug.get_message(i)

                    if not pmt.is_pair(msg):
                        continue

                    meta = pmt.car(msg)
                    data = pmt.cdr(msg)

                    try:
                        packet_bytes = bytes(pmt.u8vector_elements(data))
                        self._process_wifi_pdu(meta, packet_bytes)
                    except Exception as e:
                        logger.debug(f"Erreur traitement paquet: {e}")

                # Marquer jusqu'où on a traité
                last_processed = num_messages

            except Exception as e:
                logger.error(f"Erreur dans thread traitement: {e}")
                time.sleep(0.1)

        logger.info("Thread de traitement arrêté")

    def _process_wifi_pdu(self, meta, packet_bytes):
        """
        Traite un paquet WiFi décodé

        Args:
            packet_bytes: Paquet WiFi (bytes)
        """
        logger.debug(f"Paquet WiFi reçu: {len(packet_bytes)} octets")

        try:
            import pmt as _pmt
            try:
                md = _pmt.to_python(meta)
            except Exception:
                md = None
            if isinstance(md, dict):
                ft = md.get(b'frame_type', md.get('frame_type'))
                fs = md.get(b'frame_subtype', md.get('frame_subtype'))
                if ft is None:
                    ft = md.get(b'type', md.get('type'))
                if fs is None:
                    fs = md.get(b'subtype', md.get('subtype'))
                try:
                    if ft is not None:
                        ftv = int(ft)
                        fsv = int(fs) if fs is not None else -1
                        if ftv == 0:
                            if fsv == 8:
                                self.frame_counts['mgmt_beacon'] += 1
                            elif fsv == 13:
                                self.frame_counts['mgmt_action'] += 1
                            elif fsv == 5:
                                self.frame_counts['mgmt_probe_resp'] += 1
                            else:
                                self.frame_counts['other'] += 1
                        elif ftv == 1:
                            self.frame_counts['ctrl'] += 1
                        elif ftv == 2:
                            self.frame_counts['data'] += 1
                        else:
                            self.frame_counts['other'] += 1
                except Exception:
                    pass
        except Exception:
            pass

        # Compter le type de trame uniquement si l'en-tête semble présent
        if len(packet_bytes) >= 24:
            fc0 = packet_bytes[0]
            ftype = (fc0 >> 2) & 0x3
            fsub = (fc0 >> 4) & 0xF
            if ftype == 0:
                if fsub == 8:
                    self.frame_counts['mgmt_beacon'] += 1
                elif fsub == 13:
                    self.frame_counts['mgmt_action'] += 1
                elif fsub == 5:
                    self.frame_counts['mgmt_probe_resp'] += 1
                else:
                    self.frame_counts['other'] += 1
            elif ftype == 1:
                self.frame_counts['ctrl'] += 1
            elif ftype == 2:
                self.frame_counts['data'] += 1
            else:
                self.frame_counts['other'] += 1

        # Parser trame Beacon
        beacon_info = self.decoder.parse_beacon_frame(packet_bytes)

        if beacon_info is not None:
            logger.info("✓ Trame Beacon WiFi détectée")
            remote_id = self.decoder.extract_remote_id(beacon_info)

            if remote_id and remote_id.uas_id:
                self._handle_remote_id(remote_id, method='wifi_beacon')
            else:
                logger.debug("Beacon sans Remote ID")
            return

        beacon_body = self.decoder.parse_beacon_body(packet_bytes)
        if beacon_body is not None:
            remote_id = self.decoder.extract_remote_id(beacon_body)
            if remote_id and (remote_id.uas_id or (remote_id.latitude is not None and remote_id.longitude is not None)):
                self._handle_remote_id(remote_id, method='wifi_beacon_body')
                return

        # Tenter décodage depuis trames Action / NAN en scannant le payload
        rid = self._try_decode_from_bytes(packet_bytes)
        if rid and (rid.uas_id or (rid.latitude is not None and rid.longitude is not None)):
            self._handle_remote_id(rid, method='wifi_action_nan')

    def _try_decode_from_bytes(self, data: bytes):
        """Essaie d'extraire un Remote ID en scannant des octets arbitraires."""
        try:
            rid = self.decoder.decode_from_raw_bytes(data)
            if rid:
                has_location = (rid.latitude is not None and rid.longitude is not None)
                uas_id = rid.uas_id or ""
                uas_id_type = (rid.uas_id_type or "").lower()
                
                # Types valides incluent maintenant les détections par pattern
                allowed_types = {"serial number", "caa registration id", "utm uuid", 
                               "specific session id", "pattern detection"}
                
                # Pattern detection est toujours accepté
                is_pattern_detection = "pattern detection" in uas_id_type

                def is_plausible_ascii(s: str) -> bool:
                    if not s:
                        return False
                    if len(s) < 6 or len(s) > 32:
                        return False
                    for ch in s:
                        o = ord(ch)
                        if not (32 <= o <= 126):
                            return False
                    return True

                id_ok = ((uas_id_type in allowed_types) and is_plausible_ascii(uas_id)) or is_pattern_detection

                if id_ok or has_location:
                    return rid
        except Exception:
            pass
        n = len(data)
        for i in range(max(0, n - 128)):
            chunk = data[i:]
            try:
                rid = self.decoder.decode_from_raw_bytes(chunk)
                if rid:
                    has_location = (rid.latitude is not None and rid.longitude is not None)
                    uas_id = rid.uas_id or ""
                    uas_id_type = (rid.uas_id_type or "").lower()
                    allowed_types = {"serial number", "caa registration id", "utm uuid", "specific session id"}

                    def is_plausible_ascii(s: str) -> bool:
                        if not s:
                            return False
                        if len(s) < 6 or len(s) > 32:
                            return False
                        for ch in s:
                            o = ord(ch)
                            if not (32 <= o <= 126):
                                return False
                        return True

                    id_ok = (uas_id_type in allowed_types) and is_plausible_ascii(uas_id)

                    if id_ok or has_location:
                        return rid
            except Exception:
                continue
        return None

    def _handle_remote_id(self, remote_id, method: str):
        self.detection_count += 1
        self._display_remote_id(remote_id)
        if self.mqtt_publisher and self.mqtt_publisher.connected:
            detection_data = {
                'remote_id': remote_id.to_dict(),
                'timestamp': time.time(),
                'method': method,
                'frequency_hz': self.freq,
                'gain_db': self.gain,
                'detection_number': self.detection_count
            }
            self.mqtt_publisher.publish_detection(detection_data)

    def _channel_hopper(self):
        """Thread de hopping des canaux Wi‑Fi."""
        if not hasattr(self, 'usrp_source') or not self.channels:
            return
        idx = 0
        while self.running:
            try:
                freq = self.channels[idx % len(self.channels)]
                self.usrp_source.set_center_freq(freq, 0)
                self.freq = freq
                logger.info(f"↪️  Retune USRP: {freq/1e9:.3f} GHz")
                time.sleep(self.hop_interval)
                idx += 1
            except Exception as e:
                logger.warning(f"Erreur hopping canal: {e}")
                time.sleep(self.hop_interval)

    def _display_remote_id(self, remote_id):
        """Affiche les informations Remote ID"""
        logger.info("\n" + "="*70)
        logger.info("🎯 REMOTE ID DÉTECTÉ via GNU Radio + gr-ieee802-11")
        logger.info("="*70)

        logger.info(f"\n📡 Informations Radio:")
        logger.info(f"   Fréquence: {self.freq/1e9:.3f} GHz")
        logger.info(f"   Gain: {self.gain} dB")
        logger.info(f"   Méthode: gr-ieee802-11 (Décodage WiFi robuste)")

        logger.info(f"\n🆔 Identifiant:")
        logger.info(f"   UAS ID: {remote_id.uas_id}")
        logger.info(f"   Type: {remote_id.uas_id_type}")

        if remote_id.latitude and remote_id.longitude:
            logger.info(f"\n📍 Position Drone:")
            logger.info(f"   Latitude: {remote_id.latitude:.6f}°")
            logger.info(f"   Longitude: {remote_id.longitude:.6f}°")
            logger.info(f"   Altitude MSL: {remote_id.altitude_msl:.1f} m")
            logger.info(f"   Hauteur AGL: {remote_id.height:.1f} m")

        if remote_id.speed is not None:
            logger.info(f"\n🚁 Vélocité:")
            logger.info(f"   Vitesse: {remote_id.speed:.1f} m/s ({remote_id.speed*3.6:.1f} km/h)")
            logger.info(f"   Direction: {remote_id.direction}°")

        if remote_id.operator_latitude and remote_id.operator_longitude:
            logger.info(f"\n👤 Opérateur:")
            logger.info(f"   Position: ({remote_id.operator_latitude:.6f}°, "
                       f"{remote_id.operator_longitude:.6f}°)")

        logger.info(f"\n📊 Détection #{self.detection_count}")
        logger.info(f"   Statut: {remote_id.status}")
        logger.info("="*70 + "\n")

    def start(self, use_signals: bool = True):
        """Démarre le système"""
        logger.info("\n" + "="*70)
        logger.info("DÉMARRAGE DU SYSTÈME GNU Radio WiFi")
        logger.info("="*70 + "\n")

        # Connexion MQTT
        logger.info("Connexion MQTT...")
        if not self.mqtt_publisher.connect():
            logger.warning("MQTT non connecté - Mode autonome")

        # Créer flowgraph
        self.tb, msg_debug = self._create_flowgraph()

        # Handlers d'arrêt
        if use_signals:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

        # Démarrer flowgraph
        logger.info("\nDémarrage du flowgraph GNU Radio...")
        self.tb.start()
        logger.info("✓ Flowgraph démarré")

        # Démarrer thread de traitement
        self.running = True
        processing_thread = threading.Thread(
            target=self._process_packets_thread,
            args=(msg_debug,),
            daemon=True
        )
        processing_thread.start()

        logger.info("\n🚀 Système actif - En attente de Remote ID WiFi")
        logger.info("   Appuyez sur Ctrl+C pour arrêter\n")

        # Démarrer le channel hopping (1/6/11 par défaut)
        if self.channels and len(self.channels) > 1:
            self._hopper_thread = threading.Thread(target=self._channel_hopper, daemon=True)
            self._hopper_thread.start()

        # Boucle principale (heartbeat)
        last_heartbeat = time.time()
        heartbeat_interval = 60

        try:
            while self.running:
                time.sleep(1)

                # Heartbeat
                if time.time() - last_heartbeat > heartbeat_interval:
                    self.mqtt_publisher.publish_heartbeat()
                    logger.info(
                        f"📊 Remote IDs détectés: {self.detection_count} | "
                        f"Frames: beacon={self.frame_counts['mgmt_beacon']}, "
                        f"action={self.frame_counts['mgmt_action']}, "
                        f"probe_resp={self.frame_counts['mgmt_probe_resp']}, "
                        f"data={self.frame_counts['data']}, ctrl={self.frame_counts['ctrl']}"
                    )
                    last_heartbeat = time.time()

        except KeyboardInterrupt:
            logger.info("\nInterruption utilisateur")

        self.stop()

    def _signal_handler(self, signum, frame):
        """Gère Ctrl+C"""
        logger.info("\nSignal d'arrêt reçu...")
        self.stop()

    def stop(self):
        """Arrête le système"""
        logger.info("\n" + "="*70)
        logger.info("ARRÊT DU SYSTÈME")
        logger.info("="*70)

        self.running = False

        if self.tb:
            logger.info("Arrêt flowgraph GNU Radio...")
            self.tb.stop()
            self.tb.wait()

        if self.mqtt_publisher and self.mqtt_publisher.connected:
            logger.info("Déconnexion MQTT...")
            self.mqtt_publisher.disconnect()

        logger.info(f"\n📊 Statistiques:")
        logger.info(f"   Remote IDs détectés: {self.detection_count}")

        logger.info("\n✓ Système arrêté")
        logger.info("="*70 + "\n")


def main():
    """Point d'entrée"""
    parser = argparse.ArgumentParser(
        description="Détection Remote ID via GNU Radio + gr-ieee802-11"
    )
    parser.add_argument(
        '-f', '--freq',
        type=float,
        default=2.437e9,
        help='Fréquence centrale en Hz (défaut: 2.437 GHz - canal 6)'
    )
    parser.add_argument(
        '-g', '--gain',
        type=float,
        default=50,
        help='Gain USRP en dB (défaut: 50)'
    )
    parser.add_argument(
        '-s', '--sample-rate',
        type=float,
        default=20e6,
        help='Taux échantillonnage en Hz (défaut: 20 MS/s)'
    )
    parser.add_argument(
        '--scan-channels',
        type=str,
        default='1,6,11',
        help='Canaux à scanner: "all" pour 2.4+5 GHz, liste (ex: 1,6,11), ou format avancé ex: 2g:1-13,5g:36,40,44,48. Vide pour désactiver.'
    )
    parser.add_argument(
        '--hop-interval',
        type=float,
        default=7.0,
        help='Intervalle de hopping (secondes)'
    )
    parser.add_argument(
        '--include-5ghz',
        action='store_true',
        help='Inclure quelques canaux 5 GHz (36/40) au scanning'
    )
    parser.add_argument(
        '--uhd-args',
        type=str,
        default='type=b200,master_clock_rate=32e6,num_recv_frames=256,recv_frame_size=16384',
        help='Arguments UHD device pour la source USRP'
    )
    parser.add_argument(
        '--uhd-serial',
        type=str,
        default='',
        help='Numéro de série USRP à cibler (facultatif)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Mode verbeux (debug)'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Lancement
    try:
        # Construire la liste de fréquences à partir des canaux
        channels_arg = (args.scan_channels or '').strip().lower()
        channels_list = []
        if channels_arg:
            try:
                def ch_to_freq_2g(ch):
                    return 2412e6 + 5e6 * (ch - 1)
                def ch_to_freq_5g(ch):
                    return 5000e6 + 5e6 * ch

                def add_range_2g(start, end):
                    s = int(start); e = int(end)
                    for ch in range(s, e + 1):
                        if 1 <= ch <= 13:
                            channels_list.append(ch_to_freq_2g(ch))

                def add_list_5g(lst):
                    for ch in lst:
                        c = int(ch)
                        channels_list.append(ch_to_freq_5g(c))

                if channels_arg == 'all':
                    add_range_2g(1, 13)
                    add_list_5g([36, 40, 44, 48, 149, 153, 157, 161])
                else:
                    parts = [p.strip() for p in channels_arg.split(',') if p.strip()]
                    for p in parts:
                        if p.startswith('2g:'):
                            rng = p[3:]
                            if '-' in rng:
                                a, b = rng.split('-', 1)
                                add_range_2g(int(a), int(b))
                            else:
                                for tok in rng.split('/'):
                                    if tok:
                                        channels_list.append(ch_to_freq_2g(int(tok)))
                        elif p.startswith('5g:'):
                            rng = p[3:]
                            if rng == 'common':
                                add_list_5g([36, 40, 44, 48, 149, 153, 157, 161])
                            elif '-' in rng:
                                a, b = rng.split('-', 1)
                                a = int(a); b = int(b)
                                step = 4
                                for ch in range(a, b + 1, step):
                                    add_list_5g([ch])
                            else:
                                for tok in rng.split('/'):
                                    if tok:
                                        add_list_5g([int(tok)])
                        else:
                            channels_list.append(ch_to_freq_2g(int(p)))

                    channels_list = sorted(set(channels_list))
            except Exception:
                channels_list = [2412e6, 2437e6, 2462e6]

        if channels_arg == 'all' and args.hop_interval < 7.0:
            logger.info("Ajustement hop-interval à 7.0s pour scanning étendu")
            args.hop_interval = 7.0

        if getattr(args, 'uhd_serial', ''):
            if 'serial=' not in args.uhd_args:
                if args.uhd_args and not args.uhd_args.endswith(','):
                    args.uhd_args = args.uhd_args + f",serial={args.uhd_serial}"
                else:
                    args.uhd_args = args.uhd_args + f"serial={args.uhd_serial}"

        system = GNURadioWiFiRemoteIDSystem(
            freq=args.freq,
            gain=args.gain,
            sample_rate=args.sample_rate,
            channels=channels_list,
            hop_interval=args.hop_interval,
            include_5ghz=args.include_5ghz,
            uhd_device_args=args.uhd_args
        )
        system.start()
    except KeyboardInterrupt:
        logger.info("\nInterruption utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
