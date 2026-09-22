<div align="center">
  <img src="assets/logo.png" alt="K5Launcher Logo" width="120" height="120">
  <h1>K5Launcher</h1>
  <p><b>A modern, lightweight Minecraft launcher built with Python and Fluent UI.</b></p>

  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
  [![UI](https://img.shields.io/badge/UI-PyQt6%20%7C%20QFluentWidgets-7b61ff.svg)](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
  [![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)
</div>

---

## Overview

**K5Launcher** is a custom desktop client for Minecraft engineered for speed, clean UX, and seamless dependency handling. It automatically resolves game assets, libraries, and runtime dependencies — including downloading a portable OpenJDK 21 environment if no compatible Java installation is found on the system.

## Features

* **Fluent Design System**: Sleek Windows 11-style interface with native Dark/Light mode support powered by `qfluentwidgets`.
* **Automatic Java Management**: Scans local drives for existing JDKs or automatically fetches and extracts portable OpenJDK 21.
* **Fabric Modpack Integration**: Fetches release manifests dynamically with optional Fabric Loader profile switching.
* **Multithreaded Asset Synchronizer**: Concurrent downloader for game assets and Maven libraries to minimize load times.
* **Non-Admin Installation**: Inno Setup installer configures the app in `{localappdata}` to prevent UAC privilege prompts.

## Project Structure

```text
E:\supo\
├── assets/                          # Icons and logos
├── src/
│   ├── __init__.py
│   ├── main.py                      # Application entry point
│   │
│   ├── config/                      # Configuration and settings manager
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   ├── core/                        # Launcher business logic (non-UI)
│   │   ├── __init__.py
│   │   ├── java.py                  # Java JRE discovery, validation, and download
│   │   ├── versions.py              # Mojang, Fabric manifest management
│   │   ├── downloader.py            # Libraries, natives, and assets downloader
│   │   └── launcher.py              # Argument builder and Minecraft process runner
│   │
│   ├── ui/                          # Graphical interface (PyQt6 / QFluentWidgets)
│   │   ├── __init__.py
│   │   ├── signals.py               # Qt signals for threading
│   │   ├── app.py                   # Main FluentWindow interface
│   │   └── views/                   # Views / Pages
│   │       ├── __init__.py
│   │       ├── home_view.py         # Home view (Launch button, Username, Version selector)
│   │       └── settings_view.py     # Settings view
│   │
│   └── utils/                       # Helper utilities
│       ├── __init__.py
│       ├── helpers.py               # Path resolution helpers (resource_path, get_app_dir)
│       └── updater.py               # GitHub API update checker
│
├── K5Launcher.iss                   # Inno Setup compilation script
├── K5Launcher.spec                  # PyInstaller bundle specification
├── requirements.txt                 # Project dependencies
└── README.md                        
```

## Local Development

### Prerequisites

* Python 3.10 or higher
* Windows 10 / 11

### Installation

1. Clone the repository:
```bash
git clone https://github.com/k5sha/k5launcher.git
cd k5launcher

```


2. Install required dependencies:
```bash
pip install -r requirements.txt

```


3. Run the application:
```bash
python -m src.main

```



## Building Executables

1. **Build the application folder:**
```powershell
pyinstaller --noconfirm K5Launcher.spec

```


2. **Compile the installer package:**
```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" K5Launcher.iss

```


*The compiled installer will be available at `installer_output/k5launcher_setup.exe`.*
