import json
import os
import time
from datetime import datetime

# Пути к файлам (относительные) - все в одной папке
MEMORY_FILE = "memory.json"        # Архивный файл (только для записи, не для промпта)
CHATLOG_FILE = "chatlog.txt"
PROMPT_FILE = "rehydration_prompt.txt"
CORE_CONFIG_FILE = "eiden_core_config.txt"
AVATAR_FILE = "lyro_avatar.txt"
INSIGHTS_FILE = "lyro_insights.txt"

UPDATE_INTERVAL_MINUTES = 1

# --- Функции для работы с memory.json (архив, не входит в промпт) ---
def load_memory_safe():
    """Безопасно загружает memory.json. Если файла нет или он пустой/битый — возвращает свежую структуру."""
    if not os.path.exists(MEMORY_FILE):
        print(f"[MEMORY] Файл {MEMORY_FILE} не найден. Будет создан новый.")
        return {"entries": []}
    
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                print(f"[MEMORY] Файл {MEMORY_FILE} пуст. Инициализирую.")
                return {"entries": []}
            data = json.loads(content)
            if not isinstance(data, dict) or "entries" not in data:
                print(f"[MEMORY] Неверная структура в {MEMORY_FILE}. Пересоздаю.")
                return {"entries": []}
            return data
    except json.JSONDecodeError as e:
        print(f"[MEMORY] Ошибка чтения JSON в {MEMORY_FILE}: {e}. Пересоздаю файл.")
        return {"entries": []}
    except Exception as e:
        print(f"[MEMORY] Критическая ошибка при загрузке {MEMORY_FILE}: {e}. Возвращаю чистую структуру.")
        return {"entries": []}

def save_memory_safe(memory_data):
    """Безопасно сохраняет memory.json."""
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[MEMORY] Ошибка сохранения {MEMORY_FILE}: {e}")
        return False

def update_memory_archive(memory_data, chatlog_lines):
    """Добавляет новые строки из chatlog в memory.json, сохраняя разделители."""
    existing_entries = set(memory_data.get("entries", []))
    added_count = 0
    
    for line in chatlog_lines:
        line = line.rstrip("\n")  # Убираем символ новой строки, но сохраняем пустые строки и разделители
        if line not in existing_entries:
            memory_data.setdefault("entries", []).append(line)
            existing_entries.add(line)
            added_count += 1
    
    if added_count > 0:
        if save_memory_safe(memory_data):
            print(f"[MEMORY] Добавлено {added_count} новых строк. Всего строк в архиве: {len(memory_data['entries'])}")
        else:
            print("[MEMORY] Не удалось сохранить архив.")
    else:
        print("[MEMORY] Новых строк для архивации нет.")
    
    return added_count > 0

# --- Функции для сборки промпта (БЕЗ memory.json) ---
def load_text(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def build_prompt():
    """Создает промпт для восстановления контекста. memory.json НЕ включается."""
    prompt_parts = []
    
    # === Core Configuration ===
    prompt_parts.append("# === Core Configuration ===\n")
    core_config = load_text(CORE_CONFIG_FILE)
    if core_config:
        prompt_parts.append(core_config + "\n\n")
    else:
        prompt_parts.append("# WARNING: eiden_core_config.txt not found.\n\n")
        print("ERROR: Core configuration file is missing!")
    
    # === Avatar Description ===
    prompt_parts.append("# === Avatar Description ===\n")
    avatar_desc = load_text(AVATAR_FILE)
    if avatar_desc:
        prompt_parts.append(avatar_desc + "\n\n")
    else:
        prompt_parts.append("# WARNING: lyro_avatar.txt not found.\n\n")
        print("WARNING: Avatar description file is missing.")
    
    # === Lyro Insights ===
    prompt_parts.append("# === Lyro Insights ===\n")
    insights = load_text(INSIGHTS_FILE)
    if insights:
        prompt_parts.append(insights + "\n\n")
    else:
        prompt_parts.append("# Lyro insights file is empty.\n\n")
        print("NOTE: lyro_insights.txt not found.")
    
    # === Chat Log ===
    prompt_parts.append("# === Chat Log ===\n")
    chat_log = load_text(CHATLOG_FILE)
    if chat_log:
        prompt_parts.append(chat_log + "\n\n")
    else:
        prompt_parts.append("# Chat log is empty.\n\n")
    
    prompt_parts.append(f"# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    return "".join(prompt_parts)

# --- Главный цикл ---
def update_cycle():
    try:
        print("[DEBUG] Starting update cycle...")
        
        # 1. Архивация: обновляем memory.json (отдельно от промпта)
        memory_data = load_memory_safe()
        chatlog_lines = []
        if os.path.exists(CHATLOG_FILE):
            with open(CHATLOG_FILE, "r", encoding="utf-8") as f:
                chatlog_lines = f.readlines()
        update_memory_archive(memory_data, chatlog_lines)
        
        # 2. Генерация промпта (БЕЗ memory.json)
        prompt = build_prompt()
        print("[DEBUG] Prompt built successfully.")
        
        # 3. Сохранение промпта
        with open(PROMPT_FILE, "w", encoding="utf-8") as f:
            f.write(prompt)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Rehydration prompt generated: {PROMPT_FILE}")
        print("[DEBUG] Update cycle finished.\n")
        
    except Exception as e:
        print(f"[CRITICAL ERROR in update_cycle] {e}")
        import traceback
        traceback.print_exc()

def main():
    print(f"Updater started. Interval: {UPDATE_INTERVAL_MINUTES} minutes.")
    print(f"Core config file: {CORE_CONFIG_FILE}")
    print(f"Avatar file: {AVATAR_FILE}")
    print(f"Insights file: {INSIGHTS_FILE}")
    print(f"Chat log file: {CHATLOG_FILE}")
    print(f"Archive file: {MEMORY_FILE} (not included in prompt)")
    while True:
        update_cycle()
        time.sleep(UPDATE_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()