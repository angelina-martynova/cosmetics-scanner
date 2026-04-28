import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import re
import os
import time
import traceback
import numpy as np

# ═══════════════════════════════════════════════════════════════════
# ЗАЛЕЖНОСТІ З GRACEFUL FALLBACK
# ═══════════════════════════════════════════════════════════════════

# OpenCV — покращена попередня обробка (CLAHE, bilateral filter, deskew)
try:
    import cv2
    CV2_AVAILABLE = True
    print("[OCR] OpenCV підключено — покращена обробка зображень активна")
except ImportError:
    CV2_AVAILABLE = False
    print("[OCR] OpenCV не встановлено — базова PIL-обробка. "
          "Встановіть: pip install opencv-python-headless")

# EasyOCR — нейронна мережа для розпізнавання тексту (PyTorch-based)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    print("[OCR] EasyOCR підключено — нейромережеве розпізнавання активне")
except ImportError:
    EASYOCR_AVAILABLE = False
    print("[OCR] EasyOCR не встановлено — використовується Tesseract. "
          "Встановіть: pip install easyocr")

# TrOCR — Transformer-based OCR від Microsoft (Hugging Face)
# Архітектура: Vision Encoder (ViT/DeiT) + Text Decoder (RoBERTa)
# Найвища точність серед OCR-моделей на складних зображеннях
try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    import torch
    TROCR_AVAILABLE = True
    print("[OCR] TrOCR підключено — transformer-based розпізнавання активне")
except ImportError:
    TROCR_AVAILABLE = False
    print("[OCR] TrOCR не встановлено — використовується EasyOCR/Tesseract. "
          "Встановіть: pip install transformers torch")

# Для Windows
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Конфігурація Tesseract
TESSERACT_CONFIG_MULTI = r'--oem 3 --psm 6 -l ukr+rus+eng'
TESSERACT_CONFIG_ENG = r'--oem 3 --psm 6 -l eng'

# Lazy-init EasyOCR reader
_easyocr_reader = None

# Lazy-init TrOCR (transformer model + processor)
_trocr_processor = None
_trocr_model = None


def _get_easyocr_reader():
    """Ліниве завантаження EasyOCR reader.

    EasyOCR базується на архітектурі CRNN:
      - CNN (ResNet) витягує візуальні ознаки
      - BiLSTM аналізує послідовність символів
      - CTC-декодер формує текст без сегментації символів

    Принципова відмінність від Tesseract: не потребує ідеальної
    бінаризації, краще працює з шумом, бліками та нахилом.
    """
    global _easyocr_reader
    if _easyocr_reader is None and EASYOCR_AVAILABLE:
        print("[OCR] Завантаження EasyOCR моделі...")
        start = time.time()
        try:
            _easyocr_reader = easyocr.Reader(
                ['en'], gpu=False, verbose=False
            )
            print(f"[OCR] EasyOCR завантажено за {time.time()-start:.1f}с")
        except Exception as e:
            print(f"[OCR] Помилка EasyOCR: {e}")
    return _easyocr_reader


# ═══════════════════════════════════════════════════════════════════
# ПОПЕРЕДНЯ ОБРОБКА ЗОБРАЖЕННЯ
# ═══════════════════════════════════════════════════════════════════

def preprocess_image(image):
    """Попередня обробка зображення для покращення OCR.

    Pipeline (OpenCV):
      1. Resize
      2. Grayscale
      3. Deskew — виправлення нахилу
      4. CLAHE — локальне вирівнювання контрасту
      5. Bilateral filter — шумозаглушення зі збереженням країв
      6. Unsharp masking — підвищення різкості
      7. Морфологічне закриття
      8. Адаптивна бінаризація
    """
    try:
        MAX_SIZE = 2000
        if image.size[0] > MAX_SIZE or image.size[1] > MAX_SIZE:
            image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)

        if CV2_AVAILABLE:
            return _preprocess_opencv(image)
        else:
            return _preprocess_pil(image)
    except Exception as e:
        print(f"[Preprocess] Помилка: {e}")
        traceback.print_exc()
        return image


