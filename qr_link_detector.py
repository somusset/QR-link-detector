"""QR Link Detector — local, opt-in QR detection for Windows.

Install: pip install -r requirements.txt
Run:     python qr_link_detector.py

No screenshots or URLs are saved to disk or transmitted by this program.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timedelta
import sys
import time
import webbrowser
from urllib.parse import urlsplit

import cv2
import mss
import numpy as np
from pynput import keyboard
from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QAction, QColor, QCursor, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton,
    QSpinBox, QSystemTrayIcon, QVBoxLayout, QWidget,
)

if sys.platform != 'win32':
    raise SystemExit('This application is intended for Windows.')

user32 = ctypes.windll.user32
user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsWindow.argtypes = [wintypes.HWND]

# Qt configures its own DPI awareness. Avoid setting it here first,
# because Windows may reject Qt's subsequent attempt to configure scaling.


@dataclass
class Detection:
    url: str
    last_seen: datetime
    source: str


def windows() -> list[tuple[int, str]]:
    """Enumerate ordinary visible top-level windows, excluding our own."""
    found = []
    CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @CALLBACK
    def visit(hwnd, _):
        if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.strip()
                if title and not title.startswith('QR Link Detector'):
                    found.append((int(hwnd), title))
        return True

    user32.EnumWindows(visit, 0)
    return found


def window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    if not user32.IsWindow(hwnd) or user32.IsIconic(hwnd):
        return None
    r = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    if r.right <= r.left or r.bottom <= r.top:
        return None
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def valid_url(value: str) -> bool:
    """Only offer HTTP(S) links, never executable or custom URI schemes."""
    try:
        p = urlsplit(value.strip())
        return p.scheme.lower() in ('http', 'https') and bool(p.hostname)
    except ValueError:
        return False


def icon(active: bool) -> QIcon:
    """Draw a distinctive tray icon without bundling any image files."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor('#16824b' if active else '#64748b'), 6))
    for x, y in ((10, 10), (38, 10), (10, 38)):
        p.drawRect(x, y, 16, 16)
    p.fillRect(40, 40, 8, 8, QColor('#16824b' if active else '#64748b'))
    p.fillRect(51, 51, 6, 6, QColor('#16824b' if active else '#64748b'))
    p.end()
    return QIcon(pix)


class Bridge(QObject):
    """Safely forward events from the hotkey listener thread into Qt."""
    scan_requested = Signal()


