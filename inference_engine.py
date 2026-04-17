"""
Custom Inference Engine for UNIchat
Supports Qwen 0.5B via llama.cpp and BitNet models.
Auto-detects hardware constraints and configures optimal settings.
"""

import os
import sys
import platform
import subprocess
import json
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


# ──────────────────────────────────────────────
# Hardware Detection
# ──────────────────────────────────────────────
@dataclass
class HardwareProfile:
    """Detected hardware capabilities."""
    cpu_name: str = ""
    cpu_cores: int = 1
    cpu_threads: int = 1
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    gpu_name: str = ""
    is_integrated_gpu: bool = True
    os_name: str = ""

    # Computed recommendations
    recommended_threads: int = 2
    recommended_ctx: int = 1024
    recommended_batch: int = 128
    can_run_2b: bool = False
    can_run_1b: bool = True
    can_run_05b: bool = True


def detect_hardware() -> HardwareProfile:
    """Detect system hardware and compute optimal inference settings."""
    hw = HardwareProfile()
    hw.os_name = platform.system() + " " + platform.release()
    hw.cpu_name = platform.processor() or "Unknown CPU"
    hw.cpu_cores = os.cpu_count() or 2
    hw.cpu_threads = hw.cpu_cores

    # RAM detection (Windows)
    try:
        if platform.system() == "Windows":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            hw.ram_total_gb = round(mem.ullTotalPhys / (1024 ** 3), 1)
            hw.ram_available_gb = round(mem.ullAvailPhys / (1024 ** 3), 1)
    except Exception:
        hw.ram_total_gb = 8.0
        hw.ram_available_gb = 4.0

    # GPU detection (Windows wmic)
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True, text=True, timeout=5,
            )
            lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip() and l.strip() != "Name"]
            if lines:
                hw.gpu_name = lines[0]
                igpu_kw = ["intel", "uhd", "hd graphics", "iris", "vega", "radeon graphics"]
                hw.is_integrated_gpu = any(k in hw.gpu_name.lower() for k in igpu_kw)
    except Exception:
        hw.gpu_name = "Unknown"
        hw.is_integrated_gpu = True

    # Compute recommendations
    hw.recommended_threads = max(2, hw.cpu_cores - 2)
    hw.recommended_ctx = 2048 if hw.ram_available_gb >= 4 else 1024
    hw.recommended_batch = 256 if hw.ram_available_gb >= 8 else 128
    hw.can_run_05b = hw.ram_available_gb >= 1.0
    hw.can_run_1b = hw.ram_available_gb >= 2.0
    hw.can_run_2b = hw.ram_available_gb >= 3.0

    return hw


# ──────────────────────────────────────────────
# Inference Config
# ──────────────────────────────────────────────
@dataclass
class InferenceConfig:
    model_path: str = "models/model.gguf"
    n_ctx: int = 2048
    n_threads: int = 4
    n_batch: int = 256
    n_gpu_layers: int = 0
    max_tokens: int = 256
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    use_bitnet: bool = False
    bitnet_path: str = "BitNet"


