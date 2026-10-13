"""Functions that can be used for the most common use-cases for pdf2zh.six"""

import asyncio
import io
import os
import re
import sys
import tempfile
import logging
from asyncio import CancelledError
from pathlib import Path
from string import Template
from typing import Any, BinaryIO, List, Optional, Dict

import numpy as np
import requests
import tqdm

from pdf2zh.converter_docx import convert_to_pdf, is_convertible
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfexceptions import PDFValueError
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
import pymupdf as fitz
from pymupdf import Document, Font

from pdf2zh.converter import TranslateConverter
from pdf2zh.doclayout import OnnxModel
from pdf2zh.pdfinterp import PDFPageInterpreterEx

from pdf2zh.config import ConfigManager
from babeldoc.assets.assets import get_font_and_metadata

NOTO_NAME = "noto"

logger = logging.getLogger(__name__)

noto_list = [
    "am",  # Amharic
    "ar",  # Arabic
    "bn",  # Bengali
    "bg",  # Bulgarian
    "chr",  # Cherokee
    "el",  # Greek
    "gu",  # Gujarati
    "iw",  # Hebrew
    "hi",  # Hindi
    "kn",  # Kannada
    "ml",  # Malayalam
    "mr",  # Marathi
    "ru",  # Russian
    "sr",  # Serbian
    "ta",  # Tamil
    "te",  # Telugu
    "th",  # Thai
    "ur",  # Urdu
    "uk",  # Ukrainian
]


def check_files(files: List[str]) -> List[str]:
    files = [
        f for f in files if not f.startswith("http://")
    ]  # exclude online files, http
    files = [
        f for f in files if not f.startswith("https://")
    ]  # exclude online files, https
    missing_files = [file for file in files if not os.path.exists(file)]
    return missing_files


