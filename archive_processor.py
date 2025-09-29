import os
import zipfile
import rarfile
import shutil
from pathlib import Path

class ArchiveProcessor:
    def __init__(self):
        self.supported_formats = ['.zip', '.rar']
    
    def is_supported_format(self, filename):
        """Проверяет поддержку формата архива"""
        return any(filename.lower().endswith(fmt) for fmt in self.supported_formats)
    
    def extract_archive(self, archive_path, extract_to):
        """Распаковывает архив"""
        try:
            archive_path = Path(archive_path)
            extract_to = Path(extract_to)
            
            # Очищаем целевую директорию
            if extract_to.exists():
                shutil.rmtree(extract_to)
            extract_to.mkdir(parents=True)
            
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
                return True
                
            elif archive_path.suffix.lower() == '.rar':
                try:
                    with rarfile.RarFile(archive_path) as rar_ref:
                        rar_ref.extractall(extract_to)
                    return True
                except rarfile.RarCannotExec:
                    raise Exception("Не установлен unrar. Установите: sudo apt-get install unrar")
                    
            else:
                raise Exception(f"Неподдерживаемый формат: {archive_path.suffix}")
                
        except Exception as e:
            print(f"Ошибка распаковки: {e}")
            return False
    
    def find_main_folder(self, extract_path):
        """Находит основную папку проекта"""
        extract_path = Path(extract_path)
        items = list(extract_path.iterdir())
        
        if len(items) == 1 and items[0].is_dir():
            return str(items[0])
        return str(extract_path)
    
    def create_zip_result(self, folder_path, output_path):
        """Создает ZIP архив с результатом"""
        folder_path = Path(folder_path)
        output_path = Path(output_path)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in folder_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(folder_path)
                    zipf.write(file_path, arcname)
    
    def cleanup(self, *paths):
        """Очищает временные файлы"""
        for path in paths:
            path_obj = Path(path)
            if path_obj.exists():
                if path_obj.is_dir():
                    shutil.rmtree(path_obj)
                else:
                    path_obj.unlink()