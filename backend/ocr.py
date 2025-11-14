import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import re
import os

# Для Windows
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Конфигурация Tesseract с украинским, русским и английским
custom_config = r'--oem 3 --psm 6 -l ukr+rus+eng'

def preprocess_image(image):
    """Попередня обробка зображення для покращення OCR"""
    try:
        # Збільшуємо контрастність
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Збільшуємо різкість
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # Конвертуємо в grayscale для кращого розпізнавання
        image = image.convert('L')
        
        # Застосовуємо легке розмиття для зменшення шуму
        image = image.filter(ImageFilter.MedianFilter())
        
        return image
    except Exception as e:
        print(f"Помилка при обробці зображення: {e}")
        return image

def clean_text(text):
    """Очищення та форматування розпізнаного тексту"""
    if not text:
        return ""
    
    # Видаляємо зайві пробіли та переноси рядків
    text = ' '.join(text.split())
    
    # Видаляємо спеціальні символи, але залишаємо літери, цифри та основні знаки пунктуації
    text = re.sub(r'[^\w\s.,!?;:()\-–]', '', text)
    
    # Видаляємо зайві крапки та коми
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r',{2,}', ',', text)
    
    return text.strip()

def extract_text(file):
    """Головна функція для розпізнавання тексту"""
    try:
        # Створюємо копію файлу в пам'яті для уникнення проблем з потоком
        file.stream.seek(0)
        file_copy = io.BytesIO(file.stream.read())
        
        file_copy.seek(0)
        image = Image.open(file_copy).convert('RGB')
        
        processed_image = preprocess_image(image)
        text = pytesseract.image_to_string(processed_image, config=custom_config)
        
        print("✅ OCR успішно розпізнав текст")
        print(f"📝 Розпізнаний текст: {text[:100]}...")  # Показуємо перші 100 символів
        return clean_text(text)
    except Exception as e:
        print(f"❌ Помилка OCR: {e}")
        return ""