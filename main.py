import sys, re, csv
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QComboBox,
    QHBoxLayout, QVBoxLayout, QGridLayout, QPlainTextEdit, QMessageBox,
    QGroupBox, QLineEdit, QFileDialog, QCheckBox
)
import serial
from serial.tools import list_ports

APP_NAME = "HS RADAR SYSTEM X"
BAUD_DEFAULT = 9600

class SerialReader(QThread):
    received = Signal(str)
    failed = Signal(str)

    def __init__(self, port, baud, parent=None):
        super().__init__(parent)
        self.port_name = port
        self.baud = baud
        self.ser = None
        self.keep_running = True

    def run(self):
        try:
            self.ser = serial.Serial(self.port_name, self.baud, timeout=0.25)
            self.received.emit(f"[CONNECTED] {self.port_name} @ {self.baud}")
            while self.keep_running:
                try:
                    raw = self.ser.readline()
                    if raw:
                        self.received.emit(raw.decode("utf-8", errors="replace").strip())
                except Exception as exc:
                    self.failed.emit(str(exc))
                    break
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.received.emit("[DISCONNECTED]")

    def send(self, command):
        if self.ser and self.ser.is_open:
            self.ser.write((command.strip() + "\n").encode("ascii", errors="ignore"))
            self.ser.flush()
            return True
        return False

    def stop(self):
        self.keep_running = False
        self.wait(1500)

class RadarDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(330, 330)
        self.angle = 0
        self.distance = None
        self.target = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(40)

    def advance(self):
        self.angle = (self.angle + 2) % 360
        self.update()

    def set_reading(self, distance=None, angle=None):
        if distance is not None:
            self.distance = distance
            self.target = True
        if angle is not None:
            self.angle = angle % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#06120e"))
        side = min(self.width(), self.height()) - 24
        cx, cy = self.width()/2, self.height()/2
        r = side/2
        p.setPen(QPen(QColor("#155b42"), 1))
        for frac in (0.25, 0.5, 0.75, 1.0):
            p.drawEllipse(int(cx-r*frac), int(cy-r*frac), int(2*r*frac), int(2*r*frac))
        p.drawLine(int(cx-r), int(cy), int(cx+r), int(cy))
        p.drawLine(int(cx), int(cy-r), int(cx), int(cy+r))
        p.setPen(QPen(QColor("#00e58a"), 2))
        import math
        a = math.radians(self.angle)
        ex, ey = cx + r*math.sin(a), cy - r*math.cos(a)
        p.drawLine(int(cx), int(cy), int(ex), int(ey))
        p.setPen(QPen(QColor("#00e58a"), 1))
        p.setFont(QFont("Consolas", 9))
        p.drawText(10, 18, "RADAR SWEEP")
        if self.distance is not None:
            p.setPen(QPen(QColor("#ffcf4a"), 8))
            p.drawPoint(int(cx + r*0.55*math.sin(a)), int(cy - r*0.55*math.cos(a)))
        p.end()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1120, 760)
        self.reader = None
        self.distance = None
        self.angle = None
        self.setStyleSheet("""
            QMainWindow, QWidget { background:#08130f; color:#d7fbe9; }
            QGroupBox { border:1px solid #176044; margin-top:10px; padding:8px; color:#52f0ad; font-weight:bold; }
            QPushButton { background:#103b2c; color:#eafff4; border:1px solid #19a66b; padding:8px; border-radius:5px; }
            QPushButton:hover { background:#176044; }
            QPushButton:disabled { color:#708078; background:#18251f; }
            QComboBox, QLineEdit { background:#101f19; border:1px solid #176044; padding:6px; color:#eafff4; }
            QPlainTextEdit { background:#030a07; color:#9fffc9; border:1px solid #176044; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        header = QHBoxLayout()
        title = QLabel("HS RADAR SYSTEM X")
        title.setStyleSheet("font-size:25px;font-weight:800;color:#36f5a1;")
        self.status = QLabel("● DISCONNECTED")
        self.status.setStyleSheet("color:#ff7979;font-weight:bold;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(QLabel("DEVELOPED BY HIMANSHU SAHU"))
        header.addWidget(self.status)
        root.addLayout(header)

        connection = QGroupBox("HC-05 BLUETOOTH SERIAL CONNECTION")
        c = QHBoxLayout(connection)
        self.port_box = QComboBox()
        self.baud_box = QComboBox()
        self.baud_box.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_box.setCurrentText("9600")
        self.refresh_btn = QPushButton("Refresh COM Ports")
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        c.addWidget(QLabel("COM Port:")); c.addWidget(self.port_box, 2)
        c.addWidget(self.refresh_btn); c.addWidget(QLabel("Baud:")); c.addWidget(self.baud_box)
        c.addWidget(self.connect_btn); c.addWidget(self.disconnect_btn)
        root.addWidget(connection)

        body = QHBoxLayout()
        self.radar = RadarDisplay()
        body.addWidget(self.radar, 3)

        right = QVBoxLayout()
        readings = QGroupBox("LIVE DATA")
        rg = QGridLayout(readings)
        self.distance_label = QLabel("-- cm")
        self.angle_label = QLabel("--°")
        self.target_label = QLabel("WAITING FOR DATA")
        for w in (self.distance_label, self.angle_label, self.target_label):
            w.setStyleSheet("font-size:18px;color:#44f5a5;font-weight:bold;")
        rg.addWidget(QLabel("Distance"),0,0); rg.addWidget(self.distance_label,0,1)
        rg.addWidget(QLabel("Angle"),1,0); rg.addWidget(self.angle_label,1,1)
        rg.addWidget(QLabel("Target"),2,0); rg.addWidget(self.target_label,2,1)
        right.addWidget(readings)

        modes = QGroupBox("OPERATING MODE")
        mg = QGridLayout(modes)
        for i, cmd in enumerate(["AUTO", "MANUAL", "AIR_FORCE", "THERMAL", "ROBOTIC", "NORMAL"]):
            b = QPushButton(cmd.replace("_"," "))
            b.clicked.connect(lambda checked=False, x=cmd: self.send_command(x))
            mg.addWidget(b, i//2, i%2)
        right.addWidget(modes)

        controls = QGroupBox("SERVO / OUTPUT CONTROLS")
        cg = QGridLayout(controls)
        control_cmds = [
            ("LEFT","LEFT"),("CENTER","CENTER"),("RIGHT","RIGHT"),("STOP","STOP"),
            ("GREEN ON","GREEN_ON"),("RED ON","RED_ON"),("YELLOW ON","YELLOW_ON"),
            ("ALL LEDs OFF","ALL_LEDS_OFF"),("BUZZER ON","BUZZER_ON"),("BUZZER OFF","BUZZER_OFF"),
            ("ALL","ALL"),("STATUS","STATUS")
        ]
        for i,(label,cmd) in enumerate(control_cmds):
            b=QPushButton(label)
            b.clicked.connect(lambda checked=False, x=cmd: self.send_command(x))
            cg.addWidget(b,i//3,i%3)
        right.addWidget(controls)
        body.addLayout(right, 4)
        root.addLayout(body, 4)

        log_group = QGroupBox("COMMAND LOG — TX / RX")
        lg = QVBoxLayout(log_group)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        buttons = QHBoxLayout()
        self.clear_btn = QPushButton("Clear Log")
        self.export_btn = QPushButton("Export TXT")
        self.csv_btn = QPushButton("Export CSV")
        self.demo_check = QCheckBox("Demo mode (no hardware commands)")
        buttons.addWidget(self.clear_btn); buttons.addWidget(self.export_btn)
        buttons.addWidget(self.csv_btn); buttons.addStretch(); buttons.addWidget(self.demo_check)
        lg.addWidget(self.log); lg.addLayout(buttons)
        root.addWidget(log_group, 2)

        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.connect_btn.clicked.connect(self.connect_serial)
        self.disconnect_btn.clicked.connect(self.disconnect_serial)
        self.clear_btn.clicked.connect(self.log.clear)
        self.export_btn.clicked.connect(self.export_txt)
        self.csv_btn.clicked.connect(self.export_csv)
        self.refresh_ports()
        self.add_log("Application started. Pair HC-05 in Windows Bluetooth settings first.")

    def add_log(self, message, kind="INFO"):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log.appendPlainText(f"[{stamp}] [{kind}] {message}")

    def refresh_ports(self):
        current = self.port_box.currentText()
        self.port_box.clear()
        ports = list(list_ports.comports())
        for port in ports:
            label = f"{port.device} — {port.description}"
            self.port_box.addItem(label, port.device)
        if current:
            idx = self.port_box.findText(current)
            if idx >= 0: self.port_box.setCurrentIndex(idx)
        if not ports:
            self.port_box.addItem("No COM ports found", "")

    def connect_serial(self):
        if self.demo_check.isChecked():
            self.add_log("Demo mode is enabled; hardware connection is disabled.")
            return
        port = self.port_box.currentData()
        if not port:
            QMessageBox.warning(self, "No COM port", "Pair the HC-05 in Windows settings and refresh COM ports.")
            return
        self.reader = SerialReader(port, int(self.baud_box.currentText()))
        self.reader.received.connect(self.on_received)
        self.reader.failed.connect(self.on_failed)
        self.reader.start()
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.status.setText("● CONNECTING")
        self.status.setStyleSheet("color:#ffd166;font-weight:bold;")

    def disconnect_serial(self):
        if self.reader:
            self.reader.stop()
            self.reader = None
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.status.setText("● DISCONNECTED")
        self.status.setStyleSheet("color:#ff7979;font-weight:bold;")

    def send_command(self, command):
        if self.demo_check.isChecked():
            self.add_log(f"DEMO ONLY — would send: {command}", "DEMO")
            return
        if not self.reader or not self.reader.isRunning():
            self.add_log(f"Not connected; command not sent: {command}", "WARNING")
            return
        if self.reader.send(command):
            self.add_log(command, "TX")
        else:
            self.add_log(f"Send failed: {command}", "ERROR")

    def on_received(self, message):
        self.add_log(message, "RX")
        if message.startswith("[CONNECTED]"):
            self.status.setText("● CONNECTED")
            self.status.setStyleSheet("color:#36f5a1;font-weight:bold;")
        if message.startswith("[DISCONNECTED]"):
            self.status.setText("● DISCONNECTED")
            self.status.setStyleSheet("color:#ff7979;font-weight:bold;")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
        # Optional telemetry format examples: D=15.2,A=90 or DIST=15.2 ANG=90
        dm = re.search(r"(?:D|DIST)\s*=\s*(-?\d+(?:\.\d+)?)", message, re.I)
        am = re.search(r"(?:A|ANG|ANGLE)\s*=\s*(-?\d+(?:\.\d+)?)", message, re.I)
        if dm:
            self.distance = float(dm.group(1))
            self.distance_label.setText(f"{self.distance:.1f} cm")
        if am:
            self.angle = float(am.group(1))
            self.angle_label.setText(f"{self.angle:.0f}°")
        if dm or am:
            self.target_label.setText("DATA RECEIVED")
            self.radar.set_reading(self.distance, self.angle)

    def on_failed(self, error):
        self.add_log(error, "ERROR")
        self.status.setText("● CONNECTION ERROR")
        self.status.setStyleSheet("color:#ff7979;font-weight:bold;")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)

    def export_txt(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save log", "HS_RADAR_LOG.txt", "Text files (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log.toPlainText())
            self.add_log(f"Log exported to {path}")

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save log", "HS_RADAR_LOG.csv", "CSV files (*.csv)")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Log entry"])
                writer.writerows([[line] for line in self.log.toPlainText().splitlines()])
            self.add_log(f"CSV exported to {path}")

    def closeEvent(self, event):
        self.disconnect_serial()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
