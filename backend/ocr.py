import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import re
import os
import time
import traceback

# Для Windows
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    print(f"Використовується Tesseract з: {pytesseract.pytesseract.tesseract_cmd}")

# Конфігурація Tesseract з українською, російською та англійською
custom_config = r'--oem 3 --psm 6 -l ukr+rus+eng'

def preprocess_image(image):
    """Попередня обробка зображення для покращення OCR"""
    try:
        print(f"Початковий розмір зображення: {image.size}")
        
        # Якщо зображення занадто велике, зменшуємо його
        MAX_SIZE = 1600  # зменшимо до 1600 для кращої швидкості
        if image.size[0] > MAX_SIZE or image.size[1] > MAX_SIZE:
            image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
            print(f"Зображення зменшено до: {image.size}")
        
        # Конвертуємо в grayscale для кращого розпізнавання
        if image.mode != 'L':
            image = image.convert('L')
            print("Конвертовано в grayscale")
        
        # Збільшуємо контраст
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.5)  # збільшено з 2.0
        
        # Збільшуємо яскравість
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.3)  # збільшено з 1.2
        
        # Збільшуємо різкість
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)  # збільшено з 1.5
        
        # Бінаризація (чорно-біле)
        threshold = 150
        image = image.point(lambda p: p > threshold and 255)
        
        # Видаляємо шум
        image = image.filter(ImageFilter.MedianFilter(size=1))
        
        print("Попередня обробка зображення завершена")
        return image
        
    except Exception as e:
        print(f"Помилка при обробці зображення: {e}")
        traceback.print_exc()
        return image

def fix_common_ocr_errors(text):
    """Виправлення поширених помилок OCR"""
    if not text:
        return text
    
    # Словник для виправлення помилок OCR
    ocr_corrections = {
        # Російські літери
        'і': 'и', 'І': 'И', 'ї': 'й', 'Ї': 'Й',
        'є': 'е', 'Є': 'Е',
        # Поширені помилки в косметиці
        'mma': 'мя', 'mmaoe': 'мягкое', 'mmaкоe': 'мягкое',
        'moющaя': 'моющее', 'moющaя:': 'моющее:',
        '3': 'з', 'Оміоріде': 'Emulgade', 'Варечеебатае': 'Cocoate',
        'року': 'року', 'года': 'года',
        'йорожная': 'дорогая', 'йорожная,': 'дорогая,',
        'ха': 'на', 'хо': 'но',
        # Латинські літери
        'аqua': 'aqua', 'Аqua': 'Aqua', 'АQUA': 'AQUA',
        'sodlum': 'sodium', 'Sodlum': 'Sodium',
        'laureth': 'laureth', 'Laureth': 'Laureth',
        'sulfate': 'sulfate', 'Sulfate': 'Sulfate',
        'glycerln': 'glycerin', 'Glycerln': 'Glycerin',
        'раrrum': 'parfum', 'Раrrum': 'Parfum',
        'peg-4': 'peg-4', 'PEG-4': 'PEG-4',
        'edta': 'edta', 'EDTA': 'EDTA',
        'сіtric': 'citric', 'Сіtric': 'Citric',
        'acld': 'acid', 'Acld': 'Acid',
        'methylchloroiscthiazoline': 'methylchloroisothiazolinone',
        'methylisothiazollnone': 'methylisothiazolinone',
        'methylisothiazolino': 'methylisothiazolinone',
        'cocamidopropyl': 'cocamidopropyl',
        'betaine': 'betaine', 'Betaine': 'Betaine',
        'coco': 'coco', 'Coco': 'Coco',
        'glucoside': 'glucoside', 'Glucoside': 'Glucoside',
        'acrylates': 'acrylates', 'Acrylates': 'Acrylates',
        'copolymer': 'copolymer', 'Copolymer': 'Copolymer',
        'hydrolyzed': 'hydrolyzed', 'Hydrolyzed': 'Hydrolyzed',
        'silk': 'silk', 'Silk': 'Silk',
        'protein': 'protein', 'Protein': 'Protein',
    }
    
    for wrong, correct in ocr_corrections.items():
        text = text.replace(wrong, correct)
    
    return text

