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
import shutil

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


# Selektory przycisku "Pomiń reklamę"
SKIP_BUTTON_SELECTORS = [
    ".ytp-ad-skip-button-modern",
    ".ytp-ad-skip-button",
    ".ytp-skip-ad-button",
]


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

    path_from_shutil = shutil.which("chrome") or shutil.which("google-chrome")
    if path_from_shutil:
        return path_from_shutil

    return None


# Osobny profil dla skryptu – nie miesza się z normalnym Chrome
PROFILE_DIR = os.path.join(os.environ["LOCALAPPDATA"], "YTSkipper")
CHROME_EXE = find_chrome_executable()
DEBUG_PORT = 9222


def launch_chrome() -> subprocess.Popen:
    """Uruchamia nowe okno Chrome z włączonym remote debugging.
    Używa osobnego profilu (PROFILE_DIR) aby działać jako osobny proces
    nawet gdy inny Chrome jest już otwarty."""
    if not CHROME_EXE or not os.path.exists(CHROME_EXE):
        raise FileNotFoundError("Nie znaleziono Chrome. Upewnij się, że jest zainstalowany.")

    log.info(f"Uruchamiam nowe okno Chrome z remote debugging na porcie {DEBUG_PORT}...")
    proc = subprocess.Popen([
        CHROME_EXE,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        "https://www.youtube.com",
    ])

    log.info("Czekam na uruchomienie Chrome...")
    time.sleep(4)
    return proc


def connect_driver() -> webdriver.Chrome:
    """Podłącza Selenium do już działającego Chrome przez remote debugging."""
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    service = Service(ChromeDriverManager().install())

    last_error = None
    for i in range(15):
        try:
            driver = webdriver.Chrome(service=service, options=options)
            log.info("Polaczono z Chrome!")
            return driver
        except Exception as e:
            last_error = e
            log.info(f"Czekam na Chrome... ({i + 1}/15)")
            time.sleep(1)

    raise RuntimeError(f"Nie udalo sie polaczyc z Chrome po 15 probach.\nOstatni blad: {last_error}")


def try_click_skip_button(driver) -> bool:
    """Próbuje znaleźć i kliknąć przycisk 'Pomiń reklamę'. Zwraca True jeśli kliknięto."""
    for selector in SKIP_BUTTON_SELECTORS:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for btn in buttons:
                size = btn.size
                if btn.is_displayed() and btn.is_enabled() and size["width"] > 0 and size["height"] > 0:
                    try:
                        ActionChains(driver).move_to_element(btn).click().perform()
                    except Exception:
                        btn.click()
                    log.info(f"Kliknieto 'Pomin reklame' (selektor: {selector})")
                    time.sleep(2)
                    return True
        except Exception:
            continue
    return False


def is_ad_playing(driver) -> bool:
    """Sprawdza czy aktualnie gra reklama."""
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
    """Główna pętla monitorowania. Przerwij przez Ctrl+C."""
    log.info("Monitorowanie reklam aktywne. Wcisnij Ctrl+C aby zatrzymac.\n")
    ad_was_playing = False

    while True:
        try:
            if is_ad_playing(driver):
                if not ad_was_playing:
                    log.info("Wykryto reklame...")
                    ad_was_playing = True

                skipped = try_click_skip_button(driver)
                if not skipped:
                    mute_ad(driver)
            else:
                if ad_was_playing:
                    log.info("Reklama zakonczona, przywracam dzwiek.")
                    unmute(driver)
                    ad_was_playing = False

            time.sleep(check_interval)

        except WebDriverException as e:
            if "no such window" in str(e).lower():
                log.info("Okno przegladarki zostalo zamkniete. Koncze.")
                break
            log.warning(f"WebDriver error: {e}")
            time.sleep(2)

        except KeyboardInterrupt:
            log.info("\nZatrzymano przez uzytkownika.")
            break


def main():
    parser = argparse.ArgumentParser(description="YouTube Ad Skipper")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.8,
        help="Czestotliwosc sprawdzania w sekundach (domyslnie: 0.8)"
    )
    args = parser.parse_args()

    log.info("Uruchamianie YouTube Ad Skipper...")
    log.info("Otwieram Chrome...")
    chrome_proc = launch_chrome()

    print()
    print("=" * 55)
    print("  Zaloguj sie do YouTube w otwartym oknie Chrome.")
    print("  (Jesli jestes juz zalogowany, mozesz pominac ten krok)")
    print()
    input("  Nacisnij ENTER gdy bedziesz gotowy do monitorowania...")
    print("=" * 55)
    print()

    log.info("Podlaczam do przegladarki...")
    time.sleep(3)
    driver = connect_driver()

    try:
        log.info("Przejdz do wybranego filmu lub playlisty.\n")
        watch_for_ads(driver, check_interval=args.interval)
    finally:
        try:
            driver.service.stop()
        except Exception:
            pass
        log.info("Zakończono monitorowanie. Chrome pozostaje otwarty.")


if __name__ == "__main__":
    main()
    
