import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

def setup_logger(name: str = 'tpmb2', level: int = logging.INFO) -> logging.Logger:
    """Setup main application logger"""
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Ensure logs directory exists
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler for general logs
    file_handler = logging.FileHandler(
        os.path.join(logs_dir, 'bot.log'), 
        encoding='utf-8', 
        mode='a'
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_format)
    
    # Error file handler
    error_handler = logging.FileHandler(
        os.path.join(logs_dir, 'error.log'), 
        encoding='utf-8', 
        mode='a'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_format)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
    # Log initialization
    logger.info(f"Logger initialized: {name}")
    log_system_info(logger)
    
    return logger

def log_system_info(logger: logging.Logger):
    """Log system and environment information"""
    try:
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        logger.info(f"Executable: {sys.executable}")
        logger.info(f"Working directory: {os.getcwd()}")
        
        # Log package versions
        log_package_versions(logger)
        
    except Exception as e:
        logger.error(f"Failed to log system info: {e}")

def log_package_versions(logger: logging.Logger):
    """Log versions of key packages"""
    packages = [
        'telegram', 'cryptography', 'aiohttp', 'aiohttp_socks', 
        'certifi', 'requests', 'ntplib'
    ]
    
    for package in packages:
        try:
            module = __import__(package)
            version = getattr(module, '__version__', 'unknown')
            logger.info(f"Package {package}: {version}")
        except ImportError:
            logger.warning(f"Package {package}: not installed")
        except Exception as e:
            logger.warning(f"Package {package}: error getting version - {e}")

def create_startup_logger() -> logging.Logger:
    """Create logger specifically for startup errors"""
    logger = logging.getLogger('tpmb2.startup')
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Startup error file handler
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)
    
    startup_handler = logging.FileHandler(
        os.path.join(logs_dir, 'error-startup.log'), 
        encoding='utf-8', 
        mode='a'
    )
    startup_handler.setLevel(logging.DEBUG)
    startup_format = logging.Formatter(
        '%(asctime)s - STARTUP - %(levelname)s - %(message)s'
    )
    startup_handler.setFormatter(startup_format)
    
    logger.addHandler(startup_handler)
    
    return logger

