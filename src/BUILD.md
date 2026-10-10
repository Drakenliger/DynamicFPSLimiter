# Dynamic FPS Limiter

## Installation

### Prerequisites
1. Ensure 64-bit Python is installed on your system (Python 3.12 or 3.13 on Windows).
   - Windows CI runs tests across Python 3.12 and 3.13, and builds the standalone Windows executable on Python 3.12.
2. Install pip if not already installed:
   ```cmd
   python -m ensurepip --default-pip
   ```

### Setting up Virtual Environment
1. Open a command prompt in the project directory
2. Create a virtual environment:
   ```cmd
   python -m venv venv
   ```
3. Activate the virtual environment:
   ```cmd
   venv\Scripts\activate
   ```
4. Install required packages (includes runtime and build dependencies such as PyInstaller and DearPyGui):
   ```cmd
   pip install -r src/requirements.txt
   ```

## Usage

### Running the Application from Source
To run the application directly without building an executable:
1. Activate the virtual environment if not already activated:
   ```cmd
   venv\Scripts\activate
   ```
2. Run the application:
   ```cmd
   python src/__main__.py
   ```
   - **Administrator Elevation**: The application requires administrator privileges to interact with RTSS. If launched without elevation, `src/__main__.py` automatically prompts for UAC elevation via Windows `ShellExecuteW` (`runas`).
   - **Console Behavior**: On normal elevation, the app relaunches using `pythonw.exe` (if present in the virtual environment) to run without an extraneous console window.
   - **Debug Mode**: To retain the console window for debugging and stdout/stderr inspection, pass the `--debug` flag:
     ```cmd
     python src/__main__.py --debug
     ```
   - **Logging**:
     - In-app status messages appear in the GUI log window (retaining the 50 most recent messages).
     - RTSS framerate cap changes are logged to CSV files directly in the configuration directory (`src/config/cap_changes_*.csv` when running from source, or `output/dist/DynamicFPSLimiter/config/cap_changes_*.csv` when running the packaged executable).
     - Uncaught Python exceptions (main thread and worker threads) as well as fatal native crashes (via `faulthandler`) are written to `src/error_log.txt`.

### Building the Standalone Executable
To create a standalone Windows executable:
1. Activate the virtual environment if not already activated:
   ```cmd
   venv\Scripts\activate
   ```
2. Build the executable (no admin rights required during the build):
   ```cmd
   python src/__main__.py --build
   ```
3. The build process regenerates version resources from `src/core/version.py`, packages required assets from `src/core/assets/`, and runs PyInstaller in `--onedir` mode.

### Notes
- **Administrator Privileges**: Only required when running the application (due to RTSS privileged access), not when building. The built executable embeds `--uac-admin` in its manifest to prompt for elevation on launch.
- **Executable Location**: PyInstaller creates a directory distribution inside `output/dist/`. The executable is located at:
  ```
  output/dist/DynamicFPSLimiter/DynamicFPSLimiter.exe
  ```
  The `DynamicFPSLimiter/` folder includes the executable, bundled DLLs, dependencies, and bundled assets under `_internal/assets/` (PyInstaller 6 default contents directory `_internal`).
- **Packaged Error Logging**: When running the packaged executable, uncaught exceptions and crash reports are written to `error_log.txt` located in the executable directory beside `DynamicFPSLimiter.exe` (e.g. `output/dist/DynamicFPSLimiter/error_log.txt`).
