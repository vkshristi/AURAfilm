import os, glob, yaml
from dataclasses import asdict
from .params import Params

PRESETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presets")
USER_PRESETS_DIR = os.path.join(os.path.expanduser("~"), ".aurafilm", "presets")
os.makedirs(USER_PRESETS_DIR, exist_ok=True)

def list_presets():
    files = []
    files += sorted(glob.glob(os.path.join(PRESETS_DIR, "*.yaml")))
    files += sorted(glob.glob(os.path.join(USER_PRESETS_DIR, "*.yaml")))
    return files

def load_preset_by_name(name: str) -> dict | None:
    for p in list_presets():
        try:
            data = yaml.safe_load(open(p, "r", encoding="utf-8"))
        except Exception:
            continue
        if data and data.get("name") == name:
            return data
    return None

def apply_preset_to_params(preset: dict, params: Params):
    if not preset: return params
    t = preset.get("tone", {})
    params.toe       = float(t.get("toe", params.toe))
    params.shoulder  = float(t.get("shoulder", params.shoulder))
    params.contrast  = float(t.get("contrast", params.contrast))
    params.lift      = float(t.get("lift", params.lift))
    params.gamma     = float(t.get("gamma", params.gamma))
    params.gain      = float(t.get("gain", params.gain))
    g = preset.get("grain", {})
    params.grain_strength = float(g.get("strength", params.grain_strength))
    params.grain_scale    = float(g.get("scale", params.grain_scale))
    h = preset.get("halation", {})
    params.hal_thresh = float(h.get("thresh", params.hal_thresh))
    params.hal_r      = float(h.get("r", params.hal_r))
    params.hal_g      = float(h.get("g", params.hal_g))
    params.hal_b      = float(h.get("b", params.hal_b))
    params.hal_str    = float(h.get("strength", params.hal_str))
    b = preset.get("bloom", {})
    params.bloom_radius = float(b.get("radius", params.bloom_radius))
    params.bloom_str    = float(b.get("strength", params.bloom_str))
    o = preset.get("optics", {})
    params.ca_pixels     = float(o.get("ca_pixels", params.ca_pixels))
    params.vignette_str  = float(o.get("vignette_strength", params.vignette_str))
    params.vignette_round= float(o.get("vignette_round", params.vignette_round))
    tm = preset.get("temporal", {})
    params.flicker = float(tm.get("flicker", params.flicker))
    params.weave   = float(tm.get("weave", params.weave))
    params.preset_name = preset.get("name", params.preset_name)
    return params

def export_preset_from_params(name: str, params: Params) -> dict:
    # Build a YAML-able dict from current Params
    return {
        "name": name,
        "tone": {
            "toe": params.toe, "shoulder": params.shoulder, "contrast": params.contrast,
            "lift": params.lift, "gamma": params.gamma, "gain": params.gain
        },
        "grain": { "strength": params.grain_strength, "scale": params.grain_scale },
        "halation": {
            "thresh": params.hal_thresh, "r": params.hal_r, "g": params.hal_g,
            "b": params.hal_b, "strength": params.hal_str
        },
        "bloom": { "radius": params.bloom_radius, "strength": params.bloom_str },
        "optics": {
            "ca_pixels": params.ca_pixels,
            "vignette_strength": params.vignette_str,
            "vignette_round": params.vignette_round
        },
        "temporal": { "flicker": params.flicker, "weave": params.weave }
    }

def save_user_preset(name: str, params: Params) -> str:
    data = export_preset_from_params(name, params)
    path = os.path.join(USER_PRESETS_DIR, f"{name}.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return path
