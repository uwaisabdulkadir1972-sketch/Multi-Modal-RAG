"""
MM-RAG Streamlit App — Infineon Edition
Run with:  streamlit run app.py
"""

import streamlit as st
from pathlib import Path
import tempfile
import base64

def _img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

st.set_page_config(
    page_title="Infineon MM-RAG",
    layout="wide",
    page_icon="🔴",
)

# ─────────────────────────────────────────────────────────────────────────────
# Infineon brand colours
#   Primary Red  : #E8001C
#   Primary Blue : #003865
#   Light Blue   : #009FE3
#   Off-white bg : #F5F7FA
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Source Sans 3', sans-serif;
}

/* ── App background ── */
.stApp {
    background-color: #F5F7FA;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #003865 0%, #00264d 100%);
    border-right: 3px solid #E8001C;
}
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: #E8001C !important;
    color: #fff !important;
    border: none;
    border-radius: 6px;
    font-weight: 700;
    letter-spacing: 0.5px;
    transition: background 0.2s;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #b8001a !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.2) !important;
}
/* Slider accent */
[data-testid="stSidebar"] [data-baseweb="slider"] [data-testid="stThumbValue"] {
    color: #E8001C !important;
}
[data-testid="stSidebar"] .stSlider > div > div > div > div {
    background: #E8001C !important;
}

