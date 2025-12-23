import re
import json
import requests
from datetime import datetime, timedelta
import sqlite3
import os
import traceback


class IngredientChecker:
    def __init__(self, use_cache=True, fallback_to_local=True):
        print("🔄 Инициализация IngredientChecker...")
        self.local_ingredients = self.load_local_ingredients()
        self.common_fixes = self.load_common_fixes()
        
        # Внешние источники данных
        self.external_sources = ExternalDataFetcher()
        self.use_cache = use_cache
        self.fallback_to_local = fallback_to_local
        
        # Кэш для результатов поиска
        self.search_cache = {}
        
        # Расширенный список стоп-слов с маркетинговыми фразами
        self.stop_words = self._load_stop_words()
        
        print(f"✅ IngredientChecker инициализирован: {len(self.local_ingredients)} ингредиентов в базе")
    
    def _load_stop_words(self):
        """Загрузка расширенного списка стоп-слов"""
        stop_words = {
            # Общая маркировка
            'склад', 'інгредієнти', 'ingredients', 'inci', 'composition', 'formula',
            'продукт', 'продукція', 'product', 'назва', 'виробник', 'виготовлювач',
            'упаковка', 'пакування', 'пакет', 'пляшка', 'туба', 'флакон', 'крем-мило',
            
            # Маркетинговые фразы (из вашего примера)
            'продукция', 'косметическая', 'гигиеническая', 'моющая', 'гигиеническа',
            'крем-мыло', 'жидкое', 'гоСТ', 'гст', 'предназначено', 'наружного',
            'применения', 'изготовитель', 'качество', 'гарант', 'воронежская',
            'область', 'район', 'хохольский', 'промыть', 'чистой', 'водой',
            'использовать', 'случае', 'возникновения', 'аллергической', 'реакции',
            'раздражения', 'личной', 'гигиены', 'хранить', 'температуре', 'солнечных',
            'лучей', 'плотно', 'закрытым', 'эфко', 'косметик', 'россия', 'вопросы',
            'качества', 'органічний', 'екологічний',
            
            # Единицы и техническая информация
            'термін', 'придатності', 'придатний', 'зберігання', 'дата', 'рік',
            'місяць', 'кінець', 'вжити', 'до', 'кінця', 'маса', 'нетто', 'вага',
            'об\'єм', 'кількість', 'алергени', 'алерген', 'може', 'містити', 'сліди',
            'умови', 'температура', 'холодильник', 'вироблено', 'для', 'країна',
            'походження', 'україна', 'експортер', 'імпортер', 'адреса', 'контакти',
            'телефон', 'штрихкод', 'код', 'партія', 'серія', 'поживна', 'цінність',
            'енергетична', 'ккал', 'кдж', 'білки', 'жири', 'вуглеводи', 'цукор', 'сіль',
            
            # Единицы измерения
            'мл', 'л', 'г', 'кг', 'мг', 'мкг', 'од', 'таблетка', 'капсула',
            'шт', '%', 'відсотків', 'грам', 'мілілітр',
            
            # Предлоги и союзы
            'та', 'і', 'або', 'чи', 'на', 'в', 'у', 'з', 'зі', 'від', 'до', 'про',
            'для', 'за', 'під', 'над', 'перед', 'після', 'через', 'який', 'яка',
            'яке', 'які', 'що', 'це', 'той', 'такий',
        }
        return stop_words
    
    def load_local_ingredients(self):
        """Загрузка локальной базы ингредиентов"""
        print("📚 Загрузка локальной базы ингредиентов...")
        ingredients = [
            # 🔴 HIGH RISK
            {
                "id": 4, "name": "Formaldehyde", "risk_level": "high", "category": "preservative",
                "description": "Канцероген 1-го класса, запрещен в косметике во многих странах",
                "aliases": ["formaldehyde", "formalin", "формальдегід", "формалін"],
                "source": "local", "context": "Запрещен в ЕС в косметике для детей"
            },
            {
                "id": 5, "name": "Methylisothiazolinone", "risk_level": "high", "category": "preservative",
                "description": "Сильнейший аллерген, запрещен в несмываемой косметике в ЕС",
                "aliases": ["methylisothiazolinone", "isothiazolinone", "methylisothiazolino", "мітілізотіазолінон", "mi", "mit"],
                "source": "local", "context": "Аллерген 2013 года в Европе"
            },
            {
                "id": 21, "name": "Methylchloroisothiazolinone", "risk_level": "high", "category": "preservative",
                "description": "Сильный консервант и аллерген, часто используется в паре с MI",
                "aliases": ["methylchloroisothiazolinone", "methylchloroisothiazolinone/methylisothiazolinone", "cmit", "mi/mci"],
                "source": "local", "context": "Ограничен в ЕС до 0.0015%"
            },
            {
                "id": 10, "name": "Triclosan", "risk_level": "high", "category": "antibacterial",
                "description": "Вызывает антибиотикорезистентность, эндокринный дизраптор",
                "aliases": ["triclosan", "триклозан", "antibacterial agent"],
                "source": "local", "context": "Запрещен в мыле в США с 2017"
            },
            {
                "id": 11, "name": "Oxybenzone", "risk_level": "high", "category": "UV filter",
                "description": "Химический УФ-фильтр, проникает через кожу, эндокринный дизраптор",
                "aliases": ["oxybenzone", "бензофенон-3", "benzophenone-3", "бензофенон", "benzophenone", "bp-3"],
                "source": "local", "context": "Запрещен на Гавайях, токсичен для кораллов"
            },
            
            # 🟠 MEDIUM RISK
            {
                "id": 3, "name": "Parfum", "risk_level": "medium", "category": "fragrance",
                "description": "Ароматизатор. Может вызывать аллергию у 1-3% людей.",
                "aliases": ["parfum", "fragrance", "aroma", "perfume", "парфум", "ароматизатор", "отдушка"],
                "source": "local", "context": "Самый частый аллерген в косметике"
            },
            {
                "id": 2, "name": "Methylparaben", "risk_level": "medium", "category": "preservative",
                "description": "Консервант. Низкий риск в косметике для смывания.",
                "aliases": ["methylparaben", "methyl paraben", "парабен", "парабены", "метилпарабен", "консервант"],
                "source": "local", "context": "Разрешен в ЕС до 0.4%"
            },
            {
                "id": 1, "name": "Sodium Laureth Sulfate", "risk_level": "medium", "category": "surfactant",
                "description": "ПАВ, пенообразователь. Может сушить кожу.",
                "aliases": ["sodium laureth sulfate", "sodium lauryl sulfate", "sles", "sls", "натрію лаурет сульфат"],
                "source": "local", "context": "Безопасен в смываемых продуктах"
            },
            {
                "id": 12, "name": "Propylene Glycol", "risk_level": "medium", "category": "humectant",
                "description": "Увлажнитель и растворитель. Может вызывать раздражение при высокой концентрации.",
                "aliases": ["propylene glycol", "пропіленгліколь", "пропілен гліколь", "pg"],
                "source": "local", "context": "Безопасен до 50% в косметике"
            },
            {
                "id": 8, "name": "Alcohol Denat", "risk_level": "medium", "category": "solvent",
                "description": "Денатурированный спирт. Сушит кожу.",
                "aliases": ["alcohol denat", "alcohol", "спирт", "денатурований спирт", "ethanol"],
                "source": "local", "context": "Приемлем в тониках для жирной кожи"
            },
            {
                "id": 6, "name": "Tetrasodium EDTA", "risk_level": "medium", "category": "chelating agent",
                "description": "Хелатор. Улучшает пену и стабильность.",
                "aliases": ["tetrasodium edta", "edta", "тетранатрій едта", "тетрасодіум едта", "хелатуючий агент"],
                "source": "local", "context": "Безопасен в низких концентрациях"
            },
            
            # 🟡 LOW RISK
            {
                "id": 7, "name": "PEG-4", "risk_level": "low", "category": "emulsifier",
                "description": "Полиэтиленгликоль низкомолекулярный. Эмульгатор.",
                "aliases": ["peg-4", "peg", "поліетиленгліколь", "поліетилен гліколь", "polyethylene glycol"],
                "source": "local", "context": "Используется в фармацевтике и косметике"
            },
            {
                "id": 9, "name": "Mineral Oil", "risk_level": "low", "category": "emollient",
                "description": "Минеральное масло высокой очистки.",
                "aliases": ["mineral oil", "парафінове масло", "paraffinum liquidum", "вазелін"],
                "source": "local", "context": "Высшая степень очистки - безопасно"
            },
            {
                "id": 13, "name": "Silicone", "risk_level": "low", "category": "emollient",
                "description": "Силиконы (диметикон). Создает защитную пленку.",
                "aliases": ["silicone", "силікон", "dimethicone", "циклометикон", "диметикон"],
                "source": "local", "context": "Используется в медицинских имплантах"
            },
            {
                "id": 14, "name": "Citric Acid", "risk_level": "low", "category": "pH adjuster",
                "description": "Лимонная кислота. Регулятор pH, антиоксидант.",
                "aliases": ["citric acid", "лимонная кислота", "сітілова кислота", "acidum citricum", "e330"],
                "source": "local", "context": "Природная кислота, E330 в пище"
            },
            {
                "id": 15, "name": "Glycerin", "risk_level": "low", "category": "humectant",
                "description": "Глицерин. Натуральный увлажнитель.",
                "aliases": ["glycerin", "гліцерин", "glycerol", "glycerine", "e422"],
                "source": "local", "context": "Золотой стандарт увлажнения"
            },
            {
                "id": 16, "name": "Cocamidopropyl Betaine", "risk_level": "low", "category": "surfactant",
                "description": "Мягкий ПАВ из кокосового масла.",
                "aliases": ["cocamidopropyl betaine", "cocamidopropylbetaine", "копамідопропіл бетаїн"],
                "source": "local", "context": "Встречается в детской косметике"
            },
            {
                "id": 17, "name": "Styrene Acrylates Copolymer", "risk_level": "low", "category": "film former",
                "description": "Полимер для фиксации.",
                "aliases": ["styrene acrylates copolymer", "стирол/акрилати сополимер", "styrene/acrylates copolymer"],
                "source": "local", "context": "Используется в лаках для волос"
            },
            {
                "id": 18, "name": "Coco Glucoside", "risk_level": "low", "category": "surfactant",
                "description": "Натуральный ПАВ из кокосового масла и глюкозы.",
                "aliases": ["coco glucoside", "коко глюкозид", "coconut glucoside", "alkyl polyglucoside"],
                "source": "local", "context": "Используется в эко-косметике"
            },
            {
                "id": 19, "name": "Hydrolyzed Silk Protein", "risk_level": "low", "category": "conditioning agent",
                "description": "Гидролизованный шелковый протеин.",
                "aliases": ["hydrolyzed silk protein", "гідролізований шовковий протеїн", "silk amino acids"],
                "source": "local", "context": "Натуральный кондиционер"
            },
            {
                "id": 22, "name": "PEG-4 Cocoate", "risk_level": "low", "category": "emulsifier",
                "description": "Эфир кокосового масла и ПЭГ-4.",
                "aliases": ["peg-4 cocoate", "peg-4 coconut ester", "polyethylene glycol-4 coconut ester"],
                "source": "local", "context": "Натуральный эмульгатор"
            },
            
            # 🟢 SAFE
            {
                "id": 20, "name": "Aqua", "risk_level": "safe", "category": "solvent",
                "description": "Вода. Основа косметических средств.",
                "aliases": ["aqua", "вода", "water", "eau", "h2o"],
                "source": "local", "context": "Основной компонент косметики"
            },
            
            # Дополнительные
            {
                "id": 23, "name": "Sodium Benzoate", "risk_level": "low", "category": "preservative",
                "description": "Консервант. Разрешен в ЕС до 0.5%.",
                "aliases": ["sodium benzoate", "бензоат натрия", "e211"],
                "source": "local", "context": "Пищевой консервант E211"
            },
            {
                "id": 24, "name": "Titanium Dioxide", "risk_level": "low", "category": "UV filter",
                "description": "Минеральный УФ-фильтр.",
                "aliases": ["titanium dioxide", "діоксид титану", "ci 77891", "tio2"],
                "source": "local", "context": "Минеральный солнцезащитный фильтр"
            },
            {
                "id": 25, "name": "Zinc Oxide", "risk_level": "low", "category": "UV filter",
                "description": "Минеральный УФ-фильтр широкого спектра.",
                "aliases": ["zinc oxide", "оксид цинку", "ci 77947", "zno"],
                "source": "local", "context": "Золотой стандарт детских санскринов"
            },
            {
                "id": 26, "name": "Butylparaben", "risk_level": "medium", "category": "preservative",
                "description": "Парабеновый консервант.",
                "aliases": ["butylparaben", "бутилпарабен", "butyl paraben"],
                "source": "local", "context": "Ограничен в ЕС в детской косметике"
            },
            {
                "id": 27, "name": "Propylparaben", "risk_level": "medium", "category": "preservative",
                "description": "Парабеновый консервант.",
                "aliases": ["propylparaben", "пропилпарабен", "propyl paraben"],
                "source": "local", "context": "Часто используется с метилпарабеном"
            }
        ]
        print(f"✅ Загружено {len(ingredients)} ингредиентов")
        return ingredients

    def load_common_fixes(self):
        """Загрузка исправлений опечаток"""
        print("🔧 Загрузка исправлений опечаток...")
        fixes = {
            # Химические ошибки OCR
            "methytisctvazuivare": "methylisothiazolinone",
            "methylisothiazolino": "methylisothiazolinone",
            "methylchloroiscthiazoline": "methylchloroisothiazolinone",
            "methylchloroisothiazolino": "methylchloroisothiazolinone",
            "тетрасодіум": "tetrasodium",
            "едта": "edta",
            "парфюм": "parfum",
            "формалдегид": "formaldehyde",
            "бензофенон": "oxybenzone",
            "силикона": "silicone",
            "глицерина": "glycerin",
            "цитрик": "citric",
            "сульфат": "sulfate",
            "парабен": "paraben",
            "алкоголь": "alcohol",
            "натрію": "sodium",
            "лаурет": "laureth",
            "лауріл": "lauryl",
            "пропілен": "propylene",
            "гліцерин": "glycerin",
            "полиэтиленгликоль": "polyethylene glycol",
            "поліетиленгліколь": "polyethylene glycol",
            "минерал": "mineral",
            "вазелин": "vaseline",
            "парафін": "paraffin",
            "триклозан": "triclosan",
            "пропіленгліколь": "propylene glycol",
            "силікон": "silicone",
            "диметикон": "dimethicone",
            "циклометикон": "cyclomethicone",
            "лимонная": "citric",
            "кислота": "acid",
            "глицерол": "glycerol",
            "cocamidopropyl": "cocamidopropyl",
            "betaine": "betaine",
            "стирол": "styrene",
            "акрилати": "acrylates",
            "сополимер": "copolymer",
            "коко": "coco",
            "глюкозид": "glucoside",
            "гидролизованный": "hydrolyzed",
            "шелковый": "silk",
            "протеин": "protein",
            "вода": "aqua",
            "water": "aqua",
            "аqua": "aqua",
            "cocoate": "cocoate",
            "бензоат": "benzoate",
            "натрія": "sodium",
            "діоксид": "dioxide",
            "титану": "titanium",
            "оксид": "oxide",
            "цинку": "zinc",
            
            # Специфичные ошибки из вашего OCR
            "sodlum": "sodium",
            "glycerln": "glycerin",
            "parfume": "parfum",
            "peg4": "peg-4",
            "edta.": "edta",
            "hydrotyzed": "hydrolyzed",
            "methylchlorcisothiazoline": "methylchloroisothiazolinone",
        }
        print(f"✅ Загружено {len(fixes)} исправлений опечаток")
        return fixes
    
    def _create_not_found_response(self, ingredient_name):
        """Создание ответа для ненайденного ингредиента"""
        risk_level = "unknown"
        ingredient_lower = ingredient_name.lower()
        
        # Определяем риск по ключевым словам
        if any(word in ingredient_lower for word in ['formaldehyde', 'isothiazolinone', 'triclosan', 'oxybenzone']):
            risk_level = "high"
        elif any(word in ingredient_lower for word in ['paraben', 'parfum', 'fragrance', 'alcohol', 'sulfate', 'glycol']):
            risk_level = "medium"
        elif any(word in ingredient_lower for word in ['glycerin', 'aqua', 'water', 'benzoate', 'dioxide', 'oxide', 'acid']):
            risk_level = "low"
        
        return {
            "name": ingredient_name,
            "risk_level": risk_level,
            "category": "unknown",
            "description": f"Інгредієнт не знайдено в локальній базі.",
            "source": "not_found",
            "aliases": [],
            "context": "Оцінка на основі ключових слів у назві"
        }
    
    def is_potential_ingredient(self, text):
        """Проверка, может ли текст быть ингредиентом (УЛУЧШЕННАЯ версия)"""
        if not text or len(text) < 3:
            return False
        
        text_lower = text.lower().strip()
        
        # 1. Проверяем стоп-слова
        if text_lower in self.stop_words:
            return False
        
        # 2. Отсеиваем маркетинговые фразы (слишком длинные тексты)
        if len(text) > 80:
            return False
        
        # 3. Проверяем формат INCI названия
        # INCI обычно: заглавные буквы, могут быть цифры/дефисы/пробелы
        words = text.split()
        
        # Если это одно слово или несколько слов через дефис
        if len(words) == 1 or '-' in text:
            # Проверяем химические суффиксы
            chemical_suffixes = ['ate', 'ide', 'one', 'ene', 'ol', 'ic', 'in', 'ose', 'ium', 'ate', 'ester']
            for suffix in chemical_suffixes:
                if text_lower.endswith(suffix) and len(text) > 3:
                    return True
            
            # Проверяем наличие цифр (PEG-4, CI 77891)
            if re.search(r'\d', text):
                return True
            
            # Проверяем по словарю ингредиентов
            for ingredient in self.local_ingredients:
                if text_lower == ingredient['name'].lower():
                    return True
                for alias in ingredient.get('aliases', []):
                    if text_lower == alias.lower():
                        return True
        
        # 4. Проверяем многословные INCI названия
        if len(words) >= 2 and len(words) <= 4:
            # Проверяем, не содержит ли маркетинговых слов
            marketing_words = ['продукция', 'косметическая', 'гигиеническая', 'предназначено', 
                             'хранить', 'изготовитель', 'россия', 'область']
            if not any(marketing_word in text_lower for marketing_word in marketing_words):
                # Проверяем, содержит ли латинские буквы
                if re.search(r'[a-zA-Z]', text):
                    return True
        
        return False
    
    def extract_ingredient_candidates(self, text):
        """Извлечение кандидатов на ингредиенты из текста (УЛУЧШЕННАЯ версия)"""
        if not text:
            return []
        
        print(f"\n🧪 Извлечение кандидатов из текста ({len(text)} символов)")
        
        # 1. Находим начало списка ингредиентов
        composition_start = -1
        composition_patterns = [
            r'СОСТАВ\s*[:\-]',
            r'INGREDIENTS\s*[:\-]',
            r'INCI\s*[:\-]',
            r'СКЛАД\s*[:\-]',
            r'ІНГРЕДІЄНТИ\s*[:\-]',
            r'COMPOSITION\s*[:\-]'
        ]
        
        for pattern in composition_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                composition_start = match.end()
                print(f"   ✅ Найден раздел 'СОСТАВ' в позиции {composition_start}")
                break
        
        # Если не нашли заголовок, ищем строку с INCI названиями
        if composition_start == -1:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if ',' in line and any(word in line.upper() for word in ['AQUA', 'SODIUM', 'GLYCERIN', 'PARFUM']):
                    composition_start = sum(len(l) + 1 for l in lines[:i])
                    print(f"   ✅ Найден список ингредиентов в строке {i+1}")
                    break
        
        # 2. Извлекаем текст списка ингредиентов
        if composition_start != -1:
            # Ищем конец списка
            end_patterns = [
                r'\n\s*\d+\.',
                r'\n{2,}',
                r'\.\s*\n',
                r'Хранить|Зберігати',
                r'УСЛОВИЯ',
                r'ИЗГОТОВИТЕЛЬ|ВИГОТОВЛЮВАЧ',
                r'www\.|http://',
                r'©|™|®',
            ]
            
            end_pos = len(text)
            for pattern in end_patterns:
                match = re.search(pattern, text[composition_start:], re.IGNORECASE | re.MULTILINE)
                if match:
                    potential_end = composition_start + match.start()
                    if potential_end < end_pos:
                        end_pos = potential_end
            
            ingredients_text = text[composition_start:end_pos].strip()
            print(f"   📊 Извлечен текст ингредиентов: {len(ingredients_text)} символов")
        else:
            ingredients_text = text
            print("   ℹ️ Раздел 'СОСТАВ' не найден, используем весь текст")
        
        # 3. Очищаем текст
        ingredients_text = re.sub(r'[^\w\s.,;:\-–/()\n]', ' ', ingredients_text)
        ingredients_text = re.sub(r'\s+', ' ', ingredients_text)
        
        # 4. Разделяем на ингредиенты
        candidates = []
        
        # Стратегия 1: Разделение по запятым и точкам с запятой
        items = re.split(r'[,;]', ingredients_text)
        
        for item in items:
            item = item.strip()
            if not item or len(item) < 3:
                continue
            
            # Пропускаем маркетинговый текст
            item_lower = item.lower()
            marketing_keywords = [
                'продукция', 'косметическая', 'гигиеническая', 'моющая',
                'крем-мыло', 'жидкое', 'гоСТ', 'предназначено', 'наружного',
                'применения', 'хранить', 'температуре', 'солнечных', 'лучей',
                'изготовитель', 'качество', 'гарант', 'область', 'район',
                'промыть', 'чистой', 'водой', 'использовать', 'случае',
                'возникновения', 'аллергической', 'реакции', 'раздражения'
            ]
            
            if any(keyword in item_lower for keyword in marketing_keywords):
                continue
            
            # Проверяем, похоже ли на INCI название
            has_latin = bool(re.search(r'[a-zA-Z]', item))
            has_cyrillic = bool(re.search(r'[а-яА-Я]', item))
            
            # Если есть и латинские, и кириллические буквы в коротком тексте - пропускаем
            if has_latin and has_cyrillic and len(item) < 50:
                continue
            
            # Проверяем через is_potential_ingredient
            if self.is_potential_ingredient(item):
                candidates.append(item)
                print(f"   🧪 Кандидат: '{item}'")
        
        # Стратегия 2: По переводам строк (для сложных случаев)
        if len(candidates) < 3:
            lines = ingredients_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 10 and self.is_potential_ingredient(line):
                    candidates.append(line)
        
        # Удаляем дубликаты
        unique_candidates = []
        seen = set()
        
        for candidate in candidates:
            candidate_lower = candidate.lower()
            if candidate_lower not in seen:
                seen.add(candidate_lower)
                unique_candidates.append(candidate)
        
        print(f"📊 Найдено {len(unique_candidates)} уникальных кандидатов")
        
        return unique_candidates
    
    def search_ingredient(self, ingredient_name):
        """Улучшенный поиск ингредиента"""
        
        if not ingredient_name or not isinstance(ingredient_name, str):
            return self._create_not_found_response(ingredient_name)
        
        ingredient_name = ingredient_name.strip()
        
        # Проверка кэша
        cache_key = ingredient_name.lower()
        if cache_key in self.search_cache:
            cached_result = self.search_cache[cache_key]
            cache_age = datetime.now() - cached_result['timestamp']
            if cache_age < timedelta(hours=24):
                return cached_result['data']
        
        # 1. Применяем исправления опечаток
        cleaned_name = self.clean_text(ingredient_name)
        
        # 2. Поиск в локальной базе (сначала оригинальное имя, потом очищенное)
        local_result = self._search_local(ingredient_name)
        if not local_result and cleaned_name != ingredient_name.lower():
            local_result = self._search_local(cleaned_name)
        
        if local_result:
            self.search_cache[cache_key] = {
                'data': local_result,
                'timestamp': datetime.now(),
                'source': 'local'
            }
            return local_result
        
        # 3. Поиск во внешних источниках
        if self.use_cache:
            try:
                external_result = self.external_sources.search(ingredient_name)
                if external_result and external_result.get('source') != 'not_found':
                    self.search_cache[cache_key] = {
                        'data': external_result,
                        'timestamp': datetime.now(),
                        'source': 'external'
                    }
                    return external_result
            except Exception:
                pass
        
        # 4. Если ничего не найдено
        not_found_result = self._create_not_found_response(ingredient_name)
        self.search_cache[cache_key] = {
            'data': not_found_result,
            'timestamp': datetime.now(),
            'source': 'not_found'
        }
        return not_found_result
    
    def _search_local(self, ingredient_name):
        """Поиск в локальной базе"""
        ingredient_lower = ingredient_name.lower()
        
        for ingredient in self.local_ingredients:
            if ingredient_lower == ingredient['name'].lower():
                return ingredient
            
            for alias in ingredient.get('aliases', []):
                if ingredient_lower == alias.lower():
                    return ingredient
        
        return None
    
    def clean_text(self, text):
        """Очистка текста перед поиском"""
        if not text:
            return ""
        
        text = text.lower()
        text = re.sub(r'[^a-zA-Z0-9а-яА-ЯіІїЇєЄ\s\-.,]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Применяем исправления опечаток
        for wrong, correct in self.common_fixes.items():
            if wrong.lower() in text:
                text = text.replace(wrong.lower(), correct.lower())
        
        return text.strip()
    
    def find_ingredients(self, text):
        """Улучшенная функция поиска ингредиентов"""
        if not text or not isinstance(text, str):
            print("⚠️ Текст для анализа пуст или не является строкой")
            return []
        
        print(f"\n🔍 Поиск ингредиентов в тексте")
        
        # 1. Извлекаем кандидатов
        candidates = self.extract_ingredient_candidates(text)
        
        # 2. Ищем каждый кандидат
        found_ingredients = []
        seen_names = set()
        
        for candidate in candidates:
            ingredient = self.search_ingredient(candidate)
            
            if ingredient['name'] not in seen_names:
                found_ingredients.append(ingredient)
                seen_names.add(ingredient['name'])
                risk_icon = "🔴" if ingredient['risk_level'] == 'high' else \
                           "🟠" if ingredient['risk_level'] == 'medium' else \
                           "🟡" if ingredient['risk_level'] == 'low' else \
                           "🟢" if ingredient['risk_level'] == 'safe' else "⚫"
                print(f"✅ {risk_icon} Найден: {ingredient['name']} (риск: {ingredient['risk_level']})")
        
        print(f"📊 ИТОГО: найдено {len(found_ingredients)} ингредиентов")
        
        # 3. Статистика по рискам
        risk_stats = {'high': 0, 'medium': 0, 'low': 0, 'safe': 0, 'unknown': 0}
        
        for ing in found_ingredients:
            risk = ing.get('risk_level', 'unknown')
            if risk in risk_stats:
                risk_stats[risk] += 1
        
        print(f"📈 Статистика рисков: 🔴 {risk_stats['high']} 🟠 {risk_stats['medium']} 🟡 {risk_stats['low']} 🟢 {risk_stats['safe']} ⚫ {risk_stats['unknown']}")
        
        return found_ingredients


class ExternalDataFetcher:
    """Класс для получения данных из внешних источников"""
    
    def __init__(self, cache_dir='data_cache'):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'external_cache.db')
        os.makedirs(cache_dir, exist_ok=True)
        self.init_cache()
        print(f"✅ ExternalDataFetcher инициализирован, кэш: {self.cache_file}")
        
    def init_cache(self):
        """Инициализация кэша"""
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
        """Поиск ингредиента во внешних источниках"""
        
        # 1. Проверяем кэш
        cached = self._get_from_cache(ingredient_name)
        if cached:
            return cached
        
        # 2. Пробуем разные источники
        try:
            test_url = "http://www.google.com"
            requests.get(test_url, timeout=3)
            
            result = None
            result = self._search_cosing(ingredient_name)
            
            if not result:
                result = self._search_openfoodfacts(ingredient_name)
            
            if not result:
                result = self._search_pubchem(ingredient_name)
            
            if result:
                self._save_to_cache(ingredient_name, result)
            
            return result
            
        except (requests.ConnectionError, requests.Timeout):
            print(f"⚠️ Нет доступа к интернету, пропускаем внешние источники")
            return None
    
    def _search_cosing(self, ingredient_name):
        """Поиск в базе CosIng ЕС"""
        try:
            print(f"🔗 Запрос к CosIng API: {ingredient_name}")
            
            # Заглушка для демонстрации
            if 'paraben' in ingredient_name.lower():
                return {
                    "name": ingredient_name,
                    "risk_level": "medium",
                    "category": "preservative",
                    "description": "Консервант парабенового ряда.",
                    "source": "cosing",
                    "aliases": [],
                    "context": "ЕС ограничения: до 0.4%"
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка CosIng API: {e}")
            return None
    
    def _search_openfoodfacts(self, ingredient_name):
        """Поиск в Open Food Facts"""
        try:
            url = f"https://world.openfoodfacts.org/api/v0/product/ingredient/{ingredient_name}.json"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('product'):
                    risk_level = "low"
                    if any(word in ingredient_name.lower() for word in ['preservative', 'artificial']):
                        risk_level = "medium"
                    
                    return {
                        "name": ingredient_name,
                        "risk_level": risk_level,
                        "category": "food_ingredient",
                        "description": "Пищевой ингредиент",
                        "source": "openfoodfacts",
                        "aliases": [],
                        "context": "Данные из Open Food Facts"
                    }
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка Open Food Facts API: {e}")
            return None
    
    def _search_pubchem(self, ingredient_name):
        """Поиск в PubChem"""
        try:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{ingredient_name}/JSON"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                ingredient_lower = ingredient_name.lower()
                risk_level = "unknown"
                category = "chemical"
                
                if any(word in ingredient_lower for word in ['paraben', 'isothiazolinone', 'formalde']):
                    risk_level = "high" if 'isothiazolinone' in ingredient_lower or 'formalde' in ingredient_lower else "medium"
                    category = "preservative"
                elif any(word in ingredient_lower for word in ['parfum', 'fragrance']):
                    risk_level = "medium"
                    category = "fragrance"
                elif any(word in ingredient_lower for word in ['alcohol', 'glycol']):
                    risk_level = "medium"
                    category = "solvent"
                elif any(word in ingredient_lower for word in ['glycerin', 'aqua', 'water']):
                    risk_level = "low"
                    category = "base" if 'aqua' in ingredient_lower or 'water' in ingredient_lower else "emollient"
                elif any(word in ingredient_lower for word in ['acid', 'ate']):
                    risk_level = "low"
                    category = "pH adjuster" if 'acid' in ingredient_lower else "ester"
                
                return {
                    "name": ingredient_name,
                    "risk_level": risk_level,
                    "category": category,
                    "description": f"Химическое соединение: {ingredient_name}",
                    "source": "pubchem",
                    "aliases": [],
                    "context": "Автоматическая оценка на основе названия"
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка PubChem API: {e}")
            return None
    
    def _get_from_cache(self, ingredient_name):
        """Получение из кэша"""
        try:
            conn = sqlite3.connect(self.cache_file)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data FROM ingredients_cache WHERE name = ? AND last_updated > datetime('now', '-7 days')",
                (ingredient_name.lower(),)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка чтения кэша: {e}")
            return None
    
    def _save_to_cache(self, ingredient_name, data):
        """Сохранение в кэш"""
        try:
            conn = sqlite3.connect(self.cache_file)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO ingredients_cache (name, data, source, last_updated) VALUES (?, ?, ?, datetime('now'))",
                (ingredient_name.lower(), json.dumps(data), data.get('source', 'unknown'))
            )
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка сохранения в кэш: {e}")