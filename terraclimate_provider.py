# -*- coding: utf-8 -*-
"""
TerraClimate Provider - Processing provider and plugin management
Version 0.0.8
"""
import importlib
import os
import platform
import subprocess
import sys

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from qgis.core import Qgis, QgsApplication, QgsProcessingProvider

PLUGIN_PROVIDER_ID = "terraclimate_downloader"
PLUGIN_VERSION = "0.0.8"

REQUIRED_PACKAGES = {
    "numpy": "numpy>=1.24,<2",
    "xarray": "xarray",
    "rioxarray": "rioxarray",
    "netCDF4": "netCDF4",
}

OPTIONAL_PACKAGES = {
    "dask": "dask",
}

INSTALL_PACKAGE_SPECS = [
    "xarray",
    "rioxarray",
    "numpy>=1.24,<2",
    "netCDF4",
    "dask",
]

if platform.system() != "Windows":
    DISPLAY_INSTALL_COMMAND = 'python3 -m pip install --break-system-packages --upgrade-strategy only-if-needed xarray rioxarray "numpy>=1.24,<2" netCDF4 dask'
else:
    DISPLAY_INSTALL_COMMAND = 'python -m pip install --upgrade-strategy only-if-needed xarray rioxarray "numpy>=1.24,<2" netCDF4 dask'

MIN_PACKAGE_VERSIONS = {
    "numpy": "1.24",
    "xarray": "2023.1.0",
    "rioxarray": "0.15.0",
    "netCDF4": "1.6.0",
}


def check_package(module_name):
    """Check if a Python package is available."""
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


def _parse_version(version_text):
    """Parse a version string into a tuple of integers for lightweight comparison."""
    parts = []
    for chunk in str(version_text).replace("-", ".").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def get_package_version(module_name):
    """Return the package version if available."""
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return None

    return getattr(module, "__version__", None)


def version_is_compatible(module_name):
    """Check whether an installed module satisfies the minimum tested version."""
    installed = get_package_version(module_name)
    minimum = MIN_PACKAGE_VERSIONS.get(module_name)
    if not installed or not minimum:
        return True
    return _parse_version(installed) >= _parse_version(minimum)


def get_missing_packages():
    """Get lists of missing required and optional packages."""
    missing_required = []
    missing_optional = []

    for module, pip_name in REQUIRED_PACKAGES.items():
        if not check_package(module):
            missing_required.append((module, pip_name))

    for module, pip_name in OPTIONAL_PACKAGES.items():
        if not check_package(module):
            missing_optional.append((module, pip_name))

    return missing_required, missing_optional


def get_incompatible_packages():
    """Return required packages that are installed but older than tested versions."""
    incompatible = []
    for module, pip_name in REQUIRED_PACKAGES.items():
        if check_package(module) and not version_is_compatible(module):
            incompatible.append((module, pip_name, get_package_version(module), MIN_PACKAGE_VERSIONS[module]))
    return incompatible


def dependencies_ready():
    """True when all required packages are installed and meet minimum tested versions."""
    missing_required, _ = get_missing_packages()
    return not missing_required and not get_incompatible_packages()


def get_manual_install_command():
    """Build a pip command that uses the same Python executable as QGIS."""
    base = f'"{sys.executable}" -m pip install --upgrade-strategy only-if-needed'
    packages = " ".join(f'"{package}"' for package in INSTALL_PACKAGE_SPECS)
    # macOS and newer Linux with PEP 668 externally-managed environments
    if platform.system() != "Windows":
        return f'{base} --break-system-packages {packages}'
    return f'{base} {packages}'


def get_environment_summary():
    """Collect useful environment details for dependency troubleshooting."""
    lines = [
        f"QGIS Python executable: {sys.executable}",
        f"Python version: {sys.version.split()[0]}",
        f"Platform: {platform.system()} {platform.release()}",
    ]
    if platform.system() == "Darwin":
        lines.append(f"macOS version: {platform.mac_ver()[0]}")
    elif platform.system() == "Windows":
        shell = get_osgeo4w_shell_path()
        lines.append(f"OSGeo4W shell: {shell or 'NOT FOUND'}")
    return lines


