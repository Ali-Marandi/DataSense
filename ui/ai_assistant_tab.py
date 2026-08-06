from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QSizePolicy, QLineEdit)
from PyQt6.QtCore import Qt
from core.ai_assistant import AIAssistant

class AIAssistantTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.ai_assistant = AIAssistant(data_manager)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(QLabel("AI Assistant - Chat with your Data:"))
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("Ask me anything about your data...")
        self.layout.addWidget(self.chat_history)

        self.input_layout = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type your question here...")
        self.user_input.returnPressed.connect(self.send_message)
        self.input_layout.addWidget(self.user_input)

        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self.send_message)
        self.input_layout.addWidget(self.btn_send)

        self.layout.addLayout(self.input_layout)

    def send_message(self):
        prompt = self.user_input.text().strip()
        if not prompt:
            return

        self.chat_history.append(f"<b>You:</b> {prompt}")
        self.user_input.clear()

        response = self.ai_assistant.generate_response(prompt)
        self.chat_history.append(f"<b>AI:</b> {response}")
