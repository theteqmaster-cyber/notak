import httpx
import json
import os
from dotenv import load_dotenv
from PySide6.QtCore import QObject, Signal, QThread

# SECURITY: Load API key from environment
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

class GroqWorker(QObject):
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
            # Using Llama 3.3 for maximum speed and intelligence
            model_id = 'llama-3.3-70b-versatile'
            url = "https://api.groq.com/openai/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            
            for msg in self.chat_history:
                # Ensure role mapping is correct (OpenAI format matches self.chat_history)
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
            self.error_msg = f"Hub Connection Severed: {str(e)}"
            self.error.emit(self.error_msg)
            self.is_done = True
            self.finished.emit("")

class GroqService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GroqService, cls).__new__(cls)
        return cls._instance

    def get_chat_thread(self, prompt, system_prompt=None, chat_history=None):
        """
        Returns (QThread, GroqWorker)
        """
        thread = QThread()
        worker = GroqWorker(prompt, system_prompt, chat_history)
        worker.moveToThread(thread)
        
        thread.started.connect(worker.run)
        
        return thread, worker