def _resolve_short_path(path):
    """Resolve a Windows 8.3 short path to its long-name equivalent.

    Falls back to *path* unchanged on non-Windows or on error.
    """
    if platform.system() != "Windows":
        return path
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(512)
        result = ctypes.windll.kernel32.GetLongPathNameW(path, buf, 512)
        if result > 0:
            return buf.value
    except Exception:
        pass
    # Second attempt: os.path.realpath (works on Python 3.10+ on Windows)
    try:
        resolved = os.path.realpath(path)
        if resolved != path:
            return resolved
    except (OSError, ValueError):
        pass
    return path


def get_osgeo4w_shell_path():
    """Locate the OSGeo4W shell batch file bundled with QGIS on Windows.

    Search order:
      1. Walk up from sys.executable (resolving 8.3 short names)
      2. OSGEO4W_ROOT environment variable
      3. Windows Registry (QGIS installer writes InstallPath)
      4. Start Menu shortcut folders (read .lnk target paths)
      5. Common default install directories on disk
    """
    if platform.system() != "Windows":
        return None

    candidates = []

    # --- 1. Walk up from sys.executable (covers most layouts) ---
    try:
        exe_long = _resolve_short_path(sys.executable)
    except (OSError, ValueError):
        exe_long = sys.executable

    for exe in (exe_long, sys.executable):
        current = os.path.dirname(exe)
        for _ in range(5):
            bat = os.path.join(current, "OSGeo4W.bat")
            if os.path.isfile(bat):
                candidates.append(bat)
            current = os.path.dirname(current)
            if current == os.path.dirname(current):
                break

    # --- 2. OSGEO4W_ROOT environment variable ---
    osgeo_root = os.environ.get("OSGEO4W_ROOT", "")
    if osgeo_root:
        candidates.append(os.path.join(osgeo_root, "OSGeo4W.bat"))

    # --- 3. Windows Registry ---
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for key_path in (
                r"SOFTWARE\QGIS",
                r"SOFTWARE\WOW6432Node\QGIS",
            ):
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                        if install_path:
                            candidates.append(os.path.join(install_path, "OSGeo4W.bat"))
                except (FileNotFoundError, OSError):
                    pass
    except ImportError:
        pass

    # --- 4. Start Menu shortcut folders ---
    # QGIS standalone installer puts shortcuts under ProgramData Start Menu
    start_menu_bases = [
        os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                      "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("APPDATA", ""),
                      "Microsoft", "Windows", "Start Menu", "Programs"),
    ]
    for sm_base in start_menu_bases:
        if not os.path.isdir(sm_base):
            continue
        try:
            for entry in os.listdir(sm_base):
                if entry.upper().startswith("QGIS"):
                    sm_folder = os.path.join(sm_base, entry)
                    if not os.path.isdir(sm_folder):
                        continue
                    # Look for "OSGeo4W Shell.lnk" and try to read its target
                    for lnk_name in os.listdir(sm_folder):
                        if "osgeo4w" in lnk_name.lower() and lnk_name.lower().endswith(".lnk"):
                            target = _read_lnk_target(os.path.join(sm_folder, lnk_name))
                            if target and os.path.isfile(target):
                                candidates.append(target)
                    # Also try: the QGIS folder name hints at the install dir
                    # e.g., "QGIS 3.40.11" → C:\Program Files\QGIS 3.40.11
                    for pf in (os.environ.get("ProgramFiles", ""),
                               os.environ.get("ProgramFiles(x86)", "")):
                        if pf:
                            candidates.append(os.path.join(pf, entry, "OSGeo4W.bat"))
        except OSError:
            pass

    # --- 5. Common default install directories ---
    program_dirs = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        r"C:\OSGeo4W",
        r"C:\OSGeo4W64",
    ]
    for pdir in program_dirs:
        if not pdir or not os.path.isdir(pdir):
            continue
        candidates.append(os.path.join(pdir, "OSGeo4W.bat"))
        try:
            for entry in os.listdir(pdir):
                if entry.upper().startswith("QGIS"):
                    candidates.append(os.path.join(pdir, entry, "OSGeo4W.bat"))
        except OSError:
            pass

    # --- Return the first candidate that actually exists ---
    seen = set()
    for path in candidates:
        try:
            normed = os.path.normcase(os.path.realpath(path))
        except (OSError, ValueError):
            normed = os.path.normcase(path)
        if normed in seen:
            continue
        seen.add(normed)
        if os.path.isfile(path):
            return path

    return None


