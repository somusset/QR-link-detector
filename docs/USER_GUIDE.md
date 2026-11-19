# QR Link Detector — full user and technical guide

**Documented version:** 0.4.1. This guide describes the supplied source, not a proposed future feature.

## 1. Purpose and scope

QR Link Detector is a Windows system-tray utility for recognizing QR codes displayed on a screen and offering their decoded HTTP(S) destinations as clickable links. It does **not** integrate with Zoom, Teams, PowerPoint, or a browser. It works on screen pixels and therefore can also be used with slides, PDFs, and videos.

## 2. Running the app

Use `python qr_link_detector.py` in an environment with `requirements.txt` installed, or launch a Windows executable built with PyInstaller. The program creates a `QApplication` and `QSystemTrayIcon`, without opening a main window. Double-click the tray icon for a manual scan; right-click it for the menu. **Ctrl+Alt+Q** is registered as a global shortcut by `pynput`.

The tray icon is gray when automatic scanning is idle and green while automatic scanning is active. Quitting from the tray menu stops scanning and releases the shortcut listener.

## 3. Tray menu

| Item | Action |
| --- | --- |
| Scan now | Thorough one-time scan of the current target |
| Start automatic detection | Start a session for 30, 60, 120, 240, or 480 minutes |
| Stop automatic detection | Stop the periodic scanning timer |
| Recent QR codes (last hour) | View decoded URLs, timestamps and sources |
| Settings / select window | Set scan target, interval, and indicator duration |
| Quit | Close the app and clear its in-memory state |

Automatic sessions cannot exceed eight hours. Stopping detection does not immediately remove recently displayed indicators or erase history.

## 4. Scanning modes

### Automatic detection — lightweight

The default scan interval is two seconds, configurable from one to ten seconds. The app captures the target screen region, then runs OpenCV's QR-code detector over the original image. It attempts both multi-code and single-code decoding. If a scan is already processing, overlapping scans are skipped.

### On-demand detection — thorough

Double-clicking the tray icon, choosing **Scan now**, or pressing **Ctrl+Alt+Q** starts a thorough scan. After the normal fast pass, the worker splits the screenshot into overlapping 640 × 640-pixel tiles with 480-pixel strides, tries grayscale detection, and retries each tile enlarged 2×. This helps with small QR codes but uses more processing power. The full thorough pass runs even when a larger QR code was found on the initial pass. Work is performed in a `QThread` to keep the Qt interface responsive.

If a manual scan is requested while another scan is running, one pending manual request is queued.

### Decoded content

Only strings with an `http` or `https` scheme and a hostname are accepted. Other QR payloads, such as plain text, Wi-Fi credentials, or custom application URI schemes, are ignored. Duplicate URLs in a single scan are merged.

## 5. Clickable indicators

For every **distinct URL** found, the application creates or refreshes a small numbered clickable indicator beside the QR code. A single URL appearing in multiple codes is treated as one link, not multiple separate indicators. Each indicator has its own minimum visibility timer, default three seconds and configurable from one to thirty seconds. A repeated detection refreshes that URL's timer and position.

Indicators are temporarily hidden during screen capture to prevent the application from scanning its own overlays, then restored if their visibility deadlines have not expired. Their placement can be imperfect with multiple monitors, unusual display scaling, or QR codes near screen edges. Closely spaced indicators may overlap.

Clicking an indicator displays a confirmation dialog with the full URL. Only after confirmation is the default browser opened.

## 6. One-hour history

Every successfully decoded HTTP(S) URL is recorded in a dictionary in memory, with its last detection time and source label. A repeated detection updates the entry rather than adding a duplicate. The maintenance timer expires entries once they are older than 60 minutes since their **most recent** detection.

Open **Recent QR codes (last hour)** to view the newest entries first. Select an entry and choose **Open selected** or **Copy URL**. Double-clicking an entry also opens its confirmation dialog. **Clear history** immediately empties the history. List refreshes preserve selection when possible. No history is saved to disk and no entries persist after quitting.

## 7. Selecting what to scan

In Settings, choose **Entire desktop (all monitors)** or one of the currently visible top-level application windows. The selected-window option does not use an application API or capture hidden content: it reads the rectangle occupied by the window **as visible on the desktop**. If another window covers it, those covering pixels can be scanned instead. Minimized, closed, and entirely off-screen selected windows cannot be scanned.

The window selection is made from a list of visible window titles and Windows handles. If the selected window closes, choose a new target.

## 8. Privacy and security model

- No background screen scanning takes place when idle, except in response to an explicit manual request.
- Automatic scanning starts only when the user chooses a duration, and stops at its deadline or when stopped manually.
- Screenshots are held in memory for processing; this program does not intentionally save screenshots or transmit them.
- URL history remains in RAM only and is automatically expired.
- The global hotkey listener recognizes the registered shortcut; the program does not store typed keystrokes.
- The app does not automatically navigate to decoded URLs; it asks for confirmation.
- There is no telemetry or account integration in the supplied code.