class LinkBadge(QWidget):
    """Small clickable indicator; each QR code gets its own independent widget."""
    def __init__(self, open_callback, label="1"):
        super().__init__(None, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle('QR Link Detector indicator')
        self.url = ''
        self.open_callback = open_callback
        self.button = QPushButton(f'🔗 {label} · Open link', self)
        self.button.setStyleSheet('QPushButton {background:#e8f4ff; color:#123a62; '
                                  'border:1px solid #3178bd; border-radius:8px; '
                                  'padding:7px 11px; font-weight:bold;}')
        self.button.clicked.connect(lambda: self.open_callback(self.url))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.addWidget(self.button)
        self.adjustSize()

    def place(self, url: str, x: int, y: int):
        self.url = url
        self.button.setToolTip(url)
        # Qt widget positions use logical pixels on scaled displays.
        screen = QGuiApplication.screenAt(QPoint(x, y)) or QGuiApplication.primaryScreen()
        ratio = screen.devicePixelRatio() if screen else 1.0
        geo = screen.geometry() if screen else QRect(0, 0, 1920, 1080)
        px, py = round(x / ratio), round(y / ratio)
        px = max(geo.left(), min(px, geo.right() - self.width()))
        py = max(geo.top(), min(py, geo.bottom() - self.height()))
        self.move(px, py)
        self.show()


class HistoryDialog(QDialog):
    def __init__(self, app_controller):
        super().__init__()
        self.controller = app_controller
        self.setWindowTitle('QR Link Detector — Recent QR codes')
        self.resize(670, 380)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel('Detected URLs from the last 60 minutes (stored only in memory).'))
        self.items = QListWidget()
        lay.addWidget(self.items)
        # Double-clicking a history entry opens it without needing a button.
        self.items.itemDoubleClicked.connect(lambda item: self.controller.open_url(item.data(Qt.ItemDataRole.UserRole)))
        self._displayed_rows = None
        buttons = QHBoxLayout()
        for label, callback in (
            ('Open selected', self.open_selected),
            ('Copy URL', self.copy_selected),
            ('Clear history', self.clear),
            ('Close', self.close),
        ):
            b = QPushButton(label)
            b.clicked.connect(callback)
            buttons.addWidget(b)
        lay.addLayout(buttons)
        self.refresh()

    def selected_url(self):
        item = self.items.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def refresh(self):
        """Update history without discarding the user's current selection.

        The maintenance timer calls this once per second. Rebuilding the list
        unconditionally would clear the selected row just after it was clicked.
        """
        self.controller.expire_history()
        records = sorted(self.controller.history.values(),
                         key=lambda d: d.last_seen, reverse=True)
        rows = tuple((d.url, d.last_seen, d.source) for d in records)

        # Avoid touching the list if nothing visible has changed.
        if rows == self._displayed_rows:
            return

        selected_url = self.selected_url()
        self.items.clear()
        restored_item = None
        for d in records:
            item = QListWidgetItem(f'{d.last_seen:%H:%M:%S}  |  {d.source}\n{d.url}')
            item.setData(Qt.ItemDataRole.UserRole, d.url)
            self.items.addItem(item)
            if d.url == selected_url:
                restored_item = item

        if restored_item is not None:
            self.items.setCurrentItem(restored_item)
        self._displayed_rows = rows

    def open_selected(self):
        if self.selected_url():
            self.controller.open_url(self.selected_url())

    def copy_selected(self):
        if self.selected_url():
            QApplication.clipboard().setText(self.selected_url())

    def clear(self):
        self.controller.history.clear()
        self.refresh()


class SettingsDialog(QDialog):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle('QR Link Detector — Settings')
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel('Automatic scan target:'))
        self.target = QComboBox()
        self.target.addItem('Entire desktop (all monitors)', None)
        for hwnd, title in windows():
            self.target.addItem(title[:100], hwnd)
        idx = self.target.findData(controller.target_hwnd)
        self.target.setCurrentIndex(max(0, idx))
        lay.addWidget(self.target)
        lay.addWidget(QLabel('Scanning interval (seconds):'))
        self.interval = QSpinBox()
        self.interval.setRange(1, 10)
        self.interval.setValue(controller.interval_seconds)
        lay.addWidget(self.interval)
        lay.addWidget(QLabel('Minimum link indicator visibility (seconds):'))
        self.badge_duration = QSpinBox()
        self.badge_duration.setRange(1, 30)
        self.badge_duration.setValue(controller.badge_duration_seconds)
        lay.addWidget(self.badge_duration)
        lay.addWidget(QLabel('Tip: select the Zoom window for less screen exposure.\n'
                             'Covered or minimized windows cannot be scanned.'))
        save = QPushButton('Save settings')
        save.clicked.connect(self.save)
        lay.addWidget(save)

    def save(self):
        self.controller.target_hwnd = self.target.currentData()
        self.controller.interval_seconds = self.interval.value()
        self.controller.badge_duration_seconds = self.badge_duration.value()
        if self.controller.active:
            self.controller.scan_timer.start(self.controller.interval_seconds * 1000)
        self.accept()