def _read_lnk_target(lnk_path):
    """Try to extract the target path from a Windows .lnk shortcut file.

    Uses a lightweight binary parse — no COM / pythoncom dependency needed.
    Returns the target path string or None.
    """
    try:
        with open(lnk_path, "rb") as fh:
            content = fh.read()
        # .lnk files contain the target path as a null-terminated UTF-16 or
        # ASCII string.  Look for common path prefixes.
        for pattern in (b"C:\\", b"D:\\", b"E:\\"):
            idx = content.find(pattern)
            if idx == -1:
                continue
            # Read until null byte
            end = content.index(b"\x00", idx)
            candidate = content[idx:end].decode("ascii", errors="ignore")
            if candidate.lower().endswith(".bat"):
                return candidate
    except Exception:
        pass
    return None


class DependencyInstallerDialog(QDialog):
    """Dialog for installing Python dependencies."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TerraClimate - Install Dependencies")
        self.setMinimumWidth(680)
        self.setMinimumHeight(420)
        self.setup_ui()
        self.check_status()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("<h2>TerraClimate Downloader - Dependency Setup</h2>")
        layout.addWidget(header)

        self.status_label = QLabel("Checking dependencies...")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("font-family: 'Menlo', 'Consolas', 'Monaco', monospace; font-size: 11px;")
        layout.addWidget(self.log_output)

        btn_layout = QHBoxLayout()

        if platform.system() == "Windows":
            install_label = "Install Dependencies (OSGeo4W Shell)"
            install_tip = f"Opens the OSGeo4W Shell and runs:\n{DISPLAY_INSTALL_COMMAND}"
        elif platform.system() == "Darwin":
            install_label = "Install Dependencies"
            install_tip = f"Runs pip with the QGIS Python:\n{get_manual_install_command()}"
        else:
            install_label = "Install Dependencies"
            install_tip = f"Runs pip with the QGIS Python:\n{get_manual_install_command()}"

        self.install_btn = QPushButton(install_label)
        self.install_btn.setToolTip(install_tip)
        self.install_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 8px 16px; }"
        )
        self.install_btn.clicked.connect(self.install_packages)
        btn_layout.addWidget(self.install_btn)

        self.refresh_btn = QPushButton("Refresh Status")
        self.refresh_btn.clicked.connect(self.check_status)
        btn_layout.addWidget(self.refresh_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

        if platform.system() == "Windows":
            help_html = (
                "<small><b>What happens when you press Install:</b><br>"
                "1. The OSGeo4W Shell window will open automatically<br>"
                "2. The following command runs inside it:<br>"
                f"<code>{DISPLAY_INSTALL_COMMAND}</code><br>"
                "3. Wait for installation to finish in that shell window<br>"
                "4. Restart QGIS after installation<br><br>"
                f"<b>QGIS Python path:</b> <code>{sys.executable}</code></small>"
            )
        else:
            help_html = (
                "<small><b>What happens when you press Install:</b><br>"
                "1. pip runs using the QGIS Python interpreter<br>"
                "2. Progress is shown in the log above<br>"
                "3. If that fails, a Terminal window opens with the command<br>"
                "4. Restart QGIS after installation<br><br>"
                f"<b>Install command:</b><br><code>{get_manual_install_command()}</code><br><br>"
                f"<b>QGIS Python path:</b> <code>{sys.executable}</code></small>"
            )
        help_text = QLabel(help_html)
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

    def log(self, message):
        """Add message to log output."""
        self.log_output.append(message)
        QApplication.processEvents()

    def check_status(self):
        """Check and display dependency status."""
        self.log_output.clear()
        missing_req, missing_opt = get_missing_packages()
        incompatible = get_incompatible_packages()
        all_required_ok = not missing_req and not incompatible

        self.log("=" * 60)
        self.log("DEPENDENCY STATUS CHECK")
        self.log("=" * 60)
        self.log("")
        for line in get_environment_summary():
            self.log(line)
        self.log("")

        self.log("REQUIRED PACKAGES:")
        for module in REQUIRED_PACKAGES:
            if check_package(module):
                version_text = get_package_version(module) or "unknown"
                if version_is_compatible(module):
                    self.log(f"  OK {module} - installed ({version_text})")
                else:
                    self.log(
                        f"  UPDATE {module} - installed ({version_text}), "
                        f"tested minimum is {MIN_PACKAGE_VERSIONS[module]}"
                    )
            else:
                self.log(f"  MISSING {module} - not installed")

        self.log("")
        self.log("OPTIONAL PACKAGES:")
        for module in OPTIONAL_PACKAGES:
            if check_package(module):
                version_text = get_package_version(module) or "unknown"
                self.log(f"  OK {module} - installed ({version_text})")
            else:
                self.log(f"  OPTIONAL {module} - not installed")

        if missing_req or incompatible:
            self.log("")
            self.log("FORCE DOWNLOAD COMMAND:")
            self.log(DISPLAY_INSTALL_COMMAND)
            self.log("QGIS PYTHON COMMAND:")
            self.log(get_manual_install_command())

        self.log("")
        self.log("=" * 60)

        if all_required_ok:
            self.status_label.setText(
                "<span style='color: green; font-weight: bold;'>All required dependencies are available.</span>"
            )
            self.status_label.setStyleSheet("padding: 10px; background-color: #d4edda; border-radius: 5px;")
            self.install_btn.setEnabled(False)
            self.log("Ready to use.")
        else:
            self.status_label.setText(
                "<span style='color: red; font-weight: bold;'>Required dependencies are missing or outdated.</span>"
            )
            self.status_label.setStyleSheet("padding: 10px; background-color: #f8d7da; border-radius: 5px;")
            self.install_btn.setEnabled(True)

    def get_pip_executable(self):
        """Find the correct pip executable for QGIS Python."""
        return [sys.executable, "-m", "pip"]

    def install_packages(self):
        """Install dependencies using the appropriate method for the current OS.

        - Windows: Opens an OSGeo4W shell (or falls back to cmd.exe).
        - macOS / Linux: Runs pip directly via subprocess in the background,
          streaming output to the log panel; or opens Terminal.app / xterm
          if the in-process approach fails.
        """
        self.log("")
        self.log("=" * 60)
        self.log("INSTALLING PACKAGES")
        self.log("=" * 60)
        self.log(f"Python executable: {sys.executable}")
        self.log(f"Platform: {platform.system()}")
        self.log(f"Requested command: {DISPLAY_INSTALL_COMMAND}")
        self.log("")

        current_platform = platform.system()

        if current_platform == "Windows":
            self._install_windows()
        else:
            # macOS and Linux: try in-process pip first, then terminal fallback
            self._install_unix()

        self.log("")
        self.log("=" * 60)
        self.log("Installer launch complete")
        self.log("=" * 60)
        self.check_status()

    # ---- Windows installer path ------------------------------------------------

    def _install_windows(self):
        """Windows: generate a .bat dynamically for any QGIS 3 version and run it.

        Strategy:
          1. Try to find o4w_env.bat (works for any QGIS 3.x via OSGeo4W)
          2. Try to find OSGeo4W.bat and use it as the shell environment
          3. Fall back to running pip directly with the QGIS Python executable
        """
        # Dynamically find the QGIS/OSGeo4W root from sys.executable
        # normpath ensures backslashes only — cmd.exe cannot handle mixed slashes
        qgis_bin_dir = os.path.normpath(os.path.dirname(sys.executable))

        # Look for o4w_env.bat by walking up from the Python executable
        o4w_env_bat = None
        search_dir = qgis_bin_dir
        for _ in range(5):
            candidate = os.path.normpath(os.path.join(search_dir, "o4w_env.bat"))
            if os.path.isfile(candidate):
                o4w_env_bat = candidate
                break
            # Also check bin subfolder
            candidate_bin = os.path.normpath(os.path.join(search_dir, "bin", "o4w_env.bat"))
            if os.path.isfile(candidate_bin):
                o4w_env_bat = candidate_bin
                break
            search_dir = os.path.dirname(search_dir)
            if search_dir == os.path.dirname(search_dir):
                break

        if o4w_env_bat:
            self.log(f"Found o4w_env.bat: {o4w_env_bat}")
            self._run_bat_installer(o4w_env_bat)
            return

        # Try OSGeo4W.bat as fallback
        shell_path = get_osgeo4w_shell_path()
        if shell_path:
            shell_path = os.path.normpath(shell_path)
            self.log(f"Found OSGeo4W shell: {shell_path}")
            launch_command = f'call "{shell_path}" && {DISPLAY_INSTALL_COMMAND}'
            self.log(f"Shell command: {launch_command}")

            try:
                creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
                subprocess.Popen(
                    ["cmd.exe", "/k", launch_command],
                    creationflags=creation_flags,
                )
                self.log("OSGeo4W shell opened. Complete the install in that window, then restart QGIS.")
                QMessageBox.information(
                    self,
                    "OSGeo4W Shell Opened",
                    "An OSGeo4W shell has been opened and the dependency\n"
                    "install command was started there.\n\n"
                    "After installation finishes in that shell, restart QGIS.",
                )
                return
            except Exception as exc:
                self.log(f"FAILED Could not open OSGeo4W shell: {exc}")

        # Final fallback: cmd.exe with pip
        self._fallback_windows_pip()

    def _run_bat_installer(self, o4w_env_path):
        """Generate and run a .bat file that sets up the OSGeo4W environment
        and installs dependencies. Works for any QGIS 3.x version."""
        import tempfile

        # CRITICAL: normalize all paths to use backslashes only —
        # cmd.exe cannot handle mixed forward/back slashes
        o4w_env_path = os.path.normpath(o4w_env_path)

        packages_str = " ".join(f'"{pkg}"' for pkg in INSTALL_PACKAGE_SPECS)

        bat_content = f"""@echo off
