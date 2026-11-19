# Contributing

Thanks for your interest in QR Link Detector.

## Reporting a problem

Include your Windows version, Python version (or packaged `.exe`), QR Link Detector version, display scaling and number of monitors, the steps to reproduce, and what you expected to happen. **Do not upload confidential meeting screenshots, private URLs, or sensitive screen content.** If possible, reproduce with a public sample QR code.

## Proposing a change

Open an issue first for major behavior changes. Keep pull requests focused and explain any impact on scanning privacy, CPU usage, URL safety, or overlay placement. Avoid adding network calls, disk persistence, or always-on scanning without explicit user opt-in.

## Development

Create a Windows Python environment, install `requirements.txt`, and run `python qr_link_detector.py`. Before submitting, run `python -m py_compile qr_link_detector.py` and manually test the tray menu, on-demand and timed scans, multiple indicators, history selection, and quitting. Automated tests are not yet supplied.

## Licensing

By contributing, you agree that your contributions may be distributed under the repository's GNU GPL v3.0 license. Do not submit third-party code without compatible licensing and attribution.
