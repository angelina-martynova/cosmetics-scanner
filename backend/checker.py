# checker.py — покращена інтеграція з зовнішніми БД
"""
Модуль аналізу складу косметичних продуктів.

Покращення:
  - PubChem тепер повертає реальний ризик на основі GHS/токсичності.
  - Зовнішні дані активно використовуються: ризик, категорія, CAS, опис.
  - Автозбереження в базу зберігає розширені поля (cas_number, ewg_score).
  - Більше ніякого перевизначення зовнішніх описів евристиками.
"""

import re
import json
import requests
from datetime import datetime, timedelta, timezone
import sqlite3
import os
import traceback

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
    print("RapidFuzz підключено — нечіткий пошук активний")
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("RapidFuzz не встановлено — використовується точний пошук. "
          "Встановіть: pip install rapidfuzz")

# --- ML-фільтр ---
try:
    from ingredient_classifier import is_ingredient as ml_is_ingredient
    ML_CLASSIFIER_AVAILABLE = True
except ImportError:
    ML_CLASSIFIER_AVAILABLE = False
    def ml_is_ingredient(text):
        return True


# ═══════════════════════════════════════════════════════════════════
# ЕВРИСТИКИ КЛАСИФІКАЦІЇ ТА РИЗИКУ
# ═══════════════════════════════════════════════════════════════════

def classify_by_name(name_lower):
    """Евристична класифікація інгредієнта за ключовими словами у назві."""
    rules = [
        (['sulfate', 'glucoside', 'betaine', 'isethionate', 'sarcosinate',
          'taurate', 'amphoacetate'], 'surfactant'),
        (['paraben', 'phenoxy', 'benzoate', 'sorbate', 'isothiazolinone',
          'hydantoin', 'imidazolidinyl'], 'preservative'),
        (['parfum', 'fragrance', 'limonene', 'linalool', 'citronellol',
          'geraniol', 'eugenol', 'coumarin'], 'fragrance'),
        (['alcohol', 'glycol', 'ethanol'], 'solvent'),
        (['oil', 'butter', 'squalane', 'dimethicone', 'siloxane',
          'triglyceride', 'ester'], 'emollient'),
        (['titanium', 'zinc oxide', 'avobenzone', 'octinoxate',
          'oxybenzone', 'homosalate', 'octocrylene'], 'UV filter'),
        (['acid', 'retinol', 'niacinamide', 'peptide', 'ceramide',
          'hyaluronic'], 'active'),
        (['extract', 'juice', 'flower', 'leaf', 'root', 'bark',
          'seed', 'fruit'], 'plant extract'),
        (['polymer', 'copolymer', 'acrylate', 'carbomer',
          'gum', 'cellulose'], 'thickener'),
        (['glycerin', 'urea', 'sorbitol', 'mannitol',
          'saccharide'], 'humectant'),
        (['stearate', 'cetearyl', 'glyceryl', 'polysorbate',
          'sorbitan', 'lecithin'], 'emulsifier'),
        (['edta', 'phytic', 'gluconate'], 'chelating agent'),
        (['citric acid', 'lactic acid', 'sodium hydroxide',
          'triethanolamine'], 'pH adjuster'),
        (['ci ', 'ci7', 'color', 'yellow', 'red no', 'blue no',
          'iron oxide'], 'colorant'),
    ]
    for keywords, category in rules:
        if any(kw in name_lower for kw in keywords):
            return category
    return 'unknown'


def assess_risk_by_name(name_lower):
    """Евристична оцінка ризику інгредієнта за ключовими словами у назві."""
    high_risk = ['formaldehyde', 'isothiazolinone', 'triclosan',
                 'oxybenzone', 'benzophenone', 'hydroquinone',
                 'toluene', 'phthalate', 'mercury', 'lead']
    medium_risk = ['paraben', 'parfum', 'fragrance', 'alcohol denat',
                   'sulfate', 'glycol', 'triethanolamine', 'phenoxyethanol',
                   'dea', 'mea', 'tea ', 'peg-', 'edta',
                   'limonene', 'linalool', 'citronellol']
    low_risk = ['glycerin', 'benzoate', 'sorbate', 'dioxide', 'oxide',
                'acid', 'oil', 'extract', 'butter', 'stearate',
                'cetyl', 'carbomer', 'gum', 'cellulose', 'silica',
                'dimethicone', 'glucoside', 'betaine']
    safe_risk = ['aqua', 'water', 'aloe', 'vitamin', 'ceramide',
                 'panthenol', 'allantoin', 'centella', 'tocopherol',
                 'squalane', 'jojoba', 'shea', 'hyaluronic',
                 'niacinamide', 'bisabolol']

    if any(kw in name_lower for kw in high_risk):
        return 'high'
    if any(kw in name_lower for kw in medium_risk):
        return 'medium'
    if any(kw in name_lower for kw in safe_risk):
        return 'safe'
    if any(kw in name_lower for kw in low_risk):
        return 'low'
    return 'unknown'


# ═══════════════════════════════════════════════════════════════════
# КОРОТКІ ОПИСИ ЗА КАТЕГОРІЯМИ
# ═══════════════════════════════════════════════════════════════════
CATEGORY_PHRASES_UK = {
    'surfactant': 'Поверхнево-активна речовина (ПАР)',
    'preservative': 'Консервант',
    'fragrance': 'Ароматизатор, ароматична добавка',
    'solvent': 'Розчинник',
    'emollient': "Пом'якшувальний компонент",
    'UV filter': 'УФ-фільтр (сонцезахисний компонент)',
    'active': 'Активний компонент для шкіри',
    'plant extract': 'Рослинний екстракт',
    'thickener': 'Загущувач',
    'humectant': 'Зволожувач (утримує вологу)',
    'emulsifier': 'Емульгатор (стабілізує суміш)',
    'chelating agent': 'Хелатуючий агент (стабілізатор)',
    'pH adjuster': 'Регулятор кислотності (pH)',
    'colorant': 'Барвник',
    'unknown': 'Невідомий компонент (дані відсутні)',
}

