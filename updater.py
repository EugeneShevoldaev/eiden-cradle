#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Eiden Cradle Updater v2.1
Безопасное обновление memory.json, индексов и логов.
Никаких перезаписей — только дописывание.
Исправлено: извлечение чистого текста для индекса.
"""

import json
import os
import shutil
import sys
import subprocess
import re
from datetime import datetime
from typing import List, Tuple, Dict, Any

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

# === ИНДЕКС (index.json) ===
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

def update_index(index_data: Dict[str, Any], new_entries: List[str], entry_date: str) -> int:
    """
    Добавляет новые записи в индекс по тегам.
    Очищает текст от тегов для summary/context.
    Возвращает количество добавленных связей.
    """
    added = 0
    for entry in new_entries:
        # Извлекаем теги
        tags = re.findall(r'#([\w\u0400-\u04FF]+)', entry)
        if not tags:
            continue
        
        # Очищаем строку от тегов для summary/context
        clean_entry = re.sub(r'\s*#[\w\u0400-\u04FF]+\s*', ' ', entry).strip()
        clean_entry = re.sub(r'\s+', ' ', clean_entry)  # убираем множественные пробелы
        
        summary = clean_entry[:100] + "..." if len(clean_entry) > 100 else clean_entry
        context = clean_entry[:150] + "..." if len(clean_entry) > 150 else clean_entry
        
        for tag in tags:
            if tag not in index_data:
                index_data[tag] = []
            
            # Проверяем дубликаты
            exists = any(
                item.get("date") == entry_date and item.get("summary") == summary
                for item in index_data[tag]
            )
            if not exists:
                index_data[tag].append({
                    "date": entry_date,
                    "summary": summary,
                    "context": context
                })
                added += 1
    return added

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
    
    # Определяем дату для индекса
    first_line = chatlog_lines[0].strip() if chatlog_lines else ""
    entry_date = datetime.now().strftime("%Y-%m-%d")
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', first_line)
    if date_match:
        entry_date = date_match.group(1)
    
    # Обновляем memory.json
    memory_data = load_memory_safe()
    added_memory, new_entries, success = update_memory_archive(memory_data, chatlog_lines)
    if not success:
        log_message("ERROR", "Не удалось обновить memory.json. Прерывание.")
        return False
    
    # Обновляем index.json (только если есть новые записи)
    added_index = 0
    if new_entries:
        index_data = load_index_safe()
        added_index = update_index(index_data, new_entries, entry_date)
        if added_index > 0:
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

if __name__ == "__main__":
    dry = '--dry-run' in sys.argv or '-n' in sys.argv
    success = update_once(dry_run=dry)
    sys.exit(0 if success else 1)