def translate_patch(
    inf: BinaryIO,
    pages: Optional[list[int]] = None,
    vfont: str = "",
    vchar: str = "",
    thread: int = 0,
    doc_zh: Document = None,
    lang_in: str = "",
    lang_out: str = "",
    service: str = "",
    noto_name: str = "",
    noto: Font = None,
    callback: object = None,
    cancellation_event: asyncio.Event = None,
    model: OnnxModel = None,
    envs: Dict = None,
    prompt: Template = None,
    ignore_cache: bool = False,
    **kwarg: Any,
) -> None:
    # 1. Build Context-Aware & Glossary Prompt
    final_prompt = prompt
    if final_prompt is None:
        doc_domain = ""
        try:
            if doc_zh is not None and doc_zh.page_count > 0:
                sample_texts = []
                sample_page_count = min(3, doc_zh.page_count)
                for i in range(sample_page_count):
                    txt = doc_zh[i].get_text()
                    if txt:
                        sample_texts.append(txt[:400])
                combined_sample = " ".join(sample_texts).strip()
                if combined_sample:
                    doc_domain = " ".join(combined_sample[:250].split())
        except Exception:
            pass

        context_hint = f"\n[DOCUMENT SUBJECT & CONTEXT]\n{doc_domain}\n" if doc_domain else ""
        final_prompt = Template(
            "You are a professional, authentic academic translation engine specializing in scientific and technical literature.\n"
            "Translate the following source text into $lang_out with natural, fluent, and precise technical phrasing.\n"
            f"{context_hint}\n"
            "[GUIDELINES]\n"
            "- Maintain strict consistency in terminology and style across all sections.\n"
            "- Keep all LaTeX and math formula placeholders {v0}, {v1}, {v2}... unchanged in exact grammatical position.\n"
            "- Output ONLY the translated text directly without any additional explanation, greetings, or markdown quotes.\n\n"
            "Source Text: $text\n\n"
            "Translated Text:"
        )
    elif isinstance(final_prompt, str):
        final_prompt = Template(
            "You are a professional, authentic academic translation engine specializing in scientific and technical literature.\n"
            "Translate the following source text into $lang_out with natural, fluent, and precise technical phrasing.\n\n"
            f"[CUSTOM GLOSSARY & INSTRUCTIONS]\n{final_prompt}\n\n"
            "[GUIDELINES]\n"
            "- Maintain strict consistency in terminology and style across all sections.\n"
            "- Keep all LaTeX and math formula placeholders {v0}, {v1}, {v2}... unchanged in exact grammatical position.\n"
            "- Output ONLY the translated text directly without any additional explanation, greetings, or markdown quotes.\n\n"
            "Source Text: $text\n\n"
            "Translated Text:"
        )

    rsrcmgr = PDFResourceManager()
    layout = {}
    device = TranslateConverter(
        rsrcmgr,
        vfont,
        vchar,
        thread,
        layout,
        lang_in,
        lang_out,
        service,
        noto_name,
        noto,
        envs,
        final_prompt,
        ignore_cache,
        callback,
    )

    assert device is not None
    obj_patch = {}
    interpreter = PDFPageInterpreterEx(rsrcmgr, device, obj_patch)
    if pages:
        total_pages = len(pages)
    else:
        total_pages = doc_zh.page_count

    parser = PDFParser(inf)
    doc = PDFDocument(parser)
    processed_page_count = 0
    with tqdm.tqdm(total=total_pages, disable=bool(callback)) as progress:
        for pageno, page in enumerate(PDFPage.create_pages(doc)):
            if cancellation_event and cancellation_event.is_set():
                raise CancelledError("task cancelled")
            if pages and (pageno not in pages):
                continue
            progress.update()
            processed_page_count += 1
            device.current_page_idx = processed_page_count
            device.total_pages = total_pages
            if callback:
                callback({"type": "page_layout", "page": processed_page_count, "total": total_pages})
            page.pageno = pageno
            pix = doc_zh[page.pageno].get_pixmap()
            image = np.frombuffer(pix.samples, np.uint8).reshape(
                pix.height, pix.width, 3
            )[:, :, ::-1]
            page_layout = model.predict(image, imgsz=int(pix.height / 32) * 32)[0]
            # kdtree 是不可能 kdtree 的，不如直接渲染成图片，用空间换时间
            box = np.ones((pix.height, pix.width))
            h, w = box.shape
            vcls = ["abandon", "figure", "table", "isolate_formula", "formula_caption"]
            for i, d in enumerate(page_layout.boxes):
                if page_layout.names[int(d.cls)] not in vcls:
                    x0, y0, x1, y1 = d.xyxy.squeeze()
                    x0, y0, x1, y1 = (
                        np.clip(int(x0 - 1), 0, w - 1),
                        np.clip(int(h - y1 - 1), 0, h - 1),
                        np.clip(int(x1 + 1), 0, w - 1),
                        np.clip(int(h - y0 + 1), 0, h - 1),
                    )
                    box[y0:y1, x0:x1] = i + 2
            for i, d in enumerate(page_layout.boxes):
                if page_layout.names[int(d.cls)] in vcls:
                    x0, y0, x1, y1 = d.xyxy.squeeze()
                    x0, y0, x1, y1 = (
                        np.clip(int(x0 - 1), 0, w - 1),
                        np.clip(int(h - y1 - 1), 0, h - 1),
                        np.clip(int(x1 + 1), 0, w - 1),
                        np.clip(int(h - y0 + 1), 0, h - 1),
                    )
                    box[y0:y1, x0:x1] = 0
            layout[page.pageno] = box
            # 新建一个 xref 存放新指令流
            page.page_xref = doc_zh.get_new_xref()  # hack 插入页面的新 xref
            doc_zh.update_object(page.page_xref, "<<>>")
            doc_zh.update_stream(page.page_xref, b"")
            doc_zh[page.pageno].set_contents(page.page_xref)
            interpreter.process_page(page)

            # Extract figures, diagrams, and illustrations for DOCX export
            try:
                fitz_page = doc_zh[page.pageno]
                page_rect = fitz_page.rect
                page_images = []
                seen_boxes = []

                # 1. From PyMuPDF get_image_info
                for img_info in fitz_page.get_image_info(xrefs=True):
                    bbox = img_info.get("bbox")
                    if not bbox:
                        continue
                    x0, y0, x1, y1 = bbox
                    w = x1 - x0
                    h = y1 - y0
                    # Skip tiny decorative icons (< 35px) or full-page blank background
                    if 35 <= w <= page_rect.width + 5 and 35 <= h <= page_rect.height + 5:
                        is_dup = any(abs(x0 - sb[0]) < 15 and abs(y0 - sb[1]) < 15 for sb in seen_boxes)
                        if not is_dup:
                            seen_boxes.append((x0, y0, x1, y1))
                            clip_r = fitz.Rect(x0, y0, x1, y1) & page_rect
                            if clip_r.width >= 25 and clip_r.height >= 25:
                                crop_pix = fitz_page.get_pixmap(clip=clip_r, dpi=150)
                                page_images.append({
                                    "bbox": (x0, y0, x1, y1),
                                    "y_top": y0,
                                    "width": w,
                                    "height": h,
                                    "bytes": crop_pix.tobytes("png"),
                                })

                # 2. From DocLayout-YOLO detected figures/tables
                if model and page_layout:
                    for d in page_layout.boxes:
                        cls_name = page_layout.names[int(d.cls)]
                        if cls_name in ["figure", "table"]:
                            x0, y0, x1, y1 = [float(v) for v in d.xyxy.squeeze()]
                            w = x1 - x0
                            h = y1 - y0
                            if w >= 40 and h >= 40:
                                is_dup = any(abs(x0 - sb[0]) < 20 and abs(y0 - sb[1]) < 20 for sb in seen_boxes)
                                if not is_dup:
                                    seen_boxes.append((x0, y0, x1, y1))
                                    clip_r = fitz.Rect(x0, y0, x1, y1) & page_rect
                                    if clip_r.width >= 25 and clip_r.height >= 25:
                                        crop_pix = fitz_page.get_pixmap(clip=clip_r, dpi=150)
                                        page_images.append({
                                            "bbox": (x0, y0, x1, y1),
                                            "y_top": y0,
                                            "width": w,
                                            "height": h,
                                            "bytes": crop_pix.tobytes("png"),
                                        })

                if hasattr(device, "pages_data") and device.pages_data:
                    device.pages_data[-1]["images"] = page_images
            except Exception as e:
                logger.debug(f"Image extraction skipped on page {page.pageno}: {e}")

    pages_data = getattr(device, "pages_data", [])
    device.close()
    return obj_patch, pages_data


