import pytesseract
from PIL import Image
import io

def extract_text(file):
    """Главная функция для распознавания текста"""
    try:
        file.stream.seek(0)  # Важно! Перематываем поток в начало
        image = Image.open(file.stream).convert('RGB')
        
        processed_image = preprocess_image(image)
        text = pytesseract.image_to_string(processed_image, config=custom_config)
        return clean_text(text)
    except Exception as e:
        return ""
