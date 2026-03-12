"""
YouTube Ad Skipper - automatyczne pomijanie reklam na YouTube
Wymagania: pip install selenium webdriver-manager.

Opis: Okienkowa wersja tego samego programu co wczesniej pod nazwa 
"youtube_ad_skipper.py" .
Dodano opcje wyciszanmia dzwieku podczas trwania reklamy. 

Uruchomienie:
    dwuklik w windows w youtube_ad_skipper.pyw
"""

import time
import threading
import subprocess
import os
import shutil
import tkinter as tk
from tkinter import scrolledtext

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    import tkinter.messagebox as mb
    mb.showerror("Brak bibliotek", "Zainstaluj wymagane biblioteki:\npip install selenium webdriver-manager")
    exit(1)


# ── Selektory przycisku "Pomiń reklamę" ──────────────────────────────────────
SKIP_BUTTON_SELECTORS = [
    ".ytp-ad-skip-button-modern",
    ".ytp-ad-skip-button",
    ".ytp-skip-ad-button",
]

PROFILE_DIR = os.path.join(os.environ["LOCALAPPDATA"], "YTSkipper")
DEBUG_PORT   = 9222


# ── Chrome utils ─────────────────────────────────────────────────────────────
def find_chrome_executable():
    common_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    return shutil.which("chrome") or shutil.which("google-chrome")


CHROME_EXE = find_chrome_executable()


def launch_chrome():
    if not CHROME_EXE or not os.path.exists(CHROME_EXE):
        raise FileNotFoundError("Nie znaleziono Chrome.")
    subprocess.Popen([
        CHROME_EXE,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        "https://www.youtube.com",
    ])
    time.sleep(6)


def connect_driver():
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    service = Service(ChromeDriverManager().install())
    last_error = None
    for _ in range(15):
        try:
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            last_error = e
            time.sleep(1)
    raise RuntimeError(f"Nie udało się połączyć z Chrome.\n{last_error}")


# ── Logika reklam ─────────────────────────────────────────────────────────────
def try_click_skip_button(driver):
    for selector in SKIP_BUTTON_SELECTORS:
        try:
            for btn in driver.find_elements(By.CSS_SELECTOR, selector):
                size = btn.size
                if btn.is_displayed() and btn.is_enabled() and size["width"] > 0 and size["height"] > 0:
                    try:
                        ActionChains(driver).move_to_element(btn).click().perform()
                    except Exception:
                        btn.click()
                    return True
        except Exception:
            continue
    return False


def is_ad_playing(driver):
    try:
        classes = driver.find_element(By.ID, "movie_player").get_attribute("class") or ""
        return "ad-showing" in classes or "ad-interrupting" in classes
    except Exception:
        return False


def set_mute(driver, muted: bool):
    try:
        val = "true" if muted else "false"
        driver.execute_script(f"var v=document.querySelector('video');if(v)v.muted={val};")
    except Exception:
        pass


# ── GUI ───────────────────────────────────────────────────────────────────────
BG   = "#1a1a2e"
ACC  = "#e94560"
FG   = "#eaeaea"
DARK = "#0f0f1a"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Ad Skipper")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.mute_ads = tk.BooleanVar(value=True)
        self.running  = False
        self.driver   = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        PAD = 16

        # Nagłówek
        tk.Label(self, text="▶  YouTube Ad Skipper",
                 font=("Segoe UI", 14, "bold"), bg=BG, fg=ACC).pack(pady=(PAD, 2))
        tk.Label(self, text="AUTOMATYCZNE POMIJANIE REKLAM",
                 font=("Segoe UI", 9), bg=BG, fg="#666688").pack(pady=(0, PAD))

        # Opcje
        frame = tk.LabelFrame(self, text=" Opcje ", font=("Segoe UI", 9),
                               bg=BG, fg=FG, bd=1, relief="groove", padx=PAD, pady=8)
        frame.pack(fill="x", padx=PAD, pady=(0, PAD))

        tk.Checkbutton(
            frame,
            text="Wyciszaj dźwięk podczas reklam",
            variable=self.mute_ads,
            bg=BG, fg=FG,
            selectcolor="#2a2a4a",
            activebackground=BG, activeforeground=FG,
            font=("Segoe UI", 10),
            cursor="hand2",
        ).pack(anchor="w")

        # Przycisk START/STOP
        self.btn = tk.Button(
            self, text="▶  START",
            font=("Segoe UI", 12, "bold"),
            bg=ACC, fg="#ffffff",
            activebackground="#c73652", activeforeground="#ffffff",
            relief="flat", bd=0, padx=28, pady=10,
            cursor="hand2", command=self._toggle,
        )
        self.btn.pack(pady=(0, PAD))

        # Status
        self.lbl_status = tk.Label(self, text="● Zatrzymany",
                                   font=("Segoe UI", 9, "bold"), bg=BG, fg="#666688")
        self.lbl_status.pack(pady=(0, 6))

        # Log
        self.log_box = scrolledtext.ScrolledText(
            self, width=52, height=11,
            font=("Consolas", 8),
            bg=DARK, fg="#cccccc",
            insertbackground="white",
            relief="flat", bd=0, state="disabled",
        )
        self.log_box.pack(padx=PAD, pady=(0, PAD))
        self.log_box.tag_config("ok",    foreground="#4caf50")
        self.log_box.tag_config("warn",  foreground="#ff9800")
        self.log_box.tag_config("error", foreground="#f44336")
        self.log_box.tag_config("ad",    foreground="#e94560")

    # ── log ───────────────────────────────────────────────────────────────────
    def log(self, msg: str, tag: str = ""):
        ts = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] {msg}\n", tag)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _status(self, text, color):
        self.lbl_status.configure(text=text, fg=color)

    # ── start / stop ──────────────────────────────────────────────────────────
    def _toggle(self):
        if not self.running:
            self.running = True
            self.btn.configure(text="■  STOP", bg="#444466")
            self._status("● Uruchamianie...", "#ff9800")
            threading.Thread(target=self._worker, daemon=True).start()
        else:
            self.running = False

    def _worker(self):
        try:
            self.log("Uruchamiam Chrome...")
            launch_chrome()
            self.log("Chrome gotowy. Zaloguj się do YouTube jeśli trzeba.")
            self.log("Podłączam Selenium...")
            self.driver = connect_driver()
            self.log("Połączono! Monitorowanie aktywne.", "ok")
            self._status("● Aktywny", "#4caf50")
            self._loop()
        except Exception as e:
            self.log(f"BŁĄD: {e}", "error")
            self._status("● Błąd", "#f44336")
        finally:
            self.running = False
            self.btn.configure(text="▶  START", bg=ACC)
            self._status("● Zatrzymany", "#666688")

    def _loop(self):
        ad_was = False
        while self.running:
            try:
                if is_ad_playing(self.driver):
                    if not ad_was:
                        self.log("Wykryto reklamę...", "ad")
                        ad_was = True
                    if try_click_skip_button(self.driver):
                        self.log("Kliknięto 'Pomiń reklamę'.", "ok")
                    elif self.mute_ads.get():
                        set_mute(self.driver, True)
                else:
                    if ad_was:
                        self.log("Reklama zakończona.", "ok")
                        set_mute(self.driver, False)
                        ad_was = False
                time.sleep(0.8)
            except WebDriverException as e:
                if "no such window" in str(e).lower():
                    self.log("Okno Chrome zostało zamknięte.", "warn")
                    break
                self.log(f"WebDriver: {e}", "warn")
                time.sleep(2)

    def _on_close(self):
        self.running = False
        try:
            if self.driver:
                self.driver.service.stop()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