class TranslationStreamResult(tuple):
    def __new__(cls, s_mono, s_dual, pages_data=None):
        return super().__new__(cls, (s_mono, s_dual))

    def __init__(self, s_mono, s_dual, pages_data=None):
        self.pages_data = pages_data or []


def preprocess_scanned_pdf(
    stream: bytes,
    pages: Optional[list[int]] = None,
    callback: object = None,
    cancellation_event: asyncio.Event = None,
) -> bytes:
    """
    Detects scanned / image-only pages (pages with virtually no digital text but containing images),
    runs RapidOCR on them, whites out the source text, and injects digital text at baseline coordinates.
    This enables full downstream text translation, layout analysis, and DOCX/PDF export for scanned PDFs.
    """
    try:
        doc = Document(stream=stream)
    except Exception as e:
        logger.warning(f"Failed to open PDF stream for OCR check: {e}")
        return stream

    total_pages = doc.page_count
    target_pages = [p for p in pages if 0 <= p < total_pages] if pages else list(range(total_pages))

    # Identify pages that have no/little digital text (< 20 chars) and contain images
    scanned_pages = []
    for p_idx in target_pages:
        page = doc[p_idx]
        text = page.get_text().strip()
        images = page.get_images()
        has_large_image = any(img[2] >= 300 and img[3] >= 300 for img in images)
        if len(text) < 20 and (has_large_image or len(images) > 0):
            scanned_pages.append(p_idx)

    if not scanned_pages:
        doc.close()
        return stream

    logger.info(f"Phát hiện {len(scanned_pages)} trang tài liệu quét/ảnh cần OCR: {[p + 1 for p in scanned_pages]}")

    try:
        from rapidocr_onnxruntime import RapidOCR
        ocr_engine = RapidOCR()
    except Exception as e:
        logger.warning(f"Không thể khởi tạo mô hình RapidOCR: {e}. Bỏ qua tiền xử lý OCR.")
        doc.close()
        return stream

    for ocr_i, p_idx in enumerate(scanned_pages):
        if cancellation_event and cancellation_event.is_set():
            logger.info("OCR preprocessing cancelled by user.")
            doc.close()
            return stream

        page = doc[p_idx]
        if callback:
            try:
                callback({
                    "type": "ocr",
                    "page": p_idx + 1,
                    "total": total_pages,
                    "current": ocr_i + 1,
                    "total_ocr": len(scanned_pages),
                    "message": f"Trang {p_idx + 1}/{total_pages}: Đang quét nhận diện chữ OCR ({ocr_i + 1}/{len(scanned_pages)})...",
                })
            except Exception:
                pass

        try:
            pix = page.get_pixmap(dpi=150)
            ocr_res, _ = ocr_engine(pix.tobytes())
            if not ocr_res:
                continue

            scale_x = page.rect.width / pix.width
            scale_y = page.rect.height / pix.height

            # Pass 1: White-out the original text regions
            for box, text, score in ocr_res:
                if not text or not text.strip() or score < 0.4:
                    continue
                xs = [page.rect.x0 + pt[0] * scale_x for pt in box]
                ys = [page.rect.y0 + pt[1] * scale_y for pt in box]
                rect = fitz.Rect(min(xs) - 1.5, min(ys) - 1.5, max(xs) + 1.5, max(ys) + 1.5)
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

            # Pass 2: Inject text at baseline
            for box, text, score in ocr_res:
                clean_text = text.strip()
                if not clean_text or score < 0.4:
                    continue
                xs = [page.rect.x0 + pt[0] * scale_x for pt in box]
                ys = [page.rect.y0 + pt[1] * scale_y for pt in box]
                h = max(ys) - min(ys)
                font_size = max(7.0, min(24.0, h * 0.75))
                baseline_pt = fitz.Point(min(xs), max(ys) - h * 0.15)
                page.insert_text(baseline_pt, clean_text, fontsize=font_size, fontname="helv")

            logger.info(f"Đã OCR và chèn {len(ocr_res)} khối chữ vào trang {p_idx + 1}")
        except Exception as e:
            logger.error(f"Lỗi khi OCR trang {p_idx + 1}: {e}", exc_info=True)

    out_stream = io.BytesIO()
    doc.save(out_stream, garbage=4, deflate=True, clean=True)
    doc.close()
    return out_stream.getvalue()


