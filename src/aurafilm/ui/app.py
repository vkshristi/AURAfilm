import os, cv2, time, json
from PySide6 import QtWidgets, QtGui, QtCore
from ..utils.params import Params, ParamStore
from ..rt.engine import RTProcessor
from ..utils.config import read_config, write_config
from ..utils.presets import list_presets, load_preset_by_name, apply_preset_to_params, save_user_preset

class VideoWidget(QtWidgets.QLabel):
    def set_frame(self, bgr):
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h,w,ch = rgb.shape
        qimg = QtGui.QImage(rgb.data, w, h, ch*w, QtGui.QImage.Format.Format_RGB888)
        self.setPixmap(QtGui.QPixmap.fromImage(qimg))

class MainWindow(QtWidgets.QWidget):
    def __init__(self, camera_index=0):
        super().__init__()
        self.setWindowTitle("AURAfilm — Live Vintage")
        cfg = read_config()

        # Params & processor
        p = Params(width=cfg["width"], height=cfg["height"], preset_name=cfg["last_preset"])
        self.params = ParamStore(p)
        self.proc = RTProcessor(self.params)
        self.last_frame = None

        # --- Left: preview & status ---
        self.preview = VideoWidget()
        self.fps_label = QtWidgets.QLabel("FPS: --")

        # Resolution dropdown
        self.res_combo = QtWidgets.QComboBox()
        self.res_combo.addItems(["1280x720","1920x1080","640x480"])
        self.res_combo.setCurrentText(f"{p.width}x{p.height}")
        self.res_combo.currentTextChanged.connect(self.on_res_changed)

        # Preset controls
        self.preset_combo = QtWidgets.QComboBox()
        self._refresh_preset_combo()
        if self.preset_combo.findText(p.preset_name) >= 0:
            self.preset_combo.setCurrentText(p.preset_name)
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        self.btn_save_preset = QtWidgets.QPushButton("Save Preset…")
        self.btn_load_preset = QtWidgets.QPushButton("Load Preset YAML…")
        self.btn_reset = QtWidgets.QPushButton("Reset Sliders")
        self.btn_save_preset.clicked.connect(self.on_save_preset)
        self.btn_load_preset.clicked.connect(self.on_load_preset)
        self.btn_reset.clicked.connect(self.on_reset)

        # Sliders
        self.s_contrast = self._slider(10, 100, int(p.contrast*10), "Contrast")
        self.s_grain = self._slider(0, 50, int(p.grain_strength*100), "Grain")
        self.s_hal_str = self._slider(0, 100, int(p.hal_str*100), "Halation")
        self.s_bloom = self._slider(0, 100, int(p.bloom_str*100), "Bloom")
        self.s_vig = self._slider(0, 100, int(p.vignette_str*100), "Vignette")
        self.s_ca = self._slider(0, 20,  int(p.ca_pixels*10), "Chromatic Aberration")
        self.s_flicker = self._slider(0, 50, int(p.flicker*100), "Flicker")
        self.s_weave = self._slider(0, 10, int(p.weave), "Gate Weave")

        self.lock_grain = QtWidgets.QCheckBox("Lock Grain (no boil)")
        self.lock_grain.setChecked(p.lock_grain)
        self.lock_grain.stateChanged.connect(lambda _: self.params.update(lock_grain=self.lock_grain.isChecked()))

        # Buttons
        self.btn_photo = QtWidgets.QPushButton("Capture Photo")
        self.btn_rec = QtWidgets.QPushButton("Start Recording")
        self.btn_photo.clicked.connect(self.capture_photo)
        self.btn_rec.clicked.connect(self.toggle_recording)

        # Wire sliders
        self.s_contrast["slider"].valueChanged.connect(self.on_contrast)
        self.s_grain["slider"].valueChanged.connect(self.on_grain)
        self.s_hal_str["slider"].valueChanged.connect(self.on_hal)
        self.s_bloom["slider"].valueChanged.connect(self.on_bloom)
        self.s_vig["slider"].valueChanged.connect(self.on_vignette)
        self.s_ca["slider"].valueChanged.connect(self.on_ca)
        self.s_flicker["slider"].valueChanged.connect(self.on_flicker)
        self.s_weave["slider"].valueChanged.connect(self.on_weave)

        # Right panel layout
        right = QtWidgets.QFormLayout()
        right.addRow("Preset", self.preset_combo)
        right.addRow(self.btn_save_preset, self.btn_load_preset)
        right.addRow(self.btn_reset)
        right.addRow("Resolution", self.res_combo)
        right.addRow("FPS", self.fps_label)
        right.addRow(self.s_contrast["label"], self.s_contrast["slider"])
        right.addRow(self.s_grain["label"], self.s_grain["slider"])
        right.addRow(self.s_hal_str["label"], self.s_hal_str["slider"])
        right.addRow(self.s_bloom["label"], self.s_bloom["slider"])
        right.addRow(self.s_vig["label"], self.s_vig["slider"])
        right.addRow(self.s_ca["label"], self.s_ca["slider"])
        right.addRow(self.s_flicker["label"], self.s_flicker["slider"])
        right.addRow(self.s_weave["label"], self.s_weave["slider"])
        right.addRow(self.lock_grain)
        right.addRow(self.btn_photo, self.btn_rec)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.preview, stretch=3)
        col = QtWidgets.QWidget(); col.setLayout(right)
        layout.addWidget(col, stretch=1)

        # Camera
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        self._apply_resolution(p.width, p.height)

        # Timer loop
        self.rec = False
        self.writer = None
        self.t_last = time.time()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(0)

        os.makedirs("captures", exist_ok=True)

        # Apply the startup preset if found
        self._apply_current_preset()

        # Window size from config
        self.resize(*read_config().get("window", [1200,700]))

    # ---------- helpers ----------
    def _slider(self, lo, hi, val, text):
        s = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s.setRange(lo, hi); s.setValue(val)
        return {"slider": s, "label": QtWidgets.QLabel(text)}

    def _apply_resolution(self, w,h):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

    def _refresh_preset_combo(self):
        names = []
        for p in list_presets():
            try:
                d = __import__("yaml").safe_load(open(p, "r", encoding="utf-8"))
                if d and "name" in d: names.append(d["name"])
            except Exception:
                pass
        self.preset_combo.clear()
        self.preset_combo.addItems(sorted(set(names)))

    def _apply_current_preset(self):
        name = self.preset_combo.currentText()
        preset = load_preset_by_name(name)
        if preset:
            apply_preset_to_params(preset, self.params.snapshot())
            self._sync_sliders_from_params()
            # tone/vignette caches need recompute
            self.proc.params_changed(recalc_tone=True, recalc_vignette=True)

    def _sync_sliders_from_params(self):
        p = self.params.snapshot()
        self.s_contrast["slider"].setValue(int(p.contrast*10))
        self.s_grain["slider"].setValue(int(p.grain_strength*100))
        self.s_hal_str["slider"].setValue(int(p.hal_str*100))
        self.s_bloom["slider"].setValue(int(p.bloom_str*100))
        self.s_vig["slider"].setValue(int(p.vignette_str*100))
        self.s_ca["slider"].setValue(int(p.ca_pixels*10))
        self.s_flicker["slider"].setValue(int(p.flicker*100))
        self.s_weave["slider"].setValue(int(p.weave))

    # ---------- slider handlers ----------
    def on_contrast(self, v):
        self.params.update(contrast=max(0.1, v/10.0))
        self.proc.params_changed(recalc_tone=True, recalc_vignette=False)
    def on_grain(self, v): self.params.update(grain_strength=v/100.0)
    def on_hal(self, v):   self.params.update(hal_str=v/100.0)
    def on_bloom(self, v): self.params.update(bloom_str=v/100.0)
    def on_vignette(self, v):
        self.params.update(vignette_str=v/100.0)
        self.proc.params_changed(recalc_tone=False, recalc_vignette=True)
    def on_ca(self, v):    self.params.update(ca_pixels=v/10.0)
    def on_flicker(self, v): self.params.update(flicker=v/100.0)
    def on_weave(self, v):   self.params.update(weave=float(v))

    # ---------- preset actions ----------
    def on_preset_changed(self, _name):
        self.params.update(preset_name=self.preset_combo.currentText())
        self._apply_current_preset()

    def on_save_preset(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not name.strip(): return
        path = save_user_preset(name.strip(), self.params.snapshot())
        QtWidgets.QMessageBox.information(self, "Saved", f"Saved preset:\n{path}")
        self._refresh_preset_combo()
        idx = self.preset_combo.findText(name.strip())
        if idx >= 0: self.preset_combo.setCurrentIndex(idx)

    def on_load_preset(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Preset YAML", "", "YAML Files (*.yaml *.yml)")
        if not path: return
        import yaml
        try:
            preset = yaml.safe_load(open(path, "r", encoding="utf-8"))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Could not load preset:\n{e}")
            return
        apply_preset_to_params(preset, self.params.snapshot())
        self.params.update(preset_name=preset.get("name", os.path.splitext(os.path.basename(path))[0]))
        self._sync_sliders_from_params()
        self.proc.params_changed(recalc_tone=True, recalc_vignette=True)
        self._refresh_preset_combo()
        i = self.preset_combo.findText(self.params.snapshot().preset_name)
        if i>=0: self.preset_combo.setCurrentIndex(i)

    def on_reset(self):
        # Reload the selected preset defaults
        self._apply_current_preset()

    # ---------- resolution / main loop ----------
    def on_res_changed(self, text):
        w,h = map(int, text.split("x"))
        self.params.update(width=w, height=h)
        self._apply_resolution(w,h)
        self.proc.params_changed(recalc_tone=False, recalc_vignette=True)

    def tick(self):
        ok, frame = self.cap.read()
        if not ok: return
        p = self.params.snapshot()
        if frame.shape[1]!=p.width or frame.shape[0]!=p.height:
            frame = cv2.resize(frame, (p.width, p.height))
        out = self.proc.process(frame)
        self.last_frame = out
        self.preview.set_frame(out)

        now = time.time()
        dt = now - getattr(self, "_t_last", now)
        if dt>0: self.fps_label.setText(f"FPS: {int(1.0/dt)}")
        self._t_last = now

        if getattr(self, "rec", False) and getattr(self, "writer", None):
            self.writer.write(out)

    # ---------- capture / record ----------
    def capture_photo(self):
        if self.last_frame is None: return
        ts = QtCore.QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
        base = f"captures/{ts}_{self.params.snapshot().preset_name}"
        cv2.imwrite(base + ".jpg", self.last_frame)
        # optional metadata sidecar
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump(self.params.to_dict(), f, indent=2)

    def toggle_recording(self):
        rec = getattr(self, "rec", False)
        self.rec = not rec
        if self.rec:
            ts = QtCore.QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            p = self.params.snapshot()
            base = f"captures/{ts}_{p.preset_name}"
            self.writer = cv2.VideoWriter(base + ".mp4", fourcc, 30, (p.width, p.height))
            with open(base + ".json", "w", encoding="utf-8") as f:
                json.dump(self.params.to_dict(), f, indent=2)
            self.btn_rec.setText("Stop Recording")
        else:
            if getattr(self, "writer", None):
                self.writer.release(); self.writer=None
            self.btn_rec.setText("Start Recording")

    # ---------- persist window + last settings ----------
    def closeEvent(self, e):
        p = self.params.snapshot()
        cfg = {
            "last_preset": p.preset_name,
            "width": p.width, "height": p.height,
            "window": [self.width(), self.height()]
        }
        write_config(cfg)
        return super().closeEvent(e)
