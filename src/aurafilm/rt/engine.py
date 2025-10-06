import cv2, numpy as np
from numpy.random import default_rng
from .nodes import (lut_from_tone, apply_tone_lut, halation, bloom,
                    chrom_aberration, vignette_mask, apply_vignette, grain)

class RTProcessor:
    def __init__(self, param_store):
        self.params_store = param_store
        self._lut = None
        self._mask = None
        self._last_size = (0,0)
        self._rng_locked = default_rng(0)     # no "boiling" when locked
        self._rng_live   = default_rng(12345) # dynamic grain
        self._frame_idx = 0

    def _ensure_cache(self, w,h,p):
        if self._lut is None:
            self._lut = lut_from_tone(p)
        if self._mask is None or self._last_size!=(w,h):
            self._mask = vignette_mask(w,h, p.vignette_str, p.vignette_round)
            self._last_size=(w,h)

    def params_changed(self, recalc_tone=True, recalc_vignette=True):
        p = self.params_store.snapshot()
        if recalc_tone:
            self._lut = lut_from_tone(p)
        if recalc_vignette:
            self._mask = None  # recompute on next frame

    def process(self, frame_bgr):
        p = self.params_store.snapshot()
        h,w = frame_bgr.shape[:2]
        self._ensure_cache(w,h,p)

        img = apply_tone_lut(frame_bgr, self._lut)
        rng = self._rng_locked if p.lock_grain else self._rng_live
        img = grain(img, p.grain_strength, p.grain_scale, rng)
        img = halation(img, p)
        img = bloom(img, p.bloom_radius, p.bloom_str)
        img = chrom_aberration(img, p.ca_pixels)

        # Flicker (multiplicative luma drift)
        if p.flicker>1e-4:
            k = 1.0 + p.flicker*(np.sin(self._frame_idx*0.21)*0.6 + np.sin(self._frame_idx*0.037)*0.4)
            img = np.clip(img.astype(np.float32)*k, 0, 255).astype(np.uint8)

        # Gate weave (tiny translation)
        if p.weave>1e-4:
            dx = int(np.sin(self._frame_idx*0.013)*p.weave)
            dy = int(np.cos(self._frame_idx*0.017)*p.weave)
            M = np.float32([[1,0,dx],[0,1,dy]])
            img = cv2.warpAffine(img, M, (w,h), borderMode=cv2.BORDER_REFLECT)

        img = apply_vignette(img, self._mask)
        self._frame_idx += 1
        return img