def translate_stream(
    stream: bytes,
    pages: Optional[list[int]] = None,
    lang_in: str = "",
    lang_out: str = "",
    service: str = "",
    thread: int = 0,
    vfont: str = "",
    vchar: str = "",
    callback: object = None,
    cancellation_event: asyncio.Event = None,
    model: OnnxModel = None,
    envs: Dict = None,
    prompt: Template = None,
    skip_subset_fonts: bool = False,
    ignore_cache: bool = False,
    **kwarg: Any,
):
    font_list = [("tiro", None)]

    font_path = download_remote_fonts(lang_out.lower())
    noto_name = NOTO_NAME
    noto = Font(noto_name, font_path)
    font_list.append((noto_name, font_path))

    # Keep a copy of original stream for doc_en dual mode
    raw_stream = stream

    # Automatic OCR for scanned / image-only documents
    stream = preprocess_scanned_pdf(stream, pages=pages, callback=callback, cancellation_event=cancellation_event)

    doc_en = Document(stream=raw_stream)
    # Repair corrupt xref tables (e.g. scanned / re-exported PDFs) by
    # saving to a clean in-memory stream first, then re-opening.
    # This eliminates thousands of "MuPDF error: cannot find object in xref"
    # messages that would otherwise pollute stdout and confuse the Rust host.
    stream_clean = io.BytesIO()
    doc_en.save(stream_clean, garbage=4, deflate=True, clean=True)
    doc_en = Document(stream=stream_clean)
    doc_zh = Document(stream=stream)
    page_count = doc_zh.page_count
    font_id = {}
    for page in doc_zh:
        for font in font_list:
            font_id[font[0]] = page.insert_font(font[0], font[1])
    xreflen = doc_zh.xref_length()
    for xref in range(1, xreflen):
        for label in ["Resources/", ""]:  # 可能是基于 xobj 的 res
            try:  # xref 读写可能出错
                font_res = doc_zh.xref_get_key(xref, f"{label}Font")
                target_key_prefix = f"{label}Font/"
                if font_res[0] == "xref":
                    resource_xref_id = re.search("(\\d+) 0 R", font_res[1]).group(1)
                    xref = int(resource_xref_id)
                    font_res = ("dict", doc_zh.xref_object(xref))
                    target_key_prefix = ""

                if font_res[0] == "dict":
                    for font in font_list:
                        target_key = f"{target_key_prefix}{font[0]}"
                        font_exist = doc_zh.xref_get_key(xref, target_key)
                        if font_exist[0] == "null":
                            doc_zh.xref_set_key(
                                xref,
                                target_key,
                                f"{font_id[font[0]]} 0 R",
                            )
            except Exception:
                pass

    fp = io.BytesIO()

    doc_zh.save(fp)
    obj_patch, pages_data = translate_patch(fp, **locals())

    for obj_id, ops_new in obj_patch.items():
        # ops_old=doc_en.xref_stream(obj_id)
        # print(obj_id)
        # print(ops_old)
        # print(ops_new.encode())
        doc_zh.update_stream(obj_id, ops_new.encode())

    doc_en.insert_file(doc_zh)
    for id in range(page_count):
        doc_en.move_page(page_count + id, id * 2 + 1)

    if pages:
        dual_selected = []
        for p in pages:
            if 0 <= p < page_count:
                dual_selected.extend([p * 2, p * 2 + 1])
        valid_mono_pages = [p for p in pages if 0 <= p < page_count]
        doc_en.select(dual_selected)
        doc_zh.select(valid_mono_pages)

    if callback:
        callback({"type": "rendering"})
    if not skip_subset_fonts:
        doc_zh.subset_fonts(fallback=True)
        doc_en.subset_fonts(fallback=True)
    return TranslationStreamResult(
        doc_zh.write(deflate=True, garbage=3, use_objstms=1),
        doc_en.write(deflate=True, garbage=3, use_objstms=1),
        pages_data=pages_data,
    )


