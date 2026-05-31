Perp.de – Software-Based Finish Camera
===

This is a Python-based high-speed image assembly system, simulating a virtual slit camera for finish-line evaluation and similar applications.

---

Requirements
---

- Python 3.10+
- [Poetry](https://python-poetry.org/) for dependency and environment management

---

Setup & Usage
---

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

   To enable the experimental AI boattip detection:
   ```bash
   poetry install --extras ai
   ```
   If the AI extras are installed, AI detection is available automatically (no extra flag needed).
   Enable/disable it at runtime via the 🤖 button in the web interface.

3. **Generate HTTPS certificates** (required for HTTP/2):
   ```bash
   ./bin/gen_certificate.sh
   ```

4. **Run the app**:
   ```bash
   poetry run python main.py
   ```

5. **Access the web interface** (if not disabled):
   - The web server starts automatically by default
   - Runs over HTTPS on port **5001**
   - Visit: [https://localhost:5001](https://localhost:5001)

---

Command-Line Options
---

The application supports a variety of options to control its behavior:

- `outdir`: Output directory for images and metadata (default: `./data`)
- `--preview`: Show preview windows while capturing; optionally specify modes: `live`, `final`, `raw`, `ai_input_image`, `raw_ai_input_image`, `ai_output_image` (default when flag is set without values: `live` + `raw`)
- `--left-to-right`: Set direction of movement (default: right-to-left)
- `--time-span`: Duration in seconds per image (default: 10)
- `--fps`: Frames per second to request from the camera (default: 30)
- `--slot-width`: Width in pixels per frame column (default: 2)
- `--resolution`: Camera resolution (e.g. `hd`, `fullhd`, `4k`, ...)
- `--video-capture-index`: Index of the camera to use (default: 0)
- `--no-stamp-time`: Disable timestamp overlay on output images
- `--stamp-fps`: Show actual FPS on output images
- `--test-mode`: Generate a fixed number of synthetic test images and exit
- `--webp-quality`: WebP output quality (default: 90)
- `--no-capture`: Skip camera capture (e.g. for webserver-only mode)
- `--no-webserver`: Skip starting the web interface
- `--ai-overlap`: Overlap between consecutive AI input images in percent (default: 25)
- `--debug`: Enable debug logging

---

Listing Available Cameras
---

To find the right `--video-capture-index` for your camera:

**Linux** (`sudo apt install v4l-utils`):
```bash
v4l2-ctl --list-devices
```

**macOS** (built-in):
```bash
system_profiler SPCameraDataType
```

OpenCV numbers cameras starting at 0 in the order they appear in the output.

---

Linux Notes
---

If you prefer manual installation of system-level packages (e.g. for use outside of Poetry):

```bash
sudo apt install python3-opencv python3-numpy python3-quart
```

---

Development
---

- Core modules are located in `finishcam/`
- Image capturing, frame assembly, previewing, and web interface are decoupled via a publish-subscribe hub.
- Asynchronous execution and thread handling is done with `asyncio.to_thread()` and `asyncio.wait()`