def create_diagnostics_report(config) -> str:
    """Create comprehensive diagnostics report"""
    try:
        logs_dir = 'logs'
        os.makedirs(logs_dir, exist_ok=True)
        
        report_path = os.path.join(logs_dir, f'diagnostics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("TPMB2 Diagnostics Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # System information
            f.write("SYSTEM INFORMATION\n")
            f.write("-" * 20 + "\n")
            f.write(f"Python Version: {sys.version}\n")
            f.write(f"Python Executable: {sys.executable}\n")
            f.write(f"Platform: {sys.platform}\n")
            f.write(f"Working Directory: {os.getcwd()}\n")
            
            # Virtual environment detection
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                f.write(f"Virtual Environment: Yes (prefix: {sys.prefix})\n")
            else:
                f.write("Virtual Environment: No\n")
            f.write("\n")
            
            # Package versions
            f.write("PACKAGE VERSIONS\n")
            f.write("-" * 16 + "\n")
            packages = [
                'telegram', 'cryptography', 'aiohttp', 'aiohttp_socks',
                'certifi', 'requests', 'ntplib', 'tkinter'
            ]
            
            for package in packages:
                try:
                    if package == 'tkinter':
                        import tkinter
                        f.write(f"{package}: {tkinter.TkVersion} (built-in)\n")
                    else:
                        module = __import__(package)
                        version = getattr(module, '__version__', 'unknown')
                        f.write(f"{package}: {version}\n")
                except ImportError:
                    f.write(f"{package}: NOT INSTALLED\n")
                except Exception as e:
                    f.write(f"{package}: ERROR - {e}\n")
            f.write("\n")
            
            # Configuration summary
            f.write("CONFIGURATION SUMMARY\n")
            f.write("-" * 21 + "\n")
            try:
                summary = config.get_config_summary()
                for key, value in summary.items():
                    f.write(f"{key}: {value}\n")
            except Exception as e:
                f.write(f"Error getting config summary: {e}\n")
            f.write("\n")
            
            # Groups details
            f.write("GROUPS DETAILS\n")
            f.write("-" * 14 + "\n")
            try:
                groups = config.get_groups_objects()
                global_interval = config.get_interval_minutes()
                
                if not groups:
                    f.write("No groups configured\n")
                else:
                    for i, group in enumerate(groups, 1):
                        gid = group['id']
                        name = group.get('name', '(no name)')
                        interval = group.get('interval', f'global: {global_interval}')
                        f.write(f"{i}. ID: {gid}, Name: {name}, Interval: {interval}\n")
            except Exception as e:
                f.write(f"Error getting groups: {e}\n")
            f.write("\n")
            
            # Templates details
            f.write("TEMPLATES DETAILS\n")
            f.write("-" * 17 + "\n")
            try:
                templates = config.list_templates()
                active = config.get_active_template_key()
                
                f.write(f"Active Template: {active}\n")
                f.write(f"Available Templates: {', '.join(templates)}\n")
                
                for template in templates:
                    text = config.get_template(template)
                    preview = text[:50] + "..." if len(text) > 50 else text
                    marker = " (ACTIVE)" if template == active else ""
                    f.write(f"  {template}{marker}: {preview}\n")
            except Exception as e:
                f.write(f"Error getting templates: {e}\n")
            f.write("\n")
            
            # Proxy configuration
            f.write("PROXY CONFIGURATION\n")
            f.write("-" * 19 + "\n")
            try:
                proxy = config.get_proxy_config()
                f.write(f"Enabled: {proxy.get('enabled', False)}\n")
                if proxy.get('enabled'):
                    f.write(f"Type: {proxy.get('type', 'socks5')}\n")
                    f.write(f"Host: {proxy.get('host', 'N/A')}\n")
                    f.write(f"Port: {proxy.get('port', 'N/A')}\n")
                    f.write(f"Username: {proxy.get('username', '(empty)')}\n")
                    f.write(f"Password: {'***' if config.get_proxy_password() else '(empty)'}\n")
                else:
                    f.write("Proxy disabled\n")
            except Exception as e:
                f.write(f"Error getting proxy config: {e}\n")
            f.write("\n")
            
            # File system check
            f.write("FILE SYSTEM CHECK\n")
            f.write("-" * 17 + "\n")
            
            directories = ['logs', 'config', 'bot', 'utils']
            files = ['main.py', 'requirements.txt']
            config_files = ['settings.json', 'groups.json', 'message_templates.json', '.key']
            
            f.write("Directories:\n")
            for directory in directories:
                exists = os.path.exists(directory)
                f.write(f"  {directory}: {'EXISTS' if exists else 'MISSING'}\n")
            
            f.write("\nCore files:\n")
            for file in files:
                exists = os.path.exists(file)
                f.write(f"  {file}: {'EXISTS' if exists else 'MISSING'}\n")
            
            f.write("\nConfig files:\n")
            for file in config_files:
                path = os.path.join('config', file)
                exists = os.path.exists(path)
                size = os.path.getsize(path) if exists else 0
                f.write(f"  {file}: {'EXISTS' if exists else 'MISSING'}")
                if exists:
                    f.write(f" ({size} bytes)")
                f.write("\n")
            
            f.write("\n")
            
            # Recent log entries
            f.write("RECENT LOG ENTRIES (last 20 lines)\n")
            f.write("-" * 35 + "\n")
            try:
                log_file = os.path.join('logs', 'bot.log')
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as log_f:
                        lines = log_f.readlines()
                        recent = lines[-20:] if len(lines) > 20 else lines
                        for line in recent:
                            f.write(line)
                else:
                    f.write("No bot.log file found\n")
            except Exception as e:
                f.write(f"Error reading log file: {e}\n")
            
            f.write("\n" + "=" * 50 + "\n")
            f.write("End of diagnostics report\n")
        
        return report_path
        
    except Exception as e:
        # Fallback: create minimal report
        fallback_path = os.path.join(logs_dir, 'diagnostics_error.txt')
        with open(fallback_path, 'w', encoding='utf-8') as f:
            f.write(f"Diagnostics generation failed: {e}\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"Python: {sys.version}\n")
        return fallback_path

def setup_error_logging():
    """Setup comprehensive error logging for the application"""
    # This function can be called to ensure all loggers are properly configured
    # It's mainly for initialization and doesn't need to return anything
    
    # Ensure logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Configure root logger to catch any uncaught exceptions
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/error.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
