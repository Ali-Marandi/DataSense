from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QPushButton, QComboBox, QLabel, QMessageBox, QTextEdit)
from core.db_connector import DBConnector

class DBTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.db_connector = DBConnector()
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # Connection Form
        self.form_layout = QFormLayout()
        
        self.db_type = QComboBox()
        self.db_type.addItems(["MySQL", "PostgreSQL", "SQLite"])
        self.form_layout.addRow("Database Type:", self.db_type)

        self.host = QLineEdit("localhost")
        self.form_layout.addRow("Host:", self.host)

        self.port = QLineEdit("3306")
        self.form_layout.addRow("Port:", self.port)

        self.user = QLineEdit("root")
        self.form_layout.addRow("Username:", self.user)

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.form_layout.addRow("Password:", self.password)

        self.database = QLineEdit()
        self.form_layout.addRow("Database Name:", self.database)

        self.btn_connect = QPushButton("Connect to Database")
        self.btn_connect.clicked.connect(self.connect_db)
        self.form_layout.addRow(self.btn_connect)

        self.layout.addLayout(self.form_layout)

        # Query Area
        self.layout.addWidget(QLabel("SQL Query:"))
        self.query_input = QTextEdit("SELECT * FROM table_name LIMIT 100")
        self.layout.addWidget(self.query_input)

        self.btn_execute = QPushButton("Execute Query and Import Data")
        self.btn_execute.clicked.connect(self.execute_query)
        self.layout.addWidget(self.btn_execute)

    def connect_db(self):
        db_type = self.db_type.currentText()
        host = self.host.text()
        port = self.port.text()
        user = self.user.text()
        password = self.password.text()
        database = self.database.text()

        success, message = self.db_connector.connect(db_type, host, port, user, password, database)
        if success:
            QMessageBox.information(self, "Success", "Connected to database successfully!")
        else:
            QMessageBox.critical(self, "Error", f"Connection failed: {message}")

    def execute_query(self):
        query = self.query_input.toPlainText()
        df, error = self.db_connector.execute_query(query)
        
        if error:
            QMessageBox.critical(self, "Error", f"Query failed: {error}")
        elif df is not None:
            self.data_manager.df = df
            QMessageBox.information(self, "Success", f"Imported {len(df)} rows successfully!")
            # Trigger main window update (this will be handled by parent signal)
            if hasattr(self.parent().parent(), 'update_table'):
                self.parent().parent().update_table()
                self.parent().parent().viz_tab.update_columns()
