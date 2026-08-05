from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QLabel)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns

class VisualizationTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # Controls
        self.controls_layout = QHBoxLayout()
        
        self.controls_layout.addWidget(QLabel("Chart Type:"))
        self.chart_type = QComboBox()
        self.chart_type.addItems(["Line Plot", "Bar Chart", "Scatter Plot", "Histogram", "Heatmap"])
        self.controls_layout.addWidget(self.chart_type)

        self.controls_layout.addWidget(QLabel("X-Axis:"))
        self.x_axis = QComboBox()
        self.controls_layout.addWidget(self.x_axis)

        self.controls_layout.addWidget(QLabel("Y-Axis:"))
        self.y_axis = QComboBox()
        self.controls_layout.addWidget(self.y_axis)

        self.btn_plot = QPushButton("Generate Chart")
        self.btn_plot.clicked.connect(self.plot_data)
        self.controls_layout.addWidget(self.btn_plot)

        self.layout.addLayout(self.controls_layout)

        # Canvas
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

    def update_columns(self):
        cols = self.data_manager.get_columns()
        self.x_axis.clear()
        self.y_axis.clear()
        self.x_axis.addItems(cols)
        self.y_axis.addItems(cols)

    def plot_data(self):
        df = self.data_manager.df
        if df is None:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        chart_type = self.chart_type.currentText()
        x = self.x_axis.currentText()
        y = self.y_axis.currentText()

        try:
            if chart_type == "Line Plot":
                sns.lineplot(data=df, x=x, y=y, ax=ax)
            elif chart_type == "Bar Chart":
                sns.barplot(data=df, x=x, y=y, ax=ax)
            elif chart_type == "Scatter Plot":
                sns.scatterplot(data=df, x=x, y=y, ax=ax)
            elif chart_type == "Histogram":
                sns.histplot(data=df, x=x, ax=ax)
            elif chart_type == "Heatmap":
                sns.heatmap(df.corr(), annot=True, ax=ax)
            
            ax.set_title(f"{chart_type} of {y} vs {x}")
            self.canvas.draw()
        except Exception as e:
            print(f"Plotting error: {e}")
