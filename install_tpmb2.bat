@echo off
chcp 65001 >nul
cls

echo.
echo    ████████╗██████╗ ███╗   ███╗██████╗ ██████╗ 
echo    ╚══██╔══╝██╔══██╗████╗ ████║██╔══██╗╚════██╗
echo       ██║   ██████╔╝██╔████╔██║██████╔╝ █████╔╝
echo       ██║   ██╔═══╝ ██║╚██╔╝██║██╔══██╗██╔═══╝ 
echo       ██║   ██║     ██║ ╚═╝ ██║██████╔╝███████╗
echo       ╚═╝   ╚═╝     ╚═╝     ╚═╝╚═════╝ ╚══════╝
echo.
echo    Enhanced Telegram Bot v2.0 - Instalator
echo    =========================================
echo.

net session >nul 2>&1
if %errorLevel% == 0 (
    echo [✓] Administrator - pełna funkcjonalność NTP
) else (
    echo [⚠] Brak uprawnień Administrator - ograniczona synchronizacja czasu
    echo    Zalecamy uruchomienie jako Administrator dla pełnej funkcjonalności
    echo.
)

echo [INFO] Sprawdzanie wymagań systemowych...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [❌] BŁĄD: Python nie jest zainstalowany!
    echo.
    echo Aby kontynuować:
    echo 1. Pobierz Python z https://www.python.org/downloads/
    echo 2. Podczas instalacji zaznacz "Add Python to PATH"
    echo 3. Uruchom ponownie ten instalator
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo [✓] Python %PYTHON_VER% wykryty

pip --version >nul 2>&1
if errorlevel 1 (
    echo [❌] BŁĄD: pip nie jest dostępny!
    echo Reinstaluj Python z opcją pip
    pause
    exit /b 1
)

echo [✓] pip dostępny
echo.

python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [⚠] tkinter niedostępny - GUI może nie działać
    echo Zainstaluj python-tk lub użyj pełnej instalacji Python
) else (
    echo [✓] tkinter dostępny - GUI będzie działać
)

echo.
echo [INFO] Przygotowywanie środowiska wirtualnego...

set /p "venv_choice=Utworzyć izolowane środowisko wirtualne? [Y/n]: "
if /i "%venv_choice%"=="" set "venv_choice=y"
if /i "%venv_choice%"=="n" goto :skip_venv

echo [INFO] Tworzenie środowiska wirtualnego...
python -m venv tpmb2_env

if errorlevel 1 (
    echo [❌] Błąd tworzenia środowiska wirtualnego
    goto :skip_venv
)

echo [✓] Środowisko wirtualne utworzone

echo [INFO] Aktywacja środowiska...
call tpmb2_env\Scripts\activate.bat

if errorlevel 1 (
    echo [⚠] Problem z aktywacją venv - kontynuuję bez niego
    goto :skip_venv
)

echo [✓] Środowisko wirtualne aktywne
echo.

:skip_venv

echo [INFO] Aktualizacja pip...
python -m pip install --upgrade pip --quiet

echo [INFO] Instalacja zależności TPMB2...
echo To może potrwać kilka minut...
echo.

echo    Instalowanie pakietów podstawowych...
pip install python-telegram-bot>=20.7 --quiet
if errorlevel 1 goto :install_error

echo    Instalowanie zabezpieczeń i szyfrowania...
pip install cryptography>=41.0.0 --quiet  
if errorlevel 1 goto :install_error

pip install certifi>=2023.7.22 --quiet
if errorlevel 1 goto :install_error

pip install requests>=2.31.0 --quiet
if errorlevel 1 goto :install_error

echo    Instalowanie synchronizacji czasu...
pip install ntplib>=0.4.0 --quiet
if errorlevel 1 goto :install_error

echo    Instalowanie utilities...
pip install python-dateutil>=2.8.2 --quiet
if errorlevel 1 goto :install_error

echo [✓] Wszystkie zależności zainstalowane!
echo.

echo [INFO] Przygotowywanie struktury projektu...

mkdir bot 2>nul
mkdir utils 2>nul
mkdir gui 2>nul
mkdir config 2>nul
mkdir logs 2>nul

echo # Bot package > bot\__init__.py
echo # Utils package > utils\__init__.py  
echo # GUI package > gui\__init__.py

echo [✓] Struktura katalogów przygotowana
echo.

echo [INFO] Tworzenie pliku requirements.txt...
(
echo # TPMB2 - Enhanced Telegram Bot Requirements
echo.
echo # Core dependencies
echo python-telegram-bot^>=20.7
echo.
echo # Security and encryption
echo cryptography^>=41.0.0
echo certifi^>=2023.7.22
echo requests^>=2.31.0
echo.
echo # Time synchronization
echo ntplib^>=0.4.0
echo.
echo # Utilities
echo python-dateutil^>=2.8.2
echo.
echo # GUI ^(tkinter is built into Python^)
) > requirements.txt

echo [✓] requirements.txt utworzony
echo.

echo [SUCCESS] ======================================
echo [SUCCESS] INSTALACJA ZAKOŃCZONA POMYŚLNIE!
echo [SUCCESS] ======================================
echo.
echo 🎉 TPMB2 Enhanced Bot jest gotowy!
echo.
echo 📁 Następne kroki:
if /i "%venv_choice%"=="y" (
    echo    1. Aktywuj środowisko: tpmb2_env\Scripts\activate.bat
    echo    2. Pobierz pliki z GitHub lub uruchom: python main.py
) else (
    echo    1. Pobierz pliki z GitHub 
    echo    2. Uruchom: python main.py
)
echo.

echo 🔧 Przed pierwszym uruchomieniem:

echo    • Uzyskaj token bota od @BotFather w Telegram

echo    • Przygotuj listę ID grup docelowych

echo    • Opcjonalnie: uruchom ponownie jako Administrator

echo.

echo 📚 Dokumentacja: README.md w repozytorium

echo 💬 GUI pomoże Ci skonfigurować wszystkie ustawienia

echo.

echo 🚀 Powodzenia z TPMB2!
pause
goto :end

:install_error
echo.
echo [❌] BŁĄD PODCZAS INSTALACJI ZALEŻNOŚCI
echo.
echo Możliwe przyczyny:

echo • Brak połączenia z internetem

echo • Firewall blokuje pip

echo • Niewystarczające uprawnienia

echo • Konflikt z innymi pakietami Python

echo.

echo Rozwiązania:

echo • Uruchom instalator jako Administrator

echo • Sprawdź połączenie internetowe

echo • Zainstaluj ręcznie: pip install python-telegram-bot cryptography

echo.
pause
exit /b 1

:end
