import threading
import time
import argparse
from typing import Optional, Dict, Any

try:
    import yaml
except Exception:
    yaml = None

from src.mqtt_publisher import MQTTPublisher
from src.ble_scanner import BLERemoteIDScanner
from main_gnuradio_wifi import GNURadioWiFiRemoteIDSystem


class AutoModeRIDOrchestrator:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.mqtt: Optional[MQTTPublisher] = None
        self.ble: Optional[BLERemoteIDScanner] = None
        self.wifi: Optional[GNURadioWiFiRemoteIDSystem] = None
        self._wifi_thread: Optional[threading.Thread] = None
        self._running = False

    def _init_mqtt(self):
        mqtt_cfg = (self.config.get('mqtt') if self.config else None) or {}
        self.mqtt = MQTTPublisher(
            broker_host=mqtt_cfg.get('broker_host', 'localhost'),
            broker_port=mqtt_cfg.get('broker_port', 1883),
            client_id=mqtt_cfg.get('client_id', 'auto_rid'),
            username=mqtt_cfg.get('username'),
            password=mqtt_cfg.get('password'),
            use_tls=mqtt_cfg.get('use_tls', False),
            topics=mqtt_cfg.get('topics'),
            qos=mqtt_cfg.get('qos'),
            retain=mqtt_cfg.get('retain', False)
        )
        self.mqtt.connect()

    def _init_ble(self):
        rid_cfg = (self.config.get('remote_id', {}) if self.config else {})
        ble_cfg = rid_cfg.get('ble', {})
        if ble_cfg.get('enabled', True):
            self.ble = BLERemoteIDScanner(
                mqtt=self.mqtt,
                scan_interval=float(ble_cfg.get('scan_interval_secs', 5.0))
            )

    def _init_wifi(self):
        rid_cfg = (self.config.get('remote_id', {}) if self.config else {})
        wifi_cfg = rid_cfg.get('wifi', {})
        if wifi_cfg.get('enabled', True) is False:
            self.wifi = None
            return
        include_5ghz = bool(wifi_cfg.get('include_5ghz', False))
        hop_interval = float(wifi_cfg.get('hop_interval_secs', 2.0))
        chans = wifi_cfg.get('channels')
        channels = None
        if isinstance(chans, list) and chans:
            def ch_to_freq_2g(ch):
                return 2412e6 + 5e6 * (int(ch) - 1)
            try:
                channels = [ch_to_freq_2g(int(x)) for x in chans]
            except Exception:
                channels = None
        acq = self.config.get('acquisition', {}) if self.config else {}
        try:
            self.wifi = GNURadioWiFiRemoteIDSystem(
                freq=float(acq.get('rx_freq_2g4', 2.437e9)),
                gain=float(acq.get('rx_gain', 50.0)),
                sample_rate=float(acq.get('sample_rate', 20e6)),
                channels=channels,
                hop_interval=hop_interval,
                include_5ghz=include_5ghz,
                mqtt_publisher=self.mqtt,
                uhd_device_args=str(acq.get('device_args', 'type=b200'))
            )
        except Exception:
            # Skip Wi‑Fi if dependencies missing
            self.wifi = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._init_mqtt()
        self._init_ble()
        self._init_wifi()
        if self.ble:
            self.ble.start()
        if self.wifi:
            self._wifi_thread = threading.Thread(target=self.wifi.start, kwargs={'use_signals': False}, daemon=True)
            self._wifi_thread.start()

    def stop(self):
        self._running = False
        try:
            if self.ble:
                self.ble.stop()
        except Exception:
            pass
        try:
            if self.wifi:
                self.wifi.stop()
        except Exception:
            pass
        try:
            if self.mqtt and self.mqtt.connected:
                self.mqtt.disconnect()
        except Exception:
            pass


def load_config(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path or yaml is None:
        return None
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='Auto-detection Remote ID orchestrator (BLE + Wi-Fi)')
    parser.add_argument('--config', type=str, default='config/config.yaml')
    args = parser.parse_args()
    cfg = load_config(args.config)
    orch = AutoModeRIDOrchestrator(cfg)
    orch.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        orch.stop()


if __name__ == '__main__':
    main()
