import pandas as pd
from sqlalchemy import create_engine

class DBConnector:
    def __init__(self):
        self.engine = None

    def connect(self, db_type, host, port, user, password, database):
        """برقراری اتصال به پایگاه داده‌های مختلف"""
        try:
            if db_type == "MySQL":
                connection_str = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"
            elif db_type == "PostgreSQL":
                connection_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            elif db_type == "SQLite":
                connection_str = f"sqlite:///{database}"
            else:
                return False, "نوع پایگاه داده پشتیبانی نمی‌شود."

            self.engine = create_engine(connection_str)
            # تست اتصال
            with self.engine.connect() as conn:
                pass
            return True, "اتصال با موفقیت برقرار شد."
        except Exception as e:
            return False, str(e)

    def execute_query(self, query):
        """اجرای کوئری و دریافت نتایج به صورت DataFrame"""
        if self.engine is None:
            return None, "ابتدا به پایگاه داده متصل شوید."
        try:
            df = pd.read_sql(query, self.engine)
            return df, None
        except Exception as e:
            return None, str(e)

    def get_tables(self):
        """دریافت لیست جداول موجود در پایگاه داده"""
        if self.engine is None:
            return []
        try:
            from sqlalchemy import inspect
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception:
            return []