/* ── Top header bar ── */
.infineon-header {
    background: linear-gradient(90deg, #003865 0%, #E8001C 100%);
    padding: 18px 28px;
    border-radius: 10px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.infineon-header h1 {
    color: #fff !important;
    margin: 0;
    font-size: 1.7rem;
    font-weight: 700;
    letter-spacing: 0.3px;
}
.infineon-header p {
    color: rgba(255,255,255,0.85) !important;
    margin: 4px 0 0 0;
    font-size: 0.95rem;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    border-radius: 10px;
    margin-bottom: 8px;
    background-color: #FFFFFF;
}
/* Force all text inside chat messages to be dark/readable */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span:not(.badge):not(.mode-pill),
[data-testid="stChatMessage"] div:not(.score-row):not(.badge),
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] em {
    color: #111111 !important;
}

/* ── Source expander ── */
[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 1px solid #d0d8e4;
    border-left: 4px solid #E8001C;
    border-radius: 8px;
    margin-bottom: 10px;
}

[data-testid="stExpander"] summary {
    font-weight: 600;
    color: #003865;
}
[data-testid="stExpander"] summary p {
    color: #000000 !important;
}
details[open] [data-testid="stExpander"] summary p,
[data-testid="stExpander"] details[open] summary p {
    color: #ffffff !important;
}            

/* ── Score badge ── */
.score-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 8px;
}
.badge {
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    font-weight: 700;
}
.badge-fused  { background: #003865; color: #fff !important; }
.badge-text   { background: #009FE3; color: #fff !important; }
.badge-image  { background: #E8001C; color: #fff !important; }

/* ── OCR / Caption boxes ── */
.ocr-box {
    background: #EAF6FF;
    border-left: 3px solid #009FE3;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.84rem;
    margin-top: 6px;
    color: #003865;
}
.caption-box {
    background: #FFF0F0;
    border-left: 3px solid #E8001C;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.84rem;
    margin-top: 6px;
    color: #003865;
}

/* ── Mode pill ── */
.mode-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 700;
    background: #003865;
    color: #fff !important;
    margin-bottom: 10px;
}

/* ── Slide list in sidebar ── */
.slide-item {
    background: rgba(255,255,255,0.08);
    border-left: 3px solid #E8001C;
    border-radius: 4px;
    padding: 4px 8px;
    margin-bottom: 4px;
    font-size: 0.82rem;
}

/* ── Info / success / warning overrides ── */
[data-testid="stAlert"] {
    border-radius: 8px;
}

/* ── Primary buttons outside sidebar ── */
.stButton > button[kind="primary"] {
    background: #E8001C !important;
    color: #fff !important;
    border: none;
    border-radius: 6px;
    font-weight: 700;
}
.stButton > button[kind="primary"]:hover {
    background: #b8001a !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    border: 2px solid #003865 !important;
    border-radius: 8px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #E8001C !important;
    box-shadow: 0 0 0 2px rgba(232,0,28,0.15) !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
for key, default in [
    ("backend_loaded", False),
    ("backend", None),
    ("messages", []),
    ("top_k", 3),
    ("text_weight", 70),
    ("show_manual", False),
    ("current_page", "chat"),   # "chat" | "indexed_slides"
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────────────────────────────────────
# Backend (cached so models load once)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading models — CLIP · MiniLM · Groq · EasyOCR …")
def load_backend():
    from backend import MMRAGBackend
    return MMRAGBackend()

# ─────────────────────────────────────────────────────────────────────────────
# Helper: render source cards
# ─────────────────────────────────────────────────────────────────────────────
def show_sources(result: dict):
    sources = result.get("sources", [])
    mode    = result.get("mode", "")
    if not sources:
        return

    st.markdown(f'<span class="mode-pill">mode: {mode}</span>', unsafe_allow_html=True)
    st.markdown(f"**{len(sources)} slide(s) retrieved:**")

    for src in sources:
        fused_score = src["score"]
        txt_score   = src["text_score"]
        img_score   = src["image_score"]
        slide_type  = src.get("slide_type", "text")
        type_icon   = "🖼️ visual/diagram" if slide_type == "visual" else "📝 text"

        label = (
            f"#{src['rank']}  {src['filename']}  [{type_icon}]  —  "
            f"fused {fused_score:.4f} | text {txt_score:.4f} | img {img_score:.4f}"
        )
        with st.expander(label, expanded=(src["rank"] == 1)):
            badges = f"""
            <div class="score-row">
              <span class="badge badge-fused">Fused {fused_score:.4f}</span>
              <span class="badge badge-text">Text {txt_score:.4f}</span>
              <span class="badge badge-image">Image {img_score:.4f}</span>
              <span class="badge {'badge-image' if slide_type == 'visual' else 'badge-fused'}">
                  {'🖼️ Visual slide — caption is primary' if slide_type == 'visual' else '📝 Text slide — OCR is primary'}
              </span>
            </div>
            """
            st.markdown(badges, unsafe_allow_html=True)

            col_img, col_txt = st.columns([1, 1])

            with col_img:
                img_path = src.get("image_path", "")
                if img_path and Path(img_path).exists():
                    st.image(img_path, use_container_width=True)
                else:
                    st.write("_(image file not found)_")

            with col_txt:
                ocr = src.get("ocr_text", "").strip()
                cap = src.get("caption", "").strip()

                if slide_type == "visual":
                    # Caption first for visual/diagram slides
                    if cap:
                        st.markdown(
                            f'<div class="caption-box">🖼️ <b>Visual Description</b> '
                            f'<span style="font-size:0.75em;opacity:0.7">(primary — diagram/chart aware)</span>'
                            f'<br><br>{cap}</div>',
                            unsafe_allow_html=True,
                        )
                    if ocr:
                        st.markdown(
                            f'<div class="ocr-box">🔤 <b>Raw OCR Text</b> '
                            f'<span style="font-size:0.75em;opacity:0.7">(secondary — may be spatially disordered)</span>'
                            f'<br><br>{ocr[:500]}</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    # OCR first for text slides
                    if ocr:
                        st.markdown(
                            f'<div class="ocr-box">🔤 <b>Slide Text</b> '
                            f'<span style="font-size:0.75em;opacity:0.7">(primary)</span>'
                            f'<br><br>{ocr[:700]}</div>',
                            unsafe_allow_html=True,
                        )
                    if cap:
                        st.markdown(
                            f'<div class="caption-box">🖼️ <b>Visual Description</b> '
                            f'<span style="font-size:0.75em;opacity:0.7">(supplementary)</span>'
                            f'<br><br>{cap}</div>',
                            unsafe_allow_html=True,
                        )

                if not ocr and not cap:
                    st.write("_(no text extracted from this slide)_")

# ─────────────────────────────────────────────────────────────────────────────
# Page: Indexed Slides detail view
# ─────────────────────────────────────────────────────────────────────────────
def show_indexed_slides_page():
    """Full-page view of all indexed slides with metadata and image preview."""
    import re as _re
    import zipfile
    import io
    from collections import defaultdict

    # ── Back button ──────────────────────────────────────────────────────────
    if st.button("← Back to Chat", type="primary"):
        st.session_state.current_page = "chat"
        st.rerun()

    st.markdown("""
    <div class="infineon-header">
        <div>
            <h1>🗂️ Indexed Slides</h1>
            <p>All slides currently in the retrieval index — metadata, size, upload time, and preview</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.backend_loaded:
        st.info("👈 Click **Load System** in the sidebar to initialise the models first.")
        return

    slides = st.session_state.backend.list_slides()

    if not slides:
        st.warning("No slides indexed yet. Upload files via the sidebar and click **Index Uploaded Files**.")
        return

    # ── Helper ───────────────────────────────────────────────────────────────
    def _fmt_size(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        elif n < 1024 ** 2:
            return f"{n / 1024:.1f} KB"
        else:
            return f"{n / 1024 ** 2:.2f} MB"

    def _doc_title(filename: str) -> str:
        name = Path(filename).stem
        m = _re.match(r"^(.+?)_page_\d+$", name)
        return m.group(1).replace("_", " ").title() if m else name.replace("_", " ").title()

    def _build_zip(pages: list) -> bytes:
        """Pack all page images for a document into an in-memory ZIP."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in pages:
                img_path = Path(p["image_path"])
                if img_path.exists():
                    zf.write(img_path, arcname=img_path.name)
        buf.seek(0)
        return buf.read()

    # ── Group by document ────────────────────────────────────────────────────
    grouped: dict = defaultdict(list)
    for s in slides:
        grouped[_doc_title(s["filename"])].append(s)

    # ── Search bar ───────────────────────────────────────────────────────────
    col_search, col_count = st.columns([3, 1])
    with col_search:
        search_query = st.text_input(
            "🔍 Search documents",
            placeholder="Type a document title to filter…",
            label_visibility="collapsed",
        )
    with col_count:
        st.markdown(
            f'<p style="color:#003865; font-weight:600; font-size:0.95rem; padding-top:8px;">'
            f'📊 {len(slides)} page(s) · {len(grouped)} document(s)</p>',
            unsafe_allow_html=True,
        )

    # Filter grouped dict by search query
    query_lower = search_query.strip().lower()
    filtered = {
        title: pages
        for title, pages in grouped.items()
        if query_lower in title.lower()
    } if query_lower else grouped

    if not filtered:
        st.info(f'No documents match "{search_query}".')
        return

    if query_lower:
        st.caption(f"Showing {len(filtered)} of {len(grouped)} document(s) matching \"{search_query}\"")

    # ── Render each document ─────────────────────────────────────────────────
    global_idx = 0
    for doc_idx, (doc_title, pages) in enumerate(filtered.items()):
        total_size = sum(p["file_size"] for p in pages)
        indexed_times = [p["indexed_at"] for p in pages if p["indexed_at"] != "Unknown"]
        doc_indexed_at = min(indexed_times) if indexed_times else "Unknown"
        zip_filename = doc_title.replace(" ", "_") + "_slides.zip"

        # ── Document header card + download button side by side ──────────────
        card_col, dl_col = st.columns([3, 1])

        with card_col:
            st.markdown(f"""
            <div style="
                background:#fff;
                border:1px solid #d0d8e4;
                border-left:5px solid #003865;
                border-radius:10px;
                padding:16px 20px;
                margin-bottom:0;
            ">
                <div style="font-size:1.1rem; font-weight:700; color:#003865;">
                    📄 {doc_title}
                </div>
                <div style="margin-top:6px; display:flex; gap:18px; flex-wrap:wrap; font-size:0.88rem; color:#555;">
                    <span>🗂️ <b>{len(pages)}</b> page{'s' if len(pages) != 1 else ''}</span>
                    <span>💾 <b>{_fmt_size(total_size)}</b></span>
                    <span>🕒 Indexed: <b>{doc_indexed_at}</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with dl_col:
            # Build ZIP and offer as a single download for the whole document
            zip_bytes = _build_zip(pages)
            st.download_button(
                label="⬇️ Download all pages",
                data=zip_bytes,
                file_name=zip_filename,
                mime="application/zip",
                use_container_width=True,
                key=f"dl_doc_{doc_idx}",
            )

        # ── Individual page cards (inside expander) ──────────────────────────
        with st.expander(f'🔍 View {len(pages)} page(s) of "{doc_title}"', expanded=False):
            for slide in pages:
                global_idx += 1
                img_path = slide["image_path"]
                file_exists = Path(img_path).exists()
                type_icon = "🖼️" if slide.get("slide_type") == "visual" else "📝"
                cap_badge = "✅ Captioned" if slide["captioned"] else "—"

                col_meta, col_img = st.columns([1, 1])

                with col_meta:
                    st.markdown(f"""
                    <div style="
                        background:#F5F7FA;
                        border:1px solid #d0d8e4;
                        border-left:4px solid #E8001C;
                        border-radius:8px;
                        padding:14px 16px;
                        height:100%;
                    ">
                        <div style="font-weight:700; color:#003865; font-size:0.95rem; margin-bottom:10px;">
                            {type_icon} {slide['filename']}
                        </div>
                        <table style="font-size:0.85rem; color:#333; border-collapse:collapse; width:100%;">
                            <tr>
                                <td style="padding:3px 8px 3px 0; color:#666; white-space:nowrap;">📦 File size</td>
                                <td style="padding:3px 0; font-weight:600;">{_fmt_size(slide['file_size'])}</td>
                            </tr>
                            <tr>
                                <td style="padding:3px 8px 3px 0; color:#666; white-space:nowrap;">🕒 Indexed at</td>
                                <td style="padding:3px 0; font-weight:600;">{slide['indexed_at']}</td>
                            </tr>
                            <tr>
                                <td style="padding:3px 8px 3px 0; color:#666; white-space:nowrap;">📝 Word count</td>
                                <td style="padding:3px 0; font-weight:600;">{slide['word_count']} words</td>
                            </tr>
                            <tr>
                                <td style="padding:3px 8px 3px 0; color:#666; white-space:nowrap;">🎨 Slide type</td>
                                <td style="padding:3px 0; font-weight:600;">{slide.get('slide_type','text').title()}</td>
                            </tr>
                            <tr>
                                <td style="padding:3px 8px 3px 0; color:#666; white-space:nowrap;">🤖 Caption</td>
                                <td style="padding:3px 0; font-weight:600;">{cap_badge}</td>
                            </tr>
                        </table>
                        {"<p style='margin-top:10px;font-size:0.8rem;color:#888;'>⚠️ Image file not found on disk.</p>" if not file_exists else ""}
                    </div>
                    """, unsafe_allow_html=True)

                with col_img:
                    if file_exists:
                        st.image(img_path, use_container_width=True, caption=slide["filename"])
                    else:
                        st.info("_(image file not found on disk)_")

                st.markdown("<hr style='border-color:#e8edf4; margin:10px 0;'>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Infineon logo ────────────────────────────────────────────────────────
    _logo_path = Path(__file__).parent / "infineon_logo.png"
    if _logo_path.exists():
        _logo_b64 = _img_to_base64(str(_logo_path))
        st.markdown(
            f"""
            <div style="text-align:center; padding: 14px 16px 8px 16px;
                        background:rgba(255,255,255,0.95); border-radius:10px;
                        margin-bottom:4px;">
                <img src="data:image/png;base64,{_logo_b64}"
                     style="width:85%; max-width:180px; height:auto;" />
                <div style="font-size:0.75rem; margin-top:6px;
                            font-weight:700; letter-spacing:0.5px;
                            background: linear-gradient(90deg, #003865 0%, #E8001C 100%);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            background-clip: text;">
                    MM-RAG Slide Assistant
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Fallback if logo file not found
        st.markdown("""
        <div style="text-align:center; padding: 10px 0 4px 0;">
            <div style="font-size:1.2rem; font-weight:800; letter-spacing:1px; color:#fff;">
                INFINEON
            </div>
            <div style="font-size:0.78rem; margin-top:2px;
                        font-weight:700;
                        background: linear-gradient(90deg, #003865 0%, #E8001C 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;">
                MM-RAG Slide Assistant
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Load system ──────────────────────────────────────────────────────────
    st.markdown("**⚙️ System**")
    if not st.session_state.backend_loaded:
        if st.button("🚀 Load System", use_container_width=True, type="primary"):
            try:
                st.session_state.backend = load_backend()
                st.session_state.backend_loaded = True
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load backend:\n{e}")
    else:
        st.success("✅ System ready")

    st.divider()

    # ── Retrieval settings ───────────────────────────────────────────────────
    st.markdown("**🎯 Retrieval Settings**")

    top_k = st.slider(
        "Top-K slides to retrieve",
        min_value=1,
        max_value=5,
        value=st.session_state.top_k,
        step=1,
        help="How many slides the system fetches per question. Keep at 3+ for best accuracy.",
    )
    st.session_state.top_k = top_k
    if top_k == 1:
        st.warning("⚠️ Top-K = 1 may miss the right slide. Use 3+ for best results.")
    else:
        st.caption(f"Retrieving top {top_k} slide{'s' if top_k > 1 else ''} per question.")

    text_weight_pct = st.slider(
        "Text vs Image weight",
        min_value=10,
        max_value=90,
        value=st.session_state.text_weight,
        step=10,
        help=(
            "Controls how much the system trusts slide text (OCR) vs slide visuals (CLIP image embeddings) "
            "when deciding which slides to retrieve.\n\n"
            "• Slide LEFT (10%) → visuals dominate — good for diagram/chart-heavy decks\n"
            "• Slide RIGHT (90%) → text dominates — good for bullet-point/data decks\n"
            "• Default 70% text works well for most business presentations."
        ),
    )
    st.session_state.text_weight = text_weight_pct
    img_weight_pct = 100 - text_weight_pct
    st.caption(f"📝 Text {text_weight_pct}%  ·  🖼️ Image {img_weight_pct}%")

    # Push weights into backend if loaded
    if st.session_state.backend_loaded and st.session_state.backend is not None:
        import backend as _be
        _be.TEXT_WEIGHT  = text_weight_pct  / 100.0
        _be.IMAGE_WEIGHT = img_weight_pct   / 100.0

    st.divider()

    # ── Upload slides ────────────────────────────────────────────────────────
    st.markdown("**📤 Upload New Slides**")
    st.caption("PDF, PNG, JPG or JPEG. PDFs auto-convert to per-page images.")

    uploaded_files = st.file_uploader(
        "Drop files here",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files and st.session_state.backend_loaded:
        if st.button("📥 Index Uploaded Files", use_container_width=True, type="primary"):
            with st.spinner("Processing and indexing…"):
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_paths = []
                    for uf in uploaded_files:
                        dest = Path(tmp) / uf.name
                        dest.write_bytes(uf.read())
                        tmp_paths.append(str(dest))
                    result = st.session_state.backend.add_slides(tmp_paths)

            if result["added"]:
                st.success(f"✅ Indexed {len(result['added'])} new page(s).")
                for name in result["added"]:
                    st.markdown(f"  • `{name}`")
            if result["skipped"]:
                st.info(f"ℹ️ Skipped {len(result['skipped'])} already-indexed page(s).")
            if result.get("errors"):
                for err in result["errors"]:
                    st.error(f"❌ {err}")
            if not result["added"] and not result.get("errors"):
                st.info("No new pages to index.")
            st.rerun()
    elif uploaded_files and not st.session_state.backend_loaded:
        st.warning("Load the system first, then index your files.")

    st.divider()

    # ── Indexed slides list ──────────────────────────────────────────────────
    st.markdown("**🗂️ Indexed Slides**")
    if st.session_state.backend_loaded:
        slides = st.session_state.backend.list_slides()
        if slides:
            st.caption(f"{len(slides)} page(s) in index")
            if st.button("📋 View Indexed Slides", use_container_width=True):
                st.session_state.current_page = "indexed_slides"
                st.rerun()
        else:
            st.info("No slides indexed yet.")
    else:
        st.caption("Load the system to see indexed slides.")

    # Clear chat button at the bottom
    st.divider()
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("**🔄 Maintenance**")
    st.caption("Re-run the improved caption prompt on all slides. Do this once after upgrading.")
    if st.session_state.backend_loaded:
        if st.button("♻️ Re-caption All Slides", use_container_width=True):
            with st.spinner("Re-captioning all slides with improved prompt… this may take a few minutes."):
                n = st.session_state.backend.recaption_all()
            st.success(f"✅ Re-captioned {n} slide(s). Answers should now be more accurate.")
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Page routing
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.current_page == "indexed_slides":
    show_indexed_slides_page()
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Main area — Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="infineon-header">
    <div>
        <h1>📚 MM-RAG Slide Assistant</h1>
        <p>Ask questions — answers grounded in both slide text and visuals · Powered by Groq + CLIP + EasyOCR</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# User Manual (collapsible)
# ─────────────────────────────────────────────────────────────────────────────
col_title, col_btn = st.columns([5, 1])
with col_btn:
    if st.button(
        "📖 Hide Manual" if st.session_state.show_manual else "📖 User Manual",
        use_container_width=True,
    ):
        st.session_state.show_manual = not st.session_state.show_manual
        st.rerun()

if st.session_state.show_manual:
    st.markdown("""
<div style="background:#fff; border:1px solid #d0d8e4; border-left:5px solid #003865;
            border-radius:10px; padding:22px 28px; margin-bottom:20px; color:#111;">

<h3 style="color:#003865; margin-top:0;">📖 How to Use the MM-RAG Slide Assistant</h3>

<hr style="border-color:#e0e6f0; margin:12px 0 18px 0;">

<h4 style="color:#003865;">🚀 Getting Started</h4>
<ol>
  <li><b>Click "Load System"</b> in the sidebar. This loads the AI models (takes ~30–60 seconds the first time).</li>
  <li><b>Upload your slides</b> using the "Upload New Slides" panel — accepts <code>PDF</code>, <code>PNG</code>, <code>JPG</code>.</li>
  <li><b>Click "Index Uploaded Files"</b> to process them. Each page is OCR'd, captioned, and embedded.</li>
  <li><b>Ask questions</b> in the chat box at the bottom of the page.</li>
</ol>

<hr style="border-color:#e0e6f0; margin:12px 0 18px 0;">

<h4 style="color:#003865;">💬 Asking Questions</h4>
<p>Type your question naturally in the chat box. Examples:</p>
<ul>
  <li><i>"What is the purchase price?"</i></li>
  <li><i>"What are the three end markets shown in the pie chart?"</i></li>
  <li><i>"How many employees are in R&amp;D?"</i></li>
  <li><i>"List all sensor types added to the automotive portfolio."</i></li>
  <li><i>"What does TOM stand for?"</i></li>
</ul>
<p>The system retrieves the most relevant slides, reads both their text and visuals, then generates an answer grounded in what is actually on the slides.</p>

<hr style="border-color:#e0e6f0; margin:12px 0 18px 0;">

<h4 style="color:#003865;">🎯 Retrieval Settings (Sidebar)</h4>
<table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
  <tr style="background:#f0f4fa;">
    <td style="padding:8px 12px; font-weight:700; width:38%;">Top-K Slides</td>
    <td style="padding:8px 12px;">How many slides are fetched per question. <b>3 is recommended.</b> Higher = more context but slower. Set to 1 only for speed testing.</td>
  </tr>
  <tr>
    <td style="padding:8px 12px; font-weight:700;">Text vs Image Weight</td>
    <td style="padding:8px 12px;">
      Balances how much the retriever trusts slide text (OCR) vs slide visuals (image similarity).<br>
      • <b>High text (70–90%)</b>: best for text-heavy decks with bullet points and numbers.<br>
      • <b>High image (10–40%)</b>: better when slides are diagram or chart-heavy with little text.<br>
      • Default is <b>70% text / 30% image</b>.
    </td>
  </tr>
</table>

<hr style="border-color:#e0e6f0; margin:12px 0 18px 0;">

<h4 style="color:#003865;">📊 Reading the Source Cards</h4>
<p>After each answer, the system shows which slides it retrieved. Each card shows:</p>
<ul>
  <li><b>Fused score</b> — combined relevance score (text + image). Higher = more relevant.</li>
  <li><b>Text score</b> — how well the slide's OCR text matched your question.</li>
  <li><b>Image score</b> — how well the slide's visual matched your question.</li>
  <li><b>Slide type</b> — "Visual slide" (diagram/chart) or "Text slide" (bullets/paragraphs). This affects how the AI reads it: visual slides prioritise the caption; text slides prioritise OCR.</li>
</ul>

<hr style="border-color:#e0e6f0; margin:12px 0 18px 0;">

<h4 style="color:#003865;">🔄 Maintenance</h4>
<table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
  <tr style="background:#f0f4fa;">
    <td style="padding:8px 12px; font-weight:700; width:38%;">♻️ Re-caption All Slides</td>
    <td style="padding:8px 12px;">Re-runs the AI captioning on every indexed slide using the latest improved prompt. Run this once after updating the system. Takes a few minutes.</td>
  </tr>
  <tr>
    <td style="padding:8px 12px; font-weight:700;">🗑️ Clear Chat History</td>
    <td style="padding:8px 12px;">Clears the conversation. Does not affect the slide index.</td>
  </tr>
</table>

<hr style="border-color:#e0e6f0; margin:12px 0 18px 0;">

<h4 style="color:#003865;">💡 Tips for Better Answers</h4>
<ul>
  <li>Be specific — <i>"What is the CY26 revenue estimate?"</i> works better than <i>"Tell me about revenue."</i></li>
  <li>For chart questions, mention the chart type: <i>"pie chart"</i>, <i>"bar chart"</i>, etc.</li>
  <li>For multi-slide questions, set Top-K to 4 or 5.</li>
  <li>If the wrong slide is retrieved, try re-phrasing with keywords that appear in the correct slide.</li>
  <li>After uploading a new set of slides, always click <b>Re-caption All Slides</b> for best accuracy.</li>
</ul>

</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Gate: system must be loaded
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.backend_loaded:
    st.info("👈 Click **Load System** in the sidebar to initialise the models.")
    st.stop()

backend = st.session_state.backend
slides  = backend.list_slides()

if not slides:
    st.warning(
        "No slides are indexed yet. Either place images in `mmrag_store/pages/` "
        "and reload, or upload files using the sidebar."
    )
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Chat history
# ─────────────────────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "result" in msg:
            show_sources(msg["result"])

# ─────────────────────────────────────────────────────────────────────────────
# Chat input
# ─────────────────────────────────────────────────────────────────────────────
query = st.chat_input(f"Ask a question about your slides (Top-K = {st.session_state.top_k})…")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving slides and generating answer…"):
            result = backend.ask(
                query,
                top_k=st.session_state.top_k,
                text_weight=st.session_state.text_weight / 100.0,
                image_weight=(100 - st.session_state.text_weight) / 100.0,
            )

        answer = result.get("answer", "No answer generated.")
        st.markdown(answer)
        show_sources(result)

    st.session_state.messages.append({
        "role":    "assistant",
        "content": answer,
        "result":  result,
    })