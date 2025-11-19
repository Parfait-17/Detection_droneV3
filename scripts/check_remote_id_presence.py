#!/usr/bin/env python3
import argparse
import logging
import sys
import threading
import time
from pathlib import Path

# Assure l'import depuis la racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main_gnuradio_wifi import GNURadioWiFiRemoteIDSystem


def parse_channels(ch_str: str):
    ch_str = (ch_str or "").strip()
    if not ch_str:
        return []
    chans = []
    for x in ch_str.split(','):
        x = x.strip()
        if not x:
            continue
        try:
            chans.append(int(x))
        except Exception:
            continue
    def ch_to_freq_2g(ch):
        return 2412e6 + 5e6 * (ch - 1)
    return [ch_to_freq_2g(ch) for ch in chans]


def main():
    p = argparse.ArgumentParser(description="Test de présence Remote ID (Wi‑Fi) avec USRP B210")
    p.add_argument('--channels', type=str, default='1,6,11', help='Canaux 2.4 GHz à scanner (ex: 1,6,11)')
    p.add_argument('--hop-interval', type=float, default=2.0, help='Intervalle de hopping (s)')
    p.add_argument('--timeout', type=int, default=60, help='Durée max du test (s)')
    p.add_argument('--gain', type=float, default=50.0, help='Gain USRP (dB)')
    p.add_argument('--sample-rate', type=float, default=20e6, help='Taux d\'échantillonnage (Hz)')
    p.add_argument('--uhd-args', type=str, default='type=b200,num_recv_frames=512,recv_frame_size=16360', help='Arguments UHD')
    p.add_argument('--include-5ghz', action='store_true', help='Inclure canaux 5 GHz (36/40)')
    p.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    args = p.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    channels_freq = parse_channels(args.channels)

    system = GNURadioWiFiRemoteIDSystem(
        freq=channels_freq[0] if channels_freq else 2.437e9,
        gain=args.gain,
        sample_rate=args.sample_rate,
        channels=channels_freq,
        hop_interval=args.hop_interval,
        include_5ghz=args.include_5ghz,
        uhd_device_args=args.uhd_args,
        mqtt_publisher=None
    )

    t = threading.Thread(target=lambda: system.start(use_signals=False), daemon=True)
    t.start()

    start_ts = time.time()
    last_stats = 0
    try:
        while True:
            time.sleep(0.5)
            if system.detection_count > 0:
                print("REMOTE ID: PRESENT")
                try:
                    system.stop()
                except Exception:
                    pass
                sys.exit(0)

            now = time.time()
            if now - start_ts > args.timeout:
                print("REMOTE ID: ABSENT")
                try:
                    system.stop()
                except Exception:
                    pass
                sys.exit(1)

            if now - last_stats > 5:
                last_stats = now
                fc = system.frame_counts
                print(f"Frames beacon={fc['mgmt_beacon']} action={fc['mgmt_action']} probe_resp={fc['mgmt_probe_resp']} data={fc['data']} ctrl={fc['ctrl']}")
    except KeyboardInterrupt:
        try:
            system.stop()
        except Exception:
            pass
        sys.exit(130)


if __name__ == '__main__':
    main()