class ScanWorker(QThread):
    """Decode a captured image away from Qt's GUI thread.

    Capturing is done only after an explicit request or while a timed session
    is active. The worker never reads the screen and never saves image data.
    """
    completed = Signal(object, object, str, bool, object)

    def __init__(self, frame, region, source, manual):
        super().__init__()
        self.frame = frame
        self.region = region
        self.source = source
        self.manual = manual

    @staticmethod
    def decode(image, detector):
        results = []
        try:
            ok, decoded, points, _ = detector.detectAndDecodeMulti(image)
            if ok and points is not None:
                results.extend((url.strip(), corners) for url, corners in zip(decoded, points)
                               if valid_url(url))
        except cv2.error:
            pass
        # Always try single-code detection too: Multi sometimes misses small QR codes.
        try:
            url, points, _ = detector.detectAndDecode(image)
            if valid_url(url) and points is not None:
                results.append((url.strip(), points[0]))
        except cv2.error:
            pass
        return results

    def run(self):
        found = {}
        try:
            detector = cv2.QRCodeDetector()
            height, width = self.frame.shape[:2]

            def check(image, left=0, top=0, scale=1):
                for url, corners in self.decode(image, detector):
                    # Map coordinates from scaled/tiled image to full screenshot.
                    corners = np.asarray(corners, dtype=np.float32) / scale
                    corners[:, 0] += left
                    corners[:, 1] += top
                    found.setdefault(url, corners)

            # Fast scan: one pass over the original image.
            check(self.frame)

            if self.manual:
                # Thorough scan only on demand. Tiling avoids scaling an entire
                # multi-monitor screenshot, and overlap catches QR codes at edges.
                tile = 640
                stride = 480
                for top in range(0, height, stride):
                    for left in range(0, width, stride):
                        crop = self.frame[top:min(top + tile, height),
                                          left:min(left + tile, width)]
                        if crop.size == 0:
                            continue
                        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                        # First try unscaled grayscale, then 2x enlargement.
                        check(gray, left, top)
                        enlarged = cv2.resize(gray, None, fx=2, fy=2,
                                              interpolation=cv2.INTER_CUBIC)
                        check(enlarged, left, top, 2)
            self.completed.emit(list(found.items()), self.region,
                                self.source, self.manual, None)
        except Exception as exc:
            self.completed.emit([], self.region, self.source, self.manual, str(exc))


