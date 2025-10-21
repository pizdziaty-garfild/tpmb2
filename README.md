# TPMB2 - Enhanced Telegram Periodic Message Bot

🤖 **Zaawansowana wersja bota Telegram z GUI, systemem menu, komendami administracyjnymi i zabezpieczeniami.**

## 🎆 Nowe funkcje (vs TPMB basic)

✨ **System menu z przyciskami inline**
- Menu powitalne dla użytkowników
- Informacje o właścicielu bota
- Podgląd wiadomości
- Szyfrowany czat z operatorem
- System pomocy i nawigacji

🛡️ **Bezpieczeństwo i stabilność**
- Szyfrowane przechowywanie tokenów
- Komunikacja HTTPS/TLS
- Synchronizacja czasu NTP
- Odporność na błędy i crashe
- Zaawansowane logowanie

📱 **Komendy administracyjne przez Telegram**
- `/start` - uruchom bota
- `/stop` - zatrzymaj bota
- `/message` - edycja wiadomości
- `/interval` - ustawienie interwału
- `/groups` - zarządzanie grupami
- `/operator` - ustawienie operatora
- `/status` - status bota

🖥️ **GUI do zarządzania**
- Graficzny interfejs Windows
- Start/stop bota jednym kliknięciem
- Edycja konfiguracji
- Podgląd logów w czasie rzeczywistym
- Zarządzanie grupami

🎨 **Rich text formatting**
- **Pogrubienie**, *kursywa*, `kod`
- Zmienne w wiadomościach: {timestamp}, {date}
- HTML/Markdown parsing
- Emoji i ozdobniki

## 📥 Instalacja

