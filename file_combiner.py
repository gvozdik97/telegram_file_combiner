import os
import shutil
from pathlib import Path

def find_py_files(directory):
    """Находит все .py файлы в директории (без рекурсии)"""
    directory = Path(directory)
    return [f for f in directory.iterdir() if f.is_file() and f.suffix == '.py']

def filter_files(file_paths, exclude_files, current_directory):
    """Фильтрует файлы для исключения"""
    filtered = []
    for file_path in file_paths:
        if file_path.name in exclude_files or file_path == current_directory:
            continue
        filtered.append(file_path)
    return filtered

def combine_py_files(file_paths, output_file_path):
    """Объединяет Python файлы в один"""
    try:
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            for i, file_path in enumerate(file_paths):
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read().strip()
                
                # Добавляем разделитель с именем файла
                if i > 0:
                    outfile.write('\n\n')
                outfile.write(f"# --- Файл: {file_path.name} ---\n")
                outfile.write(content)
        
        return True
    except Exception as e:
        print(f"Ошибка объединения файлов: {e}")
        return False

def remove_original_files(file_paths):
    """Удаляет исходные файлы после объединения"""
    for file_path in file_paths:
        try:
            file_path.unlink()
        except Exception as e:
            print(f"Ошибка удаления {file_path}: {e}")

def process_directory(root_dir, exclude_folders=None, exclude_files=None, remove_original=True):
    """Основная функция обработки директории"""
    if exclude_folders is None:
        exclude_folders = ['tests', 'venv', '__pycache__', '.git']
    if exclude_files is None:
        exclude_files = ['bot.py', 'file_combiner.py', 'archive_processor.py']
    
    root_dir = Path(root_dir)
    processed_folders = 0
    processed_files = 0
    
    try:
        # Обрабатываем все подпапки рекурсивно
        for folder_path in root_dir.rglob('*'):
            if not folder_path.is_dir():
                continue
            
            # Пропускаем исключенные папки
            if any(excluded in folder_path.parts for excluded in exclude_folders):
                continue
            
            # Находим Python файлы в папке
            py_files = find_py_files(folder_path)
            filtered_files = filter_files(py_files, exclude_files, root_dir)
            
            if len(filtered_files) <= 1:
                continue
            
            # Создаем имя для объединенного файла
            output_filename = f"{folder_path.name}.py"
            output_file_path = folder_path / output_filename
            
            # Объединяем файлы
            if combine_py_files(filtered_files, output_file_path):
                processed_folders += 1
                processed_files += len(filtered_files)
                
                # Удаляем исходные файлы
                if remove_original:
                    remove_original_files(filtered_files)
        
        return True, processed_folders, processed_files
        
    except Exception as e:
        print(f"Ошибка обработки директории: {e}")
        return False, 0, 0