def convert_to_pdfa(input_path, output_path):
    """
    Convert PDF to PDF/A format

    Args:
        input_path: Path to source PDF file
        output_path: Path to save PDF/A file
    """
    from pikepdf import Dictionary, Name, Pdf

    # Open the PDF file
    pdf = Pdf.open(input_path)

    # Add PDF/A conformance metadata
    metadata = {
        "pdfa_part": "2",
        "pdfa_conformance": "B",
        "title": pdf.docinfo.get("/Title", ""),
        "author": pdf.docinfo.get("/Author", ""),
        "creator": "PDF Math Translate",
    }

    with pdf.open_metadata() as meta:
        meta.load_from_docinfo(pdf.docinfo)
        meta["pdfaid:part"] = metadata["pdfa_part"]
        meta["pdfaid:conformance"] = metadata["pdfa_conformance"]

    # Create OutputIntent dictionary
    output_intent = Dictionary(
        {
            "/Type": Name("/OutputIntent"),
            "/S": Name("/GTS_PDFA1"),
            "/OutputConditionIdentifier": "sRGB IEC61966-2.1",
            "/RegistryName": "http://www.color.org",
            "/Info": "sRGB IEC61966-2.1",
        }
    )

    # Add output intent to PDF root
    if "/OutputIntents" not in pdf.Root:
        pdf.Root.OutputIntents = [output_intent]
    else:
        pdf.Root.OutputIntents.append(output_intent)

    # Save as PDF/A
    pdf.save(output_path, linearize=True)
    pdf.close()


