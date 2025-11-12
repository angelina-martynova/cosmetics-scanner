import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

def init_db(db):
    """Ініціалізація бази даних"""
    # Створюємо папку для бази даних якщо потрібно
    os.makedirs('instance', exist_ok=True)
    
    # Створюємо таблиці
    db.create_all()
    print("✅ База даних ініціалізована")

def save_uploaded_file(file, user_id=None):
    """Зберігає завантажений файл"""
    # Створюємо папку uploads якщо не існує
    uploads_dir = os.path.join('uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Створюємо підпапку для користувача якщо вказано
    if user_id:
        user_dir = os.path.join(uploads_dir, f'user_{user_id}')
        os.makedirs(user_dir, exist_ok=True)
        uploads_dir = user_dir
    
    # Генеруємо унікальне ім'я файлу
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{file_ext}"
    
    filepath = os.path.join(uploads_dir, filename)
    file.save(filepath)
    
    print(f"✅ Файл збережено: {filename}")
    return filename

def get_file_path(filename, user_id=None):
    """Отримує шлях до файлу"""
    if user_id:
        return os.path.join('uploads', f'user_{user_id}', filename)
    return os.path.join('uploads', filename)

def file_exists(filename, user_id=None):
    """Перевіряє чи існує файл"""
    filepath = get_file_path(filename, user_id)
    return os.path.exists(filepath)