"""
AstroGen — Desktop Launcher (frontend/main.py)
Handles: dependency install, GPU detection (NVIDIA/CPU), backend launch, Vite launch.
No Intel XPU / DirectML support — uses NVIDIA CUDA or CPU only.
"""

import sys
import os
import subprocess
import time
import socket
import atexit
import re
import json
from PyQt6.QtCore import QUrl, QTimer, QThread, pyqtSignal, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QProgressBar, QTextEdit, QFrame
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QIcon, QColor, QPalette, QFont, QLinearGradient, QPainter, QBrush, QPen
from PyQt6.QtCore import QRect, QPoint
import ctypes

# ── Paths ────────────────────────────────────────────────────────────────────
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR     = os.path.dirname(FRONTEND_DIR)
PORT         = 5173
HOST         = "127.0.0.1"
URL          = f"http://{HOST}:{PORT}"

# ── Windows taskbar grouping ──────────────────────────────────────────────────
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('astro.astrogen.app.v2')
except Exception:
    pass

# ── .env helpers ──────────────────────────────────────────────────────────────
def get_env_var(key):
    env_path = os.path.join(ROOT_DIR, ".env")
    if not os.path.exists(env_path):
        return None
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(fr"^{key}\s*=\s*(.*)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip().strip("'\"")
    except Exception:
        pass
    return None

def set_env_var(key, value):
    env_path = os.path.join(ROOT_DIR, ".env")
    content = ""
    try:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
        pattern = fr"^{key}\s*=\s*(.*)$"
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, f"{key}={value}", content, flags=re.MULTILINE)
        else:
            if content and not content.endswith("\n"):
                content += "\n"
            content += f"{key}={value}\n"
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

# ── app_state.json helpers ────────────────────────────────────────────────────
def get_app_state():
    state_path = os.path.join(ROOT_DIR, "data", "app_state.json")
    default = {"launch_count": 0, "kaggle_connected": False, "kaggle_url": ""}
    try:
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                return {**default, **json.load(f)}
    except Exception:
        pass
    return default

def set_app_state(state: dict):
    state_path = os.path.join(ROOT_DIR, "data", "app_state.json")
    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

# ── Increment launch count ────────────────────────────────────────────────────
_state = get_app_state()
_state["launch_count"] = _state.get("launch_count", 0) + 1
set_app_state(_state)


# ══════════════════════════════════════════════════════════════════════════════
# DependencyInstaller — background thread
# Steps & progress mapping:
#   0-10%   GPU detection
#   10-20%  venv creation / verification
#   20-25%  pip upgrade
#   25-55%  torch install (if missing)
#   55-85%  other packages install (if missing)
#   85-95%  import verification
#   95-100% ready
# ══════════════════════════════════════════════════════════════════════════════

PACKAGES_TO_CHECK = [
    "torch", "diffusers", "transformers", "peft", "accelerate",
    "fastapi", "uvicorn", "PIL", "google.generativeai"
]

STEP_MESSAGES = [
    "Scanning hardware profile...",
    "Preparing Python workspace...",
    "Updating package manager...",
    "Installing PyTorch acceleration engine...",
    "Installing astronomy model libraries...",
    "Verifying all components...",
    "All systems go!",
]

