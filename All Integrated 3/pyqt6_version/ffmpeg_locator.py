#!/usr/bin/env python3
"""
FFmpeg Locator for GoLive Studio
- Finds a bundled ffmpeg (PyInstaller-friendly)
- Falls back to cached AppData installation
- Finally uses PATH via shutil.which
- Optional stdlib-only downloader/extractor to populate AppData cache
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

# Default download source (essentials build; stable URL pattern)
DEFAULT_FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

APP_NAME = "GoLiveStudio"


def _candidate_paths() -> list[Path]:
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))  # PyInstaller support

    candidates = [
        # 1) Third-party bundled folder inside app
        base_dir / "third_party" / "ffmpeg" / "bin" / exe_name,
        # 2) Sibling ffmpeg folder next to sources
        base_dir / "ffmpeg" / "bin" / exe_name,
    ]

    # 3) AppData cache
    local_appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    if local_appdata:
        app_cache_bin = Path(local_appdata) / APP_NAME / "ffmpeg" / "bin" / exe_name
        candidates.append(app_cache_bin)

    # 4) PATH via shutil.which
    which = shutil.which("ffmpeg")
    if which:
        candidates.append(Path(which))

    return candidates


def find_ffmpeg() -> Optional[str]:
    """Return an absolute path to ffmpeg executable if found, else None."""
    for p in _candidate_paths():
        try:
            if p and p.exists():
                return str(p)
        except Exception:
            continue
    return None


def ensure_ffmpeg_available(auto_download: bool = False, url: str = DEFAULT_FFMPEG_ZIP_URL) -> Optional[str]:
    """Ensure ffmpeg is available.
    - If found, return its path.
    - If not found and auto_download=True, download + extract to AppData cache and return its path.
    - Otherwise, return None.
    """
    found = find_ffmpeg()
    if found:
        return found

    if not auto_download:
        return None

    # Download and extract to AppData cache
    local_appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    if not local_appdata:
        return None

    cache_root = Path(local_appdata) / APP_NAME / "ffmpeg"
    bin_dir = cache_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    target_exe = bin_dir / exe_name

    # Check if we already have a cached copy
    if target_exe.exists():
        return str(target_exe)

    # Create a persistent temp directory that won't be auto-cleaned up
    temp_dir = Path(tempfile.gettempdir()) / f"{APP_NAME}_ffmpeg_download"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        import urllib.request
        
        # Download to a temporary file first
        zip_path = temp_dir / "ffmpeg.zip"
        try:
            with urllib.request.urlopen(url) as resp, open(zip_path, "wb") as f:
                shutil.copyfileobj(resp, f)
        except Exception as e:
            print(f"Failed to download FFmpeg: {e}")
            return None

        # Extract to a temporary directory
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extract all files
                zip_ref.extractall(extract_dir)
                
                # Find the ffmpeg executable in the extracted files
                found_exe = None
                for root, dirs, files in os.walk(extract_dir):
                    if exe_name in files:
                        found_exe = Path(root) / exe_name
                        break
                
                if not found_exe:
                    print("FFmpeg executable not found in the downloaded archive")
                    return None
                
                # Ensure target directory exists
                bin_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy to final location
                shutil.copy2(found_exe, target_exe)
                
                # On non-Windows, set executable permissions
                if os.name != 'nt':
                    target_exe.chmod(0o755)
                
                print(f"Successfully downloaded FFmpeg to {target_exe}")
                return str(target_exe)
                
        except Exception as e:
            print(f"Error extracting FFmpeg: {e}")
            return None
            
        finally:
            # Clean up temporary files
            try:
                if zip_path.exists():
                    zip_path.unlink(missing_ok=True)
                if extract_dir.exists():
                    shutil.rmtree(extract_dir, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Could not clean up temporary files: {e}")
                
    except Exception as e:
        print(f"Error during FFmpeg download: {e}")
        return None