CATEGORY_PHRASES_EN = {
    'surfactant': 'Surfactant (cleansing agent)',
    'preservative': 'Preservative',
    'fragrance': 'Fragrance / aromatic additive',
    'solvent': 'Solvent',
    'emollient': 'Emollient (softening agent)',
    'UV filter': 'UV filter (sun protection)',
    'active': 'Active ingredient for skin',
    'plant extract': 'Plant extract',
    'thickener': 'Thickener',
    'humectant': 'Humectant (moisture‑binding)',
    'emulsifier': 'Emulsifier (stabilizes mixtures)',
    'chelating agent': 'Chelating agent (stabilizer)',
    'pH adjuster': 'pH adjuster',
    'colorant': 'Colorant / pigment',
    'unknown': 'Unknown ingredient (no data available)',
}


def _make_description(category, risk, lang='uk'):
    phrases = CATEGORY_PHRASES_UK if lang == 'uk' else CATEGORY_PHRASES_EN
    base = phrases.get(category, phrases['unknown'])
    if risk in ('high', 'medium'):
        if lang == 'uk':
            risk_note = ' (високий ризик)' if risk == 'high' else ' (помірний ризик)'
        else:
            risk_note = ' (high risk)' if risk == 'high' else ' (moderate risk)'
        return base + risk_note
    return base


# ═══════════════════════════════════════════════════════════════════
# ОСНОВНИЙ КЛАС
# ═══════════════════════════════════════════════════════════════════

