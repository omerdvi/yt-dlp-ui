import os
import re
import subprocess
import threading
import queue
import streamlit as st
import streamlit.components.v1 as components

# ── Paths ─────────────────────────────────────────────────────────────────────
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
YTDLP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt-dlp.exe")
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_youtube_downloader.png")

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Omer's Youtube Downloader", page_icon="⬇", layout="centered")

# ── Session State Defaults ────────────────────────────────────────────────────
if "downloading" not in st.session_state:
    st.session_state.downloading = False
if "output_lines" not in st.session_state:
    st.session_state.output_lines = []

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Background ────────────────────────────────────────────────────────────── */
[data-testid="stApp"] {
    background: #0a0a1a !important;
}

/* ── Compact spacing ───────────────────────────────────────────────────────── */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 1rem !important;
    max-width: 680px !important;
}

/* ── Hide chrome ───────────────────────────────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; height: 0 !important; }
[data-testid="stStatusWidget"] { display: none !important; }

/* ── Inputs ────────────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #E8E8F0 !important;
    font-size: 0.92rem !important;
    padding: 0.55rem 0.9rem !important;
    transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #6C63FF !important;
    box-shadow: 0 0 0 3px rgba(108,99,255,0.2) !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: rgba(255,255,255,0.25) !important;
}

/* ── Selectboxes ───────────────────────────────────────────────────────────── */
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
    border-color: #6C63FF !important;
    box-shadow: 0 0 0 3px rgba(108,99,255,0.2) !important;
}
div[data-baseweb="popover"] ul, div[data-baseweb="menu"] ul {
    background: #12122a !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
}
div[data-baseweb="popover"] li, div[data-baseweb="menu"] li {
    background: transparent !important;
    color: #E8E8F0 !important;
}
div[data-baseweb="popover"] li:hover, div[data-baseweb="menu"] li:hover {
    background: rgba(108,99,255,0.15) !important;
}
div[data-baseweb="popover"] li[aria-selected="true"], div[data-baseweb="menu"] li[aria-selected="true"] {
    background: rgba(108,99,255,0.2) !important;
}

/* ── Checkbox / Radio ──────────────────────────────────────────────────────── */
[data-testid="stCheckbox"] label, [data-testid="stRadio"] label {
    color: #c0c0d8 !important;
    font-size: 0.88rem !important;
}
[data-testid="stCheckbox"] [aria-checked="true"] span:first-child,
[data-testid="stRadio"] [aria-checked="true"] span:first-child {
    border-color: #6C63FF !important;
    background: #6C63FF !important;
}

/* ── Expander ──────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    color: #9090b0 !important;
    padding: 0.6rem 1rem !important;
}
[data-testid="stExpander"] summary:hover {
    color: #c0c0d8 !important;
}

/* ── Primary Button ────────────────────────────────────────────────────────── */
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #6C63FF, #3B82F6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.55rem 1.2rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 2px 12px rgba(108,99,255,0.25) !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(108,99,255,0.4) !important;
}

/* ── Code block ────────────────────────────────────────────────────────────── */
[data-testid="stCode"] {
    background: rgba(0,0,0,0.3) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
}

