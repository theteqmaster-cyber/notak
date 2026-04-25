import os
import json
import httpx
from dotenv import load_dotenv
from PySide6.QtCore import QObject, Signal, QThread

# SECURITY: Load API key from environment
load_dotenv()
# Redirect to Groq API Key as requested
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

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
        if not GROQ_API_KEY:
            self.error_msg = "Groq API Key is missing. Please check your .env file."
            self.error.emit(self.error_msg)
            self.is_done = True
            self.finished.emit("")
            return

        try:
            # Auto-detect OpenAI vs Groq
            is_openai = GROQ_API_KEY.startswith("sk-")
            if is_openai:
                model_id = 'gpt-4o'
                url = "https://api.openai.com/v1/chat/completions"
            else:
                # Using Llama 3.3 via Groq for high speed and intelligence
                model_id = 'llama-3.3-70b-versatile'
                url = "https://api.groq.com/openai/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            
            for msg in self.chat_history:
                messages.append(msg)
            
            messages.append({"role": "user", "content": self.prompt})
            
            payload = {
                "model": model_id,
                "messages": messages,
                "temperature": 0.7,
                "stream": True
            }

            full_text = ""
            with httpx.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
                if response.status_code != 200:
                    error_content = response.read().decode()
                    try:
                        error_json = json.loads(error_content)
                        self.error_msg = error_json.get("error", {}).get("message", "Unknown error")
                    except:
                        self.error_msg = f"Groq Error {response.status_code}: {error_content}"
                    
                    self.error.emit(self.error_msg)
                    self.is_done = True
                    self.finished.emit("")
                    return

                for line in response.iter_lines():
                    if not self.is_running:
                        break
                    
                    if not line:
                        continue
                    
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    if line == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(line)
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0].get("delta", {}).get("content", "")
                            if content:
                                full_text += content
                                self.output_buffer.append(content)
                                self.chunk_received.emit(content)
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            self.is_done = True
            self.finished.emit(full_text)
            
        except Exception as e:
            self.error_msg = f"Groq Connection Severed: {str(e)}"
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
