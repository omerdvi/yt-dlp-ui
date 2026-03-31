import os
import re
import subprocess
import threading
import queue
import streamlit as st

# Ensure downloads directory exists
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Path to yt-dlp.exe
YTDLP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt-dlp.exe")

st.set_page_config(page_title="YT-DLP UI", page_icon="🎬", layout="centered")

# ── Custom CSS Injection ──────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Page & Background ─────────────────────────────────────────────────────── */
[data-testid="stApp"] {
    background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #0d0d2b 100%) !important;
    background-attachment: fixed !important;
}

.block-container {
    padding-top: 2rem !important;
    max-width: 740px !important;
}

/* ── Hide Streamlit Chrome ─────────────────────────────────────────────────── */
#MainMenu { visibility: hidden; height: 0 !important; }
footer { visibility: hidden; height: 0 !important; }
header { visibility: hidden; height: 0 !important; }
[data-testid="stStatusWidget"] { display: none !important; }

/* ── Page Load Animation ───────────────────────────────────────────────────── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
[data-testid="stAppViewBlockContainer"] {
    animation: fadeInUp 0.6s ease-out both;
}

/* ── Title ─────────────────────────────────────────────────────────────────── */
[data-testid="stHeading"] h1 {
    background: linear-gradient(135deg, #E8E8F0, #6C63FF);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 700 !important;
    letter-spacing: -0.5px !important;
}

/* ── Glassmorphism Cards (Expander) ────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.035) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
    overflow: hidden !important;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(108, 99, 255, 0.3) !important;
    box-shadow: 0 0 24px rgba(108, 99, 255, 0.07) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    color: #c8c8e0 !important;
    padding: 0.8rem 1.2rem !important;
    transition: color 0.2s ease !important;
}
[data-testid="stExpander"] summary:hover {
    color: #E8E8F0 !important;
}
[data-testid="stExpanderDetails"] {
    padding: 0 1.2rem 1rem 1.2rem !important;
}

/* ── Text Input ────────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    color: #E8E8F0 !important;
    font-size: 0.95rem !important;
    padding: 0.6rem 1rem !important;
    transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #6C63FF !important;
    box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.25) !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: rgba(255, 255, 255, 0.3) !important;
}
[data-testid="stTextInput"] label {
    color: rgba(255, 255, 255, 0.55) !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
}

/* ── Text Area (Log Output) ────────────────────────────────────────────────── */
[data-testid="stTextArea"] textarea {
    background: rgba(0, 0, 0, 0.35) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 12px !important;
    color: #a0a0b8 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    line-height: 1.5 !important;
}

/* ── Selectbox / Dropdown ──────────────────────────────────────────────────── */
[data-testid="stSelectbox"] label {
    color: rgba(255, 255, 255, 0.55) !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
    border-color: #6C63FF !important;
    box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.25) !important;
}
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"] ul {
    background: #12122a !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
}
div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li {
    background: transparent !important;
    color: #E8E8F0 !important;
    transition: background 0.15s ease !important;
}
div[data-baseweb="popover"] li:hover,
div[data-baseweb="menu"] li:hover {
    background: rgba(108, 99, 255, 0.15) !important;
}
div[data-baseweb="popover"] li[aria-selected="true"],
div[data-baseweb="menu"] li[aria-selected="true"] {
    background: rgba(108, 99, 255, 0.2) !important;
}

/* ── Radio ─────────────────────────────────────────────────────────────────── */
[data-testid="stRadio"] label {
    color: #c8c8e0 !important;
    font-weight: 500 !important;
    font-size: 0.92rem !important;
    transition: color 0.2s ease !important;
}
[data-testid="stRadio"] label:hover {
    color: #6C63FF !important;
}
[data-testid="stRadio"] [data-baseweb="radio"] span:first-child {
    border-color: rgba(255, 255, 255, 0.2) !important;
    transition: border-color 0.2s ease, background 0.2s ease !important;
}
[data-testid="stRadio"] [aria-checked="true"] span:first-child {
    border-color: #6C63FF !important;
    background: #6C63FF !important;
}

