#!/usr/bin/env python3
"""
IPC Worker for PDFMathTranslate Desktop App.
Communicates via standard I/O (stdin/stdout JSON lines) - Zero localhost network ports.
"""

import asyncio
import io
import json
import logging
import os
import sys
import unicodedata
from pathlib import Path
from string import Template

# ── Windows DLL search path fix (Python 3.8+) ───────────────────────────────
# Python 3.8+ changed DLL loading to only search trusted directories.
# We register .venv/Scripts and onnxruntime/capi, and explicitly preload runtime DLLs
# so onnxruntime and other C++ extensions load without requiring admin VC++ Redist installation.
if sys.platform == "win32":
    import ctypes
    _py_scripts = Path(sys.executable).parent
    _ort_capi = _py_scripts.parent / "Lib" / "site-packages" / "onnxruntime" / "capi"
    _mupdf_dir = _py_scripts.parent / "Lib" / "site-packages" / "pymupdf"
    if hasattr(os, "add_dll_directory"):
        if _py_scripts.is_dir():
            os.add_dll_directory(str(_py_scripts))
        if _ort_capi.is_dir():
            os.add_dll_directory(str(_ort_capi))
        if _mupdf_dir.is_dir():
            os.add_dll_directory(str(_mupdf_dir))

    for _d in [_ort_capi, _py_scripts, _mupdf_dir]:
        for _dll in ["VCRUNTIME140.dll", "VCRUNTIME140_1.dll", "MSVCP140.dll", "MSVCP140_1.dll"]:
            _target = _d / _dll
            if _target.exists():
                ctypes.windll.kernel32.LoadLibraryW(str(_target))
    _ort_dll = _ort_capi / "onnxruntime.dll"
    if _ort_dll.exists():
        ctypes.windll.kernel32.LoadLibraryW(str(_ort_dll))
# ─────────────────────────────────────────────────────────────────────────────

# Reconfigure all I/O streams to UTF-8 unbuffered
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True, errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True, errors="replace")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

# Setup minimal logging to stderr so stdout remains pure JSON-lines protocol
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("ipc_worker")


class _JsonOnlyStdout(io.TextIOWrapper):
    """
    Proxy for sys.stdout that only allows valid JSON lines through.
    Any non-JSON line (e.g. MuPDF errors, warnings) is redirected to stderr
    so it doesn't corrupt the JSON-lines protocol between Python and Rust.
    """

    def __init__(self, wrapped):
        self._wrapped = wrapped

    def write(self, text):
        for line in text.splitlines(keepends=True):
            stripped = line.strip()
            if stripped and not (stripped.startswith("{") and stripped.endswith("}")):
                # Non-JSON line — redirect to stderr silently
                try:
                    sys.stderr.write(f"[mupdf/warn] {line}")
                    sys.stderr.flush()
                except Exception:
                    pass
            else:
                self._wrapped.write(line)
        return len(text)

    def flush(self):
        self._wrapped.flush()

    def __getattr__(self, name):
        return getattr(self._wrapped, name)


# Wrap stdout to guard the JSON protocol
sys.stdout = _JsonOnlyStdout(sys.stdout)


def emit(event_type: str, **data):
    """Emit a JSON message to stdout for the Rust host process."""
    try:
        payload = {"type": event_type, **data}
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"Failed to emit event: {e}")