echo ============================================
echo  TerraClimateDownloader - Dependency Installer
echo ============================================
echo.
echo Setting up QGIS Python environment...
call "{o4w_env_path}"
call py3_env
echo.
echo Python executable:
where python3 2>nul || where python 2>nul
echo.
echo Installing required Python packages...
echo.
python3 -m pip install --upgrade pip 2>nul || python -m pip install --upgrade pip
python3 -m pip install --upgrade-strategy only-if-needed {packages_str} 2>nul || python -m pip install --upgrade-strategy only-if-needed {packages_str}
echo.
echo ============================================
echo  Installation complete! Please restart QGIS.
echo ============================================
echo.
pause
"""
        try:
            # Always write to the system temp directory — avoids permission
            # issues and path problems with the plugin directory
            temp_dir = tempfile.gettempdir()
            bat_path = os.path.normpath(os.path.join(temp_dir, "terraclimate_install_deps.bat"))

            with open(bat_path, "w") as f:
                f.write(bat_content)

            self.log(f"Generated installer script: {bat_path}")
            self.log(f"Using o4w_env.bat: {o4w_env_path}")

            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            subprocess.Popen(
                ["cmd.exe", "/k", bat_path],
                creationflags=creation_flags,
            )
            self.log("Installer window opened. Complete the install in that window, then restart QGIS.")
            QMessageBox.information(
                self,
                "Dependency Installer Opened",
                "An installer window has been opened that will:\n\n"
                "1. Set up the QGIS Python environment\n"
                "2. Install all required packages\n\n"
                "Wait for it to finish, then restart QGIS.",
            )
        except Exception as exc:
            self.log(f"FAILED Could not run bat installer: {exc}")
            self._fallback_windows_pip()

    def _fallback_windows_pip(self):
        """Run pip install in a new cmd.exe console window."""
        pip_command = (
            f'"{sys.executable}" -m pip install --upgrade-strategy only-if-needed '
            + " ".join(f'"{pkg}"' for pkg in INSTALL_PACKAGE_SPECS)
        )
        self.log(f"Fallback command: {pip_command}")

        try:
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            subprocess.Popen(
                ["cmd.exe", "/k", pip_command],
                creationflags=creation_flags,
            )
            self.log("A command prompt was opened with the pip install command.")
            QMessageBox.information(
                self,
                "Pip Install Started",
                "Could not locate OSGeo4W environment files, so a regular\n"
                "command prompt was opened running pip with the QGIS Python.\n\n"
                f"Command:\n{pip_command}\n\n"
                "After installation finishes, restart QGIS.",
            )
        except Exception as exc:
            self.log(f"FAILED Could not run pip: {exc}")
            self._show_manual_install_message()

    # ---- macOS / Linux installer path ------------------------------------------

    def _install_unix(self):
        """macOS / Linux: run pip in-process with live output, or open a terminal."""
        pip_args = [sys.executable, "-m", "pip", "install", "--break-system-packages", "--upgrade-strategy", "only-if-needed"] + list(INSTALL_PACKAGE_SPECS)
        self.log(f"Running: {' '.join(pip_args)}")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # indeterminate
        self.install_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            proc = subprocess.Popen(
                pip_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in proc.stdout:
                self.log(line.rstrip())
                QApplication.processEvents()

            proc.wait()
            self.progress.setVisible(False)
            self.install_btn.setEnabled(True)

            if proc.returncode == 0:
                self.log("")
                self.log("SUCCESS — packages installed.")
                self.log("Please restart QGIS to activate the new packages.")
                QMessageBox.information(
                    self,
                    "Installation Successful",
                    "All dependencies were installed successfully.\n\n"
                    "Please restart QGIS to activate them.",
                )
                return
            else:
                self.log(f"pip exited with return code {proc.returncode}")
                self.log("Trying terminal fallback...")
        except Exception as exc:
            self.progress.setVisible(False)
            self.install_btn.setEnabled(True)
            self.log(f"In-process pip failed: {exc}")
            self.log("Trying terminal fallback...")

        # Fallback: open a terminal window
        self._fallback_unix_terminal()

    def _fallback_unix_terminal(self):
        """Open a native terminal (macOS Terminal.app or Linux xterm) with the pip command."""
        pip_command = get_manual_install_command()
        current_platform = platform.system()

        try:
            if current_platform == "Darwin":
                # macOS: use osascript to open Terminal.app
                script = (
                    f'tell application "Terminal"\n'
                    f'    activate\n'
                    f'    do script "{pip_command}"\n'
                    f'end tell'
                )
                subprocess.Popen(["osascript", "-e", script])
                self.log("Opened Terminal.app with pip install command.")
                QMessageBox.information(
                    self,
                    "Terminal Opened",
                    "A Terminal window has been opened with the install command.\n\n"
                    "After installation finishes, restart QGIS.",
                )
            else:
                # Linux: try common terminal emulators
                terminal_opened = False
                for terminal_cmd in [
                    ["x-terminal-emulator", "-e", f"bash -c '{pip_command}; echo Done; read'"],
                    ["gnome-terminal", "--", "bash", "-c", f"{pip_command}; echo Done; read"],
                    ["xterm", "-hold", "-e", pip_command],
                    ["konsole", "-e", "bash", "-c", f"{pip_command}; echo Done; read"],
                ]:
                    try:
                        subprocess.Popen(terminal_cmd)
                        terminal_opened = True
                        self.log(f"Opened terminal: {terminal_cmd[0]}")
                        QMessageBox.information(
                            self,
                            "Terminal Opened",
                            "A terminal window has been opened with the install command.\n\n"
                            "After installation finishes, restart QGIS.",
                        )
                        break
                    except FileNotFoundError:
                        continue

                if not terminal_opened:
                    raise RuntimeError("No supported terminal emulator found.")

        except Exception as exc:
            self.log(f"FAILED Could not open terminal: {exc}")
            self._show_manual_install_message()

    # ---- Shared helpers --------------------------------------------------------

    def _show_manual_install_message(self):
        """Show a dialog with the manual install command."""
        manual = get_manual_install_command()
        self.log(f"Please run this command manually:\n{manual}")
        QMessageBox.warning(
            self,
            "Installation Failed",
            "The plugin could not install dependencies automatically.\n\n"
            "Please open a terminal and run:\n\n"
            f"{manual}\n\n"
            "Then restart QGIS.",
        )


class TerraClimateProvider(QgsProcessingProvider):
    """Processing provider for TerraClimate algorithms."""

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.svg"))

    def loadAlgorithms(self):
        from .terraclimate_algorithm import TerraClimateClipByYear_GDAL
        from .split_raster_bands_algorithm import SplitRasterBands
        from .resample_raster_algorithm import ResampleRasterToReference

        self.addAlgorithm(TerraClimateClipByYear_GDAL())
        self.addAlgorithm(SplitRasterBands())
        self.addAlgorithm(ResampleRasterToReference())

    def id(self):
        return PLUGIN_PROVIDER_ID

    def name(self):
        return self.tr("TerraClimate Downloader")

    def longName(self):
        return self.name()

    def tr(self, text):
        return QCoreApplication.translate("TerraClimateProvider", text)


class TerraClimateProviderPlugin:
    """Main plugin class - registers provider and manages menu entries."""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.actions = []
        self.menu_name = "TerraClimate Downloader"
        self.toolbar = None
        self.icon_path = os.path.join(os.path.dirname(__file__), "icon.svg")

    def initGui(self):
        """Initialize the plugin GUI."""
        self.toolbar = self.iface.addToolBar(self.menu_name)
        self.toolbar.setObjectName("TerraClimateToolbar")

        deps_ok = dependencies_ready()

        self.provider = TerraClimateProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        icon = QIcon(self.icon_path) if os.path.exists(self.icon_path) else QIcon()
        action_text = "Open TerraClimate Downloader" if deps_ok else "Open TerraClimate Downloader (Setup Required)"
        action_tooltip = (
            "Download and clip TerraClimate climate data"
            if deps_ok else
            "Open dependency diagnostics and installation help"
        )

        self.action_open = QAction(icon, action_text, self.iface.mainWindow())
        self.action_open.setToolTip(action_tooltip)
        self.action_open.triggered.connect(self.open_tool_dialog)
        self.iface.addPluginToMenu(self.menu_name, self.action_open)
        self.toolbar.addAction(self.action_open)
        self.actions.append(self.action_open)

        self.action_install = QAction(
            QIcon.fromTheme("system-software-install"),
            "Install Dependencies...",
            self.iface.mainWindow(),
        )
        self.action_install.setToolTip("Install or update Python packages for TerraClimate Downloader")
        self.action_install.triggered.connect(self.show_installer_dialog)
        self.iface.addPluginToMenu(self.menu_name, self.action_install)
        self.actions.append(self.action_install)

        self.action_help = QAction(
            QIcon.fromTheme("help-about"),
            "About / Help",
            self.iface.mainWindow(),
        )
        self.action_help.triggered.connect(self.show_help)
        self.iface.addPluginToMenu(self.menu_name, self.action_help)
        self.actions.append(self.action_help)

        if not deps_ok:
            self.iface.messageBar().pushMessage(
                "TerraClimate Downloader",
                "Dependencies need attention. Open Plugins > TerraClimate Downloader > Install Dependencies.",
                level=Qgis.Warning,
                duration=10,
            )

    def unload(self):
        """Unload the plugin."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu_name, action)
            if self.toolbar:
                self.toolbar.removeAction(action)
        self.actions = []

        if self.toolbar:
            self.toolbar.deleteLater()
            self.toolbar = None

        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

    def open_tool_dialog(self):
        """Open the main processing tool dialog."""
        missing_req, _ = get_missing_packages()
        incompatible = get_incompatible_packages()

        if missing_req or incompatible:
            details = []
            if missing_req:
                details.append("Missing packages: " + ", ".join([module for module, _ in missing_req]))
            if incompatible:
                details.append(
                    "Outdated packages: " +
                    ", ".join([f"{module} ({installed} < {minimum})" for module, _, installed, minimum in incompatible])
                )
            details.append(f"QGIS Python: {sys.executable}")

            reply = QMessageBox.question(
                self.iface.mainWindow(),
                "Dependencies Required",
                "TerraClimate Downloader needs Python dependencies before it can run.\n\n"
                + "\n".join(details)
                + "\n\nWould you like to open the dependency installer?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self.show_installer_dialog()
            return

        try:
            import processing

            alg_id = f"{PLUGIN_PROVIDER_ID}:terraclimate_clip_remote_to_layer_gdalclip"
            processing.execAlgorithmDialog(alg_id, {})
        except Exception as exc:
            self.iface.messageBar().pushMessage(
                "TerraClimate Downloader",
                f"Could not open dialog: {exc}. Try the Processing Toolbox instead.",
                level=Qgis.Warning,
                duration=5,
            )

    def show_installer_dialog(self):
        """Show the dependency installer dialog."""
        dialog = DependencyInstallerDialog(self.iface.mainWindow())
        dialog.exec_()

        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = TerraClimateProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)

        deps_ok = dependencies_ready()
        if hasattr(self, "action_open"):
            self.action_open.setText(
                "Open TerraClimate Downloader" if deps_ok else "Open TerraClimate Downloader (Setup Required)"
            )

    def show_help(self):
        """Show help/about dialog."""
        help_text = f"""
        <h2>TerraClimate Downloader v{PLUGIN_VERSION}</h2>
        <p><b>Author:</b> Hemed Lungo</p>
        <p><b>Email:</b> Hemedlungo@gmail.com</p>

        <h3>Description</h3>
        <p>Download and clip TerraClimate climate data for any region on Earth.</p>
        <p>Supports single-year downloads and multi-year stacks through 2025.</p>

        <h3>Tools</h3>
        <ul>
            <li><b>Download TerraClimate Data</b> – download and clip climate variables to your AOI</li>
            <li><b>Split Raster Bands</b> – split multi-band output into monthly or yearly files</li>
            <li><b>Resample Raster to Reference</b> – resample any raster to match a DEM or other reference grid</li>
        </ul>

        <h3>Dependencies</h3>
        <p>The tool uses the QGIS Python environment plus these packages:</p>
        <ul>
            <li>Required: numpy, xarray, rioxarray, netCDF4</li>
            <li>Optional: dask</li>
        </ul>
        <p>If the tool does not open, use <b>Plugins &gt; TerraClimate Downloader &gt; Install Dependencies</b>.</p>

        <h3>Manual Install Command</h3>
        <p><code>{get_manual_install_command()}</code></p>

        <h3>Links</h3>
        <p>
            <a href="https://github.com/Heed725/Terraclimate_QGIS_Plugin/">GitHub Repository</a><br>
            <a href="https://www.climatologylab.org/terraclimate.html">TerraClimate Dataset</a>
        </p>
        """

        QMessageBox.about(
            self.iface.mainWindow(),
            "About TerraClimate Downloader",
            help_text,
        )