**Limitations:** The software is not a security sandbox or a guarantee of confidential processing by the operating system, third-party libraries, or a managed endpoint. A malicious QR code can still point to a phishing site; review the destination. The application may capture sensitive visible content during a scan even though it does not save the screenshot. Respect workplace policies.

## 9. Settings and defaults

| Setting | Default | Range |
| --- | --- | --- |
| Scan target | Entire desktop | Desktop or selected visible window |
| Automatic interval | 2 seconds | 1–10 seconds |
| Minimum indicator visibility | 3 seconds | 1–30 seconds |
| Automatic session | User-selected | 30 min, 1 h, 2 h, 4 h, 8 h |
| History lifetime | 60 minutes since last detection | Fixed |

Settings are not persisted to a file in v0.4.1. Restarting the application restores defaults.

## 10. Implementation overview

- **PySide6 / Qt:** tray icon, menus, settings dialog, history window, indicators, maintenance timers and confirmation dialogs.
- **MSS:** screen capture of the virtual desktop or visible selected-window rectangle.
- **OpenCV:** QR detection and decoding.
- **NumPy:** screenshot pixel arrays and QR corner coordinates.
- **pynput:** global Ctrl+Alt+Q shortcut.
- **ctypes / Windows API:** enumerate windows and obtain their screen rectangles.
- **QThread:** process QR decoding away from the GUI thread.
- **webbrowser:** open a user-confirmed URL in the system browser.

### Processing sequence

1. User triggers a manual scan or a timed automatic scan fires.
2. Qt indicators are temporarily hidden; MSS captures the selected screen region.
3. Screenshot pixels are converted from BGRA to BGR.
4. A background `ScanWorker` runs fast detection; manual mode also runs the tiled/enlarged passes.
5. URLs are validated, deduplicated, and mapped to screen positions.
6. The controller updates in-memory history and shows/refreshes one indicator per distinct URL.
7. Maintenance removes expired indicators and history entries, and stops timed sessions at their deadlines.

## 11. Build and distribution

Install dependencies with `python -m pip install -r requirements.txt`, then run `build.bat`. It uses PyInstaller `--onefile --windowed` and places `QRLinkDetector.exe` in `dist`. Build on Windows and test the packaged application on the intended Windows version and display configuration. A packaged executable is not automatically code-signed; managed computers may restrict unsigned applications.

For development and troubleshooting, prefer `python qr_link_detector.py` in a terminal so warning messages remain visible. A Qt DPI awareness warning may occur even when the tray app starts normally. OpenCV can warn about QR ECI encoding support, which may affect decoding of some codes.

## 12. Known limitations

- Small, blurry, heavily stylized, or briefly displayed codes can be missed, especially in automatic mode.
- Automatic scanning only uses the fast pass; use manual mode for thorough detection.
- QR codes containing non-web payloads are not surfaced.
- Multiple identical URLs produce one indicator.
- Overlay placement may be imperfect with display scaling and multiple monitors.
- A selected-window scan cannot see obscured content.
- A scan may briefly use noticeable CPU, especially on-demand across large/multiple displays.
- No persistent settings or URL history.
- No automated cross-machine compatibility test suite is included.

## 13. Troubleshooting

**App appears stuck after starting:** look in the system tray's hidden-icons menu. The terminal remains occupied while the app runs.

**Qt DPI awareness warning:** often nonfatal. Confirm the icon appears before investigating further.

**Code not detected:** try the manual scan, enlarge the presentation, and check that the code is actually visible and sharp.

**No button but a URL in history:** indicators are temporary; use history to open the link.

**Wrong scan area:** check Settings and bring the selected window into view.

**Global shortcut does not work:** another app may have reserved Ctrl+Alt+Q; use the tray menu instead.

**Unexpected browser destination:** cancel the confirmation and inspect the full URL; do not assume QR codes are trustworthy.

**Crash in packaged build:** reproduce with `python qr_link_detector.py` to see terminal diagnostics; ensure the same source version and dependencies were used for packaging.

## 14. Future enhancements (not implemented)

Possible future work includes persistent settings, optional performance logging, automated tests, overlay collision avoidance, optional screenshot-region selection, and signed release binaries. These are **ideas**, not existing v0.4.1 features.

## AI provenance and licensing

The source code and initial documentation were generated using OpenAI ChatGPT from requirements and feedback supplied by the project initiator. The initiator conducted Windows testing and requested iterative bug fixes and usability changes. AI generation does not substitute for independent review; contributions and security audits are welcome.

The project is distributed under **GNU GPL v3.0 only (GPL-3.0-only)**. See the repository `LICENSE` file for the complete terms. This license permits commercial use but places copyleft obligations on distribution of covered software.

**Project status:** This is an independent personal project created outside the maintainer’s professional responsibilities, without institutional affiliation. Copyright (C) 2026 Sophie Musset applies to copyrightable human-authored contributions; AI-generated portions may have a different copyright status under applicable law.
