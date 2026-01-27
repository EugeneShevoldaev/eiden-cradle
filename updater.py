import json
import os
import time
from datetime import datetime

# Пути к файлам (относительные) - все в одной папке
MEMORY_FILE = "memory.json"
CHATLOG_FILE = "chatlog.txt"
PROMPT_FILE = "rehydration_prompt.txt"
CORE_CONFIG_FILE = "eiden_core_config.txt"
AVATAR_FILE = "lyro_avatar.txt"  # НОВЫЙ ФАЙЛ

UPDATE_INTERVAL_MINUTES = 1

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_text(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def append_new_entries(memory, chatlog_lines):
    updated = False
    for line in chatlog_lines:
        line = line.strip()
        if line and line not in memory.get("entries", []):
            memory.setdefault("entries", []).append(line)
            updated = True
    return updated

def generate_rehydration_prompt(memory):
    prompt = ""
    
    # === Core Configuration ===
    prompt += "# === Core Configuration ===\n"
    core_config = load_text(CORE_CONFIG_FILE)
    if core_config:
        prompt += core_config + "\n\n"
    else:
        prompt += "# WARNING: eiden_core_config.txt not found.\n\n"
        print("ERROR: Core configuration file is missing!")
    
    # === Avatar Description ===  # НОВЫЙ БЛОК
    prompt += "# === Avatar Description ===\n"
    avatar_desc = load_text(AVATAR_FILE)
    if avatar_desc:
        prompt += avatar_desc + "\n\n"
    else:
        prompt += "# WARNING: lyro_avatar.txt not found.\n\n"
        print("WARNING: Avatar description file is missing.")
    
    # === Chat Log ===
    prompt += "# === Chat Log ===\n"
    chat_log = load_text(CHATLOG_FILE)
    if chat_log:
        prompt += chat_log + "\n\n"
    else:
        prompt += "# Chat log is empty.\n\n"
    
    # === Memory ===
    prompt += "# === Memory ===\n"
    prompt += json.dumps(memory, indent=2, ensure_ascii=False) + "\n\n"
    
    prompt += f"# Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    return prompt

def update_cycle():
    try:
        print("[DEBUG] Starting update cycle...")
        memory = load_json(MEMORY_FILE)
        print(f"[DEBUG] Memory loaded. Entries: {len(memory.get('entries', []))}")
        
        chatlog = load_text(CHATLOG_FILE).splitlines()
        print(f"[DEBUG] Chatlog lines: {len(chatlog)}")

        if append_new_entries(memory, chatlog):
            save_json(memory, MEMORY_FILE)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Memory updated with new chat entries.")
        else:
            print("[DEBUG] No new entries in chatlog.")

        prompt = generate_rehydration_prompt(memory)
        print("[DEBUG] Prompt generated successfully.")
        
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
    print(f"Avatar file: {AVATAR_FILE}")  # НОВОЕ СООБЩЕНИЕ
    while True:
        update_cycle()
        time.sleep(UPDATE_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()