```markdown
# ezmedia

`ezmedia` is a lightweight Python command-line utility designed to easily download media from YouTube, YouTube Music, and image platforms without ads. It automatically handles URL sanitization, format conversion for video editors like DaVinci Resolve, and optional AI stem separation.

---

## Features

- **Ad-free YouTube & YouTube Music Downloads**: Downloads tracks or videos using `yt-dlp`.
- **Automatic Audio/Video Processing**: Converts downloaded media into DaVinci Resolve-compatible formats (`.mov` with PCM audio / DNxHR).
- **AI Stem Separation**: Optional splitting of tracks into Vocals, Drums, Bass, and Other using `demucs`.
- **Gallery-dl Integration**: Native support for downloading images/media from popular art and image hosts.
- **Smart URL Sanitization**: Handles `music.youtube.com` URLs automatically to prevent player client errors.

---

## Prerequisites & Dependencies

Ensure you have the following CLI tools installed and accessible in your system `PATH`:

- [Python 3.10+](https://www.python.org/)
- [ffmpeg](https://ffmpeg.org/) & `ffprobe`
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [gallery-dl](https://github.com/mikf/gallery-dl)

### Optional Dependencies
- **[demucs](https://github.com/facebookresearch/demucs)** (Required only if using `--split`):
  ```bash
  pip install demucs numpy soundfile

```

* **JavaScript Engine** (`deno` or `node`): Recommended for resolving YouTube JS challenges.

---

## Usage

Run `ezmedia` using Python directly:

```bash
python3 ezmedia.py <URL> [OPTIONS]

```

### 1. Download a Single Song or Video

To download a single track, pass the direct video URL:

```bash
python3 ezmedia.py "[https://music.youtube.com/watch?v=lzfyoYEGvM0](https://music.youtube.com/watch?v=lzfyoYEGvM0)"

```

> **Note:** If copying a link from a playlist, ensure it doesn't contain a `&list=...` query parameter, or use the `--no-playlist` default behavior.

---

### 2. Download an Entire Playlist

To download a full playlist, use the `--playlist` (or `--list`) flag and provide a clean playlist URL:

```bash
python3 ezmedia.py "[https://music.youtube.com/playlist?list=PLn5e0Y1Qeb40l_zmGU5mMW2RNxWFJQqdJ](https://music.youtube.com/playlist?list=PLn5e0Y1Qeb40l_zmGU5mMW2RNxWFJQqdJ)" --playlist

```

* **Correct Playlist URL**: `https://music.youtube.com/playlist?list=...`
* **Incorrect**: `https://music.youtube.com/watch?v=...&list=...`

---

### 3. AI Stem Separation (`--split`)

To extract individual audio stems (Vocals, Drums, Bass, Other) after downloading, append `--split`:

```bash
python3 ezmedia.py "[https://music.youtube.com/watch?v=f-ap_-wr_ck](https://music.youtube.com/watch?v=f-ap_-wr_ck)" --split

```

*Stems will be generated inside the `media/stems/htdemucs/` directory.*

---

## Command Flags

| Flag | Description |
| --- | --- |
| `--playlist` / `--list` | Forces download of all videos/tracks in a playlist URL. |
| `--split` | Runs Demucs AI stem separation on the downloaded media. |
| `--no-cookies` | Disables extracting Firefox browser cookies (useful when downloading behind a VPN). |

---

## License

Source-available / Personal Use.

```

```
