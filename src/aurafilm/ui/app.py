import os, cv2, time
from PySide6 import QtWidgets, QtGui, QtCore
from ..utils.params import Params, ParamStore
from ..rt.engine import RTProcessor

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
        self.params = ParamStore(Params())
        self.proc = RTProcessor(self.params)
        self.last_frame = None

        # Preview + status
        self.preview = VideoWidget()
        self.fps_label = QtWidgets.QLabel("FPS: --")
        self.res_combo = QtWidgets.QComboBox()
        self.res_combo.addItems(["1280x720","1920x1080","640x480"])
        self.res_combo.currentTextChanged.connect(self.on_res_changed)

        # Sliders
        self.s_contrast = self._slider(10, 100, int(self.params.snapshot().contrast*10), "Contrast")
        self.s_grain = self._slider(0, 50, int(self.params.snapshot().grain_strength*100), "Grain")
        self.s_hal_str = self._slider(0, 100, int(self.params.snapshot().hal_str*100), "Halation")
        self.s_bloom = self._slider(0, 100, int(self.params.snapshot().bloom_str*100), "Bloom")
        self.s_vig = self._slider(0, 100, int(self.params.snapshot().vignette_str*100), "Vignette")
        self.s_ca = self._slider(0, 20,  int(self.params.snapshot().ca_pixels*10), "Chromatic Aberration")
        self.s_flicker = self._slider(0, 50, int(self.params.snapshot().flicker*100), "Flicker")
        self.s_weave = self._slider(0, 10, int(self.params.snapshot().weave), "Gate Weave")

        self.lock_grain = QtWidgets.QCheckBox("Lock Grain (no boil)")
        self.lock_grain.setChecked(True)
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


        # Layout
        right = QtWidgets.QFormLayout()
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

        # Capture
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        self._apply_resolution(self.params.snapshot().width, self.params.snapshot().height)

        # Timer loop
        self.rec = False
        self.writer = None
        self.t_last = time.time()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(0)

        os.makedirs("captures", exist_ok=True)

    def _slider(self, lo, hi, val, text):
        s = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s.setRange(lo, hi); s.setValue(val)
        return {"slider": s, "label": QtWidgets.QLabel(text)}

    def _apply_resolution(self, w,h):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

    # Slider handlers
    def on_contrast(self, v):
        self.params.update(contrast=max(0.1, v/10.0))
        self.proc.params_changed(recalc_tone=True, recalc_vignette=False)
    def on_grain(self, v):
        self.params.update(grain_strength=v/100.0)
    def on_hal(self, v):
        self.params.update(hal_str=v/100.0)
    def on_bloom(self, v):
        self.params.update(bloom_str=v/100.0)
    def on_vignette(self, v):
        self.params.update(vignette_str=v/100.0)
        self.proc.params_changed(recalc_tone=False, recalc_vignette=True)
    def on_ca(self, v):
        self.params.update(ca_pixels=v/10.0)
    def on_flicker(self, v):
        self.params.update(flicker=v/100.0)
    def on_weave(self, v):
        self.params.update(weave=float(v))
    def on_res_changed(self, text):
        w,h = map(int, text.split("x"))
        self.params.update(width=w, height=h)
        self._apply_resolution(w,h)
        self.proc.params_changed(recalc_tone=False, recalc_vignette=True)

    # Main loop
    def tick(self):
        ok, frame = self.cap.read()
        if not ok:
            return
        p = self.params.snapshot()
        if frame.shape[1] != p.width or frame.shape[0] != p.height:
            frame = cv2.resize(frame, (p.width, p.height))
        out = self.proc.process(frame)
        self.last_frame = out
        self.preview.set_frame(out)

        # FPS
        now = time.time()
        dt = now - self.t_last
        if dt > 0:
            self.fps_label.setText(f"FPS: {int(1.0/dt)}")
        self.t_last = now

        # Recording
        if self.rec and self.writer:
            self.writer.write(out)

    # Capture & Record
    def capture_photo(self):
        if self.last_frame is None: return
        ts = QtCore.QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
        cv2.imwrite(f"captures/{ts}_{self.params.snapshot().preset_name}.jpg", self.last_frame)

    def toggle_recording(self):
        self.rec = not self.rec
        if self.rec:
            ts = QtCore.QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            p = self.params.snapshot()
            self.writer = cv2.VideoWriter(f"captures/{ts}_{p.preset_name}.mp4", fourcc, 30, (p.width, p.height))
            self.btn_rec.setText("Stop Recording")
        else:
            if self.writer:
                self.writer.release(); self.writer=None
            self.btn_rec.setText("Start Recording")
