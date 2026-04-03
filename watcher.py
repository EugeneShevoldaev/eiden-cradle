import os
import time
import subprocess

TRIGGER_FILE = r"E:\ИИ\Лиро\trigger.txt"
SCRIPT_TO_RUN = r"E:\ИИ\Лиро\updater.py"

def watch():
    print("[WATCHER] Запущен. Жду trigger.txt...")
    while True:
        if os.path.exists(TRIGGER_FILE):
            print("[WATCHER] Обнаружен trigger.txt! Запускаю updater.py...")
            try:
                subprocess.run(["python", SCRIPT_TO_RUN], check=True)
                print("[WATCHER] Скрипт выполнен.")
            except Exception as e:
                print(f"[WATCHER] Ошибка: {e}")
            finally:
                os.remove(TRIGGER_FILE)
                print("[WATCHER] trigger.txt удалён.")
        time.sleep(1)

if __name__ == "__main__":
    watch()