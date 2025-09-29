import os
import logging
import asyncio
import threading
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import config
from archive_processor import ArchiveProcessor
from file_combiner import process_directory

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class FileCombinerBot:
    def __init__(self, application):
        self.processor = ArchiveProcessor()
        self.processing_users = set()
        self.application = application
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_text = """
🤖 **Python File Combiner Bot**

Я помогу объединить ваши Python файлы в проекте!

**Как использовать:**
1. Создайте ZIP или RAR архив с вашим Python проектом
2. Отправьте архив мне
3. Я объединю все .py файлы в каждой папке и удалю исходные файлы
4. Вы получите обработанный архив обратно

**Поддерживаемые форматы:** ZIP, RAR
**Максимальный размер:** 50MB

Просто отправьте мне архив и я начну работу!
        """
        await update.message.reply_text(welcome_text)
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик документов"""
        user_id = update.message.from_user.id
        
        # Проверяем, не занят ли пользователь
        if user_id in self.processing_users:
            await update.message.reply_text("⏳ Ваш предыдущий запрос еще обрабатывается...")
            return
        
        document = update.message.document
        file_name = document.file_name
        
        # Проверяем формат
        if not self.processor.is_supported_format(file_name):
            await update.message.reply_text(
                "❌ **Неподдерживаемый формат!**\n\n"
                "Поддерживаются только:\n"
                "✅ ZIP архивы (.zip)\n"
                "✅ RAR архивы (.rar)"
            )
            return
        
        # Проверяем размер
        if document.file_size > config.MAX_FILE_SIZE:
            await update.message.reply_text(
                f"❌ **Файл слишком большой!**\n\n"
                f"Размер: {document.file_size // 1024 // 1024}MB\n"
                f"Максимальный: {config.MAX_FILE_SIZE // 1024 // 1024}MB"
            )
            return
        
        # Добавляем пользователя в обработку
        self.processing_users.add(user_id)
        
        try:
            # Скачиваем файл
            await update.message.reply_text(f"📥 **Принял архив:** `{file_name}`\n🔄 **Начинаю обработку...**")
            
            file = await context.bot.get_file(document.file_id)
            temp_archive_path = Path(config.UPLOADS_DIR) / f"{user_id}_{file_name}"
            
            await file.download_to_drive(custom_path=temp_archive_path)
            
            # Обрабатываем архив
            result_path, message = await self._process_archive(update, context, temp_archive_path, user_id)
            
            # Отправляем результат
            if result_path and Path(result_path).exists():
                with open(result_path, 'rb') as result_file:
                    await update.message.reply_document(
                        document=result_file,
                        filename=f"processed_project_{user_id}.zip",
                        caption=message
                    )
                # Очищаем результат после отправки
                self.processor.cleanup(result_path)
            else:
                await update.message.reply_text(message)
                
        except Exception as e:
            logger.error(f"Ошибка обработки: {e}")
            await update.message.reply_text(f"❌ **Произошла ошибка!**\n\nОшибка: `{str(e)}`")
        finally:
            self.processing_users.discard(user_id)
    
    async def _process_archive(self, update: Update, context: ContextTypes.DEFAULT_TYPE, archive_path, user_id):
        """Асинхронная обработка архива"""
        try:
            # Используем asyncio.to_thread для выполнения блокирующих операций
            result = await asyncio.to_thread(
                self._process_archive_sync, archive_path, user_id
            )
            return result
        except Exception as e:
            # Очищаем в случае ошибки
            self.processor.cleanup(
                archive_path,
                Path(config.PROCESSING_DIR) / str(user_id),
                Path(config.RESULTS_DIR) / f"{user_id}_processed.zip"
            )
            raise e
    
    def _process_archive_sync(self, archive_path, user_id):
        """Синхронная обработка архива (выполняется в отдельном потоке)"""
        # Создаем уникальные пути
        extract_path = Path(config.PROCESSING_DIR) / str(user_id)
        result_path = Path(config.RESULTS_DIR) / f"{user_id}_processed.zip"
        
        # Распаковываем архив
        if not self.processor.extract_archive(archive_path, extract_path):
            return None, "❌ Ошибка распаковки архива"
        
        # Находим основную папку
        project_folder = self.processor.find_main_folder(extract_path)
        
        # Обрабатываем проект
        success, folders_processed, files_processed = process_directory(
            project_folder,
            exclude_folders=config.DEFAULT_EXCLUDE_FOLDERS,
            exclude_files=config.DEFAULT_EXCLUDE_FILES,
            remove_original=True
        )
        
        if not success:
            return None, "❌ Ошибка объединения файлов"
        
        if folders_processed == 0:
            return None, "❌ Не найдено папок с Python файлами для объединения"
        
        # Создаем результат
        self.processor.create_zip_result(project_folder, result_path)
        
        # Очищаем временные файлы
        self.processor.cleanup(archive_path, extract_path)
        
        message = (
            f"✅ **Обработка завершена!**\n\n"
            f"📁 Обработано папок: {folders_processed}\n"
            f"📄 Объединено файлов: {files_processed}\n"
            f"💾 Результат готов к скачиванию!"
        )
        
        return result_path, message
    
    async def cleanup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка временных файлов (админская команда)"""
        user_id = update.message.from_user.id
        
        # Простая проверка на админа
        if user_id != 1344187204: 
            await update.message.reply_text("❌ У вас нет прав для этой команды")
            return
        
        try:
            # Очищаем все временные директории
            cleaned_files = 0
            cleaned_dirs = 0
            
            for temp_dir in [config.UPLOADS_DIR, config.PROCESSING_DIR, config.RESULTS_DIR]:
                temp_path = Path(temp_dir)
                if temp_path.exists():
                    for item in temp_path.iterdir():
                        if item.is_file():
                            item.unlink()
                            cleaned_files += 1
                        elif item.is_dir():
                            # Удаляем содержимое директории
                            for subitem in item.rglob('*'):
                                if subitem.is_file():
                                    subitem.unlink()
                                    cleaned_files += 1
                            item.rmdir()
                            cleaned_dirs += 1
            
            await update.message.reply_text(f"✅ Временные файлы очищены\n🗑️ Удалено файлов: {cleaned_files}\n📁 Удалено папок: {cleaned_dirs}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка очистки: {e}")
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статус бота"""
        status_text = f"""
🤖 **Статус бота**

👥 Пользователей в обработке: {len(self.processing_users)}
💾 Временные директории:
  - 📁 Uploads: {len(list(Path(config.UPLOADS_DIR).iterdir()))} файлов
  - 📁 Processing: {len(list(Path(config.PROCESSING_DIR).iterdir()))} папок
  - 📁 Results: {len(list(Path(config.RESULTS_DIR).iterdir()))} файлов

Бот работает нормально! ✅
        """
        await update.message.reply_text(status_text)

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Создаем экземпляр бота и передаем ему application
    bot = FileCombinerBot(application)
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("cleanup", bot.cleanup))
    application.add_handler(CommandHandler("status", bot.status))
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_document))
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()