def _preprocess_opencv(image):
    """Покращена обробка через OpenCV.

    CLAHE: локальне вирівнювання контрасту. На відміну від глобального
    вирівнювання, CLAHE розбиває зображення на блоки та вирівнює контраст
    локально. Критично для фото етикеток де частина тексту у тіні.

    Bilateral filter: зберігає чіткість країв символів. Використовує два
    Гаусівських ядра — просторове та за інтенсивністю — тому пікселі
    з різкою зміною яскравості (краї букв) не згладжуються.

    Adaptive threshold: обчислює поріг для кожного пікселя на основі його
    околу. Значно краще для етикеток з нерівномірним освітленням.
    """
    img_array = np.array(image)

    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    print("[OpenCV] Pipeline обробки:")

    # 1. Deskew
    gray = _deskew(gray)

    # 2. CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    print("  [2/6] CLAHE")

    # 3. Bilateral filter
    denoised = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    print("  [3/6] Bilateral filter")

    # 4. Unsharp masking
    gaussian = cv2.GaussianBlur(denoised, (0, 0), 3)
    sharpened = cv2.addWeighted(denoised, 1.5, gaussian, -0.5, 0)
    print("  [4/6] Unsharp masking")

    # 5. Морфологічне закриття
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    morphed = cv2.morphologyEx(sharpened, cv2.MORPH_CLOSE, kernel)
    print("  [5/6] Морфологічне закриття")

    # 6. Адаптивна бінаризація
    binary = cv2.adaptiveThreshold(
        morphed, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=21, C=10
    )
    print("  [6/6] Адаптивна бінаризація")

    return Image.fromarray(binary)


def _deskew(gray_image):
    """Виправлення нахилу тексту через minAreaRect.

    Алгоритм:
      1. Бінаризація (Оцу)
      2. Знаходження координат ненульових пікселів
      3. minAreaRect визначає кут нахилу
      4. Поворот зображення (тільки для кутів 0.5°—15°)
    """
    try:
        _, thresh = cv2.threshold(gray_image, 0, 255,
                                  cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(thresh > 0))

        if len(coords) < 100:
            print("  [1/6] Deskew — пропущено (мало пікселів)")
            return gray_image

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.5 or abs(angle) > 15:
            print(f"  [1/6] Deskew — {angle:.1f}° (пропущено)")
            return gray_image

        h, w = gray_image.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        rotated = cv2.warpAffine(gray_image, M, (w, h),
                                  flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
        print(f"  [1/6] Deskew — виправлено {angle:.1f}°")
        return rotated
    except Exception as e:
        print(f"  [1/6] Deskew — помилка: {e}")
        return gray_image


def _preprocess_pil(image):
    """Базова обробка через PIL (fallback)."""
    if image.mode != 'L':
        image = image.convert('L')

    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.5)
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.3)
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)

    image = image.point(lambda p: p > 150 and 255)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    print("[PIL] Обробка завершена")
    return image


# ═══════════════════════════════════════════════════════════════════
# OCR ДВИЖКИ
# ═══════════════════════════════════════════════════════════════════

def _ocr_easyocr(image):
    """Розпізнавання через EasyOCR (CRNN нейромережа)."""
    reader = _get_easyocr_reader()
    if reader is None:
        return None
    try:
        img_array = np.array(image)
        results = reader.readtext(
            img_array, detail=1, paragraph=False,
            min_size=20, text_threshold=0.7,
            low_text=0.4, width_ths=0.7
        )
        if not results:
            return None

        results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))

        text_parts = []
        total_conf = 0
        for bbox, text, confidence in results:
            if confidence > 0.3 and text.strip():
                text_parts.append(text.strip())
                total_conf += confidence

        if not text_parts:
            return None

        avg_conf = total_conf / len(text_parts)
        full_text = ' '.join(text_parts)
        print(f"[EasyOCR] {len(text_parts)} фрагментів, "
              f"впевненість: {avg_conf:.0%}, {len(full_text)} символів")
        return full_text
    except Exception as e:
        print(f"[EasyOCR] Помилка: {e}")
        return None