class DependencyInstaller(QThread):
    progress = pyqtSignal(str, int)   # (message, percent)
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def _detect_gpu(self):
        """Detect NVIDIA GPU via PowerShell/lspci. Returns 'nvidia' or 'cpu'."""
        try:
            if os.name == 'nt':
                out = subprocess.check_output(
                    ["powershell", "-Command",
                     "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
                    text=True, timeout=5
                )
            else:
                out = subprocess.check_output("lspci | grep -i vga", shell=True, text=True, timeout=5)
            if "nvidia" in out.lower():
                return "nvidia"
        except Exception:
            pass
        return "cpu"

    def _check_imports(self, python_exe):
        """Return True if all required packages are importable."""
        check_script = f"import {', '.join(PACKAGES_TO_CHECK)}"
        res = subprocess.run([python_exe, "-c", check_script], capture_output=True)
        return res.returncode == 0

    def _pip(self, python_exe, args, label, start_pct, end_pct):
        """Run pip install with smooth progress reporting."""
        cmd = [python_exe, "-m", "pip"] + args + ["--progress-bar", "on"]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=0, shell=(os.name == 'nt')
        )
        pct_range = end_pct - start_pct
        buffer = []
        while True:
            byte = process.stdout.read(1)
            if not byte:
                if process.poll() is not None:
                    break
                time.sleep(0.01)
                continue
            char = byte.decode("utf-8", errors="ignore")
            if char in ("\n", "\r"):
                line = "".join(buffer).strip()
                buffer = []
                if not line:
                    continue
                pct_match = re.search(r"(\d+)%", line)
                if pct_match:
                    sub_pct = int(pct_match.group(1))
                    overall = start_pct + int((sub_pct / 100.0) * pct_range)
                    self.progress.emit(f"{label} ({sub_pct}%)", overall)
                else:
                    size_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*(MB|GB|KB)", line, re.I)
                    if size_match:
                        cur, tot = float(size_match.group(1)), float(size_match.group(2))
                        sub_pct = int((cur / tot) * 100) if tot > 0 else 0
                        overall = start_pct + int((sub_pct / 100.0) * pct_range)
                        self.progress.emit(f"{label} ({cur:.0f}/{tot:.0f} {size_match.group(3)})", overall)
            else:
                buffer.append(char)
                if len(buffer) > 1000:
                    buffer = []
        process.wait()
        self.progress.emit(f"{label} — done", end_pct)

    def run(self):
        try:
            # ── Shortcut: already set up ──────────────────────────────────
            venv_dir = os.path.join(ROOT_DIR, ".venv")
            python_exe = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == "nt" \
                         else os.path.join(venv_dir, "bin", "python")
            backend_set = get_env_var("ASTROGEN_BACKEND")
            if backend_set and os.path.exists(venv_dir):
                self.progress.emit("Workspace ready — fast boot!", 100)
                self.finished.emit()
                return

            # ── Step 1: GPU detection (0→10%) ────────────────────────────
            self.progress.emit(STEP_MESSAGES[0], 5)
            gpu = self._detect_gpu()
            time.sleep(0.5)

            if gpu == "nvidia":
                self.progress.emit("NVIDIA GPU detected — CUDA acceleration enabled", 10)
            else:
                self.progress.emit("No NVIDIA GPU found — CPU mode selected", 10)

            # ── Step 2: Create venv if missing (10→20%) ───────────────────
            self.progress.emit(STEP_MESSAGES[1], 12)
            if not os.path.exists(venv_dir):
                self.progress.emit("Creating Python virtual environment...", 13)
                subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True, capture_output=True)
            self.progress.emit("Python environment ready", 18)
            time.sleep(0.3)

            # ── Step 3: Upgrade pip (20→25%) ─────────────────────────────
            self.progress.emit(STEP_MESSAGES[2], 20)
            subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "-q"],
                           capture_output=True)
            self.progress.emit("Package manager updated", 25)

            # ── Step 4: Check if all packages already installed ───────────
            self.progress.emit("Checking installed components...", 28)
            all_good = self._check_imports(python_exe)

            if all_good:
                self.progress.emit("All packages verified — no reinstall needed", 90)
                # Confirm backend
                if gpu == "nvidia":
                    cuda_ok = subprocess.run(
                        [python_exe, "-c", "import torch; assert torch.cuda.is_available()"],
                        capture_output=True
                    ).returncode == 0
                    set_env_var("ASTROGEN_BACKEND", "cuda" if cuda_ok else "cpu")
                else:
                    set_env_var("ASTROGEN_BACKEND", "cpu")
            else:
                # ── Step 5: Install torch (25→55%) ───────────────────────
                self.progress.emit(STEP_MESSAGES[3], 30)
                if gpu == "nvidia":
                    torch_cmd = ["install", "torch", "torchvision", "torchaudio",
                                 "--index-url", "https://download.pytorch.org/whl/cu121"]
                else:
                    torch_cmd = ["install", "torch", "torchvision", "torchaudio"]
                self._pip(python_exe, torch_cmd,
                          "Installing PyTorch" + (" + CUDA" if gpu == "nvidia" else " (CPU)"),
                          30, 55)

                # ── Step 6: Other packages (55→85%) ──────────────────────
                self.progress.emit(STEP_MESSAGES[4], 55)
                req_file = os.path.join(ROOT_DIR, "backend", "requirements_docker.txt")
                if os.path.exists(req_file):
                    self._pip(python_exe, ["install", "-r", req_file, "-q"],
                              "Installing model libraries", 55, 85)
                else:
                    pkgs = [
                        "fastapi", "uvicorn", "python-multipart", "python-dotenv",
                        "pydantic", "transformers==4.38.2", "accelerate==0.27.2",
                        "peft==0.9.0", "safetensors", "Pillow", "open_clip_torch",
                        "huggingface_hub", "google-generativeai", "requests", "numpy"
                    ]
                    self._pip(python_exe, ["install"] + pkgs,
                              "Installing model libraries", 55, 85)

                # ── Set backend ───────────────────────────────────────────
                if gpu == "nvidia":
                    cuda_ok = subprocess.run(
                        [python_exe, "-c", "import torch; assert torch.cuda.is_available()"],
                        capture_output=True
                    ).returncode == 0
                    set_env_var("ASTROGEN_BACKEND", "cuda" if cuda_ok else "cpu")
                else:
                    set_env_var("ASTROGEN_BACKEND", "cpu")

            # ── Step 7: Verify imports (85→95%) ──────────────────────────
            self.progress.emit(STEP_MESSAGES[5], 87)
            time.sleep(0.5)
            if not self._check_imports(python_exe):
                self.progress.emit("Some packages may need a restart — continuing...", 92)
            else:
                self.progress.emit("All modules verified successfully", 95)
            time.sleep(0.4)

            # ── Done (95→100%) ────────────────────────────────────────────
            self.progress.emit(STEP_MESSAGES[6], 100)
            time.sleep(0.5)
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))


