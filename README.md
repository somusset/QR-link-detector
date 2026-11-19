# QR Link Detector

**A small, opt-in Windows utility that turns QR codes visible on your screen into clickable links.**

QR Link Detector is useful when a presenter displays a QR code in Zoom, Teams, a slideshow, or a video, but you are already watching on your computer and don't want to scan it with a phone.

The application lives in the Windows system tray. You can request a thorough one-off scan or enable lightweight automatic detection for a limited time. Detected web links appear as clickable indicators and remain accessible in a rolling one-hour history.

> **Status:** v0.4.1. Tested by the project user on Windows; broader compatibility and security testing have not been completed. This repository does not claim affiliation with Zoom or any meeting provider.

**Independent personal project:** QR Link Detector was developed outside the creator’s professional responsibilities and has no institutional affiliation.

## AI-generated project and human oversight

**This project was generated using AI.** QR Link Detector was developed through an iterative collaboration between a human project initiator and OpenAI's ChatGPT. ChatGPT generated the Python application code, documentation, and initial implementation in response to requirements and design choices provided by the project initiator. The project initiator tested the utility on Windows, reported problems, and directed subsequent revisions.

The software has not undergone comprehensive independent security auditing or broad compatibility testing. Its AI-generated origin is disclosed for transparency, not as a guarantee of correctness or safety.

## Features

- **On-demand scan:** double-click the tray icon, choose **Scan now**, or press **Ctrl+Alt+Q**. Uses a thorough detection pass to improve recognition of small QR codes.
- **Timed automatic scanning:** 30 minutes, 1, 2, 4, or 8 hours; automatically stops when time expires.
- **Multiple codes:** a separate clickable indicator for each distinct detected URL.
- **Configurable indicator visibility:** minimum 1–30 seconds; default 3 seconds.
- **Recent links:** in-memory history of URLs detected during the past 60 minutes, with open/copy/clear actions.
- **Selected-window or desktop scanning:** choose a visible window or all monitors.
- **Local processing:** screenshots are processed in memory and are not saved or uploaded by the application.
- **Link confirmation:** only HTTP(S) URLs are offered; you must confirm before opening a link in your browser.

## Requirements

- Windows 10 or 11 (Windows-only implementation).
- Python 3.11 recommended for running from source.
- A Windows system tray; dependencies listed in `requirements.txt`.

## Quick start

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python qr_link_detector.py
```

Or use Conda:

```bat
conda create -n qr_detector python=3.11 -y
conda activate qr_detector
python -m pip install -r requirements.txt
python qr_link_detector.py
```

The app opens in the **system tray**, not in a normal main window. Expand hidden tray icons if needed.

See [QUICK_START.md](QUICK_START.md) for usage and executable-building instructions, and [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for complete documentation.

## Build a standalone Windows executable

After installing requirements, run `build.bat` or:

```bat
python -m PyInstaller --noconfirm --clean --onefile --windowed --name QRLinkDetector --collect-all cv2 qr_link_detector.py
```

Find `dist\QRLinkDetector.exe`. Build it on Windows; PyInstaller does not cross-compile a Windows executable from other operating systems.

## Privacy and security

Scanning is **off by default**. Automatic scanning only begins when requested and has a maximum session length of eight hours. Screenshots are not intentionally written to disk or transmitted over the network. The last-hour URL history exists only in RAM and disappears when the application closes. The app registers a global keyboard shortcut, but does not record typed text.

**Important limitations:** a selected window is scanned by cropping its *visible screen area*; covered or minimized content cannot be read. Automatic scanning uses a fast pass and can miss very small or fleeting QR codes. A decoded URL is not a guarantee that a destination is safe; inspect it before confirming. On a managed computer, follow your organization's screen-capture and software policies.

## Project files

- `qr_link_detector.py` — application source
- `requirements.txt` — Python dependencies
- `run.bat` — run from the current Python environment
- `build.bat` — package with PyInstaller
- `QUICK_START.md` — setup and first use
- `docs/USER_GUIDE.md` — behavior, design, privacy, troubleshooting
- `CONTRIBUTING.md` — development and contribution guidance
- `LICENSE` — GNU General Public License version 3

## Contributing

Bug reports and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). Please do not attach screenshots containing confidential meeting content.

## License

Licensed under the **GNU General Public License v3.0 only (GPL-3.0-only)**; see [LICENSE](LICENSE). Commercial use is permitted, subject to the license terms. Copyright notice: **Copyright (C) 2026 Sophie Musset**, for copyrightable human-authored contributions. AI-generated portions may not independently qualify for copyright protection in every jurisdiction.
