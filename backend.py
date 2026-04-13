"""
MM-RAG Backend — Local Edition (Infineon)
- CLIP + multi-qa-MiniLM for retrieval (runs locally on CPU)
- EasyOCR for text extraction (runs locally on CPU)
- Groq API for vision answer generation (free, cloud, fast)
- Auto-indexes existing images in pages/ on startup
"""

import os
import gc
import re
import json
import base64
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
from PIL import Image
import torch

log = logging.getLogger("mmrag")
logging.basicConfig(level=logging.WARNING)
log.setLevel(logging.INFO)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
TEXT_WEIGHT  = 0.75
IMAGE_WEIGHT = 0.25
DEFAULT_TOP_K            = 3
CAPTION_WORD_THRESHOLD   = 150
NUMBER_DENSITY_THRESHOLD = 0.12
ANSWER_IMAGE_K           = 3
MAX_CAPTION_TOKENS       = 160
MAX_ANSWER_TOKENS        = 512
MAX_CONTEXT_CHARS        = 2000
PDF_DPI                  = 150
OCR_CONF_THRESHOLD       = 0.5
SUPPORTED_IMAGE_EXTS     = {".png", ".jpg", ".jpeg", ".webp"}

VISUAL_SLIDE_MAX_WORDS   = 80
VISUAL_SLIDE_NUM_DENSITY = 0.15

# ── Groq settings ─────────────────────────────────────────────────────────────
# Get a free key at https://console.groq.com
# Set as environment variable GROQ_API_KEY or paste directly below
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "you api key here")
GROQ_MODEL      = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_MAX_IMG_PX = 1120   # resize longest side to this before sending (keeps payload small)


