import re
import html
from datetime import datetime
from typing import Dict, Any
import logging

class MessageFormatter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def format_message(self, text: str, variables: Dict[str, Any] = None) -> str:
        if not text:
            return ""
        try:
            variables = variables or {}
            now = datetime.now()
            defaults = {
                'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S')
            }
            all_vars = {**defaults, **variables}
            for k, v in all_vars.items():
                text = text.replace(f'{{{k}}}', str(v))
            # Rich text formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
            text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
            text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
            text = re.sub(r'__(.+?)__', r'<u>\1</u>', text)
            return text
        except Exception as e:
            self.logger.error(f"Blad formatowania: {e}")
            return html.escape(text)
