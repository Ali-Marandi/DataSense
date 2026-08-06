import pandas as pd
import numpy as np
import time
from PyQt6.QtCore import QThread, pyqtSignal

class RealTimeSimulator(QThread):
    data_received = pyqtSignal(pd.DataFrame)

    def __init__(self, columns):
        super().__init__()
        self.columns = columns
        self.running = True

    def run(self):
        """تولید داده‌های تصادفی برای شبیه‌سازی استریم زنده"""
        while self.running:
            data = np.random.randn(1, len(self.columns))
            df = pd.DataFrame(data, columns=self.columns)
            self.data_received.emit(df)
            time.sleep(1) # دریافت داده هر ۱ ثانیه

    def stop(self):
        self.running = False
