import sys
import subprocess
import shutil
import os
import re
import glob
import argparse

# Set download directory (uses /mnt/data_btrfs/ if available, otherwise defaults to ./media/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PREFERRED_DIR = "/mnt/data_btrfs/prg/Python/ezmedia/media/"

if os.path.exists(os.path.dirname(PREFERRED_DIR)):
    DOWNLOAD_DIR = PREFERRED_DIR
else:
    DOWNLOAD_DIR = os.path.join(SCRIPT_DIR, "media")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def check_dependencies(should_split=False):
    """Verify required CLI tools are available in PATH."""
    missing = []
    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
    if not shutil.which("gallery-dl"):
        missing.append("gallery-dl")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        missing.append("ffmpeg / ffprobe")
    if should_split and not shutil.which("demucs"):
        missing.append("demucs")
    
    if missing:
        print(f"❌ Missing required tools: {', '.join(missing)}")
        sys.exit(1)


def sanitize_url(url: str) -> str:
    """Convert music.youtube.com to www.youtube.com to bypass client PO token blocks."""
    return re.sub(r'https?://music\.youtube\.com/', 'https://www.youtube.com/', url)


def get_latest_download(before_files):
    """Identifies the newly created media file in DOWNLOAD_DIR."""
    after_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*")))
    new_files = list(after_files - set(before_files))
    
    # Exclude temporary download fragments
    valid_files = [
        f for f in new_files 
        if not f.endswith(".part") and not f.endswith(".ytdl") and os.path.isfile(f)
    ]
    
    if valid_files:
        return max(valid_files, key=os.path.getmtime)
    
    # Fallback to latest modified file overall
    all_files = [f for f in glob.glob(os.path.join(DOWNLOAD_DIR, "*")) if os.path.isfile(f)]
    if all_files:
        return max(all_files, key=os.path.getmtime)
    return None


def download_media(url, pass_cookies=True, force_playlist=False):
    """Downloads media from YouTube or image hosts."""
    clean_url = sanitize_url(url)
    url_lower = clean_url.lower()

    image_sites = ["giphy.com", "imgur.com", "deviantart.com", "pinterest.com", "flickr.com", "artstation.com"]
    before_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*"))

    if any(site in url_lower for site in image_sites):
        tool = "gallery-dl"
        cmd = ["gallery-dl", "--directory", DOWNLOAD_DIR, clean_url]
    else:
        tool = "yt-dlp"
        cmd = [
            "yt-dlp",
            "-P", DOWNLOAD_DIR,
            "-o", "%(title)s [%(id)s].%(ext)s",
            "--no-mtime",
            "--extractor-args", "youtube:player_client=web,android",
            "-f", "bestaudio/best",
        ]

        if shutil.which("deno"):
            cmd.extend(["--js-runtimes", "deno"])
        elif shutil.which("node"):
            cmd.extend(["--js-runtimes", "node"])

        if pass_cookies and shutil.which("firefox"):
            cmd.extend(["--cookies-from-browser", "firefox"])

        if not force_playlist and "list=" in clean_url:
            cmd.append("--no-playlist")

        cmd.append(clean_url)

    print(f"\n🚀 Fetching media via [{tool}]...")
    print(f"🔗 Target: {clean_url}")
    print(f"📁 Saving to: {DOWNLOAD_DIR}\n")

    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Download completed successfully!")
        if tool == "yt-dlp":
            return get_latest_download(before_files)
        return None
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error downloading media: {e}")
        return None


