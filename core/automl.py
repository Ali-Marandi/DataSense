import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_squared_error, accuracy_score
from sklearn.preprocessing import LabelEncoder

class AutoML:
    def __init__(self, df):
        self.df = df.copy()
        self.model = None
        self.target = None
        self.features = None
        self.task_type = None # 'regression' or 'classification'

    def prepare_data(self, target_col):
        """آماده‌سازی داده‌ها برای یادگیری ماشین (کدگذاری و مدیریت مقادیر خالی)"""
        self.target = target_col
        self.features = [c for c in self.df.columns if c != target_col]
        
        X = self.df[self.features]
        y = self.df[self.target]

        # کدگذاری ستون‌های متنی
        le = LabelEncoder()
        for col in X.columns:
            if X[col].dtype == 'object':
                X[col] = le.fit_transform(X[col].astype(str))
        
        if y.dtype == 'object':
            y = le.fit_transform(y.astype(str))
            self.task_type = 'classification'
        else:
            # تشخیص نوع تسک بر اساس تعداد مقادیر منحصر به فرد در هدف
            if y.nunique() < 10:
                self.task_type = 'classification'
            else:
                self.task_type = 'regression'
        
        return train_test_split(X, y, test_size=0.2, random_state=42)

    def train_best_model(self, target_col):
        """آموزش بهترین مدل بر اساس نوع تسک"""
        try:
            X_train, X_test, y_train, y_test = self.prepare_data(target_col)
            
            if self.task_type == 'regression':
                self.model = RandomForestRegressor(n_estimators=100)
                self.model.fit(X_train, y_train)
                preds = self.model.predict(X_test)
                score = np.sqrt(mean_squared_error(y_test, preds))
                metric_name = "RMSE"
            else:
                self.model = RandomForestClassifier(n_estimators=100)
                self.model.fit(X_train, y_train)
                preds = self.model.predict(X_test)
                score = accuracy_score(y_test, preds)
                metric_name = "Accuracy"

            return True, f"Model trained! {metric_name}: {score:.4f}"
        except Exception as e:
            return False, str(e)

    def predict(self, input_data):
        """پیش‌بینی برای داده‌های جدید"""
        if self.model is None:
            return None, "ابتدا مدل را آموزش دهید."
        try:
            return self.model.predict(input_data), None
        except Exception as e:
            return None, str(e)
