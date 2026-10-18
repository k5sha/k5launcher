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

**K5Launcher** is a high-performance desktop client for Minecraft engineered for speed, clean Windows 11 aesthetics, and seamless dependency handling. It automatically resolves game assets, libraries, and loader manifests - including detecting existing Java installations or downloading portable OpenJDK runtimes (Java 8, 17, or 21+) based on target Minecraft version requirements.

## Features

- **Fluent Design System**: Sleek Windows 11-style UI with native Dark/Light mode support powered by `qfluentwidgets`.
- **Comprehensive Mod Loader Support**:
  - **Vanilla**: Direct release manifest parsing and asset synchronization.
  - **Fabric**: Dynamic loader manifest resolution and profile generation.
  - **OptiFine**: Automated JAR extraction and tweak-class arguments parsing.
  - **Forge**: Full support for both modern ModLauncher (1.13+) and legacy installer direct extraction (1.7.10 – 1.12.2).
- **Dynamic Multi-Version Java Management**: Automatically scans system paths or fetches/extracts portable OpenJDK runtimes matching specific Minecraft version requirements (Java 8, 17, 21+).
- **Multithreaded Asset Synchronizer**: Parallel downloader with multi-repository fallback (Mojang, Maven Central, Forge) for libraries, natives, and asset indexes.
- **Non-Admin Installation**: Configures silently in `{localappdata}` via Inno Setup to prevent UAC privilege prompts.

---

## Project Structure

```text
k5launcher/
├── assets/                         # Application icons and branding assets
├── src/
│   ├── __init__.py
│   ├── main.py                     # Entry point (run via `py -m src.main`)
│   │
│   ├── config/                     # Application settings & configuration
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   ├── core/                       # Core business logic & launcher engine
│   │   ├── __init__.py
│   │   ├── java.py                 # JDK/JRE discovery, verification & download
│   │   ├── versions.py             # Version manifest manager
│   │   ├── downloader.py           # Parallel asset, library & native downloader
│   │   ├── launcher.py             # Process builder, argument parser & subprocess runner
│   │   └── loaders/                # Mod loader adapters
│   │       ├── __init__.py
│   │       ├── base.py             # Abstract loader base class
│   │       ├── vanilla.py          # Vanilla game loader
│   │       ├── fabric.py           # Fabric mod loader adapter
│   │       ├── optifine.py         # OptiFine installer parser
│   │       └── forge.py            # Modern & Legacy Forge installer runner
│   │
│   ├── ui/                         # PyQt6 & QFluentWidgets graphical interface
│   │   ├── __init__.py
│   │   ├── signals.py              # Qt signals for multithreading
│   │   ├── app.py                  # Main FluentWindow wrapper
│   │   └── views/                  # Navigation pages
│   │       ├── __init__.py
│   │       ├── home_view.py        # Version selector, username & Launch controls
│   │       └── settings_view.py    # RAM allocation, Java path & dir settings
│   │
│   └── utils/                      # Helper utilities
│       ├── __init__.py
│       ├── helpers.py              # Path resolution (PyInstaller frozen context support)
│       └── updater.py              # GitHub API release checker
│
├── tests/                          # Automated Pytest suite
│   ├── __init__.py
│   ├── test_vanilla.py
│   ├── test_fabric.py
│   ├── test_optifine.py
│   ├── test_forge.py
│   ├── test_downloader.py
│   ├── test_java.py
│   ├── test_versions.py
│   ├── test_launcher.py
│   ├── test_helpers.py
│   └── test_updater.py
│
├── .github/workflows/              # CI/CD Workflows
│   ├── ci.yml                      # Test suite & Ruff code quality pipeline
│   └── build.yml                   # Automated PyInstaller & Inno Setup release build
│
├── pytest.ini                      # Pytest runner configuration
├── K5Launcher.iss                  # Inno Setup installer script
├── K5Launcher.spec                 # PyInstaller specification
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # Development & testing dependencies
└── README.md                       # Documentation

```

## Local Development

### Prerequisites

* **Python 3.10** or higher
* **Windows 10 / 11**

### Setup Environment

1. Clone the repository:
```cmd
git clone https://github.com/k5sha/k5launcher.git
cd k5launcher

```


2. Create and activate a virtual environment (optional, but recommended):
```cmd
py -m venv venv
venv\Scripts\activate

```


3. Install development and testing dependencies:
```cmd
pip install -r requirements-dev.txt

```



### Running the Application

To launch the application from source code, always run the module entry point using Python's `-m` flag:

```cmd
py -m src.main

```

---

## Running Tests & Code Quality Checks

### Test Suite Execution

Run the complete test suite using `pytest`:

```cmd
pytest

```

To run tests with detailed verbosity and coverage reporting:

```cmd
pytest -v --cov=src --cov-report=term-missing

```

### Code Formatting and Linting

Check code quality and adhere to formatting standards using **Ruff**:

```cmd
# Run linter checks
ruff check .

# Automatically fix safe linting issues
ruff check --fix .

```

---

## Building Executables & Installer

### 1. Build Executable Bundle (PyInstaller)

To compile the standalone portable folder bundle (`dist/K5Launcher/`):

```cmd
pyinstaller --noconfirm K5Launcher.spec

```

### 2. Compile Windows Installer (Inno Setup)

To build the setup installer (`k5launcher-setup.exe`):

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" K5Launcher.iss

```

*The compiled installer will be available at `installer_output/k5launcher-setup.exe`.*
