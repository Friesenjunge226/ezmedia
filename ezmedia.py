import sys
import subprocess
import shutil
import os
import re
import glob

# Set download directory
DOWNLOAD_DIR = os.path.expanduser("/mnt/data_btrfs/prg/Python/ezmedia/media/")
if not os.path.exists(os.path.dirname(DOWNLOAD_DIR)):
    DOWNLOAD_DIR = os.path.expanduser("~/ezmedia_downloads/")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def check_dependencies(should_split=False):
    """Verify required CLI tools are available."""
    missing = []
    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
    if not shutil.which("gallery-dl"):
        missing.append("gallery-dl")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        missing.append("ffmpeg/ffprobe")
    if should_split and not shutil.which("demucs"):
        missing.append("demucs")
    
    if missing:
        print(f"❌ Missing required tools: {', '.join(missing)}")
        sys.exit(1)

def sanitize_url(url: str) -> str:
    """Convert music.youtube.com to www.youtube.com to bypass web_music PO token restrictions."""
    return re.sub(r'https?://music\.youtube\.com/', 'https://www.youtube.com/', url)

def download_media(url, pass_cookies=True, force_playlist=False, should_split=False):
    check_dependencies(should_split)
    
    clean_url = sanitize_url(url)
    url_lower = clean_url.lower()

    image_sites = ["giphy.com", "imgur.com", "deviantart.com", "pinterest.com", "flickr.com", "artstation.com"]
    
    if any(site in url_lower for site in image_sites):
        tool = "gallery-dl"
        cmd = [
            "gallery-dl",
            "--directory", DOWNLOAD_DIR,
            clean_url
        ]
    else:
        tool = "yt-dlp"
        cmd = [
            "yt-dlp",
            "-P", DOWNLOAD_DIR,
            "-o", "%(title)s [%(id)s].%(ext)s",
            "--no-mtime",
            "--remote-components", "ejs:github",
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
            latest_video = get_latest_download()
            if latest_video:
                # 1. Always convert for DaVinci Resolve compatibility
                converted_video = convert_media(latest_video)
                
                # 2. Run stem separation if requested
                if should_split:
                    target_for_stems = converted_video if (converted_video and os.path.exists(converted_video)) else latest_video
                    split_audio(target_for_stems)
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error downloading media: {e}")

def get_latest_download():
    """Finds the most recently downloaded video/audio file."""
    video_extensions = ["*.mp4", "*.webm", "*.mkv", "*.mov", "*.m4a", "*.opus", "*.mp3"]
    files = []
    for ext in video_extensions:
        files.extend(glob.glob(os.path.join(DOWNLOAD_DIR, ext)))
        
    if not files:
        return None

    unprocessed = [f for f in files if not os.path.basename(f).startswith("r_")]
    if not unprocessed:
        return None

    return max(unprocessed, key=os.path.getmtime)

def split_audio(source_file):
    """Splits audio using Demucs into Vocals, Bass, Drums, and Other stems."""
    filename = os.path.basename(source_file)
    print(f"\n🎛️ AI Stem Splitter: Processing '{filename}'...")
    
    stems_output_dir = os.path.join(DOWNLOAD_DIR, "stems")
    
    cmd_split = [
        "demucs",
        "-n", "htdemucs",
        "-o", stems_output_dir,
        "--filename", "{stem}.{ext}",
        source_file
    ]

    try:
        subprocess.run(cmd_split, check=True)
        print(f"\n🎛️ Stems successfully created in: {stems_output_dir}/htdemucs/")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during stem separation: {e}")

def convert_media(latest_video):
    """Converts media file for DaVinci Resolve compatibility."""
    filename = os.path.basename(latest_video)
    print(f"\n⚙️ Auto-Converter: Analyzing '{filename}'...")

    try:
        cmd_probe = [
            "ffprobe", "-v", "error", "-select_streams", "a:0", 
            "-show_entries", "stream=codec_name", 
            "-of", "default=noprint_wrappers=1", latest_video
        ]
        res = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
        
        if not res.stdout.strip():
            print("ℹ️ Video has no audio stream. Skipping conversion.")
            return None
            
        codec = res.stdout.strip().split("=")[-1].lower()
        print(f"📊 Audio Codec Detected: {codec.upper()}")

        base_name = os.path.splitext(filename)[0]
        output_filepath = os.path.join(DOWNLOAD_DIR, f"r_{base_name}.mov")

        if codec in ["opus", "aac"]:
            print(f"⚠️ {codec.upper()} codec detected. Converting to DNxHR + PCM-WAV...")
            cmd_convert = [
                "ffmpeg", "-y", "-i", latest_video,
                "-vcodec", "dnxhd", "-profile:v", "dnxhr_hq",
                "-acodec", "pcm_s16le", "-ar", "48000",
                output_filepath
            ]
            subprocess.run(cmd_convert, check=True)
        else:
            print("ℹ️ Codec supported. Remuxing to PCM container...")
            cmd_copy = [
                "ffmpeg", "-y", "-i", latest_video, 
                "-vcodec", "copy", "-acodec", "pcm_s16le", 
                output_filepath
            ]
            subprocess.run(cmd_copy, check=True)

        os.remove(latest_video)
        print(f"🚀 Converted file saved: r_{base_name}.mov")
        return output_filepath

    except subprocess.CalledProcessError as e:
        print(f"❌ Conversion failed: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ezmedia.py <URL> [--playlist] [--split] [--no-cookies]")
        sys.exit(1)

    target_url = sys.argv[1]
    is_playlist = "--playlist" in sys.argv or "--list" in sys.argv
    should_split = "--split" in sys.argv
    use_cookies = "--no-cookies" not in sys.argv

    download_media(target_url, pass_cookies=use_cookies, force_playlist=is_playlist, should_split=should_split)