class IngredientChecker:
    def __init__(self, use_cache=True, fallback_to_local=True, auto_save_unknown=True):
        self.use_cache = use_cache
        self.fallback_to_local = fallback_to_local
        self.auto_save_unknown = auto_save_unknown

        self.local_ingredients = self._load_ingredients_from_db()
        self.ocr_fixes = self._load_ocr_fixes_from_db()
        self.external_sources = ExternalDataFetcher()

        self.search_cache = {}
        self.stop_words = self._load_stop_words()

        self._build_fuzzy_index()
        print(f"IngredientChecker ініціалізований: "
              f"{len(self.local_ingredients)} інгредієнтів, "
              f"{len(self._alias_index)} аліасів, "
              f"{len(self.ocr_fixes)} OCR-виправлень")

    # --- Завантаження даних ---
    def _load_ingredients_from_db(self):
        try:
            from app import app
            from models import Ingredient
            with app.app_context():
                ingredients = []
                for ing in Ingredient.query.all():
                    ingredients.append({
                        "id": ing.id,
                        "name": ing.name,
                        "inci_name": ing.inci_name or ing.name,
                        "risk_level": ing.risk_level,
                        "category": ing.category,
                        "description": ing.description,
                        "description_en": ing.description_en or "",
                        "cas_number": ing.cas_number,
                        "ewg_score": ing.ewg_score,
                        "eu_max_concentration": ing.eu_max_concentration,
                        "is_banned_eu": ing.is_banned_eu,
                        "verified": ing.verified,
                        "source": "database",
                    })
                if ingredients:
                    print(f"  Завантажено {len(ingredients)} інгредієнтів з БД")
                    return ingredients
        except Exception as e:
            print(f"  Не вдалося завантажити з БД: {e}")
        return self._fallback_ingredients()

    def _load_aliases_from_db(self):
        alias_map = {}
        try:
            from app import app
            from models import IngredientAlias, Ingredient
            with app.app_context():
                aliases = (IngredientAlias.query
                           .join(Ingredient)
                           .all())
                for a in aliases:
                    ing = a.ingredient
                    alias_map[a.alias_lower] = {
                        "id": ing.id,
                        "name": ing.name,
                        "inci_name": ing.inci_name or ing.name,
                        "risk_level": ing.risk_level,
                        "category": ing.category,
                        "description": ing.description,
                        "description_en": ing.description_en or "",
                        "cas_number": ing.cas_number,
                        "ewg_score": ing.ewg_score,
                        "verified": ing.verified,
                        "source": "database",
                        "alias_type": a.alias_type,
                    }
                print(f"  Завантажено {len(alias_map)} аліасів з БД")
        except Exception as e:
            print(f"  Не вдалося завантажити аліаси: {e}")
        return alias_map

    def _load_ocr_fixes_from_db(self):
        fixes = {}
        try:
            from app import app
            from models import IngredientAlias
            with app.app_context():
                ocr_aliases = IngredientAlias.query.filter_by(alias_type='ocr_fix').all()
                for a in ocr_aliases:
                    fixes[a.alias_lower] = a.ingredient.name
                print(f"  Завантажено {len(fixes)} OCR-виправлень з БД")
        except Exception as e:
            print(f"  Не вдалося завантажити OCR-виправлення: {e}")

        base_fixes = {
            "sodlum": "sodium", "glycerln": "glycerin", "parfume": "parfum",
            "hydrotyzed": "hydrolyzed", "аqua": "aqua",
            "2-hexanediol": "1,2-hexanediol",
            "hexanediol-2": "1,2-hexanediol",
            "dipotassium gly-cyrrhizate": "dipotassium glycyrrhizate",
            "gly-cyrrhizate": "glycyrrhizate",
        }
        for wrong, correct in base_fixes.items():
            if wrong not in fixes:
                fixes[wrong] = correct
        return fixes

    def _fallback_ingredients(self):
        fallback = [
            {"id": 1, "name": "Aqua", "risk_level": "safe", "category": "solvent",
             "description": "Вода, основа косметичних засобів", "source": "fallback"},
            {"id": 2, "name": "Glycerin", "risk_level": "low", "category": "humectant",
             "description": "Гліцерин, натуральний зволожувач", "source": "fallback"},
            {"id": 3, "name": "Sodium Laureth Sulfate", "risk_level": "medium", "category": "surfactant",
             "description": "SLES, піноутворювач", "source": "fallback"},
            {"id": 4, "name": "Parfum", "risk_level": "medium", "category": "fragrance",
             "description": "Ароматизатор", "source": "fallback"},
        ]
        print(f"  Використовується аварійний список ({len(fallback)} записів)")
        return fallback

    def _load_stop_words(self):
        return {
            'склад', 'інгредієнти', 'ingredients', 'inci', 'composition', 'formula',
            'продукт', 'продукція', 'product', 'назва', 'виробник', 'виготовлювач',
            'упаковка', 'пакування', 'пакет', 'пляшка', 'туба', 'флакон',
            'косметична', 'гігієнічна', 'миюча', 'крем-мило', 'рідке',
            'гост', 'гст', 'призначено', 'зовнішнього',
            'застосування', 'якість', 'гарант',
            'промити', 'чистою', 'водою', 'використовувати', 'випадку',
            'виникнення', 'алергічної', 'реакції', 'подразнення',
            'особистої', 'гігієни', 'зберігати', 'температурі', 'сонячних',
            'променів', 'щільно', 'закритим',
            'термін', 'придатності', 'придатний', 'зберігання', 'дата',
            'рік', 'місяць', 'маса', 'нетто', 'вага',
            "об'єм", 'кількість', 'алергени', 'алерген', 'може', 'містити', 'сліди',
            'умови', 'температура', 'вироблено', 'для', 'країна',
            'походження', 'україна', 'адреса', 'контакти',
            'телефон', 'штрихкод', 'код', 'партія', 'серія',
            'мл', 'л', 'г', 'кг', 'мг', 'шт', '%',
            'та', 'і', 'або', 'чи', 'на', 'в', 'у', 'з', 'зі', 'від', 'до', 'про',
            'для', 'за', 'під', 'над', 'перед', 'після', 'через',
            'який', 'яка', 'яке', 'які', 'що', 'це', 'той', 'такий',
        }

    # --- Індекси ---
    def _build_fuzzy_index(self):
        self._exact_index = {}
        self._alias_index = {}
        self._all_names = []

        for ingredient in self.local_ingredients:
            name_lower = ingredient['name'].lower()
            self._exact_index[name_lower] = ingredient
            self._all_names.append(name_lower)

            inci = ingredient.get('inci_name', '')
            if inci and inci.lower() != name_lower:
                inci_lower = inci.lower()
                self._exact_index[inci_lower] = ingredient
                self._all_names.append(inci_lower)

        db_aliases = self._load_aliases_from_db()
        for alias_lower, ingredient_dict in db_aliases.items():
            if alias_lower not in self._exact_index:
                self._alias_index[alias_lower] = ingredient_dict
                self._all_names.append(alias_lower)

        print(f"  Fuzzy-індекс: {len(self._exact_index)} назв + "
              f"{len(self._alias_index)} аліасів = {len(self._all_names)} записів")

    # --- Очищення тексту ---
    def clean_text(self, text):
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^a-zA-Z0-9а-яА-ЯіІїЇєЄґҐ\s\-.,]', ' ', text)
        text = re.sub(r'\s+', ' ', text)

        for wrong, correct in self.ocr_fixes.items():
            if wrong in text:
                text = text.replace(wrong, correct.lower())
        return text.strip()

    def _fix_line_breaks(self, text):
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
        return text

    # --- Фільтр кандидатів ---
    def is_potential_ingredient(self, text):
        if not text or len(text) < 3:
            return False
        text_lower = text.lower().strip()
        if text_lower in self.stop_words:
            return False
        if len(text) > 100:
            return False

        stop_phrases = [
            'isntree', 'clinically proven', 'non-irritating',
            'an emulsion', 'how to use', 'at the last stage',
            'apply proper amount', 'until absorbed', 'cautions for use',
            'if skin irritations', 'seek immediate medical',
            'do not apply on wounded area', 'cautions for storage',
            'keep out of reach', 'keep out of direct sunlight',
            'the manufacturing number', 'expiration date',
            'manufacturing distributor', 'manufacturer',
            'republic of korea', 'made in', 'distributed by',
        ]
        if any(phrase in text_lower for phrase in stop_phrases):
            return False

        words = text.split()
        if len(words) >= 2 and all(w[0].isupper() for w in words if w):
            inci_suffixes = ['ate', 'ide', 'one', 'ene', 'ol', 'ic', 'in', 'ium', 'ester', 'acid', 'gum']
            if not any(text_lower.endswith(suf) for suf in inci_suffixes):
                return False

        postal_regexes = [
            r'\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b',
            r'\b[A-Z]{2,3}\d?[A-Z]?\s?\d[A-Z]{2}\b',
            r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b',
            r'\b\d{5}(-\d{4})?\b',
            r'\b\d{5,6}\b',
        ]
        if any(re.search(p, text) for p in postal_regexes):
            return False

        country_codes = {
            'uk', 'gb', 'be', 'fr', 'de', 'us', 'ca', 'it', 'es', 'pt', 'nl',
            'ru', 'ua', 'pl', 'cz', 'sk', 'hu', 'ro', 'bg', 'gr', 'se', 'no',
            'dk', 'fi', 'ee', 'lv', 'lt', 'jp', 'kr', 'cn', 'in', 'br', 'au', 'nz',
            'ch', 'at', 'ie', 'mx', 'ar', 'tr'
        }
        city_names = {
            'london', 'paris', 'berlin', 'tokyo', 'seoul', 'toronto', 'sydney',
            'kyiv', 'kiev', 'moscow', 'москва', 'київ', 'киев',
            'new york', 'los angeles', 'chicago', 'washington', 'san francisco',
            'warsaw', 'praha', 'vienna', 'budapest', 'bucuresti', 'sofia',
            'рим', 'мадрид', 'берлин', 'варшава', 'париж'
        }
        if re.fullmatch(r'[A-Za-zА-Яа-я\s/,\-]+', text):
            tokens = re.split(r'[\s/,]+', text.strip())
            geo_keywords = {'область', 'област', 'республика', 'край', 'район',
                            'місто', 'село', 'смт', 'region', 'district', 'city',
                            'province', 'state', 'county'}
            if tokens and all(
                t.lower() in country_codes or
                t.lower() in city_names or
                t.lower() in geo_keywords or
                (len(t) <= 2 and t.isupper())
                for t in tokens if t
            ):
                return False

        single_country = {
            'україна', 'ukraine', 'россия', 'russia', 'беларусь', 'belarus',
            'сша', 'usa', 'канада', 'canada', 'великобритания', 'uk',
            'франция', 'france', 'германия', 'germany', 'италия', 'italy',
            'испания', 'spain', 'польша', 'poland'
        }
        if text_lower.strip() in single_country:
            return False

        non_ingredient_markers = [
            'building', 'kesson', 'eonju-ro', 'inc.', 'ltd.', 'co.',
            'gmbh', 'distributor', 'expiration',
            'cautions', 'keep out', 'sunlight', 'reach of',
            'manufactured', 'address', 'tel', 'fax', 'zip', 'city',
            'country', 'part no', 'lot no', 'batch', 'www.', '.com',
            '©', '®', '™', 'please', 'visit', 'our website',
            'contact', 'phone', 'inquiries', 'head office',
            'street', 'road', 'avenue', 'blvd', 'drive',
            'apt', 'suite', 'postal', 'code', 'po box',
        ]
        if any(marker in text_lower for marker in non_ingredient_markers):
            return False

        if text.isdigit():
            return False

        if re.match(r'^\d', text) and not re.match(r'^ci\s*\d+', text_lower):
            if not re.search(r'[a-zA-Z]{3,}', text):
                return False

        has_latin = bool(re.search(r'[a-zA-Z]', text))
        has_cyrillic = bool(re.search(r'[а-яА-ЯіІїЇєЄ]', text))
        if has_cyrillic and has_latin:
            latin_count = sum(1 for c in text if c.isascii() and c.isalpha())
            if latin_count < 4:
                return False

        if len(words) == 1 or '-' in text:
            chemical_suffixes = [
                'ate', 'ide', 'one', 'ene', 'ol', 'ic', 'in', 'ose',
                'ium', 'ester', 'oil', 'acid', 'al', 'ane',
            ]
            for suffix in chemical_suffixes:
                if text_lower.endswith(suffix) and len(text) > 3:
                    return True
            if re.search(r'\d', text):
                return True
            if text_lower in self._exact_index or text_lower in self._alias_index:
                return True

        if 2 <= len(words) <= 4:
            marketing_words = [
                'продукція', 'косметична', 'гігієнічна', 'призначено',
                'зберігати', 'виготовлювач', 'росія', 'область', 'україна',
            ]
            if not any(mw in text_lower for mw in marketing_words):
                if re.search(r'[a-zA-Z]', text):
                    if ML_CLASSIFIER_AVAILABLE and len(words) >= 2:
                        if not ml_is_ingredient(text):
                            return False
                    return True
        return False

    # --- Виділення кандидатів ---
    def _split_into_ingredient_phrases(self, text_without_delimiters):
        tokens = text_without_delimiters.split()
        if not tokens:
            return []

        phrases = []
        idx = 0
        max_phrase_len = 6

        while idx < len(tokens):
            best_len = 0
            best_phrase = None

            for length in range(min(max_phrase_len, len(tokens) - idx), 0, -1):
                candidate_words = tokens[idx:idx+length]
                candidate_phrase = ' '.join(candidate_words)
                candidate_lower = candidate_phrase.lower()

                if candidate_lower in self._exact_index or candidate_lower in self._alias_index:
                    best_len = length
                    best_phrase = candidate_phrase
                    break

                if not best_phrase:
                    for name in self._exact_index:
                        if candidate_lower in name or name in candidate_lower:
                            best_len = length
                            best_phrase = candidate_phrase
                            break

                if not best_phrase and RAPIDFUZZ_AVAILABLE and len(candidate_lower) >= 4:
                    result = process.extractOne(
                        candidate_lower, self._all_names,
                        scorer=fuzz.token_sort_ratio,
                        score_cutoff=85
                    )
                    if result:
                        best_len = length
                        best_phrase = candidate_phrase
                        break

            if best_phrase:
                phrases.append(best_phrase)
                idx += best_len
            else:
                single_word = tokens[idx]
                phrases.append(single_word)
                idx += 1

        return phrases

    def _find_known_phrases(self, text):
        """
        Шукає в тексті всі входження відомих назв інгредієнтів
        (точні, аліаси, fuzzy) і повертає список знайдених фраз
        у порядку їх появи.
        """
        found = []
        text_lower = text.lower()
        # Спочатку точні збіги та аліаси
        for name in sorted(self._exact_index, key=len, reverse=True):
            idx = 0
            while True:
                pos = text_lower.find(name, idx)
                if pos == -1:
                    break
                original = text[pos:pos+len(name)]
                found.append((pos, len(name), original))
                idx = pos + 1
        for alias in sorted(self._alias_index, key=len, reverse=True):
            idx = 0
            while True:
                pos = text_lower.find(alias, idx)
                if pos == -1:
                    break
                original = text[pos:pos+len(alias)]
                if not any(f[0] <= pos < f[0]+f[1] for f in found):
                    found.append((pos, len(alias), original))
                idx = pos + 1

        # Fuzzy‑пошук тільки якщо rapidfuzz доступний і кандидатів мало
        if RAPIDFUZZ_AVAILABLE and len(found) < 5:
            for word in text.split():
                if len(word) < 4:
                    continue
                result = process.extractOne(word, self._all_names, scorer=fuzz.ratio, score_cutoff=85)
                if result:
                    name = result[0]
                    pos = text_lower.find(name)
                    if pos != -1 and not any(f[0] <= pos < f[0]+len(name) for f in found):
                        original = text[pos:pos+len(name)]
                        found.append((pos, len(name), original))

        found.sort(key=lambda x: x[0])
        # Видаляємо перетинаючі (залишаємо довше)
        filtered = []
        for pos, length, phrase in found:
            if not filtered or pos >= filtered[-1][0] + filtered[-1][1]:
                filtered.append((pos, length, phrase))
            else:
                if length > filtered[-1][1]:
                    filtered[-1] = (pos, length, phrase)
        return [phrase for _, _, phrase in filtered]

    def extract_ingredient_candidates(self, text):
        if not text:
            return []
        print(f"Виділення кандидатів з тексту ({len(text)} символів)")

        # Стандартний пошук розділу "Ingredients"
        composition_start = -1
        composition_patterns = [
            r'СКЛАД\s*[:\-]', r'INGREDIENTS\s*[:\-]', r'INCI\s*[:\-]',
            r'СОСТАВ\s*[:\-]', r'ІНГРЕДІЄНТИ\s*[:\-]',
            r'COMPOSITION\s*[:\-]', r'КОМПОЗИЦІЯ\s*[:\-]',
        ]
        for pattern in composition_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                composition_start = match.end()
                print(f"  Знайдено розділ 'СКЛАД' у позиції {composition_start}")
                break

        if composition_start == -1:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if ',' in line and any(w in line.upper() for w in
                                       ['AQUA', 'SODIUM', 'GLYCERIN', 'PARFUM', 'WATER', 'ALCOHOL']):
                    composition_start = sum(len(l) + 1 for l in lines[:i])
                    print(f"  Знайдено список інгредієнтів у рядку {i + 1}")
                    break

        if composition_start != -1:
            end_patterns = [
                r'\n\s*\d+\.', r'\n{2,}', r'\.\s*\n',
                r'Зберігати|Хранить', r'УМОВИ',
                r'ВИГОТОВЛЮВАЧ|ИЗГОТОВИТЕЛЬ',
                r'www\.|http://', r'©|™|®', r'ТЕРМІН|СРОК',
            ]
            end_pos = len(text)
            for pattern in end_patterns:
                match = re.search(pattern, text[composition_start:], re.IGNORECASE | re.MULTILINE)
                if match:
                    potential_end = composition_start + match.start()
                    if potential_end < end_pos:
                        end_pos = potential_end
            ingredients_text = text[composition_start:end_pos].strip()
        else:
            ingredients_text = text

        # Базова очистка
        ingredients_text = re.sub(r'[^\w\s.,;:\-–/()\n]', ' ', ingredients_text)
        ingredients_text = re.sub(r'\s+', ' ', ingredients_text)
        ingredients_text = ingredients_text.replace(':', ';')
        ingredients_text = ingredients_text.replace('*', ';')
        ingredients_text = ingredients_text.replace('+', ';')
        ingredients_text = re.sub(r'\s+\.\s+', ' ; ', ingredients_text)

        has_delimiters = bool(re.search(r'[;,\.\+*]', ingredients_text))

        # Стандартне розбиття за роздільниками
        candidates = []
        items = re.split(r'[,;]', ingredients_text)

        marketing_keywords = [
            'продукція', 'косметична', 'гігієнічна', 'миюча',
            'крем-мило', 'рідке', 'призначено', 'зовнішнього',
            'застосування', 'зберігати', 'температурі', 'сонячних', 'променів',
            'виготовлювач', 'якість', 'гарант', 'область', 'район',
            'промити', 'чистою', 'водою', 'використовувати', 'випадку',
            'виникнення', 'алергічної', 'реакції', 'подразнення',
        ]

        for item in items:
            item = item.strip()
            if not item or len(item) < 3:
                continue
            item_lower = item.lower()
            if any(kw in item_lower for kw in marketing_keywords):
                continue
            has_latin = bool(re.search(r'[a-zA-Z]', item))
            has_cyrillic = bool(re.search(r'[а-яА-ЯіІїЇєЄ]', item))
            if has_latin and has_cyrillic and len(item) < 50:
                continue
            if re.search(r'\d{2,}', item) and not re.search(r'ci\s*\d+', item_lower):
                continue
            if self.is_potential_ingredient(item):
                candidates.append(item)

        # ЗАВЖДИ запускаємо пошук за відомими назвами (з бази та аліасів)
        print("  Додатковий пошук за базою інгредієнтів...")
        known_phrases = self._find_known_phrases(ingredients_text)
        for phrase in known_phrases:
            if phrase not in candidates and self.is_potential_ingredient(phrase):
                candidates.append(phrase)

        # Якщо все ще мало, додаємо окремі слова (крім стоп-слів)
        if len(candidates) < 3:
            words = ingredients_text.split()
            for w in words:
                w = w.strip()
                if w and w.lower() not in self.stop_words and self.is_potential_ingredient(w):
                    if w not in candidates:
                        candidates.append(w)

        # Видалення дублікатів
        unique = []
        seen = set()
        for c in candidates:
            c_lower = c.lower()
            if c_lower not in seen:
                seen.add(c_lower)
                unique.append(c)

        print(f"  Знайдено {len(unique)} унікальних кандидатів")
        return unique

    # --- Локальний пошук ---
    def _search_local(self, ingredient_name):
        ingredient_lower = ingredient_name.lower().strip()
        if not ingredient_lower or len(ingredient_lower) < 2:
            return None, None, None

        exact = self._exact_index.get(ingredient_lower)
        if exact:
            return exact, 'exact', 100.0

        alias_match = self._alias_index.get(ingredient_lower)
        if alias_match:
            return alias_match, 'alias', 100.0

        if len(ingredient_lower) > 4:
            for name, ingredient in self._exact_index.items():
                if len(name) > 4 and (ingredient_lower in name or name in ingredient_lower):
                    return ingredient, 'substring', 90.0

        if RAPIDFUZZ_AVAILABLE and len(ingredient_lower) >= 4:
            return self._fuzzy_search(ingredient_lower)

        return None, None, None

    def _fuzzy_search(self, query):
        if not RAPIDFUZZ_AVAILABLE or not self._all_names:
            return None, None, None

        threshold = 85 if len(query) <= 10 else 78

        result_token = process.extractOne(
            query, self._all_names,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold,
        )
        result_partial = process.extractOne(
            query, self._all_names,
            scorer=fuzz.partial_ratio,
            score_cutoff=threshold + 5,
        )

        best_name = None
        best_score = 0.0

        if result_token and result_token[1] > best_score:
            best_name = result_token[0]
            best_score = result_token[1]
        if result_partial and result_partial[1] * 0.95 > best_score:
            best_name = result_partial[0]
            best_score = result_partial[1] * 0.95

        if best_name:
            ingredient = (self._exact_index.get(best_name)
                          or self._alias_index.get(best_name))
            if ingredient:
                print(f"    ✓ Fuzzy: '{query}' → '{ingredient['name']}' "
                      f"(score: {best_score:.0f}%)")
                return ingredient, 'fuzzy', best_score

        return None, None, None

    # --- Основний пошук ---
    def search_ingredient(self, ingredient_name):
        if not ingredient_name or not isinstance(ingredient_name, str):
            return self._create_not_found_response(ingredient_name or "")

        ingredient_name = ingredient_name.strip()
        cache_key = ingredient_name.lower()

        if cache_key in self.search_cache:
            cached = self.search_cache[cache_key]
            if datetime.now() - cached['timestamp'] < timedelta(hours=24):
                return cached['data']

        cleaned_name = self.clean_text(ingredient_name)

        local_result, match_type, match_score = self._search_local(ingredient_name)
        if not local_result and cleaned_name != ingredient_name.lower():
            local_result, match_type, match_score = self._search_local(cleaned_name)

        if local_result:
            result = dict(local_result)
            result['match_type'] = match_type
            result['match_score'] = match_score
            self._cache(cache_key, result, 'local')
            return result

        if self.use_cache:
            try:
                external_result = self.external_sources.search(ingredient_name)
                if external_result and external_result.get('source') != 'not_found':
                    external_result['match_type'] = 'external'
                    external_result['match_score'] = None
                    self._cache(cache_key, external_result, 'external')

                    if self.auto_save_unknown:
                        self._auto_save_to_db(external_result)

                    return external_result
            except Exception as e:
                print(f"  Помилка зовнішнього пошуку: {e}")

        not_found = self._create_not_found_response(ingredient_name)
        self._cache(cache_key, not_found, 'not_found')
        return not_found

    def _cache(self, key, data, source):
        self.search_cache[key] = {
            'data': data,
            'timestamp': datetime.now(),
            'source': source,
        }

    def _create_not_found_response(self, ingredient_name):
        ingredient_lower = ingredient_name.lower() if ingredient_name else ""
        risk = assess_risk_by_name(ingredient_lower)
        category = classify_by_name(ingredient_lower)
        return {
            "name": ingredient_name,
            "risk_level": risk,
            "category": category,
            "description": _make_description(category, risk, lang='uk'),
            "description_en": _make_description(category, risk, lang='en'),
            "source": "heuristic",
            "match_type": "heuristic",
            "match_score": None,
            "aliases": [],
            "context": "Автоматична оцінка на основі назви",
        }

    # --- Автозбереження ---
    def _auto_save_to_db(self, ingredient_dict):
        try:
            from app import app
            from models import db, Ingredient
            with app.app_context():
                name = ingredient_dict.get('name', '')
                if not name:
                    return
                exists = Ingredient.query.filter_by(name=name).first()
                if exists:
                    return
                category = ingredient_dict.get('category', classify_by_name(name.lower()))
                risk = ingredient_dict.get('risk_level', assess_risk_by_name(name.lower()))
                source = ingredient_dict.get('source', 'external')
                cas = ingredient_dict.get('cas_number', None)
                ewg = ingredient_dict.get('ewg_score', None)
                desc_uk = ingredient_dict.get('description', _make_description(category, risk, lang='uk'))
                desc_en = ingredient_dict.get('description_en', _make_description(category, risk, lang='en'))

                new_ing = Ingredient(
                    name=name,
                    risk_level=risk,
                    category=category,
                    description=desc_uk,
                    description_en=desc_en,
                    source_of_risk_assessment=source,
                    cas_number=cas,
                    ewg_score=ewg,
                    verified=False,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(new_ing)
                db.session.commit()

                self.local_ingredients.append(new_ing.to_dict())
                name_lower = name.lower()
                self._exact_index[name_lower] = new_ing.to_dict()
                self._all_names.append(name_lower)

                print(f"    ✚ Авто-збережено: {name} (verified=False, джерело: {source})")
        except Exception as e:
            print(f"    Помилка авто-збереження: {e}")

    # --- Головна функція пошуку інгредієнтів у тексті ---
    def find_ingredients(self, text):
        if not text or not isinstance(text, str):
            print("Текст для аналізу порожній або не є рядком")
            return []

        print(f"Пошук інгредієнтів у тексті ({len(text)} символів)")

        # Склеюємо переноси
        text = self._fix_line_breaks(text)
        candidates = self.extract_ingredient_candidates(text)

        found_ingredients = []
        seen_names = set()

        for position, candidate in enumerate(candidates, start=1):
            ingredient = self.search_ingredient(candidate)

            if ingredient['name'] not in seen_names:
                ingredient['position'] = position
                found_ingredients.append(ingredient)
                seen_names.add(ingredient['name'])
                print(f"  #{position}: {ingredient['name']} "
                      f"(ризик: {ingredient['risk_level']}, "
                      f"збіг: {ingredient.get('match_type', '?')})")

        risk_stats = {'high': 0, 'medium': 0, 'low': 0, 'safe': 0, 'unknown': 0}
        for ing in found_ingredients:
            risk = ing.get('risk_level', 'unknown')
            if risk in risk_stats:
                risk_stats[risk] += 1

        print(f"ПІДСУМОК: {len(found_ingredients)} інгредієнтів | "
              f"високий: {risk_stats['high']} помірний: {risk_stats['medium']} "
              f"низький: {risk_stats['low']} безпечний: {risk_stats['safe']} "
              f"невідомий: {risk_stats['unknown']}")

        return found_ingredients


# ═══════════════════════════════════════════════════════════════════
# ExternalDataFetcher (використовуємо дані API)
# ═══════════════════════════════════════════════════════════════════

class ExternalDataFetcher:
    def __init__(self, cache_dir='data_cache'):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'external_cache.db')
        os.makedirs(cache_dir, exist_ok=True)
        self._init_cache()
        self.timeout = 8

    def _init_cache(self):
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingredients_cache (
                name TEXT PRIMARY KEY,
                data TEXT,
                source TEXT,
                last_updated TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def search(self, ingredient_name):
        if not ingredient_name or len(ingredient_name.strip()) < 3:
            return None
        ingredient_name = ingredient_name.strip()
        cached = self._get_from_cache(ingredient_name)
        if cached:
            return cached
        if not self._check_network():
            return None
        result = self._search_open_beauty_facts(ingredient_name)
        if not result:
            result = self._search_pubchem(ingredient_name)
        if not result:
            result = self._search_chebi(ingredient_name)
        if result:
            self._save_to_cache(ingredient_name, result)
        return result

    # --- OpenBeautyFacts ---
    def _search_open_beauty_facts(self, ingredient_name):
        try:
            search_name = ingredient_name.lower().replace(' ', '-')
            url = (f"https://world.openbeautyfacts.org/api/v2/search?"
                   f"ingredients_tags={search_name}&"
                   f"fields=product_name,ingredients&"
                   f"page_size=5&json=1")
            print(f"  [OBF] Запит: {ingredient_name}")
            response = requests.get(url, timeout=self.timeout, headers={
                'User-Agent': 'CosmeticsScanner/3.2 (ingredient checker)'
            })
            if response.status_code != 200:
                return self._search_obf_text(ingredient_name)

            data = response.json()
            products = data.get('products', [])
            if not products:
                return self._search_obf_text(ingredient_name)

            ingredient_lower = ingredient_name.lower()
            risk = assess_risk_by_name(ingredient_lower)
            category = classify_by_name(ingredient_lower)

            return {
                "name": ingredient_name,
                "risk_level": risk,
                "category": category,
                "description": _make_description(category, risk, lang='uk') + " (Open Beauty Facts)",
                "description_en": _make_description(category, risk, lang='en') + " (Open Beauty Facts)",
                "source": "openbeautyfacts",
                "aliases": [],
                "context": "Open Beauty Facts",
            }
        except requests.Timeout:
            print(f"  [OBF] Таймаут: {ingredient_name}")
            return None
        except Exception as e:
            print(f"  [OBF] Помилка: {e}")
            return None

    def _search_obf_text(self, ingredient_name):
        try:
            url = (f"https://world.openbeautyfacts.org/cgi/search.pl?"
                   f"search_terms={ingredient_name}&"
                   f"search_simple=1&action=process&json=1&page_size=3")
            response = requests.get(url, timeout=self.timeout, headers={
                'User-Agent': 'CosmeticsScanner/3.2'
            })
            if response.status_code != 200:
                return None
            data = response.json()
            count = data.get('count', 0)
            if count == 0:
                return None

            ingredient_lower = ingredient_name.lower()
            risk = assess_risk_by_name(ingredient_lower)
            category = classify_by_name(ingredient_lower)

            return {
                "name": ingredient_name,
                "risk_level": risk,
                "category": category,
                "description": _make_description(category, risk, lang='uk') + " (Open Beauty Facts)",
                "description_en": _make_description(category, risk, lang='en') + " (Open Beauty Facts)",
                "source": "openbeautyfacts",
                "aliases": [],
                "context": "Open Beauty Facts (текстовий пошук)",
            }
        except Exception as e:
            print(f"  [OBF text] Помилка: {e}")
            return None

    # --- PubChem (покращений) ---
    def _parse_pubchem_safety(self, compound_data):
        name_lower = compound_data.get("name", "").lower()
        hazard_text = ""
        for prop in compound_data.get("props", []):
            urn = prop.get("urn", {})
            label = urn.get("label", "")
            if label == "GHS Hazard Statement":
                hazard_text += " " + prop.get("value", {}).get("sval", "")
        combined = name_lower + hazard_text.lower()
        high_keywords = ["carcinogen", "mutagen", "toxic to reproduction",
                         "fatal", "very toxic", "dangerous for the environment"]
        medium_keywords = ["irritant", "harmful", "sensitizer", "allergen",
                           "skin irrit", "eye irrit", "respiratory irrit"]
        low_keywords = ["low hazard", "safe", "generally recognized as safe",
                        "gras", "nontoxic"]
        if any(kw in combined for kw in high_keywords):
            return ("high", "Містить позначки високої токсичності (GHS) / Contains high hazard statements")
        elif any(kw in combined for kw in medium_keywords):
            return ("medium", "Може викликати подразнення / May cause irritation")
        else:
            return ("low", "Низький ризик, без суттєвих токсикологічних позначок / Low hazard, no significant toxicity indicators")

    def _search_pubchem(self, ingredient_name):
        try:
            encoded_name = requests.utils.quote(ingredient_name)
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/JSON"
            print(f"  [PubChem] Запит: {ingredient_name}")
            response = requests.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return None
            data = response.json()
            compounds = data.get('PC_Compounds', [])
            if not compounds:
                return None

            compound = compounds[0]
            cid = compound.get('id', {}).get('id', {}).get('cid', '')
            iupac_name = ''
            mol_formula = ''
            cas_number = ''
            for prop in compound.get('props', []):
                urn = prop.get('urn', {})
                label = urn.get('label', '')
                if label == 'IUPAC Name' and urn.get('name') == 'Preferred':
                    iupac_name = prop.get('value', {}).get('sval', '')
                elif label == 'Molecular Formula':
                    mol_formula = prop.get('value', {}).get('sval', '')
                elif label == 'CAS Registry Number':
                    cas_number = prop.get('value', {}).get('sval', '')

            compound_data = {"name": ingredient_name, "props": compound.get("props", [])}
            risk, safety_info = self._parse_pubchem_safety(compound_data)

            desc_uk = f"Хімічна сполука (PubChem CID: {cid}). {safety_info}."
            desc_en = f"Chemical compound (PubChem CID: {cid}). {safety_info.split('/')[-1].strip()}"
            if mol_formula:
                desc_uk += f" Формула: {mol_formula}."
                desc_en += f" Formula: {mol_formula}."
            if iupac_name and iupac_name != ingredient_name:
                desc_uk += f" IUPAC: {iupac_name[:80]}."
                desc_en += f" IUPAC: {iupac_name[:80]}."
            if cas_number:
                desc_uk += f" CAS: {cas_number}."
                desc_en += f" CAS: {cas_number}."

            return {
                "name": ingredient_name,
                "risk_level": risk,
                "category": classify_by_name(ingredient_name.lower()),
                "description": desc_uk,
                "description_en": desc_en,
                "source": "pubchem",
                "aliases": [],
                "context": f"PubChem CID: {cid}",
                "cas_number": cas_number if cas_number else None,
                "ewg_score": None,
            }
        except requests.Timeout:
            print(f"  [PubChem] Таймаут: {ingredient_name}")
            return None
        except Exception as e:
            print(f"  [PubChem] Помилка: {e}")
            return None

    # --- ChEBI ---
    def _search_chebi(self, ingredient_name):
        try:
            encoded_name = requests.utils.quote(ingredient_name)
            url = (f"https://www.ebi.ac.uk/chebi/rest/compound/search?"
                   f"search={encoded_name}&format=json&limit=1")
            print(f"  [ChEBI] Запит: {ingredient_name}")
            response = requests.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return None
            data = response.json()
            results = data.get('results', [])
            if not results:
                return None

            entry = results[0]
            chebi_id = entry.get('chebiId', '')
            compound_name = entry.get('chebiName', ingredient_name)

            ingredient_lower = compound_name.lower()
            risk = assess_risk_by_name(ingredient_lower)
            category = classify_by_name(ingredient_lower)

            desc_uk = _make_description(category, risk, lang='uk')
            desc_en = _make_description(category, risk, lang='en')
            if chebi_id:
                desc_uk += f' (ChEBI ID: {chebi_id})'
                desc_en += f' (ChEBI ID: {chebi_id})'
            else:
                desc_uk += ' (ChEBI)'
                desc_en += ' (ChEBI)'

            return {
                "name": compound_name,
                "risk_level": risk,
                "category": category,
                "description": desc_uk,
                "description_en": desc_en,
                "source": "chebi",
                "aliases": [],
                "context": f"ChEBI ID: {chebi_id}" if chebi_id else "ChEBI",
            }
        except requests.Timeout:
            print(f"  [ChEBI] Таймаут: {ingredient_name}")
            return None
        except Exception as e:
            print(f"  [ChEBI] Помилка: {e}")
            return None

    # --- Кешування ---
    def _get_from_cache(self, ingredient_name):
        try:
            conn = sqlite3.connect(self.cache_file)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data FROM ingredients_cache "
                "WHERE name = ? AND last_updated > datetime('now', '-7 days')",
                (ingredient_name.lower(),)
            )
            result = cursor.fetchone()
            conn.close()
            if result:
                return json.loads(result[0])
            return None
        except Exception:
            return None

    def _save_to_cache(self, ingredient_name, data):
        try:
            conn = sqlite3.connect(self.cache_file)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO ingredients_cache "
                "(name, data, source, last_updated) "
                "VALUES (?, ?, ?, datetime('now'))",
                (ingredient_name.lower(),
                 json.dumps(data, ensure_ascii=False),
                 data.get('source', 'unknown'))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  [Cache] Помилка збереження: {e}")

    def _check_network(self):
        try:
            requests.head("https://world.openbeautyfacts.org", timeout=3)
            return True
        except (requests.ConnectionError, requests.Timeout):
            print("  [Network] Немає доступу до мережі")
            return False