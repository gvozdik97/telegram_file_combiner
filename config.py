import os
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
UPLOADS_DIR = os.path.join(TEMP_DIR, "uploads")
PROCESSING_DIR = os.path.join(TEMP_DIR, "processing")
RESULTS_DIR = os.path.join(TEMP_DIR, "results")

# Настройки обработки
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
PROCESSING_TIMEOUT = 300  # 5 минут

# Исключения по умолчанию
DEFAULT_EXCLUDE_FOLDERS = ['tests', 'venv', '__pycache__', '.git', 'node_modules']
DEFAULT_EXCLUDE_FILES = ['bot.py', 'file_combiner.py', 'archive_processor.py', 'config.py']

# Создаем необходимые директории
for directory in [TEMP_DIR, UPLOADS_DIR, PROCESSING_DIR, RESULTS_DIR]:
    os.makedirs(directory, exist_ok=True)