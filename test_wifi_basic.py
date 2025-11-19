#!/usr/bin/env python3
"""
Test basique de réception WiFi avec gr-ieee802-11
Affiche tous les paquets WiFi décodés (pas seulement Remote ID)
"""

import logging
import time
import signal
import sys
from gnuradio import gr, blocks, uhd, fft
from gnuradio.fft import window
import ieee802_11
import pmt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BasicWiFiReceiver:
    def __init__(self, freq=2.437e9, gain=50, sample_rate=10e6):
        self.freq = freq
        self.gain = gain
        self.sample_rate = sample_rate
        self.running = False
        self.packet_count = 0

        logger.info("="*70)
        logger.info("Test Réception WiFi Basique")
        logger.info("="*70)
        logger.info(f"Fréquence: {freq/1e9:.3f} GHz")
        logger.info(f"Gain: {gain} dB")
        logger.info(f"Sample rate: {sample_rate/1e6:.1f} MS/s")
        logger.info("")

    def create_flowgraph(self):
        """Crée le flowgraph GNU Radio"""
        logger.info("Création flowgraph...")

        tb = gr.top_block("WiFi Test")

        # USRP Source
        usrp_source = uhd.usrp_source(
            ",".join(("type=b200", "")),
            uhd.stream_args(cpu_format="fc32", channels=[0]),
        )
        usrp_source.set_samp_rate(self.sample_rate)
        usrp_source.set_center_freq(self.freq, 0)
        usrp_source.set_gain(self.gain, 0)
        usrp_source.set_antenna('RX2', 0)

        # Paramètres WiFi
        sync_length = 320
        window_size = 48

        # Blocs de corrélation
        delay_16 = blocks.delay(gr.sizeof_gr_complex, 16)
        conjugate = blocks.conjugate_cc()
        multiply = blocks.multiply_vcc(1)
        moving_avg_corr = blocks.moving_average_cc(window_size, 1, 4000, 1)
        moving_avg_power = blocks.moving_average_ff(window_size + 16, 1, 4000, 1)
        complex_to_mag = blocks.complex_to_mag(1)
        complex_to_mag_sq = blocks.complex_to_mag_squared(1)
        divide = blocks.divide_ff(1)

        # Sync Short/Long
        sync_short = ieee802_11.sync_short(0.56, 2, False, False)
        delay_sync = blocks.delay(gr.sizeof_gr_complex, sync_length)
        sync_long = ieee802_11.sync_long(sync_length, False, False)

        # FFT et décodage
        stream_to_vec = blocks.stream_to_vector(gr.sizeof_gr_complex, 64)
        fft_block = fft.fft_vcc(64, True, window.rectangular(64), True, 1)
        frame_eq = ieee802_11.frame_equalizer(
            ieee802_11.COMB, self.freq, self.sample_rate, False, False
        )
        decode_mac = ieee802_11.decode_mac(True, False)  # log=True pour voir paquets

        # Message Debug
        msg_debug = blocks.message_debug()

        # Connexions
        tb.connect((usrp_source, 0), (delay_16, 0))
        tb.connect((delay_16, 0), (conjugate, 0))
        tb.connect((delay_16, 0), (sync_short, 0))

        tb.connect((usrp_source, 0), (multiply, 0))
        tb.connect((conjugate, 0), (multiply, 1))
        tb.connect((multiply, 0), (moving_avg_corr, 0))
        tb.connect((moving_avg_corr, 0), (complex_to_mag, 0))
        tb.connect((moving_avg_corr, 0), (sync_short, 1))

        tb.connect((usrp_source, 0), (complex_to_mag_sq, 0))
        tb.connect((complex_to_mag_sq, 0), (moving_avg_power, 0))
        tb.connect((complex_to_mag, 0), (divide, 0))
        tb.connect((moving_avg_power, 0), (divide, 1))
        tb.connect((divide, 0), (sync_short, 2))

        tb.connect((sync_short, 0), (sync_long, 0))
        tb.connect((sync_short, 0), (delay_sync, 0))
        tb.connect((delay_sync, 0), (sync_long, 1))

        tb.connect((sync_long, 0), (stream_to_vec, 0))
        tb.connect((stream_to_vec, 0), (fft_block, 0))
        tb.connect((fft_block, 0), (frame_eq, 0))
        tb.connect((frame_eq, 0), (decode_mac, 0))

        tb.msg_connect((decode_mac, 'out'), (msg_debug, 'store'))

        logger.info("✓ Flowgraph créé")
        return tb, msg_debug

    def process_packets(self, msg_debug):
        """Affiche tous les paquets reçus"""
        last_count = 0

        while self.running:
            time.sleep(0.5)

            num_messages = msg_debug.num_messages()

            if num_messages > last_count:
                new_packets = num_messages - last_count
                self.packet_count += new_packets
                logger.info(f"✅ {new_packets} nouveau(x) paquet(s) WiFi décodé(s)! Total: {self.packet_count}")

                # Afficher les paquets
                for i in range(last_count, num_messages):
                    msg = msg_debug.get_message(i)
                    if pmt.is_pair(msg):
                        data = pmt.cdr(msg)
                        packet_bytes = bytes(pmt.u8vector_elements(data))
                        logger.info(f"   Paquet #{i+1}: {len(packet_bytes)} octets")

                last_count = num_messages

    def start(self):
        """Démarre le test"""
        logger.info("\n🚀 Démarrage du test WiFi...")
        logger.info("   Activez un hotspot WiFi 2.4 GHz à proximité")
        logger.info("   Ou approchez un appareil WiFi de l'antenne")
        logger.info("")

        # Créer flowgraph
        self.tb, msg_debug = self.create_flowgraph()

        # Handler Ctrl+C
        def signal_handler(sig, frame):
            logger.info("\n\nArrêt...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)

        # Démarrer
        logger.info("Démarrage réception...")
        self.tb.start()
        logger.info("✓ Réception active\n")

        self.running = True

        # Traiter paquets
        try:
            self.process_packets(msg_debug)
        except KeyboardInterrupt:
            pass

        # Arrêt
        logger.info("\nArrêt...")
        self.running = False
        self.tb.stop()
        self.tb.wait()

        logger.info(f"\n📊 Total paquets WiFi décodés: {self.packet_count}")

        if self.packet_count == 0:
            logger.warning("\n⚠️  AUCUN paquet WiFi détecté!")
            logger.info("\nVérifications:")
            logger.info("  1. Hotspot WiFi 2.4 GHz activé à proximité?")
            logger.info("  2. Antenne connectée sur port RX2?")
            logger.info("  3. Essayer gain plus élevé: -g 60")
            logger.info("  4. Essayer autre canal: -f 2.412e9 (canal 1)")
        else:
            logger.info(f"\n✅ Système WiFi fonctionne! {self.packet_count} paquets décodés")
            logger.info("   → Vous pouvez maintenant tester avec votre drone")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test réception WiFi basique")
    parser.add_argument('-f', '--freq', type=float, default=2.437e9,
                       help='Fréquence (Hz)')
    parser.add_argument('-g', '--gain', type=float, default=50,
                       help='Gain (dB)')
    parser.add_argument('-s', '--sample-rate', type=float, default=10e6,
                       help='Sample rate (Hz) - 10 MS/s recommandé')

    args = parser.parse_args()

    receiver = BasicWiFiReceiver(
        freq=args.freq,
        gain=args.gain,
        sample_rate=args.sample_rate
    )

    receiver.start()