### Windows - Automatyczna instalacja
1. **Pobierz** najnowsze wydanie z [Releases](https://github.com/pizdziaty-garfild/tpmb2/releases)
2. **Ściągnij** plik `install_tpmb2.bat` z sekcji Assets
3. **Uruchom** `install_tpmb2.bat` jako Administrator (zalecane)
4. **Postępuj** zgodnie z instrukcjami instalatora
5. **Uruchom** GUI: `python main.py`

### Instalacja ręczna
```bash
git clone https://github.com/pizdziaty-garfild/tpmb2.git
cd tpmb2
pip install -r requirements.txt
python main.py
```

## 📁 Struktura projektu

```
tpmb2/
├── main.py                    # Główny launcher z GUI
├── requirements.txt           # Zależności Python
├── install_tpmb2.bat          # Instalator Windows
├── bot/
│   ├── __init__.py
│   ├── core.py                # Logika bota z async/await
│   ├── commands.py            # Komendy administracyjne
│   ├── menus.py               # System menu i przycisków
│   ├── formatting.py          # Rich text formatting
│   └── security.py            # HTTPS/TLS i bezpieczeństwo
├── gui/
│   ├── __init__.py
│   └── main_window.py         # Interfejs graficzny
├── utils/
│   ├── __init__.py
│   ├── config.py              # Zarządzanie konfiguracją
│   ├── logger.py              # System logowania
│   └── time_sync.py           # Synchronizacja NTP
├── config/
│   ├── settings.json          # Ustawienia (zaszyfrowane)
│   └── groups.json            # Lista grup
└── logs/
    ├── bot.log                # Główne logi
    └── error.log              # Logi błędów
```

## ⚙️ Pierwsze uruchomienie

### 1. Konfiguracja przez GUI
1. **Uruchom:** `python main.py`
2. **Token:** W zakładce "Konfiguracja" wprowadź token bota
3. **Wiadomość:** Ustaw treść wiadomości (obsługuje zmienne i formatowanie)
4. **Grupy:** W zakładce "Grupy" dodaj ID grup docelowych
5. **Właściciel:** Ustaw informacje o sobie
6. **Start:** Kliknij "Uruchom Bota"

### 2. Komendy administracyjne
Po uruchomieniu bota możesz zarządzać nim przez Telegram:

```
/start          - Uruchom periodyczne wysyłanie
/stop           - Zatrzymaj periodyczne wysyłanie
/message tekst  - Zmień wiadomość
/interval 30    - Ustaw interwał na 30 minut
/groups add -100123  - Dodaj grupę
/groups remove -100123 - Usuń grupę
/operator 12345      - Ustaw operatora
/status         - Pokaż status bota
```

### 3. Menu dla użytkowników
Każdy kto napisze do bota otrzyma menu z opcjami:
- ℹ️ Informacje o właścicielu
- 📄 Zobacz aktualną wiadomość
- 🔒 Szyfrowany czat z operatorem
- ❓ Pomoc

## 📊 Zaawansowane funkcje

### Rich text formatting
```
**pogrubienie** -> pogrubienie
*kursywa* -> kursywa
`kod` -> kod
~~przekreślenie~~ -> przekreślenie
__podkreślenie__ -> podkreślenie

Zmienne:
{timestamp} -> 2025-10-21 23:30:00
{date} -> 2025-10-21
{time} -> 23:30:00
```

### Zabezpieczenia
- **Tokeny zaszyfrowane** - AES-256 encryption
- **HTTPS/TLS** - Wszystkie połączenia zabezpieczone
- **Walidacja wejść** - Ochrona przed injection
- **Audit logi** - Pełne śledzenie działań
- **Synchronizacja NTP** - Dokładny czas niezależnie od systemu

### Monitoring
- **GUI dashboard** - Status w czasie rzeczywistym
- **Rotacyjne logi** - Automatyczne archiwizowanie
- **Error tracking** - Szczegółowe raporty błędów
- **Performance metrics** - Statystyki wydajności

## 📋 Wymagania

- **Python 3.8+**
- **System:** Windows 10+ (GUI), Linux/macOS (CLI)
- **Pakiety:** patrz `requirements.txt`
- **Opcjonalnie:** Uprawnienia administratora (dla pełnej funkcjonalności NTP)

## 🔧 Rozwązywanie problemów

### GUI nie uruchamia się
```bash
# Sprawdź czy tkinter jest dostępny
python -c "import tkinter"

# Zainstaluj brakujące pakiety
pip install -r requirements.txt
```

### Bot nie łączy się z Telegram
1. Sprawdź token w GUI -> Konfiguracja
2. Sprawdź połączenie internetowe
3. Zobacz logi w GUI -> Logi

### Problemy z synchronizacją czasu
- Uruchom jako Administrator (Windows)
- Sprawdź dostęp do serwerów NTP
- Zobacz `logs/error.log`

### Błędy uprawnien
- Bot musi być administratorem w grupach
- ID grupy musi być prawidłowe (format: -100...)
- Sprawdź czy grupa nie została usunięta

## 📊 Porównanie z TPMB basic

| Funkcja | TPMB | TPMB2 |
|---------|------|-------|
| Podstawowe wysyłanie | ✅ | ✅ |
| Pliki tekstowe config | ✅ | ❗ JSON + szyfrowanie |
| GUI | ❌ | ✅ |
| Komendy admin | ❌ | ✅ |
| Menu dla użytkowników | ❌ | ✅ |
| Rich text | ❌ | ✅ |
| Zabezpieczenia | Podstawowe | Zaawansowane |
| Synchronizacja NTP | ❌ | ✅ |
| Error handling | Podstawowy | Zaawansowany |
| Logi | Plik tekstowy | Rotacyjne + GUI |

## 🎆 Przyszłość

Planowane funkcje:
- 🔗 Multi-instance management
- 🌐 VPN per-instance
- 📈 Analytics i statystyki
- 📱 Webhook support
- 📊 Database integration
- 🌍 Web dashboard

## 📄 Licencja

Projekt do celów edukacyjnych i testowych.

---

🔗 **Wersja podstawowa:** [TPMB](https://github.com/pizdziaty-garfild/tpmb)  
⭐ **Gwiazdka mile widziana!**