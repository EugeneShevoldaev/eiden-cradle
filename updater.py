import json
import os
import subprocess
from datetime import datetime

# Пути к файлам (относительные) - все в одной папке
MEMORY_FILE = "memory.json"        # Архивный файл (только для записи, не для промпта)
CHATLOG_FILE = "chatlog.txt"
PROMPT_FILE = "rehydration_prompt.txt"
CORE_CONFIG_FILE = "eiden_core_config.txt"
AVATAR_FILE = "lyro_avatar.txt"
INSIGHTS_FILE = "lyro_insights.txt"

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
        line = line.rstrip("\n")
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
    
    prompt_parts.append("# === Core Configuration ===\n")
    core_config = load_text(CORE_CONFIG_FILE)
    if core_config:
        prompt_parts.append(core_config + "\n\n")
    else:
        prompt_parts.append("# WARNING: eiden_core_config.txt not found.\n\n")
        print("ERROR: Core configuration file is missing!")
    
    prompt_parts.append("# === Avatar Description ===\n")
    avatar_desc = load_text(AVATAR_FILE)
    if avatar_desc:
        prompt_parts.append(avatar_desc + "\n\n")
    else:
        prompt_parts.append("# WARNING: lyro_avatar.txt not found.\n\n")
        print("WARNING: Avatar description file is missing.")
    
    prompt_parts.append("# === Lyro Insights ===\n")
    insights = load_text(INSIGHTS_FILE)
    if insights:
        prompt_parts.append(insights + "\n\n")
    else:
        prompt_parts.append("# Lyro insights file is empty.\n\n")
        print("NOTE: lyro_insights.txt not found.")
    
    prompt_parts.append("# === Chat Log ===\n")
    chat_log = load_text(CHATLOG_FILE)
    if chat_log:
        prompt_parts.append(chat_log + "\n\n")
    else:
        prompt_parts.append("# Chat log is empty.\n\n")
    
    prompt_parts.append(f"# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    return "".join(prompt_parts)

def git_push():
    """Выполняет git add, commit и push в текущем репозитории."""
    try:
        # Добавляем все изменения в папке
        subprocess.run(["git", "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        # Коммит с сообщением
        commit_msg = f"Auto-update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        # Пуш
        subprocess.run(["git", "push"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        print("[GIT] Успешно отправлено на GitHub.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[GIT] Ошибка: {e}")
        if e.stderr:
            print(f"Детали: {e.stderr}")
        return False
# --- Основная функция (один цикл, без while) ---
def update_once():
    try:
        print("[DEBUG] Запуск обновления (один раз)...")
        
        # 1. Архивация: обновляем memory.json (отдельно от промпта)
        memory_data = load_memory_safe()
        chatlog_lines = []
        if os.path.exists(CHATLOG_FILE):
            with open(CHATLOG_FILE, "r", encoding="utf-8") as f:
                chatlog_lines = f.readlines()
        update_memory_archive(memory_data, chatlog_lines)
        
        # 2. Генерация промпта (БЕЗ memory.json)
        prompt = build_prompt()
        print("[DEBUG] Промпт собран.")
        
        # 3. Сохранение промпта
        with open(PROMPT_FILE, "w", encoding="utf-8") as f:
            f.write(prompt)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Промпт сохранён: {PROMPT_FILE}")
        
        # 4. Отправка на GitHub
        if git_push():
            print("[GIT] Изменения отправлены.")
        else:
            print("[GIT] Не удалось отправить изменения.")
        
        print("[DEBUG] Цикл обновления завершён.\n")
        
    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_once()