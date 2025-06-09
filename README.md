Perp.de – Software-Based Finish Camera
===

This is a Python-based high-speed image assembly system, simulating a virtual slit camera for finish-line evaluation and similar applications.

---

Requirements
---

- Python 3.8+
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
- `--preview`: Show live OpenCV preview windows while capturing
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
- `--debug`: Enable debug logging

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