/* ── Checkbox ──────────────────────────────────────────────────────────────── */
[data-testid="stCheckbox"] label {
    color: #c8c8e0 !important;
    font-weight: 500 !important;
    font-size: 0.92rem !important;
    transition: color 0.2s ease !important;
}
[data-testid="stCheckbox"] label:hover {
    color: #E8E8F0 !important;
}
[data-testid="stCheckbox"] [data-baseweb="checkbox"] span:first-child {
    border-color: rgba(255, 255, 255, 0.2) !important;
    border-radius: 6px !important;
    transition: border-color 0.2s ease, background 0.2s ease !important;
}
[data-testid="stCheckbox"] [aria-checked="true"] span:first-child {
    border-color: #6C63FF !important;
    background: #6C63FF !important;
}

/* ── Animated Progress Bar ─────────────────────────────────────────────────── */
@keyframes gradientFlow {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
[data-testid="stProgress"] > div > div {
    background: rgba(255, 255, 255, 0.06) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #6C63FF, #3B82F6, #06B6D4, #6C63FF) !important;
    background-size: 300% 100% !important;
    animation: gradientFlow 3s ease infinite !important;
    border-radius: 10px !important;
    height: 10px !important;
    box-shadow: 0 0 18px rgba(108, 99, 255, 0.35) !important;
    transition: width 0.3s ease !important;
}

/* ── Download Button (CTA) ─────────────────────────────────────────────────── */
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #6C63FF, #3B82F6) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 0.8rem 2rem !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    width: 100% !important;
    letter-spacing: 0.3px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 20px rgba(108, 99, 255, 0.3) !important;
    cursor: pointer !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(108, 99, 255, 0.5) !important;
    background: linear-gradient(135deg, #7B73FF, #4B92F6) !important;
}
[data-testid="stButton"] button[kind="primary"]:active {
    transform: translateY(0) !important;
    box-shadow: 0 2px 12px rgba(108, 99, 255, 0.4) !important;
}

/* ── Code Block (Command Display) ──────────────────────────────────────────── */
[data-testid="stCode"] {
    background: rgba(0, 0, 0, 0.3) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* ── Subheaders ────────────────────────────────────────────────────────────── */
[data-testid="stHeading"] h3 {
    color: #a8a8c8 !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    letter-spacing: 0.3px !important;
    margin-top: 0.5rem !important;
}

/* ── Label Text (Global) ───────────────────────────────────────────────────── */
[data-testid="stWidgetLabel"] p {
    color: rgba(255, 255, 255, 0.55) !important;
    font-weight: 500 !important;
}

/* ── Success / Error Messages ──────────────────────────────────────────────── */
[data-testid="stAlert"][data-baseweb="notification"] {
    border-radius: 12px !important;
    border: none !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🎬 yt-dlp Downloader")

# ── Main Section ──────────────────────────────────────────────────────────────
url = st.text_input("Video / Playlist URL", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns(2)
with col1:
    media_type = st.radio("Media Type", ["Video", "Audio Only"], horizontal=True)
with col2:
    download_playlist = st.checkbox("Download entire playlist", value=False)

# ── Video Settings ────────────────────────────────────────────────────────────
if media_type == "Video":
    st.subheader("Video Settings")
    vc1, vc2 = st.columns(2)
    with vc1:
        resolution = st.selectbox("Resolution", ["Best", "4K", "1080p", "720p"])
    with vc2:
        video_format = st.selectbox("Format", ["mp4", "mkv"])
else:
    resolution = "Best"
    video_format = "mp4"

# ── Audio Settings ────────────────────────────────────────────────────────────
if media_type == "Audio Only":
    st.subheader("Audio Settings")
    audio_format = st.selectbox("Audio Format", ["mp3", "flac", "wav"])
else:
    audio_format = "mp3"

# ── Subtitles ─────────────────────────────────────────────────────────────────
with st.expander("Subtitles"):
    dl_subs = st.checkbox("Download Subtitles")
    sub_langs = st.text_input("Subtitle Languages", value="en", placeholder="e.g. en,he")
    embed_subs = st.checkbox("Embed Subtitles in video file")

# ── Advanced & Metadata ──────────────────────────────────────────────────────
with st.expander("Advanced & Metadata"):
    embed_chapters = st.checkbox("Embed Chapters")
    embed_thumbnail = st.checkbox("Embed Video Thumbnail / Cover Art")
    remove_sponsorblock = st.checkbox("Remove SponsorBlock segments")
    cookie_browser = st.selectbox(
        "Browser Cookies (bypass age-restrictions)",
        ["None", "chrome", "edge", "firefox"],
    )

# ── Build Command ─────────────────────────────────────────────────────────────
def build_command() -> list[str]:
    cmd: list[str] = [YTDLP_PATH]

    # Playlist handling
    cmd.append("--yes-playlist" if download_playlist else "--no-playlist")

    # Force newline for parseable progress output
    cmd.append("--newline")

    # Output template
    cmd += ["-o", os.path.join(DOWNLOADS_DIR, "%(playlist_title)s", "%(title)s.%(ext)s")]

    if media_type == "Video":
        height_map = {"Best": None, "4K": 2160, "1080p": 1080, "720p": 720}
        h = height_map[resolution]
        if h:
            fmt = f"bv*[height<={h}]+ba/b"
        else:
            fmt = "bv*+ba/b"
        cmd += ["-f", fmt, "--merge-output-format", video_format]
    else:
        cmd += ["-x", "--audio-format", audio_format, "--audio-quality", "0"]

    # Subtitles
    if dl_subs:
        cmd += ["--write-subs", "--sub-langs", sub_langs]
        if embed_subs:
            cmd.append("--embed-subs")

    # Advanced / Metadata
    if embed_chapters:
        cmd.append("--embed-chapters")
    if embed_thumbnail:
        cmd.append("--embed-thumbnail")
    cmd.append("--embed-metadata")
    if remove_sponsorblock:
        cmd += ["--sponsorblock-remove", "all"]
    if cookie_browser != "None":
        cmd += ["--cookies-from-browser", cookie_browser]

    # URL must be last
    cmd.append(url)
    return cmd


# ── Real-time Output ─────────────────────────────────────────────────────────
def enqueue_output(pipe, q):
    """Read lines from a pipe and put them into a queue."""
    for line in iter(pipe.readline, b""):
        q.put(line.decode(errors="replace"))
    pipe.close()


# ── Download Handler ─────────────────────────────────────────────────────────
if st.button("⬇ Download", type="primary", use_container_width=True):
    if not url.strip():
        st.error("Please enter a URL.")
    else:
        cmd = build_command()
        st.code(" ".join(cmd), language="bash")

        progress_bar = st.progress(0)
        status_text = st.empty()
        output_area = st.empty()

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )
        except FileNotFoundError:
            st.error(f"yt-dlp.exe not found at: {YTDLP_PATH}")
            st.stop()

        q: queue.Queue[str] = queue.Queue()
        t = threading.Thread(target=enqueue_output, args=(proc.stdout, q), daemon=True)
        t.start()

        progress_re = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")
        speed_eta_re = re.compile(r"at\s+(\S+)\s+ETA\s+(\S+)")
        current_pct = 0.0

        output_lines: list[str] = []
        while proc.poll() is None or not q.empty():
            try:
                line = q.get(timeout=0.1)
                output_lines.append(line)

                m = progress_re.search(line)
                if m:
                    current_pct = float(m.group(1))
                    progress_bar.progress(min(int(current_pct), 100))
                    se = speed_eta_re.search(line)
                    if se:
                        status_text.text(f"Downloading... {current_pct:.1f}%  |  Speed: {se.group(1)}  |  ETA: {se.group(2)}")
                    else:
                        status_text.text(f"Downloading... {current_pct:.1f}%")
                elif current_pct >= 100:
                    if "[ffmpeg]" in line or "[ExtractAudio]" in line:
                        status_text.text("Post-processing...")

                output_area.text_area("Output", "".join(output_lines), height=350)
            except queue.Empty:
                pass

        proc.wait()
        if proc.returncode == 0:
            progress_bar.progress(100)
            status_text.success("Download completed successfully!")
        else:
            status_text.error(f"Process exited with code {proc.returncode}")
