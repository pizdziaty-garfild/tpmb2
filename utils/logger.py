import logging
import logging.handlers
import os
from datetime import datetime

def setup_logger(name: str = "tpmb2", log_level: str = "INFO") -> logging.Logger:
    log_dir = "logs"; os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    for h in list(logger.handlers):
        logger.removeHandler(h)
    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    fh = logging.handlers.RotatingFileHandler(os.path.join(log_dir, "bot.log"), maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    fh.setLevel(logging.INFO); fh.setFormatter(fmt); logger.addHandler(fh)
    eh = logging.handlers.RotatingFileHandler(os.path.join(log_dir, "error.log"), maxBytes=2*1024*1024, backupCount=3, encoding='utf-8')
    eh.setLevel(logging.ERROR); eh.setFormatter(fmt); logger.addHandler(eh)
    ch = logging.StreamHandler(); ch.setLevel(logging.WARNING); ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(ch)
    logger.info("="*60); logger.info(f"TPMB2 Logger initialized - {datetime.now():%Y-%m-%d %H:%M:%S}"); logger.info("="*60)
    return logger