/* ── Alerts ─────────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border: none !important;
}
</style>
""", unsafe_allow_html=True)


# ── Custom Progress Card ──────────────────────────────────────────────────────
def progress_card(percent: float, speed: str = "--", eta: str = "--", phase: str = "Downloading"):
    pct = min(max(percent, 0), 100)
    is_done = pct >= 100 and phase == "Complete"
    bar_color = "#22C55E" if is_done else "#6C63FF"
    bar_end = "#16A34A" if is_done else "#06B6D4"
    status_icon = "✓" if is_done else "●"
    status_color = "#22C55E" if is_done else "#6C63FF"
    pulse_class = "" if is_done else "pulse"

    html = f"""
    <style>
        @keyframes shimmer {{
            0% {{ background-position: 200% 0; }}
            100% {{ background-position: -200% 0; }}
        }}
        @keyframes pulseAnim {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .pulse {{ animation: pulseAnim 1.5s ease-in-out infinite; }}
        .card {{
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px;
            padding: 14px 18px;
            font-family: 'Inter', -apple-system, sans-serif;
        }}
        .bar-track {{
            background: rgba(255,255,255,0.06);
            border-radius: 6px;
            height: 8px;
            overflow: hidden;
        }}
        .bar-fill {{
            height: 100%;
            border-radius: 6px;
            background: linear-gradient(90deg, {bar_color}, {bar_end}, {bar_color});
            background-size: 200% 100%;
            animation: shimmer 2.5s linear infinite;
            transition: width 0.4s ease;
        }}
    </style>
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="color:{status_color}; font-size:0.85rem; font-weight:600;" class="{pulse_class}">
                {status_icon} {phase}
            </span>
            <span style="color:#E8E8F0; font-size:1.3rem; font-weight:700;">{pct:.0f}%</span>
        </div>
        <div class="bar-track"><div class="bar-fill" style="width:{pct}%;"></div></div>
        <div style="display:flex; justify-content:space-between; margin-top:8px; color:rgba(255,255,255,0.4); font-size:0.78rem;">
            <span>{speed}</span>
            <span>ETA {eta}</span>
        </div>
    </div>
    """
    return components.html(html, height=105)


# ── UI: Logo & Title ──────────────────────────────────────────────────────────
lc, mc, rc = st.columns([1, 2, 1])
with mc:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_container_width=True)
    else:
        st.markdown("### Omer's Youtube Downloader")
st.markdown("")  # spacer

# ── UI: Hero Row (URL + Download) ─────────────────────────────────────────────
is_downloading = st.session_state.downloading

hero_l, hero_r = st.columns([5, 1.2])
with hero_l:
    url = st.text_input(
        "URL",
        placeholder="Paste a YouTube, Twitter, or video URL...",
        label_visibility="collapsed",
        disabled=is_downloading,
    )
with hero_r:
    go = st.button(
        "Download",
        type="primary",
        use_container_width=True,
        disabled=is_downloading,
    )

# ── UI: Format Row (hidden during download) ───────────────────────────────────
if not is_downloading:
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        media_type = st.selectbox("Type", ["Video", "Audio Only"], label_visibility="collapsed")
    with fc2:
        if media_type == "Video":
            video_format = st.selectbox("Format", ["mp4", "mkv"], label_visibility="collapsed")
        else:
            video_format = "mp4"
            audio_format = st.selectbox("Format", ["mp3", "flac", "wav"], label_visibility="collapsed")
    with fc3:
        if media_type == "Video":
            resolution = st.selectbox("Quality", ["Best", "1080p", "720p", "4K"], label_visibility="collapsed")
        else:
            resolution = "Best"
            # placeholder to keep column alignment
            st.selectbox("Quality", ["Best"], label_visibility="collapsed", disabled=True)
else:
    media_type = "Video"
    video_format = "mp4"
    audio_format = "mp3"
    resolution = "Best"

# ── UI: Settings Expander ─────────────────────────────────────────────────────
with st.expander("⚙ Settings", expanded=False):
    # Row 1: Playlist + Cookies
    sc1, sc2 = st.columns(2)
    with sc1:
        download_playlist = st.checkbox("Download entire playlist")
    with sc2:
        cookie_browser = st.selectbox("Browser cookies", ["None", "chrome", "edge", "firefox"])

    st.divider()

    # Row 2: Subtitles
    dl_subs = st.checkbox("Download subtitles")
    if dl_subs:
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            sub_langs = st.text_input("Languages", value="en", placeholder="en,he")
        with sub_col2:
            embed_subs = st.checkbox("Embed in video file")
    else:
        sub_langs = "en"
        embed_subs = False

    st.divider()

    # Row 3: Metadata & Extras
    mc1, mc2 = st.columns(2)
    with mc1:
        embed_chapters = st.checkbox("Embed chapters")
        embed_thumbnail = st.checkbox("Embed thumbnail")
    with mc2:
        remove_sponsorblock = st.checkbox("Remove SponsorBlock")
        # embed_metadata is always on


# ── Build Command ─────────────────────────────────────────────────────────────
def build_command() -> list[str]:
    cmd: list[str] = [YTDLP_PATH]
    cmd.append("--yes-playlist" if download_playlist else "--no-playlist")
    cmd.append("--newline")
    cmd += ["-o", os.path.join(DOWNLOADS_DIR, "%(playlist_title)s", "%(title)s.%(ext)s")]

    if media_type == "Video":
        height_map = {"Best": None, "4K": 2160, "1080p": 1080, "720p": 720}
        h = height_map[resolution]
        fmt = f"bv*[height<={h}]+ba/b" if h else "bv*+ba/b"
        cmd += ["-f", fmt, "--merge-output-format", video_format]
    else:
        cmd += ["-x", "--audio-format", audio_format, "--audio-quality", "0"]

    if dl_subs:
        cmd += ["--write-subs", "--sub-langs", sub_langs]
        if embed_subs:
            cmd.append("--embed-subs")

    if embed_chapters:
        cmd.append("--embed-chapters")
    if embed_thumbnail:
        cmd.append("--embed-thumbnail")
    cmd.append("--embed-metadata")
    if remove_sponsorblock:
        cmd += ["--sponsorblock-remove", "all"]
    if cookie_browser != "None":
        cmd += ["--cookies-from-browser", cookie_browser]

    cmd.append(url)
    return cmd


# ── Output Reader Thread ──────────────────────────────────────────────────────
def enqueue_output(pipe, q):
    for line in iter(pipe.readline, b""):
        q.put(line.decode(errors="replace"))
    pipe.close()


# ── Download Logic ────────────────────────────────────────────────────────────
if go:
    if not url.strip():
        st.error("Please enter a URL.")
    elif not is_downloading:
        st.session_state.downloading = True
        st.session_state.output_lines = []
        st.rerun()

if is_downloading and not go:
    # This rerun is the actual download execution (go=False prevents re-trigger)
    cmd = build_command()

    progress_placeholder = st.empty()
    log_placeholder = st.empty()

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
    except FileNotFoundError:
        st.error(f"yt-dlp.exe not found at: {YTDLP_PATH}")
        st.session_state.downloading = False
        st.stop()

    q: queue.Queue[str] = queue.Queue()
    t = threading.Thread(target=enqueue_output, args=(proc.stdout, q), daemon=True)
    t.start()

    progress_re = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")
    speed_re = re.compile(r"at\s+(\S+)")
    eta_re = re.compile(r"ETA\s+(\S+)")
    current_pct = 0.0
    current_speed = "--"
    current_eta = "--"
    phase = "Downloading"

    output_lines: list[str] = []

    while proc.poll() is None or not q.empty():
        try:
            line = q.get(timeout=0.1)
            output_lines.append(line)
            st.session_state.output_lines = output_lines

            # Parse progress
            m = progress_re.search(line)
            if m:
                current_pct = float(m.group(1))
                sm = speed_re.search(line)
                em = eta_re.search(line)
                if sm:
                    current_speed = sm.group(1)
                if em:
                    current_eta = em.group(1)
                phase = "Downloading"
            elif current_pct >= 100 and ("[ffmpeg]" in line or "[ExtractAudio]" in line):
                phase = "Processing"

            # Update progress card
            with progress_placeholder.container():
                progress_card(current_pct, current_speed, current_eta, phase)

        except queue.Empty:
            pass

    proc.wait()

    with progress_placeholder.container():
        if proc.returncode == 0:
            progress_card(100, "--", "--", "Complete")
            st.success("Download completed!")
        else:
            progress_card(current_pct, "--", "--", f"Error (code {proc.returncode})")
            st.error(f"Process exited with code {proc.returncode}")

    # Show output log
    with log_placeholder.expander("Output Log", expanded=False):
        st.code("".join(output_lines[-40:]), language="bash")

    st.session_state.downloading = False
