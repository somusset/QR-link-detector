@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name QRLinkDetector --collect-all cv2 qr_link_detector.py
pause
