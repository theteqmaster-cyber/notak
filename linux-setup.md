# Notak Linux Mint Setup Guide

Follow these step-by-step instructions to install Notak on a new Linux Mint PC and create an application menu/desktop shortcut.

## 1. Prepare the Project Folder
First, ensure you have the `notak` project folder on your new PC (e.g., in your `~/Desktop/notak` directory). You can copy it via USB or clone it from your repository.

Open your terminal (`Ctrl + Alt + T`).

## 2. Install System Prerequisites
Linux Mint usually comes with Python 3, but you'll need the `venv` package to create virtual environments, and `pip` to install packages.

Run this command in your terminal:
```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip -y
```

## 3. Configure API Keys
Navigate to your project directory. Assuming you placed it on your Desktop:
```bash
cd ~/Desktop/notak
```

If you don't already have a `.env` file, copy the example:
```bash
cp .env.example .env
```
Open `.env` using your preferred text editor (like `nano` or `xed`) and paste your Groq/Gemini API keys inside:
```bash
xed .env
```
*(Save and close the file when done).*

## 4. Run the Setup Script
The project includes a convenient `run.sh` script that automatically creates the virtual environment, installs the `requirements.txt`, and launches Notak.

Make sure the script is executable:
```bash
chmod +x run.sh
```

Run it once to perform the initial setup and verify it launches correctly:
```bash
./run.sh
```
*(If Notak opens successfully, you can close it and proceed to create the shortcut).*

## 5. Create the Desktop & Application Menu Shortcut
To make Notak appear in your application menu and allow you to pin it to your panel/desktop, you need to create a `.desktop` file.

Run this command to create and edit the shortcut file:
```bash
xed ~/.local/share/applications/Notak.desktop
```

Paste the following text into the editor. 
**IMPORTANT:** Replace `your_username` with your actual Linux username on the new PC. If your `notak` folder is located somewhere other than `~/Desktop/notak`, update the `Exec` and `Icon` paths accordingly.

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Notak Study Hub
Comment=Your Celestial Study Companion
Exec=/home/your_username/Desktop/notak/run.sh
Icon=/home/your_username/Desktop/notak/icon.png
Terminal=false
Categories=Education;Utility;
```

Save and close the file. 

## 6. Make the Shortcut Executable (Optional for Desktop)
If you want to place a copy of this shortcut directly on your desktop, you can copy it and allow launching:

```bash
cp ~/.local/share/applications/Notak.desktop ~/Desktop/
chmod +x ~/Desktop/Notak.desktop
```
*(You may need to right-click the icon on your Desktop and select "Allow Launching").*

---
**Done!** 🎉 You can now open your Linux Mint application menu, search for "Notak", and launch it just like any other installed application.