def run_translation(request_data: dict):
    from pdf2zh.doclayout import ModelInstance, OnnxModel
    from pdf2zh.high_level import translate
    from pdf2zh.translator import GeminiTranslator

    # Reset any previous session status
    GeminiTranslator.reset_status()

    input_file = request_data.get("file")
    if not input_file or not Path(input_file).exists():
        emit("error", message=f"Không tìm thấy file tài liệu: {input_file}")
        return

    output_dir = request_data.get("output_dir", "pdf2zh_desktop_output")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    lang_in = request_data.get("lang_in", "en")
    lang_out = request_data.get("lang_out", "vi")
    service = request_data.get("service", "google")
    pages = request_data.get("pages")  # e.g. [0, 1, 2] or None
    envs = request_data.get("envs", {})
    prompt = request_data.get("prompt")
    thread = int(request_data.get("thread") or 4)
    if thread <= 0:
        thread = 4

    emit("progress", value=0.05, stage="init", message="Khởi tạo mô hình nhận diện bố cục AI...")

    # Load ONNX model
    try:
        if ModelInstance.value is None:
            ModelInstance.value = OnnxModel.load_available()
    except Exception as e:
        logger.warning(f"Error loading ONNX model: {e}")

    def progress_callback(info=None):
        if isinstance(info, dict):
            event_type = info.get("type")
            if event_type == "ocr":
                cur_p = max(1, int(info.get("page", 1)))
                tot_p = max(1, int(info.get("total", 1)))
                cur_ocr = int(info.get("current", 1))
                tot_ocr = max(1, int(info.get("total_ocr", 1)))
                ocr_prog = cur_ocr / tot_ocr
                overall_val = min(0.90, 0.05 + (ocr_prog * 0.10))
                emit(
                    "progress",
                    value=overall_val,
                    page_progress=ocr_prog,
                    current_page=cur_p,
                    total_pages=tot_p,
                    stage="ocr",
                    message=info.get("message", f"Trang {cur_p}/{tot_p}: Đang quét nhận diện chữ OCR..."),
                )
            elif event_type in ["page_layout", "page"]:
                cur_p = max(1, int(info.get("page", 1)))
                tot_p = max(1, int(info.get("total", 1)))
                page_progress = 0.15
                overall_val = min(0.90, 0.05 + (((cur_p - 1) + page_progress) / tot_p) * 0.85)
                emit(
                    "progress",
                    value=overall_val,
                    page_progress=page_progress,
                    current_page=cur_p,
                    total_pages=tot_p,
                    stage="layout",
                    message=f"Trang {cur_p}/{tot_p}: Đang phân tích bố cục AI...",
                )
            elif event_type == "translate":
                done = int(info.get("done", 0))
                tot = max(1, int(info.get("total", 1)))
                cur_p = max(1, int(info.get("page", 1)))
                tot_p = max(1, int(info.get("total_pages", 1)))
                fb = info.get("fallback")
                page_progress = min(1.0, 0.15 + (done / tot) * 0.85)
                overall_val = min(0.90, 0.05 + (((cur_p - 1) + page_progress) / tot_p) * 0.85)
                if fb and fb.get("active"):
                    fb_page = fb.get("page") or cur_p
                    if fb.get("permanent"):
                        msg = f"Trang {cur_p}/{tot_p} ⚠️ [Google Translate từ trang {fb_page}]: Đang dịch đoạn {done}/{tot} ({int(page_progress * 100)}%)..."
                    else:
                        msg = f"Trang {cur_p}/{tot_p} ⚠️ [Tạm dùng Google Translate trang {fb_page}]: Đang dịch đoạn {done}/{tot} ({int(page_progress * 100)}%)..."
                    fallback_info = fb.get("message")
                    fallback_page = fb.get("page")
                else:
                    msg = f"Trang {cur_p}/{tot_p}: Đang dịch đoạn {done}/{tot} ({int(page_progress * 100)}%)..."
                    fallback_info = None
                    fallback_page = None

                emit(
                    "progress",
                    value=overall_val,
                    page_progress=page_progress,
                    current_page=cur_p,
                    total_pages=tot_p,
                    current_sentence=done,
                    total_sentences=tot,
                    stage="translating",
                    message=msg,
                    fallback_info=fallback_info,
                    fallback_page=fallback_page,
                )
            elif event_type == "rendering":
                exp_fmt = request_data.get("export_format", "both")
                if exp_fmt == "docx":
                    msg = "Giai đoạn 3: Đang kết xuất tài liệu Word (.docx) chuẩn Times New Roman (95%)..."
                elif exp_fmt == "pdf":
                    msg = "Giai đoạn 3: Đang xuất file PDF & nhúng font Times New Roman (95%)..."
                else:
                    msg = "Giai đoạn 3: Đang xuất file PDF & Word (.docx) chuẩn Times New Roman (95%)..."
                emit(
                    "progress",
                    value=0.95,
                    page_progress=1.0,
                    stage="rendering",
                    message=msg,
                )
        elif isinstance(info, (int, float)):
            val = min(0.95, max(0.05, float(info)))
            emit("progress", value=val, page_progress=val, stage="translating", message=f"Đang xử lý ({int(val*100)}%)...")

    try:
        result_files = translate(
            files=[input_file],
            output=output_dir,
            pages=pages,
            lang_in=lang_in,
            lang_out=lang_out,
            service=service,
            thread=thread,
            vfont="",
            vchar="",
            callback=progress_callback,
            model=ModelInstance.value,
            envs=envs,
            prompt=prompt,
            skip_subset_fonts=False,
            ignore_cache=request_data.get("ignore_cache", False),
            export_format=request_data.get("export_format", "both"),
        )

        if not result_files:
            emit("error", message="Không tạo được file kết quả sau khi dịch.")
            return

        res_tuple = result_files[0]
        mono_path = res_tuple[0]
        dual_path = res_tuple[1]
        docx_path = res_tuple[2] if len(res_tuple) > 2 else None

        exp_fmt = request_data.get("export_format", "both")
        emit("progress", value=1.0, stage="done", message="Hoàn thành dịch tài liệu!")
        fb_status = GeminiTranslator.get_fallback_status()
        fallback_notice = fb_status.get("message") if (fb_status and fb_status.get("permanent")) else None
        emit(
            "success",
            mono=str(Path(mono_path).resolve()) if mono_path and Path(mono_path).exists() else None,
            dual=str(Path(dual_path).resolve()) if dual_path and Path(dual_path).exists() else None,
            docx=str(Path(docx_path).resolve()) if docx_path and Path(docx_path).exists() else None,
            filename=Path(input_file).name,
            output_dir=str(Path(output_dir).resolve()),
            export_format=exp_fmt,
            fallback_notice=fallback_notice,
        )

    except Exception as e:
        import traceback
        err_msg = str(e)
        logger.error(f"Translation error occurred: {traceback.format_exc()}")
        emit("error", message=f"{err_msg}")


def main():
    emit("ready", message="PDFMathTranslate IPC Engine Ready")

    # If parameters passed as command line argument (e.g. JSON file or inline JSON)
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        try:
            if Path(arg).exists():
                with open(arg, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = json.loads(arg)
            run_translation(data)
            return
        except Exception as e:
            emit("error", message=f"Failed to parse arguments: {e}")
            return

    # Interactive loop over stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            action = data.get("action", "translate")
            if action == "translate":
                run_translation(data)
            elif action == "ping":
                emit("pong", message="alive")
            elif action == "exit":
                break
        except json.JSONDecodeError:
            emit("error", message="Invalid JSON input")
        except Exception as e:
            emit("error", message=str(e))


if __name__ == "__main__":
    main()
