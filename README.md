# YouTube Ad Skipper 🎬

Skrypt w Pythonie automatycznie pomijający reklamy na YouTube.  
Otwiera Chrome z trwałym profilem, dzięki czemu logujesz się tylko raz.

Skrypt należy uruchomic poprzez okno cmd uruchomione w trybie admin. 

## Jak działa

1. Skrypt uruchamia Chrome normalnie (bez śladów automatyzacji)
2. Logujesz się do YouTube (tylko za pierwszym razem)
3. Naciskasz **ENTER** — Selenium podłącza się do okna i zaczyna monitorować
4. Gdy pojawi się reklama z przyciskiem „Pomiń" — klika automatycznie
5. Gdy reklamy nie da się pominąć — wycisza ją i przywraca dźwięk po jej zakończeniu

## Plik youtube_ad_skipper.pyw - okienkowa wersja
To ten sam skrypt w wersji okienkowej. 
Dodawno opcje wyboru czy podczas wycinania reklam i w czasie oczekiwania 
na przycisk POMIN wylaczac dzwiek. Przycisk start uruchamia przegladarke 
z strona YouTube. Samo dzialanie skryptu jest identyczne jak poprzedniej wersji. 


## Wymagania

- Python 3.9+
- Google Chrome (zainstalowany standardowo)

## Instalacja

```bash
pip install selenium webdriver-manager
```

## Użycie

```bash
python youtube_ad_skipper.py
```

Opcjonalne argumenty:

```
--interval FLOAT    Częstotliwość sprawdzania w sekundach (domyślnie: 0.8)
```

Aby zatrzymać monitorowanie: **Ctrl+C** (Chrome pozostaje otwarty)

## Uwagi

- Profil Chrome jest zapisywany w `%LOCALAPPDATA%\YTSkipper` — dane logowania są zachowywane między sesjami
- Skrypt wykrywa reklamy przez klasy CSS playera YouTube (`ad-showing`, `ad-interrupting`)
- Działa z Python 3.14 i Chrome 145+

## Licencja

MIT
