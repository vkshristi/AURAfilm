import os, json
CFG_DIR  = os.path.join(os.path.expanduser("~"), ".aurafilm")
CFG_PATH = os.path.join(CFG_DIR, "config.json")
os.makedirs(CFG_DIR, exist_ok=True)

DEFAULT_CFG = {
    "last_preset": "portra_00s",
    "width": 1280,
    "height": 720,
    "window": [1200, 700]
}

def read_config():
    if not os.path.exists(CFG_PATH):
        return DEFAULT_CFG.copy()
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # fill defaults for any missing keys
        for k, v in DEFAULT_CFG.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return DEFAULT_CFG.copy()

def write_config(cfg: dict):
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass
