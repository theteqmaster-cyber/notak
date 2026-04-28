# Notak Windows Setup Guide

Follow these steps to get the Notak Study Hub running on your Windows machine.

## Prerequisites

1. **Python**: Ensure you have Python 3.10 or newer installed. You can download it from [python.org](https://www.python.org/downloads/windows/). 
   *⚠️ Important: Make sure to check the box that says **"Add Python to PATH"** during installation.*
2. **Project Code**: You should have the Notak project folder extracted and ready on your PC.
3. **API Keys**: You will need your Groq API key (and optionally your Gemini API key if you plan to use Ingracia AI features).

## Installation

1. **Open your Terminal**
   Open PowerShell or Command Prompt, and navigate to your `notak` project folder:
   ```cmd
   cd path\to\notak
   ```

2. **Create a Virtual Environment (Recommended)**
   To keep the dependencies clean and isolated, create a virtual environment inside the project folder:
   ```cmd
   python -m venv venv
   ```
   Activate the virtual environment:
   ```cmd
   .\venv\Scripts\activate
   ```
   *(Your terminal prompt should now show `(venv)` at the beginning).*

3. **Install Required Packages**
   Install all the necessary Python libraries required for Notak to run:
   ```cmd
   pip install -r requirements.txt
   ```

## Configuration

1. **Set up the Environment File**
   In the root of the `notak` folder, you need a configuration file named `.env`.
   
   You can copy the existing example file:
   ```cmd
   copy .env.example .env
   ```

2. **Add Your API Keys**
   Open the newly created `.env` file in Notepad or any text editor and insert your Groq API key (and Gemini key if you have it):
   ```env
   # Ingracia AI Configuration
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Groq Configuration
   GROQ_API_KEY=your_groq_api_key_here
   ```
   *(If you only have a Groq API key and aren't using Gemini, you can leave the Gemini key blank).*

## Running the Application

Once everything is installed and your `.env` file is configured, you can launch Notak right from your terminal (ensure your virtual environment is still activated):

```cmd
python main.py
```

The application will compile its resources, show the splash screen, and load directly into the Study Hub dashboard!
