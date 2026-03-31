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
