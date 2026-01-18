# reset_token.py
import os
from dotenv import load_dotenv, set_key

def reset_bot_token():
    """Сброс токена бота в .env файле"""
    
    # Проверяем, существует ли файл .env
    config_file = ".env"
    
    if not os.path.exists(config_file):
        print("❌ Файл .env не найден!")
        print("Создайте .env файл на основе .env.example")
        return
    
    try:
        # Загружаем текущие переменные
        load_dotenv()
        
        print("=" * 50)
        print("RESET BOT TOKEN / СБРОС ТОКЕНА БОТА")
        print("=" * 50)
        
        # Показываем текущий токен (частично)
        current_token = os.getenv('TELEGRAM_BOT_TOKEN', 'Не найден')
        if current_token != 'Не найден':
            masked_token = f"{current_token[:10]}...{current_token[-5:]}"
            print(f"Текущий токен: {masked_token}")
        
        # Запрашиваем новый токен
        new_token = input("\nВведите новый TELEGRAM_BOT_TOKEN: ").strip()
        
        if not new_token:
            print("❌ Токен не может быть пустым!")
            return
        
        # Обновляем токен в .env
        set_key('.env', 'TELEGRAM_BOT_TOKEN', new_token)
        
        print(f"✅ Токен успешно обновлен в .env файле!")
        print(f"📁 Конфигурация сохранена в: {config_file}")
        
        # Удаляем файл блокировки, если он существует
        lock_file = "bot.lock"
        if os.path.exists(lock_file):
            os.remove(lock_file)
            print("🗑️ Файл блокировки удален")
        
        print("\n⚠️ Остановите бота (Ctrl+C) и перезапустите его")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    reset_bot_token()
