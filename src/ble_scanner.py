import asyncio
import threading
import time
from typing import Optional, Dict, Any, Callable

try:
    from bleak import BleakScanner
except Exception:
    BleakScanner = None

from src.remote_id_decoder import WiFiRemoteIDDecoder, RemoteIDData
from src.mqtt_publisher import MQTTPublisher


class BLERemoteIDScanner:
    def __init__(self, mqtt: Optional[MQTTPublisher] = None, scan_interval: float = 5.0,
                 on_remote_id: Optional[Callable[[RemoteIDData, Dict[str, Any]], None]] = None):
        self.mqtt = mqtt
        self.scan_interval = scan_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._decoder = WiFiRemoteIDDecoder()
        self._on_remote_id = on_remote_id

    def start(self):
        if BleakScanner is None:
            raise RuntimeError("bleak not available")
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _run_loop(self):
        asyncio.run(self._scan_loop())

    async def _scan_loop(self):
        while self._running:
            try:
                devices = await BleakScanner.discover(timeout=self.scan_interval, return_adv=True)
                for dev, adv in devices:
                    self._handle_adv(dev.address, adv)
            except Exception:
                await asyncio.sleep(1.0)

    def _handle_adv(self, addr: str, adv: Any):
        try:
            sd: Dict[str, bytes] = getattr(adv, "service_data", {}) or {}
            md: Dict[int, bytes] = getattr(adv, "manufacturer_data", {}) or {}
            candidates = []
            for _, v in sd.items():
                if isinstance(v, (bytes, bytearray)) and len(v) >= 5:
                    candidates.append(bytes(v))
            for _, v in md.items():
                if isinstance(v, (bytes, bytearray)) and len(v) >= 5:
                    candidates.append(bytes(v))
            for payload in candidates:
                rid = self._try_decode(payload)
                if rid:
                    self._publish(addr, rid)
        except Exception:
            pass

    def _try_decode(self, data: bytes) -> Optional[RemoteIDData]:
        try:
            rid = self._decoder.decode_from_raw_bytes(data)
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
            pass
        n = len(data)
        for i in range(max(0, n - 64)):
            chunk = data[i:]
            try:
                rid = self._decoder.decode_from_raw_bytes(chunk)
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

    def _publish(self, source: str, rid: RemoteIDData):
        if not self.mqtt or not self.mqtt.connected:
            pass
        payload = {
            "timestamp": time.time(),
            "method": "ble_advertising",
            "source_mac": source,
            "remote_id": rid.to_dict(),
        }
        try:
            if self.mqtt and self.mqtt.connected:
                self.mqtt.publish_detection(payload)
        except Exception:
            pass
        try:
            if self._on_remote_id:
                self._on_remote_id(rid, payload)
        except Exception:
            pass