# ══════════════════════════════════════════════════════════════════════════════
# Loading Screen Widget — premium dark space theme
# ══════════════════════════════════════════════════════════════════════════════

LOADING_STYLE = """
QWidget#loadingRoot {
    background-color: #040508;
}
QLabel#appTitle {
    color: #ffffff;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: 6px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
QLabel#appSubtitle {
    color: #6366f1;
    font-size: 12px;
    letter-spacing: 3px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 600;
}
QLabel#statusMsg {
    color: #94a3b8;
    font-size: 13px;
    font-family: 'Segoe UI', sans-serif;
}
QProgressBar#mainBar {
    border: none;
    border-radius: 4px;
    background-color: rgba(255, 255, 255, 0.05);
    height: 6px;
    text-align: center;
}
QProgressBar#mainBar::chunk {
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:0.5 #8b5cf6, stop:1 #06b6d4);
}
QTextEdit#logPanel {
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    color: #475569;
    font-family: 'Consolas', monospace;
    font-size: 11px;
    padding: 8px 10px;
}
QLabel#pctLabel {
    color: #6366f1;
    font-size: 13px;
    font-weight: 700;
    font-family: 'Consolas', monospace;
}
QLabel#gpuBadge {
    color: #10b981;
    font-size: 11px;
    font-family: 'Consolas', monospace;
    padding: 3px 10px;
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 10px;
    background: rgba(16, 185, 129, 0.08);
}
QLabel#cpuBadge {
    color: #f59e0b;
    font-size: 11px;
    font-family: 'Consolas', monospace;
    padding: 3px 10px;
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 10px;
    background: rgba(245, 158, 11, 0.08);
}
"""

class LoadingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loadingRoot")
        self.setStyleSheet(LOADING_STYLE)
        self._gpu_badge = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Center card ──────────────────────────────────────────────
        card = QWidget()
        card.setFixedWidth(480)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo / icon area
        logo_label = QLabel("✦ ASTROGEN")
        logo_label.setObjectName("appTitle")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(logo_label)

        card_layout.addSpacing(4)

        subtitle = QLabel("SPACE STUDIO")
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(32)

        # GPU badge row
        badge_row = QHBoxLayout()
        badge_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gpu_badge = QLabel("● Detecting hardware...")
        self._gpu_badge.setObjectName("cpuBadge")
        badge_row.addWidget(self._gpu_badge)
        card_layout.addLayout(badge_row)

        card_layout.addSpacing(24)

        # Status message
        self._status = QLabel("Initializing AstroGen...")
        self._status.setObjectName("statusMsg")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)
        card_layout.addWidget(self._status)

        card_layout.addSpacing(12)

        # Progress bar + percentage row
        pbar_row = QHBoxLayout()
        pbar_row.setSpacing(12)
        self._bar = QProgressBar()
        self._bar.setObjectName("mainBar")
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        pbar_row.addWidget(self._bar)

        self._pct = QLabel("0%")
        self._pct.setObjectName("pctLabel")
        self._pct.setFixedWidth(40)
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        pbar_row.addWidget(self._pct)
        card_layout.addLayout(pbar_row)

        card_layout.addSpacing(20)

        # Log console
        self._log = QTextEdit()
        self._log.setObjectName("logPanel")
        self._log.setReadOnly(True)
        self._log.setFixedHeight(110)
        card_layout.addWidget(self._log)

        self._log_entries = []

        outer.addWidget(card)

    def set_gpu(self, gpu_type: str):
        if gpu_type == "nvidia":
            self._gpu_badge.setObjectName("gpuBadge")
            self._gpu_badge.setText("● NVIDIA CUDA  •  GPU Acceleration")
        else:
            self._gpu_badge.setObjectName("cpuBadge")
            self._gpu_badge.setText("● CPU Mode  •  Kaggle GPU available via popup")
        # Re-apply stylesheet to pick up objectName change
        self._gpu_badge.setStyleSheet("")
        self.setStyleSheet(LOADING_STYLE)

    def update_progress(self, msg: str, val: int):
        self._status.setText(msg)
        self._bar.setValue(val)
        self._pct.setText(f"{val}%")

        # Update gpu badge from first message
        if val <= 12:
            if "nvidia" in msg.lower() or "cuda" in msg.lower():
                self.set_gpu("nvidia")
            elif "cpu" in msg.lower() or "no nvidia" in msg.lower():
                self.set_gpu("cpu")

        # Smart log — update in place if same step, else append
        is_update = False
        action_prefix = msg.split("(")[0].split("—")[0].strip()
        if self._log_entries:
            last = self._log_entries[-1]
            if last.startswith("[→] " + action_prefix[:20]) or last.startswith("[✔] " + action_prefix[:20]):
                self._log_entries[-1] = f"[→] {msg}"
                is_update = True

        if not is_update:
            if self._log_entries:
                prev = self._log_entries[-1]
                if prev.startswith("[→]"):
                    self._log_entries[-1] = "[✔]" + prev[3:].split("(")[0].rstrip() + " — done"
            self._log_entries.append(f"[→] {msg}")

        self._log.setPlainText("\n".join(self._log_entries))
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())


# ══════════════════════════════════════════════════════════════════════════════
# MainWindow
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AstroGen Space Studio")
        self.setMinimumSize(1280, 800)
        icon_path = os.path.join(FRONTEND_DIR, "logo.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Root widget
        self._root = QWidget()
        self.setCentralWidget(self._root)
        self._layout = QVBoxLayout(self._root)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Loading screen
        self._loading = LoadingWidget()
        self._layout.addWidget(self._loading)

        # Web view (hidden until Vite is ready)
        self._web = QWebEngineView()

        # Vite readiness timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_server)

        # Start installer
        self._installer = DependencyInstaller()
        self._installer.progress.connect(self._on_progress)
        self._installer.finished.connect(self._on_finished)
        self._installer.error.connect(self._on_error)
        self._installer.start()

    def _on_progress(self, msg: str, val: int):
        self._loading.update_progress(msg, val)

    def _on_finished(self):
        self._loading.update_progress("Launching AstroGen servers...", 100)
        self._start_backend()
        self._vite_proc = start_vite()
        self._timer.start(500)

    def _on_error(self, err: str):
        self._loading._status.setText(f"Error: {err}")
        self._loading._status.setStyleSheet("color: #ef4444;")

    def _start_backend(self):
        venv_dir = os.path.join(ROOT_DIR, ".venv")
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == "nt" \
                     else os.path.join(venv_dir, "bin", "python")
        backend_main = os.path.join(ROOT_DIR, "backend", "main.py")
        log_file     = os.path.join(ROOT_DIR, "backend_log.txt")
        proc = subprocess.Popen(
            [python_exe, "-u", backend_main],
            cwd=ROOT_DIR,
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            shell=(os.name == "nt")
        )
        def _kill():
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                proc.terminate()
        atexit.register(_kill)

    def _check_server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            s.connect((HOST, PORT))
            s.close()
            self._timer.stop()
            self._layout.removeWidget(self._loading)
            self._loading.deleteLater()
            self._layout.addWidget(self._web)
            self._web.setUrl(QUrl(URL))
        except Exception:
            pass


# ── Vite process launcher ─────────────────────────────────────────────────────
def start_vite():
    env = os.environ.copy()
    env["PORT"] = str(PORT)
    env["BASE_PATH"] = "/"
    log_file = os.path.join(ROOT_DIR, "vite_log.txt")
    proc = subprocess.Popen(
        ["npx", "-y", "pnpm", "--filter", "@workspace/astrogen", "run", "dev"],
        cwd=FRONTEND_DIR,
        env=env,
        shell=True,
        stdout=open(log_file, "a"),
        stderr=subprocess.STDOUT,
    )
    def _kill():
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            proc.terminate()
    atexit.register(_kill)
    return proc


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
