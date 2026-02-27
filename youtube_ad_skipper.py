"""
YouTube Ad Skipper - automatyczne pomijanie reklam na YouTube
Wymagania: pip install selenium webdriver-manager

Uruchomienie:
    1. Uruchom cmd w Windows, tryb admina
    2. Jesli nie posiadasz jeszcze zainstalowanej biblioteki ktora program wymaga
        wykonaj instalacje bibliotek jeden raz :
        "pip install selenium webdriver-manager"
    3. Uruchom program w zapisanej lokalizacji : 
    "python youtube_ad_skipper.py"
    - jesli chcesz uruchomic z odpowiednim filmem :
    python youtube_ad_skipper.py --url "https://www.youtube.com/watch?v=XXXX"

    Uruchomi sie osobne okno chrome. Dalej wystarczy juz tylko ogladac :)
"""

import time
import argparse
import logging
import subprocess
import os

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Zainstaluj wymagane biblioteki:")
    print("  pip install selenium webdriver-manager")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# Selektory przycisku "Pomiń reklamę" (tylko konkretne klasy, bez wildcard)
SKIP_BUTTON_SELECTORS = [
    ".ytp-ad-skip-button-modern",
    ".ytp-ad-skip-button",
    ".ytp-skip-ad-button",
]


import shutil

# ... (rest of imports)

def find_chrome_executable():
    """Próbuje znaleźć ścieżkę do pliku wykonywalnego Chrome."""
    common_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
            
    # Spróbuj znaleźć w PATH
    path_from_shutil = shutil.which("chrome") or shutil.which("google-chrome")
    if path_from_shutil:
        return path_from_shutil
        
    return None

# Stały profil – dane logowania są zapamiętywane między sesjami
PROFILE_DIR = r"C:\Users\-\AppData\Local\YTSkipper"
CHROME_EXE = find_chrome_executable()
DEBUG_PORT = 9222


def launch_chrome() -> subprocess.Popen:
    """Uruchamia Chrome normalnie (bez automatyzacji) z włączonym remote debugging."""
    if not CHROME_EXE or not os.path.exists(CHROME_EXE):
        raise FileNotFoundError(f"Nie znaleziono Chrome. Upewnij się, że jest zainstalowany.")
    return subprocess.Popen([
        CHROME_EXE,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://www.youtube.com",
    ])


def connect_driver() -> webdriver.Chrome:
    """Podłącza Selenium do już działającego Chrome przez remote debugging."""
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def try_click_skip_button(driver) -> bool:
    """Próbuje znaleźć i kliknąć przycisk 'Pomiń reklamę'. Zwraca True jeśli kliknięto."""
    for selector in SKIP_BUTTON_SELECTORS:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for btn in buttons:
                # Sprawdź czy przycisk ma rozmiar > 0 (faktycznie widoczny)
                size = btn.size
                if btn.is_displayed() and btn.is_enabled() and size["width"] > 0 and size["height"] > 0:
                    try:
                        # Najpierw spróbuj prawdziwy klik (ActionChains)
                        ActionChains(driver).move_to_element(btn).click().perform()
                    except Exception:
                        # Fallback: bezpośredni .click()
                        btn.click()
                    log.info(f"✅ Kliknięto 'Pomiń reklamę' (selektor: {selector})")
                    time.sleep(2)  # daj YouTube czas na przetworzenie kliknięcia
                    return True
        except Exception:
            continue
    return False


def is_ad_playing(driver) -> bool:
    """Sprawdza czy aktualnie gra reklama – tylko przez klasy playera (najbardziej wiarygodne)."""
    try:
        player = driver.find_element(By.ID, "movie_player")
        classes = player.get_attribute("class") or ""
        return "ad-showing" in classes or "ad-interrupting" in classes
    except Exception:
        return False


def mute_ad(driver):
    """Wycisza reklamę gdy nie można jej pominąć."""
    try:
        driver.execute_script("""
            var video = document.querySelector('video');
            if (video) video.muted = true;
        """)
    except Exception:
        pass


def unmute(driver):
    """Przywraca dźwięk po reklamie."""
    try:
        driver.execute_script("""
            var video = document.querySelector('video');
            if (video) video.muted = false;
        """)
    except Exception:
        pass


def watch_for_ads(driver, check_interval: float = 0.8):
    """
    Główna pętla monitorowania – działa w tle i pomija reklamy.
    Przerwij przez Ctrl+C.
    """
    log.info("🎬 Monitorowanie reklam aktywne. Wciśnij Ctrl+C aby zatrzymać.\n")
    ad_was_playing = False

    while True:
        try:
            if is_ad_playing(driver):
                if not ad_was_playing:
                    log.info("📢 Wykryto reklamę...")
                    ad_was_playing = True

                skipped = try_click_skip_button(driver)
                if not skipped:
                    mute_ad(driver)  # wycisz jeśli nie można pominąć
            else:
                if ad_was_playing:
                    log.info("✔️  Reklama zakończona, przywracam dźwięk.")
                    unmute(driver)
                    ad_was_playing = False

            time.sleep(check_interval)

        except WebDriverException as e:
            if "no such window" in str(e).lower():
                log.info("Okno przeglądarki zostało zamknięte. Kończę.")
                break
            log.warning(f"WebDriver error: {e}")
            time.sleep(2)

        except KeyboardInterrupt:
            log.info("\nZatrzymano przez użytkownika.")
            break


def main():
    parser = argparse.ArgumentParser(description="YouTube Ad Skipper")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.8,
        help="Częstotliwość sprawdzania w sekundach (domyślnie: 0.8)"
    )
    args = parser.parse_args()

    log.info("🚀 Uruchamianie YouTube Ad Skipper...")
    log.info("🌐 Otwieram Chrome...")
    chrome_proc = launch_chrome()

    print()
    print("=" * 55)
    print("  Zaloguj się do YouTube w otwartym oknie Chrome.")
    print("  (Jeśli jesteś już zalogowany, możesz pominąć ten krok)")
    print()
    input("  Naciśnij ENTER gdy będziesz gotowy do monitorowania...")
    print("=" * 55)
    print()

    log.info("🔌 Podłączam do przeglądarki...")
    time.sleep(1)
    driver = connect_driver()

    try:
        log.info("ℹ️  Przejdź do wybranego filmu lub playlisty.\n")
        watch_for_ads(driver, check_interval=args.interval)
    finally:
        # Nie zamykamy Chrome przez driver.quit() – tylko odłączamy Selenium
        try:
            driver.service.stop()
        except Exception:
            pass
        log.info("Zakończono monitorowanie. Chrome pozostaje otwarty.")


if __name__ == "__main__":
    main()
