import pandas as pd
import os

class DataManager:
    def __init__(self):
        self.df = None
        self.file_path = None

    def load_data(self, file_path):
        """بارگذاری داده از فرمت‌های مختلف"""
        self.file_path = file_path
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.csv':
                self.df = pd.read_csv(file_path)
            elif ext in ['.xls', '.xlsx']:
                self.df = pd.read_excel(file_path)
            elif ext == '.json':
                self.df = pd.read_json(file_path)
            else:
                raise ValueError(f"فرمت فایل پشتیبانی نمی‌شود: {ext}")
            return True, "داده با موفقیت بارگذاری شد."
        except Exception as e:
            return False, str(e)

    def get_summary(self):
        """دریافت خلاصه آماری داده‌ها"""
        if self.df is not None:
            return self.df.describe(include='all').to_dict()
        return None

    def get_columns(self):
        """دریافت نام ستون‌ها"""
        if self.df is not None:
            return self.df.columns.tolist()
        return []

    def get_data_preview(self, rows=10):
        """دریافت پیش‌نمایش داده‌ها"""
        if self.df is not None:
            return self.df.head(rows)
        return None

    def clean_data(self, fill_na=True, drop_duplicates=True):
        """پاکسازی هوشمند داده‌ها"""
        if self.df is None:
            return False, "داده‌ای برای پاکسازی وجود ندارد."
        
        try:
            if drop_duplicates:
                self.df.drop_duplicates(inplace=True)
            
            if fill_na:
                # پر کردن مقادیر خالی بر اساس نوع داده
                for col in self.df.columns:
                    if self.df[col].dtype in ['int64', 'float64']:
                        self.df[col] = self.df[col].fillna(self.df[col].mean())
                    else:
                        val = self.df[col].mode()[0] if not self.df[col].mode().empty else "Unknown"
                        self.df[col] = self.df[col].fillna(val)
            
            return True, "پاکسازی با موفقیت انجام شد."
        except Exception as e:
            return False, str(e)