class MMRAGBackend:
    def __init__(self, base_path: str = "mmrag_store"):
        self.base_path     = Path(base_path)
        self.image_dir     = self.base_path / "pages"
        self.index_dir     = self.base_path / "index"
        self.kb_path       = self.index_dir / "knowledge_base.json"
        self.text_emb_path = self.index_dir / "text_embeddings.npy"
        self.clip_emb_path = self.index_dir / "clip_embeddings.npy"

        for d in [self.image_dir, self.index_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.device     = "cuda" if torch.cuda.is_available() else "cpu"
        self.cpu_device = "cpu"

        self.knowledge_base:  List[Dict]           = []
        self.text_embeddings: Optional[np.ndarray] = None
        self.clip_embeddings: Optional[np.ndarray] = None

        self._load_models()
        self._load_index()
        self._auto_index_existing_pages()

    # ─────────────────────────────────────────────────────────────────────────
    # Model loading
    # ─────────────────────────────────────────────────────────────────────────
    def _load_models(self):
        import open_clip
        import easyocr
        from sentence_transformers import SentenceTransformer

        self._cleanup()

        log.info("Loading CLIP ViT-B/32 on CPU...")
        self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="openai"
        )
        self.clip_tokenizer = open_clip.get_tokenizer("ViT-B-32")
        self.clip_model = self.clip_model.to(self.cpu_device).eval()
        log.info("CLIP loaded.")

        log.info("Loading multi-qa-MiniLM text retriever on CPU...")
        self.text_model = SentenceTransformer(
            "sentence-transformers/multi-qa-MiniLM-L6-cos-v1",
            device=self.cpu_device,
        )
        log.info("Text retriever loaded.")

        log.info("Loading EasyOCR on CPU...")
        self.ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        log.info("EasyOCR loaded.")

        log.info("Checking Groq connection...")
        self._check_groq()

        self._cleanup()
        log.info("All models loaded.")

    def _check_groq(self):
        if GROQ_API_KEY == "your_groq_api_key_here" or not GROQ_API_KEY:
            raise RuntimeError(
                "Groq API key not set.\n"
                "1. Get a free key at https://console.groq.com\n"
                "2. Set it in backend.py: GROQ_API_KEY = 'your_key'"
            )
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            # lightweight ping — list models
            client.models.list()
            self.groq_client = client
            log.info("Groq connection OK — model: " + GROQ_MODEL)
        except ImportError:
            raise RuntimeError(
                "groq package not installed.\n"
                "Run: pip install groq"
            )
        except Exception as e:
            raise RuntimeError("Groq connection failed: " + str(e))

    def _cleanup(self):
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # ─────────────────────────────────────────────────────────────────────────
    # Embedding helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _embed_texts(self, texts) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        return np.asarray(
            self.text_model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=32,
            ),
            dtype=np.float32,
        )

    def _embed_image_clip(self, image_path: str) -> np.ndarray:
        pil   = Image.open(image_path).convert("RGB")
        img_t = self.clip_preprocess(pil).unsqueeze(0).to(self.cpu_device)
        with torch.no_grad():
            feat = self.clip_model.encode_image(img_t)
            feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.cpu().numpy()[0].astype(np.float32)

    def _embed_query_clip(self, text: str) -> np.ndarray:
        tokens = self.clip_tokenizer([text]).to(self.cpu_device)
        with torch.no_grad():
            feat = self.clip_model.encode_text(tokens)
            feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.cpu().numpy()[0].astype(np.float32)

    @staticmethod
    def _normalize_rows(x: np.ndarray) -> np.ndarray:
        x     = np.asarray(x, dtype=np.float32)
        denom = np.linalg.norm(x, axis=-1, keepdims=True) + 1e-12
        return (x / denom).astype(np.float32)

    @staticmethod
    def _minmax_scale(x: np.ndarray) -> np.ndarray:
        x      = np.asarray(x, dtype=np.float32)
        lo, hi = float(np.min(x)), float(np.max(x))
        if hi - lo < 1e-8:
            s = float(np.sum(np.abs(x)))
            return (np.abs(x) / s).astype(np.float32) if s > 1e-12 else np.ones_like(x) / len(x)
        return ((x - lo) / (hi - lo)).astype(np.float32)

    # ─────────────────────────────────────────────────────────────────────────
    # OCR + captioning
    # ─────────────────────────────────────────────────────────────────────────
    def _extract_ocr(self, image_path: str) -> str:
        try:
            results = self.ocr_reader.readtext(image_path)
            lines   = [t for _, t, c in results if c >= OCR_CONF_THRESHOLD]
            return "\n".join(lines).strip()
        except Exception as e:
            log.warning(f"OCR failed {image_path}: {e}")
            return ""

    @staticmethod
    def _number_density(text: str) -> float:
        tokens = re.findall(r"\S+", text or "")
        if not tokens:
            return 0.0
        return sum(bool(re.search(r"\d", t)) for t in tokens) / len(tokens)

    def _should_caption(self, ocr_text: str) -> Tuple[bool, int, float]:
        wc = len(ocr_text.split())
        nd = self._number_density(ocr_text)
        return (wc < CAPTION_WORD_THRESHOLD) or (nd >= NUMBER_DENSITY_THRESHOLD), wc, nd

    # ─────────────────────────────────────────────────────────────────────────
    # Groq vision inference
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _image_to_b64(image_path: str, max_px: int = GROQ_MAX_IMG_PX) -> str:
        """
        Resize image so longest side <= max_px, then return base64 PNG string.
        Keeps payload small for fast Groq responses.
        """
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        if max(w, h) > max_px:
            scale = max_px / max(w, h)
            img   = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    def _groq_generate(self, image_paths: List[str], prompt: str, max_tokens: int) -> str:
        """
        Send images + prompt to Groq Llama 4 Scout (vision model).
        Images are base64-encoded PNGs. Falls back to text-only if images fail.
        """
        content = []

        # Add images first
        for img_path in image_paths:
            try:
                b64 = self._image_to_b64(img_path)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                })
            except Exception as e:
                log.warning(f"Could not encode image {img_path}: {e}")

        # Add text prompt
        content.append({"type": "text", "text": prompt})

        try:
            response = self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": content}],
                max_tokens=max_tokens,
                temperature=0,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            log.warning(f"Groq vision call failed: {e} — retrying text-only")
            # Fallback: text-only if vision fails
            try:
                response = self.groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0,
                )
                return response.choices[0].message.content.strip()
            except Exception as e2:
                log.warning(f"Groq text-only fallback also failed: {e2}")
                return f"(Generation failed: {e2})"

    def _qwen_caption(self, image_path: str, ocr_text: str) -> str:
        """Generate a retrieval caption for a slide using Groq vision."""
        prompt = (
            f"OCR text from this slide:\n{ocr_text[:700]}\n\n"
            "Write a factual retrieval caption that exhaustively lists every specific item visible. Rules:\n"
            "1. Slide title and main topic\n"
            "2. For tables with columns (e.g. Automotive / Industrial / Medical): list EVERY item under EACH column header separately\n"
            "3. For acquisition/portfolio slides: explicitly name which items are NEW/ACQUIRED vs existing\n"
            "4. Chart/graph: type, axis labels, key data values, main trend\n"
            "5. Flow diagrams: components, order, process shown\n"
            "6. ALL specific product names, sensor types, numbers, percentages, named entities\n"
            "Be exhaustive — list every named item. 4-6 sentences."
        )
        try:
            return self._groq_generate([image_path], prompt, MAX_CAPTION_TOKENS)
        except Exception as e:
            log.warning(f"Caption failed for {image_path}: {e}")
            return ""

    def _build_context(self, candidates: List[Dict], max_chars: int = MAX_CONTEXT_CHARS) -> str:
        parts, total = [], 0
        for i, c in enumerate(candidates, 1):
            block = f"[Slide {i}: {c['filename']}]\n{c.get('combined_text','').strip()}"
            if total + len(block) > max_chars:
                remain = max_chars - total
                if remain > 80:
                    parts.append(block[:remain])
                break
            parts.append(block)
            total += len(block) + 2
        return "\n\n".join(parts).strip()

    def _qwen_answer(self, question: str, candidates: List[Dict]) -> Tuple[str, str]:
        """Retrieve relevant slides and generate an answer using Groq vision."""
        image_paths = [
            str(self.image_dir / c["filename"])
            for c in candidates[:ANSWER_IMAGE_K]
            if (self.image_dir / c["filename"]).exists()
        ]

        ctx = self._build_context(candidates)
        n_imgs = len(image_paths)
        img_lbl = f"{n_imgs} slide image{'s' if n_imgs != 1 else ''}" if n_imgs else "text context only"

        prompt = (
            f"You are analysing {img_lbl} from a presentation or document.\n"
            f"Text extracted from the retrieved slides:\n---\n{ctx}\n---\n\n"
            f"Question: {question}\n\n"
            "Instructions:\n"
            "- Examine every image carefully — read chart axes, bar heights, "
            "table values, and diagram labels directly from the visuals.\n"
            "- Do not estimate chart values — read the exact numbers shown.\n"
            "- Cross-reference the images with the extracted text above.\n"
            "- Give a direct, complete answer with specific figures where visible.\n\n"
            "Answer:"
        )

        if image_paths:
            answer = self._groq_generate(image_paths, prompt, MAX_ANSWER_TOKENS)
            mode   = "multi-image"
        else:
            answer = self._groq_generate([], prompt, MAX_ANSWER_TOKENS)
            mode   = "text-only"

        return answer, mode

    # ─────────────────────────────────────────────────────────────────────────
    # Index management
    # ─────────────────────────────────────────────────────────────────────────
    def _load_index(self):
        if self.kb_path.exists():
            with open(self.kb_path, encoding="utf-8") as f:
                self.knowledge_base = json.load(f)
            log.info(f"Loaded {len(self.knowledge_base)} pages from saved index.")
        if self.text_emb_path.exists() and self.knowledge_base:
            self.text_embeddings = np.load(self.text_emb_path).astype(np.float32)
        if self.clip_emb_path.exists() and self.knowledge_base:
            self.clip_embeddings = np.load(self.clip_emb_path).astype(np.float32)

    def _save_index(self):
        with open(self.kb_path, "w", encoding="utf-8") as f:
            json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)
        if self.text_embeddings is not None:
            np.save(self.text_emb_path, self.text_embeddings)
        if self.clip_embeddings is not None:
            np.save(self.clip_emb_path, self.clip_embeddings)

    def _rebuild_embeddings(self):
        texts = [e.get("combined_text", "") or "[no text]" for e in self.knowledge_base]
        self.text_embeddings = self._embed_texts(texts)
        clip_list = []
        for e in self.knowledge_base:
            p = self.image_dir / e["filename"]
            clip_list.append(
                self._embed_image_clip(str(p)) if p.exists()
                else np.zeros(512, dtype=np.float32)
            )
        self.clip_embeddings = self._normalize_rows(np.vstack(clip_list))

    @staticmethod
    def _detect_slide_type(ocr_text: str, caption: str) -> str:
        ocr_lower = ocr_text.lower()
        cap_lower = caption.lower()
        wc = len(ocr_text.split())
        nd = MMRAGBackend._number_density(ocr_text)  # type: ignore[attr-defined]

        if wc <= VISUAL_SLIDE_MAX_WORDS:
            return "visual"
        if nd >= VISUAL_SLIDE_NUM_DENSITY:
            return "visual"

        cap_visual_kw = {
            "diagram", "flowchart", "chart", "graph", "table", "row", "column",
            "step", "arrow", "box", "flow", "process", "workflow", "pipeline",
            "architecture", "numbered", "stages", "phases", "quadrant", "matrix",
            "axis", "axes", "plot", "grid", "bubble", "node", "edge", "network",
            "framework", "model", "tier", "layer", "cluster", "map", "heatmap",
            "scatter", "bar", "pie", "donut", "funnel", "hierarchy", "tree",
        }
        if any(kw in cap_lower for kw in cap_visual_kw):
            return "visual"

        ocr_visual_kw = {
            "axis", "x-axis", "y-axis", "complexity", "modality", "quadrant",
            "simple", "complex", "one", "many", "low", "high", "step 1", "step 2",
            "phase", "stage",
        }
        if any(kw in ocr_lower for kw in ocr_visual_kw):
            return "visual"

        words = ocr_text.split()
        if wc > 0:
            unique_ratio = len(set(w.lower() for w in words)) / wc
            if unique_ratio < 0.55 and wc < 150:
                return "visual"

        return "text"

    def _index_one(self, img_path: Path) -> Dict:
        filename       = img_path.name
        page_id        = f"page_{len(self.knowledge_base) + 1:04d}"
        ocr_text       = self._extract_ocr(str(img_path))
        do_cap, wc, nd = self._should_caption(ocr_text)
        caption        = self._qwen_caption(str(img_path), ocr_text) if do_cap else ""
        slide_type     = self._detect_slide_type(ocr_text, caption)

        if slide_type == "visual" and caption.strip():
            combined = caption.strip() + ("\n\nOCR (raw):\n" + ocr_text.strip() if ocr_text.strip() else "")
        else:
            combined = (
                (ocr_text.strip() + ("\n\n" + caption.strip() if caption.strip() else "")).strip()
                or "[no text]"
            )

        return {
            "page_id":        page_id,
            "filename":       filename,
            "ocr_text":       ocr_text,
            "caption":        caption,
            "combined_text":  combined,
            "slide_type":     slide_type,
            "word_count":     int(wc),
            "number_density": round(float(nd), 4),
            "captioned":      bool(do_cap),
        }

    def _extend_embeddings(self, new_clip_embs: List[np.ndarray], prev_count: int):
        texts = [e.get("combined_text", "") or "[no text]" for e in self.knowledge_base]
        self.text_embeddings = self._embed_texts(texts)

        if (
            self.clip_embeddings is not None
            and len(self.clip_embeddings) == prev_count
            and prev_count > 0
        ):
            self.clip_embeddings = self._normalize_rows(
                np.vstack([self.clip_embeddings] + new_clip_embs)
            )
        else:
            self._rebuild_embeddings()

    # ─────────────────────────────────────────────────────────────────────────
    # Auto-index pages/ on startup
    # ─────────────────────────────────────────────────────────────────────────
    def _auto_index_existing_pages(self):
        cached    = {e["filename"] for e in self.knowledge_base}
        existing  = sorted(
            p for p in self.image_dir.iterdir()
            if p.suffix.lower() in SUPPORTED_IMAGE_EXTS
        )
        new_paths = [p for p in existing if p.name not in cached]

        if not new_paths:
            log.info("Auto-index: all existing pages already indexed.")
            return

        log.info(f"Auto-indexing {len(new_paths)} new page(s) found in pages/...")
        prev_count    = len(self.knowledge_base)
        new_clip_embs: List[np.ndarray] = []

        for img_path in new_paths:
            entry = self._index_one(img_path)
            self.knowledge_base.append(entry)
            new_clip_embs.append(self._embed_image_clip(str(img_path)))
            log.info(f"  Indexed: {img_path.name}")

        self._extend_embeddings(new_clip_embs, prev_count)
        self._save_index()
        log.info(f"Auto-index done. Total pages in index: {len(self.knowledge_base)}")

    # ─────────────────────────────────────────────────────────────────────────
    # PDF conversion
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _pdf_to_images(pdf_path: str, dpi: int = PDF_DPI) -> List[Image.Image]:
        try:
            import fitz
            doc    = fitz.open(pdf_path)
            images = []
            zoom   = dpi / 72.0
            mat    = fitz.Matrix(zoom, zoom)
            for page in doc:
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            doc.close()
            log.info(f"PDF converted via PyMuPDF: {len(images)} page(s)")
            return images
        except ImportError:
            pass

        try:
            from pdf2image import convert_from_path
            from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError
            try:
                pages = list(convert_from_path(pdf_path, dpi=dpi))
                log.info(f"PDF converted via pdf2image: {len(pages)} page(s)")
                return pages
            except (PDFInfoNotInstalledError, PDFPageCountError):
                raise RuntimeError(
                    "pdf2image requires poppler.\n"
                    "Easiest fix: pip install pymupdf"
                )
        except ImportError:
            pass

        raise RuntimeError("No PDF engine installed. Run: pip install pymupdf")

    # ─────────────────────────────────────────────────────────────────────────
    # Public: add_slides
    # ─────────────────────────────────────────────────────────────────────────
    def add_slides(self, file_paths: List[str]) -> Dict:
        cached          = {e["filename"] for e in self.knowledge_base}
        new_image_paths: List[Path] = []
        added_names:     List[str]  = []
        skipped:         List[str]  = []
        errors:          List[str]  = []

        for fp in file_paths:
            fp   = Path(fp)
            stem = fp.stem.replace(" ", "_")
            ext  = fp.suffix.lower().lstrip(".")

            if ext == "pdf":
                try:
                    pages = self._pdf_to_images(str(fp), dpi=PDF_DPI)
                    for i, pg in enumerate(pages, 1):
                        out = self.image_dir / f"{stem}_page_{i:03d}.png"
                        if out.name not in cached:
                            pg.save(out, "PNG")
                            new_image_paths.append(out)
                        else:
                            skipped.append(out.name)
                    log.info(f"PDF '{fp.name}' converted to {len(pages)} page(s).")
                except RuntimeError as e:
                    errors.append(str(e))
                except Exception as e:
                    errors.append(f"Failed to convert '{fp.name}': {e}")

            elif ext in {"png", "jpg", "jpeg", "webp"}:
                out = self.image_dir / f"{stem}.{ext}"
                if out.name not in cached:
                    shutil.copy(str(fp), str(out))
                    new_image_paths.append(out)
                else:
                    skipped.append(out.name)
            else:
                errors.append(
                    f"'{fp.name}' has unsupported type '.{ext}'. "
                    "Supported: pdf, png, jpg, jpeg, webp."
                )

        prev_count    = len(self.knowledge_base)
        new_clip_embs: List[np.ndarray] = []
        for img_path in new_image_paths:
            try:
                entry = self._index_one(img_path)
                self.knowledge_base.append(entry)
                new_clip_embs.append(self._embed_image_clip(str(img_path)))
                added_names.append(img_path.name)
            except Exception as e:
                errors.append(f"Failed to index '{img_path.name}': {e}")

        if added_names:
            self._extend_embeddings(new_clip_embs, prev_count)
            self._save_index()

        return {
            "added":   added_names,
            "skipped": skipped,
            "errors":  errors,
            "total":   len(self.knowledge_base),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Public: recaption_all
    # ─────────────────────────────────────────────────────────────────────────
    def recaption_all(self) -> int:
        count = 0
        for entry in self.knowledge_base:
            img_path = self.image_dir / entry["filename"]
            if not img_path.exists():
                continue
            ocr_text   = entry.get("ocr_text", "")
            caption    = self._qwen_caption(str(img_path), ocr_text)
            slide_type = self._detect_slide_type(ocr_text, caption)

            do_cap, wc, nd          = self._should_caption(ocr_text)
            entry["caption"]        = caption
            entry["captioned"]      = bool(do_cap)
            entry["word_count"]     = int(wc)
            entry["number_density"] = round(float(nd), 4)
            entry["slide_type"]     = slide_type

            if slide_type == "visual" and caption.strip():
                entry["combined_text"] = caption.strip() + (
                    "\n\nOCR (raw):\n" + ocr_text.strip() if ocr_text.strip() else ""
                )
            else:
                entry["combined_text"] = (
                    ocr_text.strip() + ("\n\n" + caption.strip() if caption.strip() else "")
                ).strip() or "[no text]"
            count += 1

        if count:
            texts = [e.get("combined_text", "") or "[no text]" for e in self.knowledge_base]
            self.text_embeddings = self._embed_texts(texts)
            self._save_index()
            log.info(f"Recaptioned {count} slides and rebuilt text embeddings.")
        return count

    # ─────────────────────────────────────────────────────────────────────────
    # Public: list_slides
    # ─────────────────────────────────────────────────────────────────────────
    def list_slides(self) -> List[Dict]:
        import datetime
        results = []
        for e in self.knowledge_base:
            img_path = self.image_dir / e["filename"]
            # File size in bytes (0 if file missing)
            try:
                file_size = img_path.stat().st_size if img_path.exists() else 0
            except Exception:
                file_size = 0
            # Indexed-at: use file mtime as a proxy for when it was indexed
            try:
                mtime = img_path.stat().st_mtime if img_path.exists() else None
                indexed_at = (
                    datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    if mtime else "Unknown"
                )
            except Exception:
                indexed_at = "Unknown"
            results.append({
                "filename":   e["filename"],
                "word_count": e.get("word_count", 0),
                "captioned":  e.get("captioned", False),
                "slide_type": e.get("slide_type", "text"),
                "image_path": str(img_path),
                "file_size":  file_size,
                "indexed_at": indexed_at,
            })
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Public: retrieve
    # ─────────────────────────────────────────────────────────────────────────
    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K,
                 text_weight: float = TEXT_WEIGHT,
                 image_weight: float = IMAGE_WEIGHT) -> List[Dict]:
        if not self.knowledge_base:
            return []
        if self.text_embeddings is None or self.clip_embeddings is None:
            self._rebuild_embeddings()

        q_text = self._embed_texts(query)[0]
        q_clip = self._embed_query_clip(query)

        t_scores = self.text_embeddings @ q_text
        c_scores = self.clip_embeddings @ q_clip

        t_scaled = self._minmax_scale(t_scores)
        c_scaled = self._minmax_scale(c_scores)
        fused    = text_weight * t_scaled + image_weight * c_scaled

        top_k = min(top_k, len(self.knowledge_base))
        order = np.argsort(-fused)[:top_k]

        return [
            {
                "rank":          rank,
                "page_id":       self.knowledge_base[int(i)]["page_id"],
                "filename":      self.knowledge_base[int(i)]["filename"],
                "image_path":    str(self.image_dir / self.knowledge_base[int(i)]["filename"]),
                "score":         round(float(fused[i]), 4),
                "text_score":    round(float(t_scaled[i]), 4),
                "image_score":   round(float(c_scaled[i]), 4),
                "combined_text": self.knowledge_base[int(i)].get("combined_text", ""),
                "ocr_text":      self.knowledge_base[int(i)].get("ocr_text", ""),
                "caption":       self.knowledge_base[int(i)].get("caption", ""),
                "captioned":     bool(self.knowledge_base[int(i)].get("captioned", False)),
                "slide_type":    self.knowledge_base[int(i)].get("slide_type", "text"),
            }
            for rank, i in enumerate(order, 1)
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # Public: ask
    # ─────────────────────────────────────────────────────────────────────────
    def ask(self, query: str, top_k: int = DEFAULT_TOP_K,
            text_weight: float = TEXT_WEIGHT,
            image_weight: float = IMAGE_WEIGHT) -> Dict:
        if not self.knowledge_base:
            return {
                "answer":  "No slides indexed yet. Please upload some slides first.",
                "sources": [],
                "mode":    "no_index",
            }
        candidates = self.retrieve(query, top_k=top_k,
                                   text_weight=text_weight,
                                   image_weight=image_weight)
        if not candidates:
            return {"answer": "No relevant slides found.", "sources": [], "mode": "no_results"}
        answer, mode = self._qwen_answer(query, candidates)

        # Re-rank sources so the slide with most word overlap with the answer appears first
        answer_words = set(re.findall(r"\w+", answer.lower()))
        def overlap(c):
            slide_words = set(re.findall(r"\w+", c.get("combined_text", "").lower()))
            return len(answer_words & slide_words)
        reranked = sorted(candidates, key=overlap, reverse=True)
        for i, c in enumerate(reranked, 1):
            c["rank"] = i

        return {"answer": answer, "sources": reranked, "mode": mode}