def convert_media(source_file, target_format=None, custom_ffmpeg_args=None):
    """Converts the downloaded file into the requested format."""
    if not source_file or not os.path.exists(source_file):
        print("ℹ️ No input file found to convert.")
        return None

    filename = os.path.basename(source_file)
    base_name, current_ext = os.path.splitext(filename)
    current_ext = current_ext.lower().lstrip(".")

    # Default to .mov if no target specified and no custom args
    if not target_format and not custom_ffmpeg_args:
        target_format = "mov"

    # Skip conversion if file is already in requested format
    if target_format == current_ext and not custom_ffmpeg_args:
        print(f"ℹ️ File is already in .{target_format} format. Skipping conversion.")
        return source_file

    out_ext = target_format if target_format else current_ext
    output_filepath = os.path.join(DOWNLOAD_DIR, f"r_{base_name}.{out_ext}")

    print(f"\n⚙️ Converter: Transcoding '{filename}' -> 'r_{base_name}.{out_ext}'...")

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", source_file]

    # Format Presets
    if target_format == "mp3":
        cmd.extend(["-vn", "-c:a", "libmp3lame", "-b:a", "320k"])
    elif target_format == "mov":
        try:
            cmd_probe = [
                "ffprobe", "-v", "error", "-select_streams", "a:0", 
                "-show_entries", "stream=codec_name", 
                "-of", "default=noprint_wrappers=1", source_file
            ]
            res = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
            codec = res.stdout.strip().split("=")[-1].lower() if res.stdout else ""
        except Exception:
            codec = ""

        if codec in ["opus", "aac"]:
            cmd.extend(["-vcodec", "dnxhd", "-profile:v", "dnxhr_hq", "-acodec", "pcm_s16le", "-ar", "48000"])
        else:
            cmd.extend(["-vcodec", "copy", "-acodec", "pcm_s16le"])
    elif target_format == "mp4":
        cmd.extend(["-vcodec", "libx264", "-acodec", "aac", "-b:a", "192k"])
    elif target_format == "webm":
        cmd.extend(["-c:v", "libvpx-vp9", "-c:a", "libopus"])
    elif target_format == "gif":
        cmd.extend(["-vf", "fps=15,scale=480:-1:flags=lanczos", "-c:v", "gif"])

    # Append custom FFmpeg arguments from -i flag
    if custom_ffmpeg_args:
        cmd.extend(custom_ffmpeg_args.split())

    cmd.append(output_filepath)

    try:
        subprocess.run(cmd, check=True)
        # Remove original download file after successful conversion
        if os.path.exists(output_filepath) and output_filepath != source_file:
            try:
                os.remove(source_file)
            except OSError:
                pass
        print(f"🚀 Saved converted file: r_{base_name}.{out_ext}")
        return output_filepath
    except subprocess.CalledProcessError as e:
        print(f"❌ Conversion failed: {e}")
        return source_file


def split_audio(source_file):
    """Splits audio using Demucs into Vocals, Bass, Drums, and Other stems."""
    if not source_file or not os.path.exists(source_file):
        print("❌ Cannot run stem separation: file not found.")
        return

    filename = os.path.basename(source_file)
    print(f"\n🎛️ AI Stem Splitter: Processing '{filename}'...")
    stems_output_dir = os.path.join(DOWNLOAD_DIR, "stems")
    
    cmd_split = [
        "demucs", "-n", "htdemucs", "-o", stems_output_dir,
        "--filename", "{stem}.{ext}", source_file
    ]

    try:
        subprocess.run(cmd_split, check=True)
        print(f"\n🎛️ Stems successfully created in: {stems_output_dir}/htdemucs/")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during stem separation: {e}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="ezmedia - Lightweight YouTube/Media downloader with conversion & AI stem separation."
    )
    parser.add_argument("url", help="Media or Playlist URL to download")
    
    # Target format flags (Mutually exclusive)
    fmt_group = parser.add_mutually_exclusive_group()
    fmt_group.add_argument("--mov", action="store_true", help="Convert output to DaVinci Resolve-compatible .mov")
    fmt_group.add_argument("--mp3", action="store_true", help="Convert output to 320kbps .mp3 audio")
    fmt_group.add_argument("--mp4", action="store_true", help="Convert output to .mp4 video")
    fmt_group.add_argument("--webm", action="store_true", help="Convert output to .webm video")
    fmt_group.add_argument("--gif", action="store_true", help="Convert output to animated .gif")

    # Custom FFmpeg options
    parser.add_argument("-i", "--ffmpeg-args", type=str, default=None, help="Custom FFmpeg flags to append during conversion")

    # Downloading / Stem options
    parser.add_argument("--split", action="store_true", help="Split audio into Vocals, Bass, Drums, and Other stems using Demucs")
    parser.add_argument("--no-cookies", action="store_true", help="Disable browser cookie extraction (useful for VPNs)")
    parser.add_argument("--playlist", "--list", action="store_true", help="Download full playlist if a playlist parameter is present")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    check_dependencies(should_split=args.split)

# Determine requested format
    target_fmt = None
    if args.mov:
        target_fmt = "mov"
    elif args.mp3:
        target_fmt = "mp3"
    elif args.mp4:
        target_fmt = "mp4"
    elif args.webm:
        target_fmt = "webm"
    elif args.gif:
        target_fmt = "gif"

    downloaded_file = download_media(
        url=args.url,
        pass_cookies=not args.no_cookies,
        force_playlist=args.playlist
    )

    if downloaded_file:
        processed_file = convert_media(
            source_file=downloaded_file,
            target_format=target_fmt,
            custom_ffmpeg_args=args.ffmpeg_args
        )

        if args.split:
            split_audio(processed_file or downloaded_file)
