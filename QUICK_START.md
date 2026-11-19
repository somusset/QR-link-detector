# Quick start — QR Link Detector v0.4.1

## 1. Install (Windows)

Download or clone the repository, then open **Anaconda Prompt**, Command Prompt, or PowerShell in its folder.

**Conda:**

```bat
conda create -n qr_detector python=3.11 -y
conda activate qr_detector
python -m pip install -r requirements.txt
python qr_link_detector.py
```

**Alternatively, standard Python:**

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python qr_link_detector.py
```

If your terminal remains occupied after launching, that is normal: the app runs in the system tray (including the hidden-icons area near the clock).

## 2. Detect a QR code now

Show a QR code on your screen. Double-click the tray icon, select **Scan now**, or press **Ctrl+Alt+Q**. A numbered clickable indicator should appear near each distinct decoded web URL. Click it, inspect the URL, and confirm to open in your browser.

## 3. Enable automatic detection

Right-click the tray icon → **Start automatic detection** → choose **30 minutes**, **1 hour**, **2 hours**, **4 hours**, or **8 hours**. The icon changes to indicate active detection. Stop at any time using **Stop automatic detection**. Automatic detection is lightweight and may miss very small codes; trigger a manual scan when needed.

## 4. Find a missed link

Right-click the tray icon → **Recent QR codes (last hour)**. Select a URL and choose **Open selected** or **Copy URL**, or double-click an entry to open its confirmation dialog. **Clear history** empties the list. History automatically expires one hour after each URL was last detected and is lost when the app closes.

## 5. Configure settings

Right-click → **Settings / select window**. Choose **Entire desktop** or a visible application window; set automatic scanning interval (**1–10 seconds**, default **2**) and minimum indicator visibility (**1–30 seconds**, default **3**). Settings are in-memory for this version and reset when the app restarts.

## 6. Build a Windows executable (optional)

With dependencies installed in the active environment, run `build.bat` or:

```bat
python -m PyInstaller --noconfirm --clean --onefile --windowed --name QRLinkDetector --collect-all cv2 qr_link_detector.py
```

Launch `dist\QRLinkDetector.exe`. It can run without activating Conda. Do not run the Python and `.exe` copies simultaneously: both would use the same global shortcut.

## Troubleshooting

- **Nothing appears after launch:** check hidden tray icons; there is no main window.
- **Qt DPI awareness warning:** it may be nonfatal; confirm whether the tray icon appears.
- **QR code not detected:** enlarge the code, avoid blurring, and use a manual scan (thorough mode).
- **Selected window fails:** bring it to the foreground; a minimized or closed window cannot be captured.
- **No clickable indicator:** check the history to see whether a URL was decoded; indicator visibility is temporary.
- **Antivirus / work policy blocks app:** follow your organization's policies; do not bypass security restrictions.

For more detail see [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## Licensing and AI provenance

This is an AI-generated project developed from human-provided requirements and tested iteratively by the project initiator. See the README for the full disclosure. Distributed under GNU GPL v3.0 only; see `LICENSE`.

This is an independent personal project without institutional affiliation. Copyright (C) 2026 Sophie Musset (copyrightable human-authored contributions); see `COPYRIGHT_NOTICE.txt`.
