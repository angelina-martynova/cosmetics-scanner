import re
import json
import requests
from datetime import datetime, timedelta
import sqlite3
import os


class IngredientChecker:
    def __init__(self, use_cache=True, fallback_to_local=True):
        self.local_ingredients = self.load_local_ingredients()
        self.common_fixes = self.load_common_fixes()
        
        # Внешние источники данных
        self.external_sources = ExternalDataFetcher()
        self.use_cache = use_cache
        self.fallback_to_local = fallback_to_local
        
        # Кэш для результатов поиска
        self.search_cache = {}
        
    def load_local_ingredients(self):
        """Загрузка локальной базы ингредиентов"""
        return [
            {
                "id": 1,
                "name": "Sodium Laureth Sulfate",
                "risk_level": "medium",
                "category": "surfactant", 
                "description": "Пінник, може викликати подразнення шкіри",
                "aliases": [
                    "sodium laureth sulfate", 
                    "sodium lauryl sulfate",
                    "sles", 
                    "sls", 
                    "sodium lauryl ether sulfate",
                    "натрію лаурет сульфат",
                    "натрію лауріл сульфат",
                    "лаурет сульфат натрію",
                    "лауріл сульфат натрію"
                ]
            },
            {
                "id": 2, 
                "name": "Methylparaben",
                "risk_level": "medium",
                "category": "preservative",
                "description": "Консервант з можливим гормональним впливом",
                "aliases": [
                    "methylparaben", 
                    "methyl paraben", 
                    "paraben",
                    "parabens",
                    "метилпарабен",
                    "парабен",
                    "консервант"
                ]
            },
            {
                "id": 3,
                "name": "Parfum", 
                "risk_level": "high",
                "category": "fragrance",
                "description": "Ароматизатор, може викликати алергії",
                "aliases": [
                    "parfum", 
                    "fragrance", 
                    "aroma", 
                    "perfume", 
                    "парфум", 
                    "ароматизатор",
                    "отдушка",
                    "frag"
                ]
            },
            {
                "id": 4,
                "name": "Formaldehyde",
                "risk_level": "high",
                "category": "preservative", 
                "description": "Канцероген, може викликати алергії",
                "aliases": [
                    "formaldehyde", 
                    "formalin", 
                    "формальдегід",
                    "формальдегід"
                ]
            },
            {
                "id": 5,
                "name": "Methylisothiazolinone",
                "risk_level": "high",
                "category": "preservative",
                "description": "Сильний алерген, заборонений в деяких країнах",
                "aliases": [
                    "methylisothiazolinone",
                    "isothiazolinone",
                    "methylisothiazolino",
                    "мітілізотіазолінон"
                ]
            },
            {
                "id": 6,
                "name": "Tetrasodium EDTA",
                "risk_level": "medium",
                "category": "chelating agent",
                "description": "Хелатуючий агент, може викликати подразнення",
                "aliases": [
                    "tetrasodium edta",
                    "edta",
                    "тетранатрій едта",
                    "тетрасодіум едта",
                    "хелатуючий агент"
                ]
            },
            {
                "id": 7,
                "name": "PEG-4",
                "risk_level": "low",
                "category": "emulsifier",
                "description": "Емульгатор, вважається безпечним",
                "aliases": [
                    "peg-4",
                    "peg",
                    "поліетиленгліколь",
                    "поліетилен гліколь",
                    "peg 4"
                ]
            },
            {
                "id": 8,
                "name": "Alcohol Denat",
                "risk_level": "medium",
                "category": "solvent",
                "description": "Денатурированный спирт, сушит кожу",
                "aliases": [
                    "alcohol denat",
                    "alcohol",
                    "спирт",
                    "денатурований спирт",
                    "ethanol",
                    "алкоголь"
                ]
            },
            {
                "id": 9,
                "name": "Mineral Oil",
                "risk_level": "low",
                "category": "emollient",
                "description": "Минеральное масло, может забивать поры",
                "aliases": [
                    "mineral oil",
                    "парафінове масло",
                    "paraffinum liquidum",
                    "вазелін",
                    "минеральное масло"
                ]
            },
            {
                "id": 10,
                "name": "Triclosan",
                "risk_level": "high",
                "category": "antibacterial",
                "description": "Антибактериальный агент, может вызывать резистентность",
                "aliases": [
                    "triclosan",
                    "триклозан",
                    "antibacterial agent"
                ]
            },
            {
                "id": 11,
                "name": "Oxybenzone",
                "risk_level": "high",
                "category": "UV filter",
                "description": "Химический УФ-фильтр, эндокринный дизраптор",
                "aliases": [
                    "oxybenzone",
                    "бензофенон-3",
                    "benzophenone-3",
                    "бензофенон"
                ]
            },
            {
                "id": 12,
                "name": "Propylene Glycol",
                "risk_level": "medium",
                "category": "humectant",
                "description": "Увлажнитель, может вызывать раздражение",
                "aliases": [
                    "propylene glycol",
                    "пропіленгліколь",
                    "пропілен гліколь"
                ]
            },
            {
                "id": 13,
                "name": "Silicone",
                "risk_level": "low",
                "category": "emollient",
                "description": "Силикон, создает пленку на коже",
                "aliases": [
                    "silicone",
                    "силікон",
                    "dimethicone",
                    "циклометикон",
                    "диметикон"
                ]
            },
            {
                "id": 14,
                "name": "Citric Acid",
                "risk_level": "low",
                "category": "pH adjuster",
                "description": "Регулятор pH, безопасный в малых количествах",
                "aliases": [
                    "citric acid",
                    "лимонная кислота",
                    "сітілова кислота"
                ]
            },
            {
                "id": 15,
                "name": "Glycerin",
                "risk_level": "low",
                "category": "humectant",
                "description": "Увлажнитель, безопасный и эффективный",
                "aliases": [
                    "glycerin",
                    "гліцерин",
                    "glycerol"
                ]
            }
        ]

    def load_common_fixes(self):
        """Загрузка исправлений опечаток"""
        return {
            "methytisctvazuivare": "methylisothiazolinone",
            "methylisothiazolino": "methylisothiazolinone",
            "тетрасодіум": "tetrasodium",
            "едта": "edta",
            # ... (ваши исправления)
        }
    
    def search_ingredient(self, ingredient_name):
        """Поиск ингредиента во всех источниках"""
        
        # Проверка кэша
        cache_key = ingredient_name.lower()
        if cache_key in self.search_cache:
            cached_result = self.search_cache[cache_key]
            if datetime.now() - cached_result['timestamp'] < timedelta(hours=24):
                return cached_result['data']
        
        # 1. Поиск в локальной базе
        local_result = self._search_local(ingredient_name)
        if local_result:
            self.search_cache[cache_key] = {
                'data': local_result,
                'timestamp': datetime.now(),
                'source': 'local'
            }
            return local_result
        
        # 2. Поиск во внешних источниках (если включено)
        if self.use_cache:
            external_result = self.external_sources.search(ingredient_name)
            if external_result:
                self.search_cache[cache_key] = {
                    'data': external_result,
                    'timestamp': datetime.now(),
                    'source': 'external'
                }
                return external_result
        
        # 3. Если ничего не найдено
        return {
            "name": ingredient_name,
            "risk_level": "unknown",
            "category": "unknown",
            "description": "Інгредієнт не знайдено в базі даних",
            "source": "not_found",
            "aliases": []
        }
    
    def _search_local(self, ingredient_name):
        """Поиск в локальной базе"""
        ingredient_lower = ingredient_name.lower()
        
        for ingredient in self.local_ingredients:
            # Проверка основного имени
            if ingredient_lower == ingredient['name'].lower():
                return ingredient
            
            # Проверка алиасов
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
        """Основная функция поиска ингредиентов"""
        if not text or not isinstance(text, str):
            print("⚠️ Текст для анализа пуст или не является строкой")
            return []
        
        cleaned_text = self.clean_text(text)
        
        print(f"\n🔍 Поиск ингредиентов в тексте ({len(text)} символов):")
        print(f"📝 Очищенный текст: {cleaned_text[:150]}...")
        
        found_ingredients = []
        seen_names = set()
        
        # Разбиваем текст на возможные названия ингредиентов
        # Это упрощенный парсинг - в реальном проекте нужен более сложный
        words = cleaned_text.split()
        
        for i in range(len(words)):
            # Пробуем найти ингредиенты разной длины
            for length in range(1, 4):
                if i + length <= len(words):
                    possible_name = ' '.join(words[i:i+length])
                    
                    # Пропускаем слишком короткие или общие слова
                    if len(possible_name) < 3 or possible_name in ['and', 'with', 'water', 'aqua', 'вода']:
                        continue
                    
                    # Ищем ингредиент
                    ingredient = self.search_ingredient(possible_name)
                    
                    if (ingredient['source'] != 'not_found' and 
                        ingredient['name'] not in seen_names):
                        
                        found_ingredients.append(ingredient)
                        seen_names.add(ingredient['name'])
                        print(f"✅ Найден: {ingredient['name']} (источник: {ingredient['source']})")
        
        print(f"📊 ИТОГО: найдено {len(found_ingredients)} ингредиентов")
        
        return found_ingredients


