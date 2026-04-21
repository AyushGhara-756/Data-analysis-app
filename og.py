import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QComboBox, QLabel, QListWidget,
    QListWidgetItem, QScrollArea, QGroupBox, QFormLayout,
    QPushButton, QFileDialog
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PyQt6.QtWidgets import QPushButton, QFileDialog


class GraphPanel(QWidget):
    def __init__(self, df, numeric_cols):
        super().__init__()

        self.df = df
        self.numeric_cols = numeric_cols

        layout = QVBoxLayout()

        controls = QFormLayout()

        self.x_axis = QComboBox()
        self.x_axis.addItems(list(df.columns))

        self.y_axis = QComboBox()
        self.y_axis.addItems(list(numeric_cols))

        self.chart_type = QComboBox()
        self.chart_type.addItems(["line", "bar", "scatter"])

        self.agg = QComboBox()
        self.agg.addItems(["sum", "mean", "median", "count"])

        controls.addRow("X:", self.x_axis)
        controls.addRow("Y:", self.y_axis)
        controls.addRow("Type:", self.chart_type)
        controls.addRow("Agg:", self.agg)

        layout.addLayout(controls)

        self.figure, self.ax = plt.subplots(figsize=(4, 3))
        self.canvas = FigureCanvas(self.figure)

        layout.addWidget(self.canvas)
        self.setLayout(layout)

        # auto update
        self.x_axis.currentIndexChanged.connect(self.update_graph)
        self.y_axis.currentIndexChanged.connect(self.update_graph)
        self.chart_type.currentIndexChanged.connect(self.update_graph)
        self.agg.currentIndexChanged.connect(self.update_graph)

        self.update_graph()

    def apply_filters(self, df, filters):
        for col, selected in filters["categorical"].items():
            if selected:
                df = df[df[col].isin(selected)]

        for col, (min_val, max_val) in filters["numeric"].items():
            if col in df.columns:
                df = df[(df[col] >= min_val) & (df[col] <= max_val)]

        return df

    def update(self, df, filters):
        self.df = self.apply_filters(df, filters)
        self.update_graph()

    def update_graph(self):
        if self.df.empty:
            return

        x = self.x_axis.currentText()
        y = self.y_axis.currentText()
        chart = self.chart_type.currentText()
        agg = self.agg.currentText()

        df = self.df.copy()

        if x not in df.columns or y not in df.columns:
            return

        grouped = df.groupby(x)

        if agg == "sum":
            data = grouped[y].sum()
        elif agg == "mean":
            data = grouped[y].mean()
        elif agg == "median":
            data = grouped[y].median()
        elif agg == "count":
            data = grouped[y].count()

        self.ax.clear()

        if chart == "line":
            data.plot(ax=self.ax)
        elif chart == "bar":
            data.plot(kind="bar", ax=self.ax)
        elif chart == "scatter":
            self.ax.scatter(data.index, data.values)

        self.ax.set_title(f"{y} vs {x}")
        self.canvas.draw()


class App(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Data Analysis App")
        self.resize(1400, 900)

        self.df = pd.read_csv("Video_Games_Sales_Cleaned.csv")

        self.numeric_cols = self.df.select_dtypes(include=['number']).columns
        self.categorical_cols = self.df.select_dtypes(exclude=['number']).columns

        main_layout = QHBoxLayout()

        sidebar = QScrollArea()
        sidebar.setWidgetResizable(True)

        sidebar_content = QWidget()
        self.sidebar_layout = QVBoxLayout()
        self.export_button = QPushButton("Export PDF")
        self.export_button.clicked.connect(self.export_pdf)
        self.sidebar_layout.addWidget(self.export_button)

        self.load_button = QPushButton("Load CSV")
        self.load_button.clicked.connect(self.load_file)
        self.sidebar_layout.addWidget(self.load_button)

        self.filter_group = QGroupBox("Filters")
        self.filter_layout = QFormLayout()

        self.categorical_widgets = {}
        self.numeric_widgets = {}

        self.build_filters()

        self.filter_group.setLayout(self.filter_layout)
        self.sidebar_layout.addWidget(self.filter_group)
        self.sidebar_layout.addStretch()

        sidebar_content.setLayout(self.sidebar_layout)
        sidebar.setWidget(sidebar_content)

        # graphs
        grid = QGridLayout()
        self.panels = []

        for i in range(4):
            panel = GraphPanel(self.df, self.numeric_cols)
            self.panels.append(panel)
            grid.addWidget(panel, i // 2, i % 2) # widget, row, column

        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addLayout(grid)
        right_widget.setLayout(right_layout)

        main_layout.addWidget(sidebar, 2) # widget, stretch factor
        main_layout.addWidget(right_widget, 5)

        self.setLayout(main_layout)

        self.apply_filters()

    def export_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF",
            "",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        with PdfPages(file_path) as pdf:
            for panel in self.panels:
                pdf.savefig(panel.figure)
                
    def build_filters(self):
        while self.filter_layout.rowCount():
            self.filter_layout.removeRow(0)

        self.categorical_widgets.clear()
        self.numeric_widgets.clear()

        # categorical
        for col in self.categorical_cols:
            lw = QListWidget()
            lw.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

            for val in sorted(self.df[col].dropna().unique()):
                lw.addItem(QListWidgetItem(str(val)))

            lw.itemSelectionChanged.connect(self.apply_filters)

            self.categorical_widgets[col] = lw
            self.filter_layout.addRow(col, lw)

        # numeric
        for col in self.numeric_cols:
            min_val = int(self.df[col].min())
            max_val = int(self.df[col].max())

            min_box = QComboBox()
            max_box = QComboBox()

            min_box.addItems([str(i) for i in range(min_val, max_val+1)])
            max_box.addItems([str(i) for i in range(min_val, max_val+1)])

            min_box.setCurrentText(str(min_val))
            max_box.setCurrentText(str(max_val))

            min_box.currentIndexChanged.connect(self.apply_filters)
            max_box.currentIndexChanged.connect(self.apply_filters)

            self.numeric_widgets[col] = (min_box, max_box)

            h = QHBoxLayout()
            h.addWidget(QLabel("Min"))
            h.addWidget(min_box)
            h.addWidget(QLabel("Max"))
            h.addWidget(max_box)

            w = QWidget()
            w.setLayout(h)

            self.filter_layout.addRow(col, w)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV Files (*.csv)"
        )

        if not file_path:
            return

        self.df = pd.read_csv(file_path)

        self.numeric_cols = self.df.select_dtypes(include=['number']).columns
        self.categorical_cols = self.df.select_dtypes(exclude=['number']).columns

        self.build_filters()

        for panel in self.panels:
            panel.df = self.df
            panel.numeric_cols = self.numeric_cols

            panel.x_axis.clear()
            panel.x_axis.addItems(list(self.df.columns))

            panel.y_axis.clear()
            panel.y_axis.addItems(list(self.numeric_cols))

            panel.update_graph()

        self.apply_filters()

    def get_filters(self):
        filters = {"categorical": {}, "numeric": {}}

        for col, lw in self.categorical_widgets.items():
            selected = [item.text() for item in lw.selectedItems()]
            filters["categorical"][col] = selected

        for col, (min_box, max_box) in self.numeric_widgets.items():
            min_val = float(min_box.currentText())
            max_val = float(max_box.currentText())
            filters["numeric"][col] = (min_val, max_val)

        return filters

    def apply_filters(self):
        filters = self.get_filters()
        for panel in self.panels:
            panel.update(self.df.copy(), filters)


app = QApplication(sys.argv)
window = App()
window.show()
sys.exit(app.exec())