INSIGHTS_FILE = "lyro_insights.txt"  # НОВЫЙ ФАЙЛ С ИНСАЙТАМИ
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
    
    # === Avatar Description ===
    prompt += "# === Avatar Description ===\n"
    avatar_desc = load_text(AVATAR_FILE)
    if avatar_desc:
        prompt += avatar_desc + "\n\n"
    else:
        prompt += "# WARNING: lyro_avatar.txt not found.\n\n"
        print("WARNING: Avatar description file is missing.")
    
    # === Core Insights (Living Notes) ===  # НОВЫЙ БЛОК
    prompt += "# === Core Insights (Living Notes) ===\n"
    insights = load_text("lyro_insights.txt")  # Имя файла
    if insights:
        prompt += insights + "\n\n"
    else:
        prompt += "# No active insights recorded.\n\n"
    
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