class ExternalDataFetcher:
    """Класс для получения данных из внешних источников"""
    
    def __init__(self, cache_dir='data_cache'):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'external_cache.db')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Инициализация кэша SQLite
        self.init_cache()
        
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
        result = None
        
        # Источник 1: CosIng (ЕС)
        result = self._search_cosing(ingredient_name)
        
        # Источник 2: Open Food Facts (если CosIng не дал результатов)
        if not result:
            result = self._search_openfoodfacts(ingredient_name)
        
        # Источник 3: PubChem (химическая информация)
        if not result:
            result = self._search_pubchem(ingredient_name)
        
        # Сохраняем в кэш
        if result:
            self._save_to_cache(ingredient_name, result)
        
        return result
    
    def _search_cosing(self, ingredient_name):
        """Поиск в базе CosIng ЕС"""
        try:
            # CosIng API endpoint (примерный)
            # В реальности нужно использовать официальный API
            url = f"https://ec.europa.eu/growth/tools-databases/cosing/api/ingredient/{ingredient_name}"
            
            # В демо-версии возвращаем заглушку
            # Для реального использования нужно зарегистрироваться и получить доступ к API
            
            print(f"🔗 Запрос к CosIng API: {ingredient_name}")
            
            # Заглушка для демонстрации
            if 'paraben' in ingredient_name.lower():
                return {
                    "name": ingredient_name,
                    "risk_level": "medium",
                    "category": "preservative",
                    "description": "Консервант. Разрешен в ЕС с ограничениями.",
                    "source": "cosing",
                    "aliases": []
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка CosIng API: {e}")
            return None
    
    def _search_openfoodfacts(self, ingredient_name):
        """Поиск в Open Food Facts"""
        try:
            # Open Food Facts API
            url = f"https://world.openfoodfacts.org/api/v0/product/ingredient/{ingredient_name}.json"
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('product'):
                    # Извлекаем информацию об ингредиенте
                    ingredient_data = {
                        "name": ingredient_name,
                        "risk_level": "low",  # По умолчанию
                        "category": "food_ingredient",
                        "description": f"Пищевой ингредиент из Open Food Facts",
                        "source": "openfoodfacts",
                        "aliases": []
                    }
                    
                    return ingredient_data
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка Open Food Facts API: {e}")
            return None
    
    def _search_pubchem(self, ingredient_name):
        """Поиск в PubChem"""
        try:
            # PubChem API
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{ingredient_name}/JSON"
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # Анализ химической информации
                ingredient_data = {
                    "name": ingredient_name,
                    "risk_level": "unknown",
                    "category": "chemical",
                    "description": "Химическое соединение из базы PubChem",
                    "source": "pubchem",
                    "aliases": []
                }
                
                return ingredient_data
            
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


# Для быстрого тестирования
if __name__ == "__main__":
    checker = IngredientChecker(use_cache=True)
    
    test_texts = [
        "Состав: Aqua, Sodium Laureth Sulfate, Methylparaben, Butylparaben",
        "Ingredients: Water, Titanium Dioxide, Zinc Oxide",
        "INCI: Cetearyl Alcohol, Glyceryl Stearate, Phenoxyethanol",
    ]
    
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ РАСШИРЕННОГО INGREDIENT CHECKER")
    print("=" * 60)
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n📝 Тест #{i}:")
        print(f"Текст: {text[:80]}...")
        
        result = checker.find_ingredients(text)
        
        print(f"Найдено: {len(result)} ингредиентов")
        
        for ing in result:
            print(f"  - {ing['name']} (риск: {ing['risk_level']}, источник: {ing.get('source', 'local')})")
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено")
    print("=" * 60)