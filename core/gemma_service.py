import json
import httpx
import os
from PySide6.QtCore import QObject, Signal, QThread

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma:2b"

class GemmaWorker(QObject):
    finished = Signal(str)
    chunk_received = Signal(str)
    error = Signal(str)

    def __init__(self, prompt, system_prompt=None, chat_history=None):
        super().__init__()
        self.prompt = prompt
        self.system_prompt = system_prompt
        self.chat_history = chat_history or []
        self.is_running = True
        self.output_buffer = [] # Thread-safe shared list
        self.is_done = False
        self.error_msg = None

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            
            for msg in self.chat_history:
                messages.append(msg)
            
            messages.append({"role": "user", "content": self.prompt})

            payload = {
                "model": MODEL_NAME,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": 0.9,
                    "top_p": 0.95,
                    "top_k": 50,
                    "num_ctx": 4096,
                    "num_predict": -1 
                }
            }

            full_response = ""
            # Increase timeout to 30s to allow for "cold start" model loading
            with httpx.stream("POST", OLLAMA_CHAT_URL, json=payload, timeout=30.0) as response:
                if response.status_code != 200:
                    self.error.emit(f"Ollama error: {response.status_code}")
                    self.is_done = True
                    return
                # Increase timeout for streaming chunks to 30s
                response.read_timeout = 30.0

                for line in response.iter_lines():
                    if not self.is_running:
                        break
                    if line:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            content = chunk["message"]["content"]
                            full_response += content
                            self.output_buffer.append(content)
                        if chunk.get("done"):
                            self.is_done = True
                            break

            self.is_done = True
            self.finished.emit(full_response)
        except Exception as e:
            msg = f"Connection error: {str(e)}"
            self.error_msg = msg
            self.error.emit(msg)
            self.is_done = True
            self.finished.emit("")

class GemmaService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GemmaService, cls).__new__(cls)
            cls._instance.history_file = os.path.expanduser("~/.notak_gemma_history.json")
            cls._instance.active_session_objects = [] # Keep references to prevent GC
        return cls._instance

    def get_recommendation_prompt(self, stats, recent_files):
        files_str = "\n".join([f"- {f.get('path')}" for f in recent_files[:3]])
        categories = ["Science", "Philosophy", "Art", "Literature", "Imperial History", "Space Exploration"]
        import time
        chosen_cat = categories[int(time.time()) % len(categories)]
        
        prompt = f"""
        You are a highly creative study assistant. Analyze these stats {stats} and notes {files_str}.
        Provide:
        1. A one-sentence study tip specific to the data. 
        2. A fresh, unique motivational quote related to {chosen_cat}.
        
        IMPORTANT: Never repeat a previous quote. Surprise me with something deep and imperial.
        Format as: Tip: [sentence] | Quote: [quote]
        Keep total response under 35 words.
        """
        return prompt

    def get_chat_thread(self, prompt, system_prompt=None, history=None):
        worker = GemmaWorker(prompt, system_prompt, history)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        
        # Keep references alive
        self.active_session_objects.append((thread, worker))
        
        def cleanup():
            if (thread, worker) in self.active_session_objects:
                self.active_session_objects.remove((thread, worker))
        
        thread.finished.connect(cleanup)
        return thread, worker

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_history(self, history):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=4)
        except:
            pass