def _get_trocr():
    """Ліниве завантаження TrOCR моделі та процесора.

    TrOCR (Transformer-based OCR) — архітектура від Microsoft:
      - Vision Encoder (DeiT/ViT): розбиває зображення на патчі 16×16 пікселів,
        кожен патч перетворюється у вектор ознак. Механізм самоуваги (self-attention)
        аналізує зв'язки між УСІМА патчами одночасно — на відміну від CNN у EasyOCR,
        яка бачить лише локальне оточення кожного пікселя.
      - Text Decoder (RoBERTa): авторегресивно генерує текст символ за символом,
        враховуючи контекст усіх попередніх символів. Це дозволяє виправляти
        помилки на рівні мовної моделі.

    Перевага над EasyOCR/Tesseract:
      - Глобальний контекст замість локального (бачить усе зображення)
      - Вбудована мовна модель виправляє OCR-артефакти
      - Найвища точність на benchmark-ах (IAM, SROIE)
    """
    global _trocr_processor, _trocr_model
    if _trocr_processor is None and TROCR_AVAILABLE:
        print("[OCR] Завантаження TrOCR моделі (перший запуск ~60с)...")
        start = time.time()
        try:
            model_name = "microsoft/trocr-base-printed"
            _trocr_processor = TrOCRProcessor.from_pretrained(model_name)
            _trocr_model = VisionEncoderDecoderModel.from_pretrained(model_name)
            _trocr_model.eval()  # Режим інференсу (без dropout)
            print(f"[OCR] TrOCR завантажено за {time.time()-start:.1f}с")
        except Exception as e:
            print(f"[OCR] Помилка завантаження TrOCR: {e}")
            _trocr_processor = None
            _trocr_model = None
    return _trocr_processor, _trocr_model


def _ocr_trocr(image):
    """Розпізнавання через TrOCR (Vision Transformer + Text Decoder).

    TrOCR працює порядково: зображення розрізається на горизонтальні смуги,
    кожна смуга розпізнається окремо. Це пов'язано з тим, що модель натренована
    на однорядкових фрагментах тексту.

    Для етикеток косметики цей підхід ефективний, бо список інгредієнтів
    зазвичай розташований рядками або через кому в горизонтальних блоках.
    """
    processor, model = _get_trocr()
    if processor is None or model is None:
        return None

    try:
        # Конвертуємо в RGB якщо потрібно
        if image.mode != 'RGB':
            image = image.convert('RGB')

        img_array = np.array(image)
        h, w = img_array.shape[:2]

        # Розбиваємо на менше смуг для швидкості
        # Замість h//15 (~15 смуг) беремо h//8 (~8 смуг)
        line_height = max(60, h // 8)
        overlap = 10  # Мінімальне перекриття

        lines_text = []
        y = 0
        while y < h:
            y_end = min(y + line_height, h)
            if h - y_end < line_height // 2:
                y_end = h  # Захоплюємо залишок

            line_crop = image.crop((0, y, w, y_end))

            # TrOCR inference
            pixel_values = processor(
                images=line_crop, return_tensors="pt"
            ).pixel_values

            with torch.no_grad():
                generated_ids = model.generate(
                    pixel_values,
                    max_new_tokens=128
                )

            line_text = processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0].strip()

            if line_text and len(line_text) > 1:
                lines_text.append(line_text)

            y = y_end - overlap if y_end < h else h

        if not lines_text:
            return None

        full_text = ' '.join(lines_text)
        print(f"[TrOCR] {len(lines_text)} рядків, {len(full_text)} символів")
        return full_text

    except Exception as e:
        print(f"[TrOCR] Помилка: {e}")
        traceback.print_exc()
        return None


def _ocr_tesseract(image, config=None):
    """Розпізнавання через Tesseract OCR."""
    try:
        return pytesseract.image_to_string(
            image, config=config or TESSERACT_CONFIG_MULTI, timeout=30
        )
    except Exception as e:
        print(f"[Tesseract] Помилка: {e}")
        return None


def _ocr_tesseract_multimode(processed_image):
    """Мультирежимний Tesseract — вибір найкращого результату."""
    configs = [
        ("multi_lang", TESSERACT_CONFIG_MULTI),
        ("english", TESSERACT_CONFIG_ENG),
    ]
    best_text, best_score = "", 0

    for name, config in configs:
        text = _ocr_tesseract(processed_image, config)
        if text:
            alpha = sum(1 for c in text if c.isalpha())
            total = len(text)
            score = (alpha / total * 100) if total else 0
            if score > best_score:
                best_score = score
                best_text = text
                print(f"  [{name}] {total} символів, якість: {score:.0f}%")
    return best_text


# ═══════════════════════════════════════════════════════════════════
# ENSEMBLE OCR
# ═══════════════════════════════════════════════════════════════════

