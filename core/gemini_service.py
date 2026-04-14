from google import genai
import os
from dotenv import load_dotenv
from PySide6.QtCore import QObject, Signal, QThread

# SECURITY: Load API key from environment
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Modern SDK uses Client initialization
client = genai.Client(api_key=GEMINI_API_KEY)

class GeminiWorker(QObject):
    finished = Signal(str)
    chunk_received = Signal(str)
    error = Signal(str)

    def __init__(self, prompt, system_prompt=None, chat_history=None):
        super().__init__()
        self.prompt = prompt
        self.system_prompt = system_prompt
        self.chat_history = chat_history or []
        self.is_running = True
        self.output_buffer = [] # Thread-safe shared list for 'Air Gap' polling
        self.is_done = False
        self.error_msg = None

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            # Modern SDK setup: Use gemini-2.5-flash for maximum stability and power
            model_id = 'models/gemini-2.5-flash'
            
            # Map history to modern SDK format: [{'role': 'user', 'parts': [{'text': '...'}]}]
            contents = []
            for msg in self.chat_history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            
            # Add current prompt
            contents.append({
                "role": "user",
                "parts": [{"text": self.prompt}]
            })

            # System instruction is a separate field in modern SDK config
            config = {
                "system_instruction": self.system_prompt if self.system_prompt else None,
                "temperature": 0.7,
                # "top_p": 0.9,
            }

            response = client.models.generate_content_stream(
                model=model_id,
                contents=contents,
                config=config
            )
            
            full_text = ""
            for chunk in response:
                if not self.is_running:
                    break
                
                try:
                    if chunk.text:
                        full_text += chunk.text
                        self.output_buffer.append(chunk.text)
                except (ValueError, AttributeError):
                    # Handle safety filters or blocked content
                    continue
            
            self.is_done = True
            self.finished.emit(full_text)
            
        except Exception as e:
            self.error_msg = str(e)
            self.error.emit(self.error_msg)
            self.is_done = True
            self.finished.emit("")

class GeminiService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiService, cls).__new__(cls)
        return cls._instance

    def get_chat_thread(self, prompt, system_prompt=None, chat_history=None):
        """
        Returns (QThread, GeminiWorker)
        """
        thread = QThread()
        worker = GeminiWorker(prompt, system_prompt, chat_history)
        worker.moveToThread(thread)
        
        thread.started.connect(worker.run)
        
        return thread, worker

    def get_recommendation_prompt(self, stats, recent_files):
        """Generates a prompt for Ingracia's powerful dashboard tips"""
        return f"""
        As Ingracia, a powerful celestial study assistant, analyze these stats:
        {stats}
        Recent work: {recent_files}
        
        Provide a brilliant study tip and an imperial motivational quote.
        Format strictly as: Tip: [One sentence tip] | Quote: [One sentence quote]
        """
