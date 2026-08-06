from cryptography.fernet import Fernet
import pandas as pd

class DataSecurity:
    def __init__(self, key=None):
        if key is None:
            self.key = Fernet.generate_key()
        else:
            self.key = key
        self.cipher = Fernet(self.key)

    def encrypt_column(self, df, column_name):
        """رمزنگاری یک ستون خاص در DataFrame"""
        if column_name not in df.columns:
            return df, f"ستون {column_name} یافت نشد."
        
        try:
            df[column_name] = df[column_name].astype(str).apply(
                lambda x: self.cipher.encrypt(x.encode()).decode()
            )
            return df, None
        except Exception as e:
            return df, str(e)

    def decrypt_column(self, df, column_name):
        """رمزگشایی یک ستون خاص در DataFrame"""
        if column_name not in df.columns:
            return df, f"ستون {column_name} یافت نشد."
        
        try:
            df[column_name] = df[column_name].apply(
                lambda x: self.cipher.decrypt(x.encode()).decode()
            )
            return df, None
        except Exception as e:
            return df, str(e)

    def get_key(self):
        return self.key.decode()