def clean_text(text):
    """Очищення та форматування розпізнаного тексту"""
    if not text:
        return ""
    
    print(f"Очистка тексту ({len(text)} символів)")
    
    # Виправляємо помилки OCR
    text = fix_common_ocr_errors(text)
    
    # Видаляємо зайві пробіли
    text = ' '.join(text.split())
    
    # Зберігаємо основні знаки пунктуації та хімічні символи
    text = re.sub(r'[^\w\s.,!?;:()\-–/&%+@*#=\[\]°\d]', ' ', text)
    
    # Видаляємо поодинокі літери та цифри на початку рядків
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Зберігаємо рядки з хімічними назвами або що містять більше 3 символів
        if len(line) > 3 or any(c.isalpha() for c in line):
            # Перевіряємо, що це не тільки цифри або символи
            if re.search(r'[a-zA-Zа-яА-Я]', line):
                cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Видаляємо повторювані пробіли
    text = re.sub(r'\s+', ' ', text)
    
    # Виправляємо регістр для хімічних назв
    # Всі хімічні назви повинні починатися з великої літери
    def capitalize_chemical(match):
        word = match.group(0)
        # Якщо слово схоже на хімічну назву (містить великі літери або цифри)
        if re.search(r'[A-Z]', word) or re.search(r'\d', word):
            # Робимо першу літеру великою, решту - малими
            return word[0].upper() + word[1:].lower() if len(word) > 1 else word
        return word
    
    # Знаходимо слова, які можуть бути хімічними назвами
    words = text.split()
    corrected_words = []
    for word in words:
        # Якщо слово містить латинські літери та цифри - це ймовірно хімічна назва
        if re.search(r'[a-zA-Z]', word) and (re.search(r'[A-Z]', word) or re.search(r'\d', word)):
            # Зберігаємо регістр для хімічних назв
            corrected_words.append(word)
        else:
            corrected_words.append(word)
    
    text = ' '.join(corrected_words)
    
    print(f"Текст очищено, залишилося {len(text)} символів")
    if text:
        print(f"Перші 200 символів: {text[:200]}...")
    
    return text.strip()

def extract_text(file):
    """Головна функція для розпізнавання тексту"""
    try:
        print(f"Початок OCR обробки файлу: {file.filename if hasattr(file, 'filename') else 'unknown'}")
        
        # Читаємо файл в пам'ять
        file.stream.seek(0)
        file_bytes = io.BytesIO(file.stream.read())
        
        file_bytes.seek(0)
        
        # Перевіряємо, що файл не порожній
        if file_bytes.getbuffer().nbytes == 0:
            print("Файл порожній")
            return ""
        
        # Відкриваємо зображення
        try:
            image = Image.open(file_bytes)
            print(f"Зображення відкрито, формат: {image.format}, розмір: {image.size}, режим: {image.mode}")
        except Exception as e:
            print(f"Не вдалося відкрити зображення: {e}")
            return ""
        
        # Попередня обробка зображення
        processed_image = preprocess_image(image)
        
        print("Запуск Tesseract OCR...")
        start_time = time.time()
        
        # Зберігаємо проміжне зображення для налагодження
        debug_dir = 'ocr_debug'
        os.makedirs(debug_dir, exist_ok=True)
        debug_path = os.path.join(debug_dir, f'processed_{int(time.time())}.jpg')
        processed_image.save(debug_path)
        print(f"Оброблене зображення збережено: {debug_path}")
        
        try:
            # Пробуємо кілька режимів OCR для кращого результату
            texts = []
            
            # Режим 1: стандартний
            text1 = pytesseract.image_to_string(
                processed_image, 
                config=custom_config,
                timeout=30
            )
            texts.append(("standard", text1))
            
            # Режим 2: тільки латинський (для хімічних назв)
            text2 = pytesseract.image_to_string(
                processed_image,
                config=r'--oem 3 --psm 6 -l eng',
                timeout=30
            )
            texts.append(("english_only", text2))
            
            # Режим 3: тільки російський (для описів)
            text3 = pytesseract.image_to_string(
                processed_image,
                config=r'--oem 3 --psm 6 -l rus',
                timeout=30
            )
            texts.append(("russian_only", text3))
            
            elapsed_time = time.time() - start_time
            
            print(f"OCR завершено за {elapsed_time:.2f} секунд")
            
            # Вибираємо найкращий результат
            best_text = ""
            best_score = 0
            
            for mode, text in texts:
                if text:
                    # Оцінюємо якість тексту
                    # Більше літер та менше незрозумілих символів = краще
                    alpha_count = sum(1 for c in text if c.isalpha())
                    space_count = text.count(' ')
                    total_chars = len(text)
                    
                    if total_chars > 0:
                        score = (alpha_count / total_chars) * 100
                        if score > best_score:
                            best_score = score
                            best_text = text
                            print(f"  {mode}: {len(text)} символів, оцінка: {score:.1f}%")
            
            if not best_text:
                best_text = text1  # fallback
            
            print(f"Вибрано найкращий результат: {len(best_text)} символів")
            
            if best_text:
                # Показуємо частину розпізнаного тексту
                preview = best_text[:300].replace('\n', ' ')
                print(f"Попередній перегляд: {preview}...")
            
        except RuntimeError as timeout_error:
            elapsed_time = time.time() - start_time
            print(f"Таймаут OCR через {elapsed_time:.2f} секунд: {timeout_error}")
            return "OCR перевищив час очікування. Спробуйте зображення меншого розміру або кращої якості."
        
        except Exception as e:
            print(f"Помилка Tesseract: {e}")
            traceback.print_exc()
            return ""
        
        # Очищення пам'яті
        image.close()
        processed_image.close()
        file_bytes.close()
        
        # Очищення тексту
        cleaned_text = clean_text(best_text)
        
        if not cleaned_text or len(cleaned_text.strip()) < 20:
            print("OCR повернув замало тексту або порожній результат")
            return cleaned_text
        
        print(f"OCR успішно завершено, розпізнано {len(cleaned_text)} символів")
        return cleaned_text
        
    except Exception as e:
        print(f"КРИТИЧНА ПОМИЛКА в OCR: {e}")
        traceback.print_exc()
        return ""