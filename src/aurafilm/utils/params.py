from dataclasses import dataclass, asdict
from threading import RLock

@dataclass
class Params:
    # resolution
    width: int = 1280
    height: int = 720
    # tone
    toe: float = 0.12
    shoulder: float = 0.88
    contrast: float = 5.2
    lift: float = 0.01
    gamma: float = 1.02
    gain: float = 1.03
    # grain
    grain_strength: float = 0.12
    grain_scale: float = 1.2
    lock_grain: bool = True
    # halation
    hal_thresh: float = 0.80
    hal_r: float = 8.0
    hal_g: float = 5.0
    hal_b: float = 3.0
    hal_str: float = 0.18
    # bloom
    bloom_radius: float = 7.0
    bloom_str: float = 0.15
    # optics
    ca_pixels: float = 0.6
    vignette_str: float = 0.18
    vignette_round: float = 0.7
    # temporal
    flicker: float = 0.02
    weave: float = 0.5
    # preset
    preset_name: str = "portra_00s"

class ParamStore:
    def __init__(self, p: Params):
        self._p = p
        self._lock = RLock()
    def snapshot(self) -> Params:
        with self._lock:
            return self._p
    def update(self, **kw):
        with self._lock:
            for k,v in kw.items():
                if hasattr(self._p, k):
                    setattr(self._p, k, v)
    def to_dict(self):
        with self._lock:
            return asdict(self._p)
