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
    print(f"🔧 Используется Tesseract из: {pytesseract.pytesseract.tesseract_cmd}")

# Конфигурация Tesseract с украинским, русским и английским
custom_config = r'--oem 3 --psm 6 -l ukr+rus+eng'

def preprocess_image(image):
    """Попередня обробка зображення для покращення OCR"""
    try:
        print(f"🖼️ Исходный размер изображения: {image.size}")
        
        # Если изображение слишком большое, уменьшаем его
        MAX_SIZE = 1600  # уменьшим до 1600 для лучшей скорости
        if image.size[0] > MAX_SIZE or image.size[1] > MAX_SIZE:
            image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
            print(f"🖼️ Изображение уменьшено до: {image.size}")
        
        # Конвертуємо в grayscale для кращого розпізнавання
        if image.mode != 'L':
            image = image.convert('L')
            print("🖼️ Конвертировано в grayscale")
        
        # Увеличиваем контраст
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.5)  # увеличено с 2.0
        
        # Увеличиваем яркость
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.3)  # увеличено с 1.2
        
        # Увеличиваем резкость
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)  # увеличено с 1.5
        
        # Бинаризация (черно-белое)
        threshold = 150
        image = image.point(lambda p: p > threshold and 255)
        
        # Удаляем шум
        image = image.filter(ImageFilter.MedianFilter(size=1))
        
        print("✅ Предобработка изображения завершена")
        return image
        
    except Exception as e:
        print(f"❌ Помилка при обробці зображення: {e}")
        traceback.print_exc()
        return image