def _ensemble_ocr(original_image, processed_image):
    """Швидкий Ensemble OCR: пріоритетний запуск з ранньою зупинкою.

    Замість запуску всіх трьох движків послідовно (TrOCR ~30с + EasyOCR ~10с
    + Tesseract ~5с = ~45с), використовуємо стратегію раннього виходу:
    
      1. EasyOCR (швидший за TrOCR, краще для реальних фото)
      2. Якщо EasyOCR дав хороший результат (INCI-score ≥ 3) → ЗУПИНЯЄМОСЬ
      3. Інакше → Tesseract як fallback
      4. TrOCR використовується ТІЛЬКИ якщо обидва дали поганий результат
    
    Це зменшує час обробки з ~45с до ~10-15с у типовому випадку.
    """
    results = {}
    inci_kw = {
        'aqua', 'water', 'sodium', 'glycerin', 'acid', 'parfum',
        'fragrance', 'alcohol', 'oil', 'extract', 'butter', 'oxide',
        'sulfate', 'chloride', 'hydroxide', 'stearate', 'cetyl',
        'lauryl', 'laureth', 'cocamidopropyl', 'betaine', 'glucoside',
        'dimethicone', 'tocopherol', 'panthenol', 'phenoxyethanol',
        'carbomer', 'xanthan', 'acrylates', 'polysorbate',
    }

    def _inci_score(text):
        lo = text.lower()
        return sum(1 for kw in inci_kw if kw in lo) + text.count(',') * 0.5

    # ─── Етап 1: EasyOCR (CRNN, ~8-12с, найкращий баланс) ───
    if EASYOCR_AVAILABLE:
        print("[Ensemble] Етап 1: EasyOCR...")
        t = time.time()
        text = _ocr_easyocr(original_image)
        if text:
            score = _inci_score(text)
            results['easyocr'] = (text, score)
            print(f"[Ensemble] EasyOCR: {len(text)} символів, "
                  f"INCI={score:.1f}, {time.time()-t:.1f}с")
            # Рання зупинка: якщо знайдено ≥3 INCI-слова — результат достатній
            if score >= 3:
                print(f"[Ensemble] ✓ EasyOCR достатній (INCI≥3), пропускаємо інші")
                return text

    # ─── Етап 2: Tesseract (LSTM, ~3-5с, швидкий fallback) ───
    print("[Ensemble] Етап 2: Tesseract...")
    t = time.time()
    text = _ocr_tesseract_multimode(processed_image)
    if text:
        score = _inci_score(text)
        results['tesseract'] = (text, score)
        print(f"[Ensemble] Tesseract: {len(text)} символів, "
              f"INCI={score:.1f}, {time.time()-t:.1f}с")

    # ─── Етап 3: TrOCR ТІЛЬКИ якщо попередні дали поганий результат ───
    best_so_far = max((s for _, s in results.values()), default=0)
    if TROCR_AVAILABLE and best_so_far < 2:
        print("[Ensemble] Етап 3: TrOCR (попередні результати слабкі)...")
        t = time.time()
        text = _ocr_trocr(original_image)
        if text:
            score = _inci_score(text)
            results['trocr'] = (text, score)
            print(f"[Ensemble] TrOCR: {len(text)} символів, "
                  f"INCI={score:.1f}, {time.time()-t:.1f}с")
    elif TROCR_AVAILABLE:
        print(f"[Ensemble] TrOCR пропущено (вже є результат з INCI={best_so_far:.1f})")

    if not results:
        return ""

    # Вибираємо найкращий за INCI-метрикою
    best_src = max(results, key=lambda k: results[k][1])
    best_text = results[best_src][0]
    print(f"[Ensemble] ✓ Обрано: {best_src} (INCI={results[best_src][1]:.1f})")
    return best_text


# ═══════════════════════════════════════════════════════════════════
# ВИПРАВЛЕННЯ ПОМИЛОК OCR
# ═══════════════════════════════════════════════════════════════════

