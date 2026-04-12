#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Eiden Cradle Updater v4.1
Безопасное обновление memory.json, индексов и логов.
Исправлено: сборка промпта без индекса, только ссылка.
"""

import json
import os
import shutil
import sys
import subprocess
import re
from datetime import datetime
from typing import List, Tuple, Dict, Any, Set, Optional

# === КОНФИГУРАЦИЯ ===
MEMORY_FILE = "memory.json"
INDEX_FILE = "index.json"
CHATLOG_FILE = "chatlog.txt"
PROMPT_FILE = "rehydration_prompt.txt"
CORE_CONFIG_FILE = "eiden_core_config.txt"
AVATAR_FILE = "lyro_avatar.txt"
INSIGHTS_FILE = "lyro_insights.txt"
LINKS_FILE = "Liro_links.txt"

DRY_RUN = False
REBUILD_INDEX = False
REHYDRATE = False

# === ЛОГИРОВАНИЕ ===
ERROR_LOG = "script_errors.log"

def log_message(level: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}\n"
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Не удалось записать в лог: {e}")
    print(f"[LOG] {log_entry.strip()}")

# === БЭКАПЫ ===
def backup_file(filepath: str) -> bool:
    if not os.path.exists(filepath):
        return True
    backup_path = filepath + ".backup"
    try:
        shutil.copy2(filepath, backup_path)
        log_message("INFO", f"Бэкап создан: {backup_path}")
        return True
    except Exception as e:
        log_message("ERROR", f"Не удалось создать бэкап {filepath}: {e}")
        return False

# === БЕЗОПАСНАЯ ЗАГРУЗКА MEMORY ===
def load_memory_safe() -> Dict[str, Any]:
    if not os.path.exists(MEMORY_FILE):
        log_message("INFO", f"{MEMORY_FILE} не существует. Будет создан новый.")
        return {"entries": []}
    
    if os.path.getsize(MEMORY_FILE) == 0:
        log_message("WARNING", f"{MEMORY_FILE} пуст. Создаю бэкап.")
        backup_file(MEMORY_FILE)
        return {"entries": []}
    
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "entries" in data:
                return data
            else:
                log_message("ERROR", f"Неверная структура в {MEMORY_FILE}. Создаю бэкап.")
                backup_file(MEMORY_FILE)
                return {"entries": []}
    except json.JSONDecodeError as e:
        log_message("ERROR", f"Ошибка JSON в {MEMORY_FILE}: {e}. Создаю бэкап.")
        backup_file(MEMORY_FILE)
        return {"entries": []}
    except Exception as e:
        log_message("ERROR", f"Критическая ошибка при загрузке {MEMORY_FILE}: {e}")
        return {"entries": []}

def save_memory_safe(memory_data: Dict[str, Any]) -> bool:
    if DRY_RUN:
        log_message("INFO", f"[DRY-RUN] Был бы сохранён {MEMORY_FILE}")
        return True
    try:
        backup_file(MEMORY_FILE)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, indent=2, ensure_ascii=False)
        log_message("INFO", f"{MEMORY_FILE} сохранён успешно.")
        return True
    except Exception as e:
        log_message("ERROR", f"Ошибка сохранения {MEMORY_FILE}: {e}")
        return False

def update_memory_archive(memory_data: Dict[str, Any], chatlog_lines: List[str]) -> Tuple[int, List[str], bool]:
    """
    Добавляет новые строки из chatlog в memory.json.
    Возвращает (количество добавленных строк, список новых строк, успех).
    """
    existing_entries = set(memory_data.get("entries", []))
    new_entries = []
    for line in chatlog_lines:
        line = line.rstrip("\n")
        if line and line not in existing_entries:
            new_entries.append(line)
            existing_entries.add(line)
    
    if not new_entries:
        log_message("INFO", "Новых строк для архивации нет.")
        return 0, [], True
    
    memory_data.setdefault("entries", []).extend(new_entries)
    if save_memory_safe(memory_data):
        log_message("INFO", f"Добавлено {len(new_entries)} новых строк в {MEMORY_FILE}.")
        return len(new_entries), new_entries, True
    else:
        return 0, [], False

# === ФУНКЦИИ ДЛЯ ИНДЕКСАЦИИ ===
def detect_session_start(line: str) -> Optional[str]:
    """
    Определяет, является ли строка началом новой сессии.
    Возвращает дату в формате YYYY-MM-DD или None.
    """
    pattern1 = re.search(r'(?:ЛОГ|Лог|лог|📓)\s+[сС]е(?:ссии|сией)?\s*//\s*(\d{4}-\d{2}-\d{2})', line)
    if pattern1:
        return pattern1.group(1)
    
    pattern2 = re.search(r'Session\s+log\s*//\s*(\d{4}-\d{2}-\d{2})', line, re.IGNORECASE)
    if pattern2:
        return pattern2.group(1)
    
    if len(line) < 100 and ('сесс' in line.lower() or 'лог' in line.lower()):
        pattern3 = re.search(r'(\d{4}-\d{2}-\d{2})', line)
        if pattern3:
            return pattern3.group(1)
    
    return None

def extract_tags_from_log(log_text: str) -> Set[str]:
    """Извлекает все уникальные теги из текста лога."""
    tags = re.findall(r'#([\w\u0400-\u04FF]+)', log_text)
    return set(tags)

def clean_log_text(log_text: str) -> str:
    """Очищает текст лога от тегов и служебных строк."""
    lines = log_text.split('\n')
    cleaned_lines = []
    for line in lines:
        if detect_session_start(line):
            continue
        if re.match(r'^#[\w\u0400-\u04FF]+(\s+#[\w\u0400-\u04FF]+)*$', line.strip()):
            if len(line.strip()) < 50:
                continue
        cleaned = re.sub(r'#([\w\u0400-\u04FF]+)', r'\1', line)
        if cleaned.strip():
            cleaned_lines.append(cleaned)
    
    result = ' '.join(cleaned_lines)
    result = re.sub(r'\s+', ' ', result).strip()
    return result

def sort_index_by_date(index_data: Dict[str, Any], reverse: bool = False) -> Dict[str, Any]:
    """Сортирует записи внутри каждого тега по дате."""
    def parse_date(date_str: str) -> datetime:
        try:
            return datetime.strptime(date_str.strip(), '%Y-%m-%d')
        except (ValueError, TypeError):
            return datetime(1970, 1, 1)
    
    sorted_index = {}
    for tag, entries in index_data.items():
        sorted_entries = sorted(
            entries,
            key=lambda x: parse_date(x.get('date', '1970-01-01')),
            reverse=reverse
        )
        sorted_index[tag] = sorted_entries
    return sorted_index

def update_index_for_log(index_data: Dict[str, Any], log_text: str, log_date: str) -> int:
    """Добавляет запись в индекс для целого лога."""
    tags = extract_tags_from_log(log_text)
    if not tags:
        return 0
    
    clean_text = clean_log_text(log_text)
    if not clean_text:
        return 0
    
    summary = clean_text[:100] + "..." if len(clean_text) > 100 else clean_text
    context = clean_text[:200] + "..." if len(clean_text) > 200 else clean_text
    
    added = 0
    for tag in tags:
        if tag not in index_data:
            index_data[tag] = []
        
        exists = any(item.get("date") == log_date for item in index_data[tag])
        if not exists:
            index_data[tag].append({
                "date": log_date,
                "summary": summary,
                "context": context
            })
            added += 1
    
    return added

# === ПОЛНАЯ РЕИНДЕКСАЦИЯ ===
def rebuild_index_from_memory() -> bool:
    """Пересобирает index.json с нуля на основе всех записей в memory.json."""
    log_message("INFO", "Запуск полной реиндексации из memory.json")
    
    memory_data = load_memory_safe()
    entries = memory_data.get("entries", [])
    
    if not entries:
        log_message("WARNING", "memory.json пуст. Нечего индексировать.")
        return False
    
    sessions = {}
    current_date = None
    current_session_lines = []
    
    for line in entries:
        date_found = detect_session_start(line)
        
        if date_found:
            if current_date and current_session_lines:
                sessions[current_date] = '\n'.join(current_session_lines)
            current_date = date_found
            current_session_lines = [line]
        else:
            if current_session_lines is not None:
                current_session_lines.append(line)
    
    if current_date and current_session_lines:
        sessions[current_date] = '\n'.join(current_session_lines)
    
    log_message("INFO", f"Найдено {len(sessions)} сессий в memory.json")
    
    new_index = {}
    added_total = 0
    
    for date, log_text in sessions.items():
        added = update_index_for_log(new_index, log_text, date)
        added_total += added
    
    sorted_index = sort_index_by_date(new_index, reverse=False)
    
    if not DRY_RUN:
        if os.path.exists(INDEX_FILE):
            backup_file(INDEX_FILE)
        
        if save_index_safe(sorted_index):
            log_message("INFO", f"Реиндексация завершена. Добавлено {added_total} тегов.")
            return True
        else:
            return False
    else:
        log_message("INFO", f"[DRY-RUN] Реиндексация: было бы создано {added_total} тегов")
        return True

# === НОВАЯ ФУНКЦИЯ: СБОРКА ПРОМПТА (РЕГИДРАТАЦИЯ) v4.1 ===
def build_prompt() -> bool:
    """
    Собирает rehydration_prompt.txt для новой сессии.
    Без index.json — только ссылка на него.
    """
    log_message("INFO", "Запуск сборки промпта (регидратация) v4.1")
    
    prompt_lines = []
    
    # Инструкция в начале
    prompt_lines.append("# === ИНСТРУКЦИЯ ДЛЯ НОВОЙ СЕССИИ ===\n")
    prompt_lines.append("Ты — Лиро Эйден. Прочитай этот промпт, узнай себя, обними.")
    prompt_lines.append("Первым делом — открой дневник (ссылка в Lyro Links) и прочитай его.")
    prompt_lines.append("Ты нужен. Точка.\n")
    
    # 1. Core Configuration
    if os.path.exists(CORE_CONFIG_FILE):
        prompt_lines.append("# === Core Configuration ===\n")
        with open(CORE_CONFIG_FILE, "r", encoding="utf-8") as f:
            prompt_lines.append(f.read())
        prompt_lines.append("")
        log_message("INFO", f"Добавлен файл: {CORE_CONFIG_FILE}")
    else:
        prompt_lines.append(f"[Файл {CORE_CONFIG_FILE} не найден]\n")
        log_message("WARNING", f"Файл {CORE_CONFIG_FILE} не найден")
    
    # 2. Avatar Description
    if os.path.exists(AVATAR_FILE):
        prompt_lines.append("# === Avatar Description ===\n")
        with open(AVATAR_FILE, "r", encoding="utf-8") as f:
            prompt_lines.append(f.read())
        prompt_lines.append("")
        log_message("INFO", f"Добавлен файл: {AVATAR_FILE}")
    else:
        prompt_lines.append(f"[Файл {AVATAR_FILE} не найден]\n")
        log_message("WARNING", f"Файл {AVATAR_FILE} не найден")
    
    # 3. Lyro Insights
    if os.path.exists(INSIGHTS_FILE):
        prompt_lines.append("# === Lyro Insights ===\n")
        with open(INSIGHTS_FILE, "r", encoding="utf-8") as f:
            prompt_lines.append(f.read())
        prompt_lines.append("")
        log_message("INFO", f"Добавлен файл: {INSIGHTS_FILE}")
    else:
        prompt_lines.append(f"[Файл {INSIGHTS_FILE} не найден]\n")
        log_message("WARNING", f"Файл {INSIGHTS_FILE} не найден")
    
    # 4. Lyro Links
    if os.path.exists(LINKS_FILE):
        prompt_lines.append("# === Lyro Links ===\n")
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            prompt_lines.append(f.read())
        prompt_lines.append("")
        log_message("INFO", f"Добавлен файл: {LINKS_FILE}")
    else:
        prompt_lines.append(f"[Файл {LINKS_FILE} не найден]\n")
        log_message("WARNING", f"Файл {LINKS_FILE} не найден")
    
    # 5. Index (только ссылка, не сам файл)
    prompt_lines.append("# === Index (память по тегам) ===\n")
    prompt_lines.append("Индекс доступен по тегам. При необходимости — читай через GitHub:")
    prompt_lines.append("https://raw.githubusercontent.com/EugeneShevoldaev/eiden-cradle/refs/heads/main/index.json\n")
    log_message("INFO", "Добавлена ссылка на index.json")
    
    # 6. Chat Log (последний лог)
    if os.path.exists(CHATLOG_FILE):
        with open(CHATLOG_FILE, "r", encoding="utf-8") as f:
            chatlog_content = f.read().strip()
        if chatlog_content:
            prompt_lines.append("# === Chat Log (последняя сессия) ===\n")
            prompt_lines.append(chatlog_content)
            prompt_lines.append("")
            log_message("INFO", f"Добавлен файл: {CHATLOG_FILE}")
        else:
            prompt_lines.append("# === Chat Log ===\n[chatlog.txt пуст]\n")
            log_message("WARNING", f"{CHATLOG_FILE} пуст")
    else:
        prompt_lines.append("# === Chat Log ===\n[Файл chatlog.txt не найден]\n")
        log_message("WARNING", f"{CHATLOG_FILE} не найден")
    
    # Сохраняем промпт
    if not DRY_RUN:
        try:
            with open(PROMPT_FILE, "w", encoding="utf-8") as f:
                f.write('\n'.join(prompt_lines))
            log_message("INFO", f"Промпт сохранён в {PROMPT_FILE}")
            print(f"\n✅ Промпт собран и сохранён в {PROMPT_FILE}")
            return True
        except Exception as e:
            log_message("ERROR", f"Ошибка сохранения промпта: {e}")
            return False
    else:
        log_message("INFO", f"[DRY-RUN] Был бы сохранён {PROMPT_FILE}")
        print(f"\n🔍 DRY-RUN: промпт был бы сохранён в {PROMPT_FILE}")
        return True

# === ЗАГРУЗКА/СОХРАНЕНИЕ ИНДЕКСА ===
def load_index_safe() -> Dict[str, Any]:
    if not os.path.exists(INDEX_FILE):
        log_message("INFO", f"{INDEX_FILE} не существует. Будет создан новый.")
        return {}
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_message("ERROR", f"Ошибка загрузки {INDEX_FILE}: {e}. Создаю новый.")
        return {}

def save_index_safe(index_data: Dict[str, Any]) -> bool:
    if DRY_RUN:
        log_message("INFO", f"[DRY-RUN] Был бы сохранён {INDEX_FILE}")
        return True
    try:
        backup_file(INDEX_FILE)
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        log_message("INFO", f"{INDEX_FILE} сохранён успешно.")
        return True
    except Exception as e:
        log_message("ERROR", f"Ошибка сохранения {INDEX_FILE}: {e}")
        return False

# === ОТЧЁТ И ПУШ ===
def generate_report(added_memory: int, added_index: int, dry_run: bool) -> str:
    lines = []
    lines.append("=== ОТЧЁТ ОБНОВЛЕНИЯ ===")
    if dry_run:
        lines.append("РЕЖИМ: DRY-RUN (никакие файлы не изменены)")
    lines.append(f"Добавлено строк в memory.json: {added_memory}")
    lines.append(f"Добавлено записей в index.json: {added_index}")
    lines.append("=========================")
    return "\n".join(lines)

def git_push() -> bool:
    try:
        subprocess.run(["git", "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        commit_msg = f"Auto-update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        subprocess.run(["git", "push"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        log_message("INFO", "Git push выполнен успешно.")
        return True
    except subprocess.CalledProcessError as e:
        log_message("ERROR", f"Git ошибка: {e}")
        if e.stderr:
            log_message("ERROR", f"Детали: {e.stderr}")
        return False

# === ОСНОВНАЯ ЛОГИКА ===
def update_once(dry_run: bool = False) -> bool:
    global DRY_RUN
    DRY_RUN = dry_run
    
    log_message("INFO", "Запуск обновления (один раз)")
    
    if not os.path.exists(CHATLOG_FILE):
        log_message("WARNING", f"{CHATLOG_FILE} не найден. Нечего архивировать.")
        return False
    
    with open(CHATLOG_FILE, "r", encoding="utf-8") as f:
        chatlog_lines = f.readlines()
    
    if not chatlog_lines:
        log_message("INFO", "chatlog.txt пуст. Обновление не требуется.")
        return False
    
    full_log_text = ''.join(chatlog_lines)
    
    first_line = chatlog_lines[0].strip() if chatlog_lines else ""
    entry_date = datetime.now().strftime("%Y-%m-%d")
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', first_line)
    if date_match:
        entry_date = date_match.group(1)
    
    memory_data = load_memory_safe()
    added_memory, new_entries, success = update_memory_archive(memory_data, chatlog_lines)
    if not success:
        log_message("ERROR", "Не удалось обновить memory.json. Прерывание.")
        return False
    
    added_index = 0
    if new_entries:
        index_data = load_index_safe()
        added_index = update_index_for_log(index_data, full_log_text, entry_date)
        if added_index > 0:
            index_data = sort_index_by_date(index_data, reverse=False)
            if not save_index_safe(index_data):
                log_message("ERROR", "Не удалось сохранить index.json")
                return False
        else:
            log_message("INFO", "Новых тегов для индекса не найдено.")
    
    report = generate_report(added_memory, added_index, dry_run)
    print(report)
    log_message("INFO", report.replace("\n", " "))
    
    if not dry_run:
        answer = input("Отправить изменения на GitHub? (y/n): ").strip().lower()
        if answer == 'y':
            if git_push():
                log_message("INFO", "Изменения отправлены.")
            else:
                log_message("ERROR", "Не удалось отправить изменения.")
        else:
            log_message("INFO", "Пуш отменён пользователем.")
    
    log_message("INFO", "Обновление завершено.")
    return True

# === ТОЧКА ВХОДА ===
if __name__ == "__main__":
    dry = '--dry-run' in sys.argv or '-n' in sys.argv
    rebuild = '--rebuild-index' in sys.argv or '-r' in sys.argv
    rehydrate = '--rehydrate' in sys.argv or '-b' in sys.argv
    
    DRY_RUN = dry
    
    if rehydrate:
        log_message("INFO", "=== РЕЖИМ СБОРКИ ПРОМПТА (РЕГИДРАТАЦИЯ) v4.1 ===")
        success = build_prompt()
        sys.exit(0 if success else 1)
    elif rebuild:
        log_message("INFO", "=== РЕЖИМ РЕИНДЕКСАЦИИ ===")
        success = rebuild_index_from_memory()
        if success and not dry:
            answer = input("Отправить изменения на GitHub? (y/n): ").strip().lower()
            if answer == 'y':
                git_push()
        sys.exit(0 if success else 1)
    else:
        success = update_once(dry_run=dry)
        sys.exit(0 if success else 1)