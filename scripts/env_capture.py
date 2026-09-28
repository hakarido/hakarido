#!/usr/bin/env python3
"""env_capture.py — 記事の「環境」欄に貼る情報を results/env.txt に書く。

集めるもの: 日付、OS（種類・カーネル・WSL か）、CPU モデル・コア数、メモリ総量、Python、主要パッケージの版、
           生成に使ったモデル名（引数で渡す）。
集めないもの（公開物に載せない）: ホスト名、ユーザー名、ホームディレクトリのパス、IP・MAC・ネットワーク、環境変数。
最後に、ホームディレクトリ名が本文に紛れ込んでいないかを確認して置換する（保険）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import platform
import sys
from importlib import metadata
from pathlib import Path

PACKAGES = ["pytest", "pytest-cov", "coverage", "mutmut", "hypothesis", "ruff", "mypy", "bandit", "radon", "matplotlib"]


def read_first(path: str, key: str) -> str:
    try:
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith(key.lower()):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def cpu_model() -> str:
    return read_first("/proc/cpuinfo", "model name") or platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "") or "unknown"


def mem_total_gb() -> str:
    raw = read_first("/proc/meminfo", "MemTotal")  # 例: "16318428 kB"
    if raw:
        try:
            return f"{int(raw.split()[0]) / 1024 / 1024:.1f} GB"
        except (ValueError, IndexError):
            pass
    if platform.system() == "Windows":  # Windows ネイティブで動かしたとき用（値だけ、機器名は取らない）
        try:
            import ctypes

            class _MemStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            status = _MemStatus()
            status.dwLength = ctypes.sizeof(_MemStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return f"{status.ullTotalPhys / 1024 ** 3:.1f} GB"
        except Exception:
            pass
    return "unknown"


def is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return False


def pkg_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "-"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="unknown", help="生成に使ったモデル名・バージョン")
    p.add_argument("--date", default=dt.date.today().isoformat())
    p.add_argument("--out", default="results/env.txt")
    a = p.parse_args()

    lines = [
        f"date: {a.date}",
        f"model: {a.model}",
        f"os: {platform.system()} {platform.release()} ({platform.machine()}){'  [WSL2]' if is_wsl() else ''}",
        f"cpu: {cpu_model()}  cores={os.cpu_count()}",
        f"memory: {mem_total_gb()}",
        f"python: {sys.version.split()[0]}",
        "packages: " + ", ".join(f"{n} {pkg_version(n)}" for n in PACKAGES),
        "note: ホスト名・ユーザー名・パス・ネットワーク情報は収集していません",
    ]
    text = "\n".join(lines) + "\n"

    home_name = Path.home().name
    if home_name and len(home_name) >= 3 and home_name in text:
        text = text.replace(home_name, "<home>")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