def fix_common_ocr_errors(text):
    """Виправлення помилок OCR для INCI-назв."""
    if not text:
        return text

    cyrillic_to_latin = {
        'а': 'a', 'с': 'c', 'е': 'e', 'о': 'o', 'р': 'p',
        'у': 'y', 'х': 'x', 'А': 'A', 'С': 'C', 'Е': 'E',
        'О': 'O', 'Р': 'P', 'Н': 'H', 'К': 'K', 'Т': 'T',
        'В': 'B', 'М': 'M',
    }

    corrections = {
        'sodlum': 'sodium', 'glycerln': 'glycerin',
        'раrfum': 'parfum', 'parfume': 'parfum',
        'acld': 'acid', 'сіtric': 'citric',
        'аqua': 'aqua', 'peg4': 'peg-4',
        'edta.': 'edta', 'hydrotyzed': 'hydrolyzed',
        'methylchloroiscthiazoline': 'methylchloroisothiazolinone',
        'methylisothiazollnone': 'methylisothiazolinone',
    }

    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)

    # Виправлення змішаних кириличних/латинських символів
    words = text.split()
    fixed = []
    for word in words:
        lat = sum(1 for c in word if c.isascii() and c.isalpha())
        cyr = sum(1 for c in word if '\u0400' <= c <= '\u04FF')
        if lat > 2 and cyr > 0 and lat > cyr:
            word = ''.join(cyrillic_to_latin.get(c, c) for c in word)
        fixed.append(word)

    return ' '.join(fixed)


def clean_text(text):
    """Очищення розпізнаного тексту."""
    if not text:
        return ""

    text = fix_common_ocr_errors(text)
    text = ' '.join(text.split())
    text = re.sub(r'[^\w\s.,!?;:()\-\u2013/&%+@*#=\[\]\u00B0\d]', ' ', text)

    lines = text.split('\n')
    cleaned = [l.strip() for l in lines
               if len(l.strip()) > 3 and re.search(r'[a-zA-Z\u0400-\u04FF]', l)]

    text = re.sub(r'\s+', ' ', '\n'.join(cleaned))
    # Мягкая фильтрация: удаляем только целые строки, которые
    # являются типичными адресными/контактными паттернами
    address_patterns = [
        r'^\s*COSRX\s*(INC\.|GLOBAL)?\s*$',
        r'^\s*RP\s*Biorius\s*$',
        r'^\s*Seoul\s*,\s*Korea\s*$',
        r'^\s*Wavre\s*,\s*BE\s*$',
        r'^\s*London\s+WC[EH]\d+\s+\d*[A-Z]{2}\s*,\s*GB\s*$',
        r'^\s*\d{5,}\s*$',  # чистый индекс
        r'^\s*www\..*\s*$',
        r'^\s*FSC\s*Mix\s*$',
    ]
    lines = text.split('\n')
    filtered = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Если строка полностью соответствует одному из адресных шаблонов – пропускаем
        if any(re.match(p, stripped, re.IGNORECASE) for p in address_patterns):
            continue
        filtered.append(line)
    text = '\n'.join(filtered)
    
    return text.strip()


# ═══════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ
# ═══════════════════════════════════════════════════════════════════

def extract_text(file):
    """Головна функція: зображення → текст.

    Pipeline:
      1. Завантаження зображення
      2. Попередня обробка (OpenCV або PIL)
      3. Ensemble OCR (EasyOCR + Tesseract)
      4. Очищення та корекція
    """
    try:
        filename = file.filename if hasattr(file, 'filename') else 'unknown'
        print(f"\n{'='*60}")
        print(f"[OCR] Обробка: {filename}")
        print(f"{'='*60}")

        total_start = time.time()

        file.stream.seek(0)
        file_bytes = io.BytesIO(file.stream.read())
        file_bytes.seek(0)

        if file_bytes.getbuffer().nbytes == 0:
            return ""

        try:
            image = Image.open(file_bytes)
        except Exception as e:
            print(f"[OCR] Не вдалося відкрити: {e}")
            return ""

        original_image = image.copy()
        processed_image = preprocess_image(image)

        # # Debug
        # debug_dir = 'ocr_debug'
        # os.makedirs(debug_dir, exist_ok=True)
        # processed_image.save(
        #     os.path.join(debug_dir, f'processed_{int(time.time())}.jpg')
        # )

        raw_text = _ensemble_ocr(original_image, processed_image)

        image.close()
        original_image.close()
        processed_image.close()
        file_bytes.close()

        cleaned_text = clean_text(raw_text)
        elapsed = time.time() - total_start

        print(f"[OCR] ✓ Готово за {elapsed:.1f}с, {len(cleaned_text)} символів")
        return cleaned_text

    except Exception as e:
        print(f"[OCR] КРИТИЧНА ПОМИЛКА: {e}")
        traceback.print_exc()
        return ""