class Controller(QObject):
    MAX_HISTORY = timedelta(hours=1)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.active = False
        self.end_monotonic = 0.0
        self.target_hwnd = None
        self.interval_seconds = 2
        self.badge_duration_seconds = 3
        # Each URL owns a separate indicator and expiration deadline.
        # The monotonic clock is unaffected by wall-clock changes.
        self.badges: dict[str, LinkBadge] = {}
        self.badge_deadlines: dict[str, float] = {}
        self.badge_positions: dict[str, tuple[int, int]] = {}
        self.history: dict[str, Detection] = {}
        self.worker = None
        self.pending_manual = False
        self.history_dialog = None
        self.bridge = Bridge()
        self.bridge.scan_requested.connect(self.scan_once)
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.auto_scan)
        self.maintenance = QTimer()
        self.maintenance.timeout.connect(self.maintain)
        self.maintenance.start(1000)
        self.tray = QSystemTrayIcon(icon(False))
        self.tray.setToolTip('QR Link Detector — idle')
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
        self.menu.aboutToShow.connect(self.build_menu)
        self.tray.activated.connect(self.tray_clicked)
        self.tray.show()
        self.build_menu()
        # Global hotkey: Ctrl+Alt+Q. Listener never captures keystroke content.
        self.hotkeys = keyboard.GlobalHotKeys({'<ctrl>+<alt>+q': self.bridge.scan_requested.emit})
        self.hotkeys.start()
        self.app.aboutToQuit.connect(self.cleanup)

    def tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.scan_once()

    def build_menu(self):
        self.menu.clear()
        a = self.menu.addAction('Scan now  (Ctrl+Alt+Q or double-click)')
        a.triggered.connect(self.scan_once)
        if self.active:
            remaining = max(0, int((self.end_monotonic - time.monotonic()) / 60) + 1)
            status = self.menu.addAction(f'Automatic detection active — ~{remaining} min left')
            status.setEnabled(False)
            stop = self.menu.addAction('Stop automatic detection')
            stop.triggered.connect(self.stop)
        else:
            submenu = self.menu.addMenu('Start automatic detection')
            for minutes, name in ((30, '30 minutes'), (60, '1 hour'), (120, '2 hours'),
                                  (240, '4 hours'), (480, '8 hours')):
                a = submenu.addAction(name)
                a.triggered.connect(lambda checked=False, m=minutes: self.start(m))
        self.menu.addSeparator()
        self.menu.addAction('Recent QR codes (last hour)', self.show_history)
        self.menu.addAction('Settings / select window', self.show_settings)
        self.menu.addSeparator()
        self.menu.addAction('Quit', self.app.quit)

    def start(self, minutes):
        self.end_monotonic = time.monotonic() + min(minutes, 480) * 60
        self.active = True
        self.tray.setIcon(icon(True))
        self.tray.setToolTip('QR Link Detector — automatic detection ACTIVE')
        self.scan_timer.start(self.interval_seconds * 1000)
        self.auto_scan()

    def stop(self):
        self.active = False
        self.scan_timer.stop()
        # Stopping scanning does not invalidate a recently detected link.
        self.tray.setIcon(icon(False))
        self.tray.setToolTip('QR Link Detector — idle')

    def maintain(self):
        self.expire_history()
        # Expire each link independently; another link can remain visible.
        for url, deadline in list(self.badge_deadlines.items()):
            if time.monotonic() >= deadline:
                badge = self.badges.pop(url, None)
                if badge is not None:
                    badge.hide()
                    badge.deleteLater()
                self.badge_deadlines.pop(url, None)
                self.badge_positions.pop(url, None)
        if self.active and time.monotonic() >= self.end_monotonic:
            self.stop()
        if self.history_dialog and self.history_dialog.isVisible():
            self.history_dialog.refresh()

    def expire_history(self):
        cutoff = datetime.now() - self.MAX_HISTORY
        self.history = {u: d for u, d in self.history.items() if d.last_seen > cutoff}

    def capture(self):
        """Capture selected window rectangle or entire desktop into RAM only.

        The window option crops the visible desktop; it does NOT read pixels from
        behind other windows. Hide overlays during capture to avoid self-detection.
        """
        # Temporarily hide ALL indicators to keep them out of screenshots.
        # Their independent deadlines continue running while capture occurs.
        visible_urls = [url for url, badge in self.badges.items()
                        if badge.isVisible()]
        for url in visible_urls:
            self.badges[url].hide()
        try:
            return self._capture_pixels()
        finally:
            now = time.monotonic()
            for url in visible_urls:
                badge = self.badges.get(url)
                position = self.badge_positions.get(url)
                if badge and position and now < self.badge_deadlines.get(url, 0):
                    badge.place(url, *position)

    def _capture_pixels(self):
        """Capture pixels while the link badge is temporarily hidden."""
        with mss.MSS() as sct:
            if self.target_hwnd is None:
                region = dict(sct.monitors[0])  # all physical monitors
                source = 'Desktop'
            else:
                rect = window_rect(self.target_hwnd)
                if rect is None:
                    raise RuntimeError('Selected window is closed or minimized. Choose another in Settings.')
                x, y, w, h = rect
                # Clamp to virtual desktop; off-screen windows must not crash mss.
                virtual = sct.monitors[0]
                left = max(x, virtual['left'])
                top = max(y, virtual['top'])
                right = min(x + w, virtual['left'] + virtual['width'])
                bottom = min(y + h, virtual['top'] + virtual['height'])
                if right <= left or bottom <= top:
                    raise RuntimeError('Selected window is outside the visible desktop.')
                region = {'left': left, 'top': top, 'width': right-left, 'height': bottom-top}
                source = next((t for h, t in windows() if h == self.target_hwnd), 'Selected window')
            shot = np.asarray(sct.grab(region))
            # OpenCV accepts 8-bit BGR; mss returns BGRA.
            return cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR), region, source

    def scan_once(self):
        self.perform_scan(manual=True)

    def auto_scan(self):
        if not self.active or time.monotonic() >= self.end_monotonic:
            self.stop()
            return
        self.perform_scan(manual=False)

    def perform_scan(self, manual):
        # Never run overlapping scans. A manual request takes priority and is
        # queued if an automatic scan is currently decoding.
        if self.worker is not None:
            if manual:
                self.pending_manual = True
            return
        try:
            frame, region, source = self.capture()
        except Exception as exc:
            if manual:
                QMessageBox.warning(None, 'QR Link Detector', str(exc))
            else:
                self.stop()
                self.tray.showMessage('Detection stopped', str(exc),
                                      QSystemTrayIcon.MessageIcon.Warning, 5000)
            return
        worker = ScanWorker(frame, region, source, manual)
        self.worker = worker
        worker.completed.connect(self.scan_completed)
        worker.finished.connect(self.worker_finished)
        worker.start()

    def scan_completed(self, found, region, source, manual, error):
        if error:
            if manual:
                QMessageBox.warning(None, 'QR Link Detector', error)
            else:
                self.stop()
                self.tray.showMessage('Detection stopped', error,
                                      QSystemTrayIcon.MessageIcon.Warning, 5000)
            return
        now = datetime.now()
        for url, _ in found:
            self.history[url] = Detection(url, now, source)
        # Display one independent clickable badge for EVERY detected URL.
        # Repeated detection refreshes only that URL's timer and position.
        if found and (manual or self.active):
            now_mono = time.monotonic()
            for url, corners in found:
                x = region['left'] + int(np.max(corners[:, 0])) + 8
                y = region['top'] + int(np.min(corners[:, 1]))
                badge = self.badges.get(url)
                if badge is None:
                    # Numbers help distinguish links on slides with several codes.
                    # Reuse the same badge if the same URL appears again.
                    badge = LinkBadge(self.open_url, str(len(self.badges) + 1))
                    self.badges[url] = badge
                self.badge_positions[url] = (x, y)
                self.badge_deadlines[url] = now_mono + self.badge_duration_seconds
                badge.place(url, x, y)
        elif manual and not found:
            self.tray.showMessage('QR Link Detector', 'No QR-code URL detected.',
                                  QSystemTrayIcon.MessageIcon.Information, 2500)

    def worker_finished(self):
        worker = self.worker
        self.worker = None
        if worker is not None:
            worker.deleteLater()
        if self.pending_manual:
            self.pending_manual = False
            QTimer.singleShot(0, self.scan_once)

    def open_url(self, url):
        if not valid_url(url):
            return
        # Display the actual destination and require confirmation before opening.
        response = QMessageBox.question(None, 'Open QR link?',
            f'Open this link in your default browser?\n\n{url}',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if response == QMessageBox.StandardButton.Yes:
            webbrowser.open(url)

    def show_history(self):
        if self.history_dialog is None:
            self.history_dialog = HistoryDialog(self)
        self.history_dialog.refresh()
        self.history_dialog.show()
        self.history_dialog.raise_()
        self.history_dialog.activateWindow()

    def show_settings(self):
        SettingsDialog(self).exec()

    def cleanup(self):
        self.stop()
        self.hotkeys.stop()
        # Let any in-progress decoding finish before Qt destroys the thread.
        if self.worker is not None:
            self.worker.wait()
        for badge in self.badges.values():
            badge.hide()
        self.badges.clear()
        self.badge_deadlines.clear()
        self.badge_positions.clear()
        self.tray.hide()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('QR Link Detector')
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, 'QR Link Detector', 'Windows system tray is unavailable.')
        return 1
    controller = Controller(app)
    # Keep controller alive for the entire Qt event loop.
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
