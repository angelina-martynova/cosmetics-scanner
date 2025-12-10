import re
import json

class IngredientChecker:
    def __init__(self):
        self.ingredients = self.load_ingredients()
        self.common_fixes = {
            "methytisctvazuivare": "methylisothiazolinone",
            "methylisothiazolino": "methylisothiazolinone",
            "isothiazolinone": "methylisothiazolinone",
            "тетрасодіум": "tetrasodium",
            "едта": "edta",
            "тетрасодіум едта": "tetrasodium edta",
            "tetrasodiurs edta": "tetrasodium edta", 
            "tetrasodiumedta": "tetrasodium edta",
            "tetrasodium edta": "tetrasodium edta",
            "sodim laureth sulfate": "sodium laureth sulfate",
            "sodium lauryl": "sodium laureth sulfate",
            "sodium laureth": "sodium laureth sulfate",
            "sles": "sodium laureth sulfate",
            "sls": "sodium laureth sulfate",
            "peg~4": "peg-4",
            "peg-4": "peg-4",
            "peg": "peg-4",
            "polietilenglikol": "peg-4",
            "fragranc": "fragrance",
            "frag": "fragrance",
            "perfume": "fragrance",
            "paraben": "parabens",
            "parabens": "methylparaben",
            "формальдегід": "formaldehyde",
            "формальдегід": "formaldehyde",
            "натрію": "sodium",
            "сульфат": "sulfate",
            "лаурет": "laureth",
            "лауріл": "lauryl",
            "парабен": "paraben",
            "метилпарабен": "methylparaben",
            "консервант": "preservative",
            "ароматизатор": "fragrance",
            "отдушка": "fragrance",
            "вода": "aqua",
            "aqua": "water",
            "гліцерин": "glycerin",
            "гіалуронова кислота": "hyaluronic acid",
            "сітілова кислота": "citric acid",
            "алкоголь": "alcohol",
            "спирт": "alcohol",
            "минеральное масло": "mineral oil",
            "парафиновое масло": "mineral oil",
            "силикон": "silicone",
            "диметикон": "silicone",
            "циклометикон": "silicone",
            "пропиленгликоль": "propylene glycol",
            "бензофенон": "oxybenzone",
            "триклозан": "triclosan",
        }

    def load_ingredients(self):
        # Расширенный список ингредиентов
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

    def clean_text(self, text):
        """Очистка текста перед поиском"""
        if not text:
            return ""
        
        text = text.lower()
        
        # Заменяем сложные символы
        text = re.sub(r'[^a-zA-Z0-9а-яА-ЯіІїЇєЄ\s\-.,]', ' ', text)
        
        # Удаляем лишние пробелы
        text = re.sub(r'\s+', ' ', text)
        
        # Применяем исправления опечаток
        for wrong, correct in self.common_fixes.items():
            if wrong.lower() in text:
                text = text.replace(wrong.lower(), correct.lower())
        
        return text.strip()

    def check_match(self, ingredient_name, cleaned_text):
        """Проверка совпадения ингредиента в тексте"""
        if not ingredient_name or not cleaned_text:
            return False
        
        ingredient_lower = ingredient_name.lower()
        cleaned_lower = cleaned_text.lower()
        
        # Проверяем прямое вхождение
        if ingredient_lower in cleaned_lower:
            return True
        
        # Проверяем вхождение по частям для многословных ингредиентов
        ingredient_words = ingredient_lower.split()
        if len(ingredient_words) > 1:
            # Проверяем вхождение всех слов
            matches = sum(1 for word in ingredient_words if word in cleaned_lower)
            if matches >= len(ingredient_words) * 0.7:  # 70% совпадение
                return True
        
        return False

    def find_ingredients(self, text):
        """Поиск ингредиентов в тексте - ОСНОВНАЯ ФУНКЦИЯ"""
        if not text or not isinstance(text, str):
            print("⚠️ Текст для анализа пуст или не является строкой")
            return []
        
        cleaned_text = self.clean_text(text)
        
        # Отладочная информация
        print(f"\n🔍 Поиск ингредиентов в тексте ({len(text)} символов):")
        print(f"📝 Очищенный текст: {cleaned_text[:150]}...")
        
        found_ingredients = []
        seen_ids = set()
        
        for ingredient in self.ingredients:
            if ingredient["id"] in seen_ids:
                continue

            # Проверяем основное имя
            if self.check_match(ingredient["name"], cleaned_text):
                found_ingredients.append(ingredient)
                seen_ids.add(ingredient["id"])
                print(f"✅ Найден по имени: {ingredient['name']} (ID: {ingredient['id']})")
                continue

            # Проверяем алиасы
            for alias in ingredient.get("aliases", []):
                if self.check_match(alias, cleaned_text):
                    found_ingredients.append(ingredient)
                    seen_ids.add(ingredient["id"])
                    print(f"✅ Найден по алиасу '{alias}': {ingredient['name']}")
                    break
        
        print(f"📊 ИТОГО: найдено {len(found_ingredients)} ингредиентов")
        
        return found_ingredients

    def analyze_text_detailed(self, text):
        """Детальный анализ текста с дополнительной информацией"""
        results = {
            "text_length": len(text),
            "cleaned_text": self.clean_text(text),
            "found_ingredients": [],
            "ingredients_by_risk": {
                "high": [],
                "medium": [],
                "low": []
            },
            "statistics": {
                "total_found": 0,
                "high_risk": 0,
                "medium_risk": 0,
                "low_risk": 0
            }
        }
        
        found_ingredients = self.find_ingredients(text)
        results["found_ingredients"] = found_ingredients
        results["statistics"]["total_found"] = len(found_ingredients)
        
        for ingredient in found_ingredients:
            risk_level = ingredient.get("risk_level", "unknown")
            if risk_level in results["ingredients_by_risk"]:
                results["ingredients_by_risk"][risk_level].append({
                    "name": ingredient["name"],
                    "id": ingredient["id"]
                })
                results["statistics"][f"{risk_level}_risk"] += 1
        
        return results

# Для быстрого тестирования
if __name__ == "__main__":
    checker = IngredientChecker()
    
    test_texts = [
        "Состав: Aqua, Sodium Laureth Sulfate, Cocamidopropyl Betaine, Parfum, Methylparaben, Citric Acid, Glycerin",
        "Ingredients: Water, Formaldehyde, Glycerin, Alcohol Denat, Fragrance, Mineral Oil",
        "INCI: Methylisothiazolinone, Tetrasodium EDTA, PEG-4, Sodium Lauryl Sulfate, Silicone",
        "Компоненты: Вода, Натрію лаурет сульфат, Формальдегід, Ароматизатор, Консервант, Гліцерин",
        "Состав: Алое Вера, Гіалуронова кислота, Вітамін Е - натуральний склад",
    ]
    
    print("\n" + "=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ INGREDIENT CHECKER")
    print("=" * 60)
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n📝 Тест #{i}:")
        print(f"Текст: {text[:80]}...")
        
        result = checker.analyze_text_detailed(text)
        
        print(f"Найдено: {result['statistics']['total_found']} ингредиентов")
        print(f"Высокий риск: {result['statistics']['high_risk']}")
        print(f"Средний риск: {result['statistics']['medium_risk']}")
        print(f"Низкий риск: {result['statistics']['low_risk']}")
        
        if result['found_ingredients']:
            print("Найденные ингредиенты:")
            for ing in result['found_ingredients']:
                print(f"  - {ing['name']} ({ing['risk_level']})")
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено")
    print("=" * 60)