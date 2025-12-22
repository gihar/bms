import re
from typing import List

class TextParser:
    """Парсер текста для создания чек-листов"""

    @staticmethod
    def parse_text(text: str) -> List[str]:
        """
        Парсит входной текст и возвращает список задач

        Поддерживаемые форматы:
        - Разделенные запятыми: Молоко, Хлеб, Сыр
        - Нумерованные списки: 1. Купить молоко\n2. Купить хлеб
        - Маркированные списки: • Молоко\n• Хлеб\n• Сыр
        - Построчно: Молоко\nХлеб\nСыр
        """
        text = text.strip()

        # Проверяем нумерованные списки
        numbered_pattern = r'^\d+\.\s*(.+?)(?:\n|$)'
        numbered_matches = re.findall(numbered_pattern, text, re.MULTILINE)
        if numbered_matches:
            return [task.strip() for task in numbered_matches if task.strip()]

        # Проверяем маркированные списки
        bullet_patterns = [
            r'^[•·]\s*(.+?)(?:\n|$)',
            r'^[-*]\s*(.+?)(?:\n|$)',
            r'^-\s*\[(.*?)\]\s*(.+?)(?:\n|$)'  # Markdown чекбоксы
        ]

        for pattern in bullet_patterns:
            bullet_matches = re.findall(pattern, text, re.MULTILINE)
            if bullet_matches:
                if pattern == bullet_patterns[2]:  # Markdown чекбоксы
                    return [task.strip() for task, _ in bullet_matches if task.strip()]
                else:
                    return [task.strip() for task in bullet_matches if task.strip()]

        # Проверяем разделенные запятыми (игнорируем запятые внутри скобок)
        if ',' in text:
            # Разбиваем по запятым, но не внутри скобок
            parts = []
            current = ""
            depth = 0
            for char in text:
                if char in '([{':
                    depth += 1
                    current += char
                elif char in ')]}':
                    depth -= 1
                    current += char
                elif char == ',' and depth == 0:
                    parts.append(current.strip())
                    current = ""
                else:
                    current += char
            if current.strip():
                parts.append(current.strip())
            
            # Возвращаем только если получилось больше одной части
            if len(parts) > 1:
                return [task for task in parts if task]

        # Проверяем разделенные точкой с запятой
        if ';' in text:
            return [task.strip() for task in text.split(';') if task.strip()]

        # Разделяем по строкам
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Если это одна строка, пробуем разделить по разным разделителям
        if len(lines) == 1:
            line = lines[0]
            # Разные разделители
            separators = [r'\s+\|\s+', r'\s+и\s+', r'\s+\+\s+']
            for sep in separators:
                if re.search(sep, line):
                    return [task.strip() for task in re.split(sep, line) if task.strip()]

        return lines

    @staticmethod
    def generate_title(tasks: List[str]) -> str:
        """Генерирует заголовок для чек-листа на основе задач"""
        if not tasks:
            return "Мой список"

        if len(tasks) == 1:
            return tasks[0]
        elif len(tasks) <= 3:
            return f"Список: {', '.join(tasks[:2])}..."
        else:
            return f"Список из {len(tasks)} пунктов"