# ──────────────────────────────────────────────
# Inference Engine
# ──────────────────────────────────────────────
class InferenceEngine:
    """
    Custom inference engine for UNIchat.

    Backends:
    1. llama.cpp (via llama-cpp-python) - Qwen 0.5B GGUF models
    2. BitNet (via bitnet.cpp subprocess) - BitNet b1.58 1-bit models

    Auto-configures based on detected hardware constraints.
    """

    def __init__(self, config: Optional[InferenceConfig] = None):
        self.hw = detect_hardware()
        self.config = config or self._auto_config()
        self.llm = None
        self.backend = None  # "llama_cpp" | "bitnet" | None
        self._print_hw_report()
        self._init_backend()

    def _auto_config(self) -> InferenceConfig:
        cfg = InferenceConfig()
        cfg.n_threads = self.hw.recommended_threads
        cfg.n_ctx = self.hw.recommended_ctx
        cfg.n_batch = self.hw.recommended_batch
        cfg.n_gpu_layers = 0  # CPU-only for integrated GPU

        bitnet_dir = Path("BitNet")
        if bitnet_dir.exists():
            cfg.use_bitnet = True
            cfg.bitnet_path = str(bitnet_dir)

        return cfg

    def _print_hw_report(self):
        hw = self.hw
        cfg = self.config
        print("")
        print("=" * 55)
        print("  UNIchat Inference Engine - Hardware Profile")
        print("=" * 55)
        print(f"  OS:            {hw.os_name}")
        print(f"  CPU:           {hw.cpu_name}")
        print(f"  CPU Cores:     {hw.cpu_cores}")
        print(f"  RAM Total:     {hw.ram_total_gb} GB")
        print(f"  RAM Available: {hw.ram_available_gb} GB")
        print(f"  GPU:           {hw.gpu_name}")
        print(f"  GPU Type:      {'Integrated' if hw.is_integrated_gpu else 'Discrete'}")
        print("-" * 55)
        print("  Inference Settings (auto-tuned):")
        print(f"    Threads:     {cfg.n_threads} / {hw.cpu_cores}")
        print(f"    Context:     {cfg.n_ctx} tokens")
        print(f"    Batch Size:  {cfg.n_batch}")
        print(f"    GPU Offload: {'None (CPU only)' if cfg.n_gpu_layers == 0 else str(cfg.n_gpu_layers) + ' layers'}")
        print("-" * 55)
        print("  Model Compatibility:")
        print(f"    Qwen 0.5B Q4: {'OK' if hw.can_run_05b else 'INSUFFICIENT RAM (need 1GB+)'}")
        print(f"    Qwen 1.5B Q4: {'OK' if hw.can_run_1b else 'INSUFFICIENT RAM (need 2GB+)'}")
        print(f"    BitNet 2B:    {'OK' if hw.can_run_2b else 'INSUFFICIENT RAM (need 3GB+)'}")
        print("=" * 55)
        print("")

    def _init_backend(self):
        """Initialize best available backend (BitNet first, then llama.cpp)."""
        if self.config.use_bitnet and self._init_bitnet():
            return
        if self._init_llama_cpp():
            return
        print("[Engine] No model backend. Running in RAG-only mode (direct KB answers).")

    def _init_llama_cpp(self) -> bool:
        """Load Qwen GGUF model via llama-cpp-python."""
        mp = self.config.model_path
        if not os.path.exists(mp):
            print(f"[Engine] Model not found: {mp}")
            return False
        try:
            from llama_cpp import Llama
            self.llm = Llama(
                model_path=mp,
                n_ctx=self.config.n_ctx,
                n_threads=self.config.n_threads,
                n_batch=self.config.n_batch,
                n_gpu_layers=self.config.n_gpu_layers,
                verbose=False,
            )
            self.backend = "llama_cpp"
            sz = os.path.getsize(mp) / (1024 * 1024)
            print(f"[Engine] Loaded Qwen via llama.cpp ({sz:.0f} MB)")
            return True
        except ImportError:
            print("[Engine] llama-cpp-python not installed. pip install llama-cpp-python")
            return False
        except Exception as e:
            print(f"[Engine] llama.cpp load failed: {e}")
            return False

    def _init_bitnet(self) -> bool:
        """Check BitNet installation and readiness."""
        bd = Path(self.config.bitnet_path)
        if not bd.exists():
            print("[Engine] BitNet dir not found. Clone: git clone --recursive https://github.com/microsoft/BitNet.git")
            return False

        build = bd / "build"
        if not build.exists():
            print("[Engine] BitNet not built. Run: python setup_env.py -md models/BitNet-b1.58-2B-4T -q i2_s")
            return False

        self.backend = "bitnet"
        print(f"[Engine] BitNet backend ready at {bd}")
        return True

    @property
    def is_available(self) -> bool:
        return self.backend is not None

    def generate(self, system_prompt: str, user_message: str) -> str:
        """Generate a response using the active backend."""
        if self.backend == "llama_cpp":
            return self._gen_llama(system_prompt, user_message)
        elif self.backend == "bitnet":
            return self._gen_bitnet(system_prompt, user_message)
        return ""

    def _gen_llama(self, sys_prompt: str, user_msg: str) -> str:
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ]
        try:
            out = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                repeat_penalty=self.config.repeat_penalty,
            )
            return out["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[Engine] llama.cpp generation error: {e}")
            return ""

    def _gen_bitnet(self, sys_prompt: str, user_msg: str) -> str:
        """Generate via BitNet subprocess call."""
        full_prompt = sys_prompt + "\n\nUser: " + user_msg + "\nAssistant:"
        bd = Path(self.config.bitnet_path)

        try:
            # BitNet uses its own inference binary
            result = subprocess.run(
                [
                    sys.executable, str(bd / "run_inference.py"),
                    "-m", str(bd / "models" / "BitNet-b1.58-2B-4T"),
                    "-p", full_prompt,
                    "-n", str(self.config.max_tokens),
                    "-t", str(self.config.n_threads),
                ],
                capture_output=True, text=True, timeout=30,
                cwd=str(bd),
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"[Engine] BitNet error: {result.stderr[:200]}")
                return ""
        except subprocess.TimeoutExpired:
            print("[Engine] BitNet generation timed out")
            return ""
        except Exception as e:
            print(f"[Engine] BitNet error: {e}")
            return ""

    def get_status(self) -> dict:
        """Return engine status for health checks."""
        return {
            "backend": self.backend or "none",
            "model": self.config.model_path if self.backend == "llama_cpp" else self.config.bitnet_path,
            "hardware": {
                "cpu": self.hw.cpu_name,
                "cores": self.hw.cpu_cores,
                "ram_gb": self.hw.ram_total_gb,
                "ram_free_gb": self.hw.ram_available_gb,
                "gpu": self.hw.gpu_name,
                "gpu_type": "integrated" if self.hw.is_integrated_gpu else "discrete",
            },
            "config": {
                "threads": self.config.n_threads,
                "ctx": self.config.n_ctx,
                "batch": self.config.n_batch,
                "gpu_layers": self.config.n_gpu_layers,
            },
        }


# ──────────────────────────────────────────────
# Quick test
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("Running hardware detection and engine init...")
    engine = InferenceEngine()
    print("\nEngine status:")
    print(json.dumps(engine.get_status(), indent=2))

    if engine.is_available:
        print("\nTest generation:")
        resp = engine.generate(
            "You are UNIchat, MUJ's chatbot. Be brief.",
            "What programs does MUJ offer?"
        )
        print(f"Response: {resp}")
    else:
        print("\nNo model loaded. Install a model to test generation.")
