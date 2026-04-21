import sys
import pandas as pd
import numpy as np
import sounddevice as sd
import whisper
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class GraphPanel(QWidget):
    clicked = pyqtSignal(object)

    def __init__(self, df, index):
        super().__init__()
        self.df = df
        self.index = index
        self.active = False
        
        layout = QVBoxLayout(self)
        self.label = QLabel(f"Panel {self.index + 1}")
        layout.addWidget(self.label)

        grid = QFormLayout()
        self.x_axis = QComboBox()
        self.y_axis = QComboBox()
        self.chart_type = QComboBox()
        self.chart_type.addItems(["bar", "line", "scatter"])
        self.agg = QComboBox()
        self.agg.addItems(["sum", "mean", "count"])

        grid.addRow("X:", self.x_axis)
        grid.addRow("Y:", self.y_axis)
        grid.addRow("Type:", self.chart_type)
        grid.addRow("Agg:", self.agg)
        layout.addLayout(grid)

        self.fig, self.ax = plt.subplots(figsize=(4, 3))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        self.x_axis.currentIndexChanged.connect(self.draw)
        self.y_axis.currentIndexChanged.connect(self.draw)
        self.chart_type.currentIndexChanged.connect(self.draw)
        self.agg.currentIndexChanged.connect(self.draw)

        self.setStyleSheet("border: 1px solid black; background: #f0f0f0;")

    def mousePressEvent(self, event):
        self.clicked.emit(self)

    def highlight(self, state):
        self.active = state
        color = "blue" if state else "black"
        self.setStyleSheet(f"border: 2px solid {color}; background: white;")

    def draw(self):
        if self.df.empty or not self.x_axis.currentText(): return
        self.ax.clear()
        x = self.x_axis.currentText()
        y = self.y_axis.currentText()
        t = self.chart_type.currentText()
        a = self.agg.currentText()
        
        try:
            res = getattr(self.df.groupby(x)[y], a)()
            if t == "line": res.plot(ax=self.ax)
            elif t == "bar": res.plot(kind="bar", ax=self.ax)
            elif t == "scatter": self.ax.scatter(res.index, res.values)
            self.fig.tight_layout()
            self.canvas.draw()
        except:
            pass

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Free Dashboard")
        self.resize(1000, 700)
        
        self.df = pd.DataFrame()
        self.model = None
        self.recording = False
        self.audio_data = []
        self.selected = None

        main = QWidget()
        self.setCentralWidget(main)
        outer = QVBoxLayout(main)

        top = QHBoxLayout()
        self.load_btn = QPushButton("1. Load CSV")
        self.load_btn.clicked.connect(self.get_file)
        
        self.mic_btn = QPushButton("2. Select a Panel then Hold to Speak")
        self.mic_btn.setEnabled(False)
        self.mic_btn.pressed.connect(self.record_on)
        self.mic_btn.released.connect(self.record_off)

        self.info = QLabel("Status: Waiting...")

        top.addWidget(self.load_btn)
        top.addWidget(self.mic_btn)
        top.addWidget(self.info)
        outer.addLayout(top)

        self.grid = QGridLayout()
        self.panels = []
        outer.addLayout(self.grid)

    def load_file(self, file):
        try:
            if file.endswith(".csv"):
                self.df = pd.read_csv(file)

            elif file.endswith(".xlsx") or file.endswith(".xls"):
                self.df = pd.read_excel(file)

            else:
                QMessageBox.warning(self, "Error", "Unsupported file format")
                return

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        nums = self.df.select_dtypes(include=['number']).columns
        cols = self.df.columns

        for p in self.panels:
            p.setParent(None)
        self.panels.clear()

        for i in range(4):
            p = GraphPanel(self.df, i)
            p.clicked.connect(self.select_panel)
            p.x_axis.addItems(cols)
            p.y_axis.addItems(nums)
            self.panels.append(p)
            self.grid.addWidget(p, i//2, i%2)

        self.info.setText("File Loaded. Click a panel box.")

    def get_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Open Data File",
            "",
            "Data Files (*.csv *.xlsx *.xls)"
        )
        if file:
            self.load_file(file)

    def select_panel(self, p):
        if self.selected: self.selected.highlight(False)
        self.selected = p
        p.highlight(True)
        self.mic_btn.setEnabled(True)

    def record_on(self):
        self.recording = True
        self.audio_data = []
        self.mic_btn.setText("I'm listening...")
        self.stream = sd.InputStream(samplerate=16000, channels=1, dtype='int16', 
                                    callback=lambda i,f,t,s: self.audio_data.append(i.copy()))
        self.stream.start()

    def record_off(self):
        self.recording = False
        self.stream.stop()
        self.mic_btn.setText("Thinking...")
        self.mic_btn.setEnabled(False)
        QApplication.processEvents()

        if not self.model:
            self.model = whisper.load_model("tiny") 
        raw = np.concatenate(self.audio_data).flatten().astype(np.float32) / 32768.0
        out = self.model.transcribe(raw)
        text = out["text"].lower()
        self.info.setText(f"Heard: {text}")

        all_cols = list(self.df.columns)
        num_cols = list(self.df.select_dtypes(include=['number']).columns)

        for c in all_cols:
            if c.lower() in text: self.selected.x_axis.setCurrentText(c)
        for c in num_cols:
            if c.lower() in text and c.lower() != self.selected.x_axis.currentText().lower(): 
                self.selected.y_axis.setCurrentText(c)
        
        if "bar" in text: self.selected.chart_type.setCurrentText("bar")
        if "line" in text: self.selected.chart_type.setCurrentText("line")
        if "scatter" in text: self.selected.chart_type.setCurrentText("scatter")
        
        if "mean" in text or "average" in text: self.selected.agg.setCurrentText("mean")
        if "sum" in text or "total" in text: self.selected.agg.setCurrentText("sum")
        if "count" in text: self.selected.agg.setCurrentText("count")

        self.mic_btn.setEnabled(True)
        self.mic_btn.setText("Hold to Speak")

app = QApplication(sys.argv)
win = App()
win.show()
sys.exit(app.exec())