def fix_common_ocr_errors(text):
    """Исправление частых ошибок OCR"""
    if not text:
        return text
    
    # Словарь для исправления ошибок OCR
    ocr_corrections = {
        # Русские буквы
        'і': 'и', 'І': 'И', 'ї': 'й', 'Ї': 'Й',
        'є': 'е', 'Є': 'Е',
        # Частые ошибки в косметике
        'mma': 'мя', 'mmaoe': 'мягкое', 'mmaкоe': 'мягкое',
        'moющaя': 'моющее', 'moющaя:': 'моющее:',
        '3': 'з', 'Оміоріде': 'Emulgade', 'Варечеебатае': 'Cocoate',
        'року': 'року', 'года': 'года',
        'йорожная': 'дорогая', 'йорожная,': 'дорогая,',
        'ха': 'на', 'хо': 'но',
        # Латинские буквы
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
    
    print(f"🧹 Очистка текста ({len(text)} символов)")
    
    # Исправляем ошибки OCR
    text = fix_common_ocr_errors(text)
    
    # Удаляем лишние пробелы
    text = ' '.join(text.split())
    
    # Сохраняем основные знаки препинания и химические символы
    text = re.sub(r'[^\w\s.,!?;:()\-–/&%+@*#=\[\]°\d]', ' ', text)
    
    # Удаляем одиночные буквы и цифры в начале строк
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Сохраняем строки с химическими названиями или содержащие более 3 символов
        if len(line) > 3 or any(c.isalpha() for c in line):
            # Проверяем, что это не только цифры или символы
            if re.search(r'[a-zA-Zа-яА-Я]', line):
                cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Удаляем повторяющиеся пробелы
    text = re.sub(r'\s+', ' ', text)
    
    # Исправляем регистр для химических названий
    # Все химические названия должны начинаться с заглавной буквы
    def capitalize_chemical(match):
        word = match.group(0)
        # Если слово похоже на химическое название (содержит заглавные буквы или цифры)
        if re.search(r'[A-Z]', word) or re.search(r'\d', word):
            # Делаем первую букву заглавной, остальные - строчными
            return word[0].upper() + word[1:].lower() if len(word) > 1 else word
        return word
    
    # Находим слова, которые могут быть химическими названиями
    words = text.split()
    corrected_words = []
    for word in words:
        # Если слово содержит латинские буквы и цифры - это вероятно химическое название
        if re.search(r'[a-zA-Z]', word) and (re.search(r'[A-Z]', word) or re.search(r'\d', word)):
            # Сохраняем регистр для химических названий
            corrected_words.append(word)
        else:
            corrected_words.append(word)
    
    text = ' '.join(corrected_words)
    
    print(f"✅ Текст очищен, осталось {len(text)} символов")
    if text:
        print(f"📄 Первые 200 символов: {text[:200]}...")
    
    return text.strip()

def extract_text(file):
    """Головна функція для розпізнавання тексту"""
    try:
        print(f"\n🔍 Начало OCR обработки файла: {file.filename if hasattr(file, 'filename') else 'unknown'}")
        
        # Читаем файл в память
        file.stream.seek(0)
        file_bytes = io.BytesIO(file.stream.read())
        
        file_bytes.seek(0)
        
        # Проверяем, что файл не пустой
        if file_bytes.getbuffer().nbytes == 0:
            print("❌ Файл пустой")
            return ""
        
        # Открываем изображение
        try:
            image = Image.open(file_bytes)
            print(f"✅ Изображение открыто, формат: {image.format}, размер: {image.size}, режим: {image.mode}")
        except Exception as e:
            print(f"❌ Не удалось открыть изображение: {e}")
            return ""
        
        # Предобработка изображения
        processed_image = preprocess_image(image)
        
        print("🔄 Запуск Tesseract OCR...")
        start_time = time.time()
        
        # Сохраняем промежуточное изображение для отладки
        debug_dir = 'ocr_debug'
        os.makedirs(debug_dir, exist_ok=True)
        debug_path = os.path.join(debug_dir, f'processed_{int(time.time())}.jpg')
        processed_image.save(debug_path)
        print(f"💾 Обработанное изображение сохранено: {debug_path}")
        
        try:
            # Пробуем несколько режимов OCR для лучшего результата
            texts = []
            
            # Режим 1: стандартный
            text1 = pytesseract.image_to_string(
                processed_image, 
                config=custom_config,
                timeout=30
            )
            texts.append(("standard", text1))
            
            # Режим 2: только латинский (для химических названий)
            text2 = pytesseract.image_to_string(
                processed_image,
                config=r'--oem 3 --psm 6 -l eng',
                timeout=30
            )
            texts.append(("english_only", text2))
            
            # Режим 3: только русский (для описаний)
            text3 = pytesseract.image_to_string(
                processed_image,
                config=r'--oem 3 --psm 6 -l rus',
                timeout=30
            )
            texts.append(("russian_only", text3))
            
            elapsed_time = time.time() - start_time
            
            print(f"✅ OCR завершен за {elapsed_time:.2f} секунд")
            
            # Выбираем лучший результат
            best_text = ""
            best_score = 0
            
            for mode, text in texts:
                if text:
                    # Оцениваем качество текста
                    # Больше букв и меньше непонятных символов = лучше
                    alpha_count = sum(1 for c in text if c.isalpha())
                    space_count = text.count(' ')
                    total_chars = len(text)
                    
                    if total_chars > 0:
                        score = (alpha_count / total_chars) * 100
                        if score > best_score:
                            best_score = score
                            best_text = text
                            print(f"  {mode}: {len(text)} chars, score: {score:.1f}%")
            
            if not best_text:
                best_text = text1  # fallback
            
            print(f"📝 Выбран лучший результат: {len(best_text)} символов")
            
            if best_text:
                # Показываем часть распознанного текста
                preview = best_text[:300].replace('\n', ' ')
                print(f"📄 Предпросмотр: {preview}...")
            
        except RuntimeError as timeout_error:
            elapsed_time = time.time() - start_time
            print(f"⏰ Таймаут OCR через {elapsed_time:.2f} секунд: {timeout_error}")
            return "OCR превысил время ожидания. Попробуйте изображение меньшего размера или лучшего качества."
        
        except Exception as e:
            print(f"❌ Ошибка Tesseract: {e}")
            traceback.print_exc()
            return ""
        
        # Очистка памяти
        image.close()
        processed_image.close()
        file_bytes.close()
        
        # Очистка текста
        cleaned_text = clean_text(best_text)
        
        if not cleaned_text or len(cleaned_text.strip()) < 20:
            print("⚠️ OCR вернул слишком мало текста или пустой результат")
            return cleaned_text
        
        print(f"✅ OCR успешно завершен, распознано {len(cleaned_text)} символов")
        return cleaned_text
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в OCR: {e}")
        traceback.print_exc()
        return ""