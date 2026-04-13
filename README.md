# Multi-Modal-RAG

A production-ready Multimodal Retrieval-Augmented Generation (RAG) system that answers natural-language questions grounded in both text and visuals from slide decks. Built for enterprise document QA — no GPU required.

---

## What it does

Upload a PDF or set of slide images and ask questions in plain English. The system retrieves the most relevant slides using both text and visual similarity, then generates a grounded answer by reading the actual slide images — including charts, tables, and diagrams.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   INDEXING (offline)                 │
│  Slide Image → EasyOCR → MiniLM (384-dim text emb) │
│             → Groq caption → CLIP (512-dim img emb) │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│                  RETRIEVAL (online)                  │
│  Query → MiniLM text score (×0.75)                  │
│        → CLIP image score  (×0.25)                  │
│        → Fused score → Top-K slides                 │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│               GENERATION (online)                    │
│  Top-K slides + query → Groq Llama-4-Scout-17B      │
│  Reads images directly → Grounded answer            │
└─────────────────────────────────────────────────────┘
```

---

## Models

| Component | Model | Where |
|---|---|---|
| OCR | EasyOCR | Local (CPU) |
| Text retrieval | MiniLM L6 (multi-qa) | Local (CPU) |
| Image retrieval | CLIP ViT-B/32 | Local (CPU) |
| Caption generation | Llama-4-Scout-17B | Groq API |
| Answer generation | Llama-4-Scout-17B | Groq API |
| Evaluation judge | Llama-3.3-70B | Groq API |

---

## Evaluation Results

Automated 4-tier LLM-as-a-Judge evaluation on Infineon acquisition slide deck (6 slides, 16 questions). Judge model (Llama-3.3-70B) kept independent from generator to prevent self-evaluation bias.

| Metric | Score |
|---|---|
| Hit Rate | 100% |
| Fact Coverage | 97% |
| Overall (Tiers 1–3) | 99% |

| Tier | Description | Hit Rate | Fact Cov. |
|---|---|---|---|
| Tier 1 — Direct Text | Headline facts | 100% | 100% |
| Tier 2 — Visual Read | Charts & tables | 100% | 100% |
| Tier 3 — Multi-Slide | Cross-slide reasoning | 100% | 92% |
| Tier 4 — Stress Tests | Hard edge cases (excluded) | 67% | 33% |

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) (for local evaluation judge)
- Groq API key — free at [console.groq.com](https://console.groq.com)

---

## Setup

**1. Clone the repo:**
```bash
git clone https://github.com/uwaisabdulkadir1972-sketch/Multi-Modal-RAG.git
cd Multi-Modal-RAG
```

**2. Create and activate a virtual environment:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate.bat

# Mac/Linux
source venv/bin/activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Set your Groq API key in `backend.py`:**
```python
GROQ_API_KEY = "your_groq_api_key_here"
```

---

## Running the app

```bash
streamlit run app.py
```

Browser opens at `http://localhost:8501`.

1. Click **Load System** in the sidebar
2. Upload PDF or image slides via the sidebar
3. Ask questions in the chat box

---

## Running the evaluation

**1. Pull the judge model (one time):**
```bash
ollama pull llama3.1:8b
```

**2. Set your Groq judge key in `evaluate.py`:**
```python
GROQ_JUDGE_KEY = "your_groq_api_key_here"
```

**3. Run:**
```bash
# Start Ollama in a separate terminal
ollama serve

# Run evaluation
python evaluate.py
```

Results print live. `mmrag_evaluation.xlsx` is saved in your project folder.

**To re-export Excel without re-running:**
```bash
python evaluate.py --excel-only
```

---

## Project structure

```
Multi-Modal-RAG/
├── app.py              # Streamlit UI
├── backend.py          # CLIP + MiniLM + Groq pipeline
├── evaluate.py         # 4-tier evaluation + Excel export
├── requirements.txt    # Python dependencies
└── mmrag_store/        # Created at runtime (slides + index)
    ├── pages/          # Slide images
    └── index/          # Embeddings + knowledge base
```

---

## Limitations

- Groq free tier: 500k tokens/day — sufficient for normal use, may hit limits during bulk evaluation
- OCR struggles with handwritten text and very small fonts
- Single-page retrieval — cannot synthesise across more than top-K slides per query
- No GPU required, but indexing and retrieval are slower on CPU-only machines

---

## Future Work

- Scale to 1000+ page enterprise repositories with approximate nearest-neighbour search (FAISS)
- Multi-page synthesis for complex cross-document queries
- API-based answering with GPT-4o or Gemini for higher visual accuracy
- Support for additional document types (Word, Excel, PowerPoint)

---

## Built with

`Python` `Streamlit` `PyTorch` `CLIP` `EasyOCR` `Sentence Transformers` `Groq` `OpenCLIP` `Ollama` `OpenPyXL`

---

*Singapore University of Technology and Design — Engineering Systems and Design*
