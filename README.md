# Multimodal RAG for Slide Decks

A question-answering application that retrieves relevant slides using text and visual embeddings, then sends the selected images to a vision model to generate an answer. The interface is built with Streamlit; retrieval and OCR can run on a CPU, while captioning and answer generation use the Groq API.

## How it works

1. Convert uploaded PDFs to slide images and extract text with EasyOCR.
2. Index slides using multi-qa-MiniLM text embeddings and CLIP image embeddings. Groq generates captions for visual content.
3. Combine text and image similarity scores (default weights 0.75 and 0.25) to retrieve the top slides.
4. Send the selected images and question to Llama 4 Scout through Groq. The interface shows the answer and retrieved sources.

**Stack:** Python, Streamlit, EasyOCR, sentence-transformers, OpenCLIP, PyTorch, Groq and PyMuPDF.

## Run locally

Requirements: Python, an internet connection for initial model downloads and Groq requests, and a Groq API key. Model downloads and CPU indexing can take time. A GPU is not required for the retrieval models.

```bash
git clone https://github.com/uwaisabdulkadir1972-sketch/Multi-Modal-RAG.git
cd Multi-Modal-RAG
python -m venv .venv
```

Activate the environment (`.venv\\Scripts\\Activate.ps1` in PowerShell or `source .venv/bin/activate` on macOS/Linux), then:

```bash
python -m pip install -r requirements.txt
```

Set `GROQ_API_KEY` as an environment variable before starting the app. For example, in PowerShell:

```powershell
$env:GROQ_API_KEY = 'your-key'
streamlit run app.py
```

Open the address printed by Streamlit, select **Load System**, upload a PDF or slide images, and ask a question. Do not commit API keys to the repository.

## Evaluation

`evaluate.py` contains 14 hand-written questions: four direct-text, four visual, four multi-slide and two stress-test questions. The script measures retrieval, fact coverage and answer quality. The summary excludes the stress tier. It requests five retrieved slides for each question; multi-slide retrieval uses partial recall rather than a simple hit.

When `GROQ_JUDGE_KEY` is set and the service is available, answer quality is graded by `llama-3.3-70b-versatile` through Groq. Otherwise the script falls back to a word-overlap heuristic, marked with `*` in the output. Results from these methods are not directly equivalent.

A prior workbook for a six-slide Infineon acquisition deck records 100% retrieval hit rate and 97% fact coverage across 12 non-stress questions, with a composite score of 99%. It reports four additional stress questions separately (67% hit rate and 33% fact coverage where applicable). This was a small, single-deck test; the workbook is from a different question set than the current script, and its judge label cannot be independently confirmed. These results have not been reproduced from the current repository.

To run the current evaluation, first index the source slides referenced in `golden_qa` using the app. Set `GROQ_API_KEY`, optionally set `GROQ_JUDGE_KEY`, and run:

```bash
python evaluate.py
```

The script saves detailed results to `mmrag_results.json` and an Excel workbook to `mmrag_evaluation.xlsx`. Model availability, API limits and service costs depend on the provider and account.

## Limitations

- Results depend on retrieval quality, OCR and the vision model; answers should be checked against source slides.
- The evaluation is a small, manually written set focused on one slide deck, not a general benchmark.
- Images and questions are sent to Groq. Only use documents you are permitted to send to an external service.
- The repository does not include the evaluation slides or a sample dataset, so reproducing the original experiment requires those files.

## Files

- `app.py` — Streamlit interface
- `backend.py` — indexing, retrieval and answer generation
- `evaluate.py` — evaluation and Excel export
- `requirements.txt` — pinned dependencies