def translate(
    files: list[str],
    output: str = "",
    pages: Optional[list[int]] = None,
    lang_in: str = "",
    lang_out: str = "",
    service: str = "",
    thread: int = 0,
    vfont: str = "",
    vchar: str = "",
    callback: object = None,
    compatible: bool = False,
    cancellation_event: asyncio.Event = None,
    model: OnnxModel = None,
    envs: Dict = None,
    prompt: Template = None,
    skip_subset_fonts: bool = False,
    ignore_cache: bool = False,
    export_format: str = "both",
    **kwarg: Any,
):
    if not files:
        raise PDFValueError("No files to process.")

    missing_files = check_files(files)

    if missing_files:
        print("The following files do not exist:", file=sys.stderr)
        for file in missing_files:
            print(f"  {file}", file=sys.stderr)
        raise PDFValueError("Some files do not exist.")

    result_files = []

    for file in files:
        if type(file) is str and (
            file.startswith("http://") or file.startswith("https://")
        ):
            print("Online files detected, downloading...")
            try:
                r = requests.get(file, allow_redirects=True)
                if r.status_code == 200:
                    with tempfile.NamedTemporaryFile(
                        suffix=".pdf", delete=False
                    ) as tmp_file:
                        print(f"Writing the file: {file}...")
                        tmp_file.write(r.content)
                        file = tmp_file.name
                else:
                    r.raise_for_status()
            except Exception as e:
                raise PDFValueError(
                    f"Errors occur in downloading the PDF file. Please check the link(s).\nError:\n{e}"
                )

        # Convert doc/docx to PDF if needed
        _converted_pdf = None
        if is_convertible(file):
            _converted_pdf = convert_to_pdf(file)
            filename = os.path.splitext(os.path.basename(file))[0]
            file = _converted_pdf
        else:
            filename = os.path.splitext(os.path.basename(file))[0]

        # If the commandline has specified converting to PDF/A format
        # --compatible / -cp
        if compatible:
            with tempfile.NamedTemporaryFile(
                suffix="-pdfa.pdf", delete=False
            ) as tmp_pdfa:
                print(f"Converting {file} to PDF/A format...")
                convert_to_pdfa(file, tmp_pdfa.name)
                doc_raw = open(tmp_pdfa.name, "rb")
                os.unlink(tmp_pdfa.name)
        else:
            doc_raw = open(file, "rb")
        s_raw = doc_raw.read()
        doc_raw.close()

        temp_dir = Path(tempfile.gettempdir())
        file_path = Path(file)
        try:
            if file_path.exists() and file_path.resolve().is_relative_to(
                temp_dir.resolve()
            ):
                file_path.unlink(missing_ok=True)
                logger.debug(f"Cleaned temp file: {file_path}")
        except Exception:
            logger.warning(f"Failed to clean temp file {file_path}", exc_info=True)

        stream_res = translate_stream(
            s_raw,
            **locals(),
        )
        s_mono, s_dual = stream_res
        pages_data = getattr(stream_res, "pages_data", [])

        file_mono = Path(output) / f"{filename}-mono.pdf"
        file_dual = Path(output) / f"{filename}-dual.pdf"
        file_docx = Path(output) / f"{filename}-mono.docx"

        want_pdf = export_format in ["both", "pdf"]
        want_docx = export_format in ["both", "docx"]

        out_mono = None
        out_dual = None
        out_docx = None

        if want_pdf:
            file_mono.parent.mkdir(parents=True, exist_ok=True)
            doc_mono = open(file_mono, "wb")
            doc_dual = open(file_dual, "wb")
            doc_mono.write(s_mono)
            doc_dual.write(s_dual)
            doc_mono.close()
            doc_dual.close()
            out_mono = str(file_mono)
            out_dual = str(file_dual)

        if want_docx:
            try:
                from pdf2zh.docx_exporter import export_pages_to_docx
                export_pages_to_docx(pages_data, str(file_docx))
                logger.info(f"Successfully exported DOCX to {file_docx}")
                out_docx = str(file_docx)
            except Exception as e:
                logger.error(f"Failed to export DOCX: {e}", exc_info=True)

        result_files.append((out_mono, out_dual, out_docx))

    return result_files


def download_remote_fonts(lang: str):
    lang = lang.lower()
    custom_font_path = ConfigManager.get("NOTO_FONT_PATH")
    if custom_font_path and Path(custom_font_path).exists():
        logger.info(f"use custom font: {custom_font_path}")
        return custom_font_path

    if lang in ["vi", "vietnamese"]:
        for win_font in ["C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/arial.ttf"]:
            if Path(win_font).exists():
                logger.info(f"use font: {win_font}")
                return win_font

    LANG_NAME_MAP = {
        **{la: "GoNotoKurrent-Regular.ttf" for la in noto_list},
        **{
            la: f"SourceHanSerif{region}-Regular.ttf"
            for region, langs in {
                "CN": ["zh-cn", "zh-hans", "zh"],
                "TW": ["zh-tw", "zh-hant"],
                "JP": ["ja"],
                "KR": ["ko"],
            }.items()
            for la in langs
        },
    }
    font_name = LANG_NAME_MAP.get(lang, "GoNotoKurrent-Regular.ttf")

    # docker
    font_path = ConfigManager.get("NOTO_FONT_PATH", Path("/app", font_name).as_posix())
    if not Path(font_path).exists():
        font_path, _ = get_font_and_metadata(font_name)
        font_path = font_path.as_posix()

    logger.info(f"use font: {font_path}")

    return font_path
