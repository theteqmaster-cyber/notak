# Deployment Guide: Notak Study Sanctuary

Congratulations on your sanctuary being "production ready"! Migrating Notak to a new Linux Mint (or Ubuntu/Debian) machine is straightforward. Follow these steps to set up your immersion hub from scratch.

---

## 1. System Requirements

Before installing the app, ensure your machine has the required system packages for PDF processing and OCR:

```bash
# Update and install system dependencies
sudo apt update
sudo apt install python3-pip python3-venv wkhtmltopdf tesseract-ocr -y
```

---

## 2. Setting Up Notak

1. **Move Codebase**: Transfer the `notak` folder to your new machine (e.g., to `~/Desktop/notak`).
2. **First-Time Run**:
   Open a terminal in the folder and run the launcher. The new `run.sh` will automatically create a virtual environment and install all dependencies for you:

   ```bash
   ./run.sh
   ```

---

## 3. Creating the Launcher (Optional/Recommended)

To make Notak show up in your start menu and dashboard, you can create a ".desktop" entry:

1. **Create the Shortcut**:
   In your terminal, run this command (adjust paths if you moved the folder elsewhere):

   ```bash
   cat > ~/.local/share/applications/notak.desktop <<EOF
   [Desktop Entry]
   Version=1.0
   Type=Application
   Name=Notak
   Comment=Study Sanctuary & Focus Hub
   Exec=$HOME/Desktop/notak/run.sh
   Icon=$HOME/Desktop/notak/icon.png
   Terminal=false
   Categories=Education;Utility;Qt;
   Path=$HOME/Desktop/notak
   StartupNotify=true
   EOF
   ```

2. **Grant Permissions**:
   ```bash
   chmod +x ~/.local/share/applications/notak.desktop
   ```

3. **Profit**: You can now search for **"Notak"** in your Mint Menu and pin it to your panel for one-click access.

---

## Troubleshooting

- **Permissions**: If `run.sh` doesn't launch, run `chmod +x run.sh`.
- **Database**: The app will automatically create a new, empty database in your `~/StudyVault` folder on the first launch. To bring over your old notes, simply copy the `~/StudyVault` directory from your old machine to the new one.

> [!TIP]
> **Pro Tip**: Keep your `icon.png` in the app directory. It ensures your sanctuary always looks premium in the taskbar!
