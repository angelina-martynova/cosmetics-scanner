import re
import json
import requests
from datetime import datetime, timedelta
import sqlite3
import os
import traceback

# Нечіткий пошук для покращеного розпізнавання інгредієнтів
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
    print("RapidFuzz підключено — нечіткий пошук активний")
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("RapidFuzz не встановлено — використовується точний пошук. "
          "Встановіть: pip install rapidfuzz")


class IngredientChecker:
    def __init__(self, use_cache=True, fallback_to_local=True):
        print("Ініціалізація IngredientChecker...")
        self.local_ingredients = self.load_local_ingredients()
        self.common_fixes = self.load_common_fixes()
        
        # Зовнішні джерела даних
        self.external_sources = ExternalDataFetcher()
        self.use_cache = use_cache
        self.fallback_to_local = fallback_to_local
        
        # Кеш для результатів пошуку
        self.search_cache = {}
        
        # Розширений список стоп-слів з маркетинговими фразами
        self.stop_words = self._load_stop_words()
        
        print(f"IngredientChecker ініціалізований: {len(self.local_ingredients)} інгредієнтів у базі")
        
        # Побудова індексу для швидкого нечіткого пошуку
        self._build_fuzzy_index()
    
    def _load_stop_words(self):
        """Завантаження розширеного списку стоп-слів"""
        stop_words = {
            # Загальна маркування
            'склад', 'інгредієнти', 'ingredients', 'inci', 'composition', 'formula',
            'продукт', 'продукція', 'product', 'назва', 'виробник', 'виготовлювач',
            'упаковка', 'пакування', 'пакет', 'пляшка', 'туба', 'флакон', 'крем-мило',
            
            # Маркетингові фрази (з вашого прикладу)
            'продукція', 'косметична', 'гігієнічна', 'миюча', 'гігієніческа',
            'крем-мило', 'рідке', 'гоСТ', 'гст', 'призначено', 'зовнішнього',
            'застосування', 'виготовлювач', 'якість', 'гарант', 'воронежська',
            'область', 'район', 'хохольський', 'промити', 'чистою', 'водою',
            'використовувати', 'випадку', 'виникнення', 'алергічної', 'реакції',
            'подразнення', 'особистої', 'гігієни', 'зберігати', 'температурі', 'сонячних',
            'променів', 'щільно', 'закритим', 'ефко', 'косметик', 'росія', 'питання',
            'якості', 'органічний', 'екологічний',
            
            # Одиниці та технічна інформація
            'термін', 'придатності', 'придатний', 'зберігання', 'дата', 'рік',
            'місяць', 'кінець', 'вжити', 'до', 'кінця', 'маса', 'нетто', 'вага',
            'об\'єм', 'кількість', 'алергени', 'алерген', 'може', 'містити', 'сліди',
            'умови', 'температура', 'холодильник', 'вироблено', 'для', 'країна',
            'походження', 'україна', 'експортер', 'імпортер', 'адреса', 'контакти',
            'телефон', 'штрихкод', 'код', 'партія', 'серія', 'поживна', 'цінність',
            'енергетична', 'ккал', 'кдж', 'білки', 'жири', 'вуглеводи', 'цукор', 'сіль',
            
            # Одиниці вимірювання
            'мл', 'л', 'г', 'кг', 'мг', 'мкг', 'од', 'таблетка', 'капсула',
            'шт', '%', 'відсотків', 'грам', 'мілілітр',
            
            # Прийменники та сполучники
            'та', 'і', 'або', 'чи', 'на', 'в', 'у', 'з', 'зі', 'від', 'до', 'про',
            'для', 'за', 'під', 'над', 'перед', 'після', 'через', 'який', 'яка',
            'яке', 'які', 'що', 'це', 'той', 'такий',
        }
        return stop_words
    
    def _build_fuzzy_index(self):
        """Побудова індексу всіх назв та псевдонімів для швидкого пошуку.
        
        Створює словник {normalized_name: ingredient_dict} 
        для O(1) lookup замість повного перебору при точному збігу.
        """
        self._exact_index = {}
        self._all_names = []  # Для RapidFuzz process.extractOne
        
        for ingredient in self.local_ingredients:
            name_lower = ingredient['name'].lower()
            self._exact_index[name_lower] = ingredient
            self._all_names.append(name_lower)
            
            for alias in ingredient.get('aliases', []):
                alias_lower = alias.lower()
                if alias_lower and alias_lower not in self._exact_index:
                    self._exact_index[alias_lower] = ingredient
                    self._all_names.append(alias_lower)
        
        print(f"Fuzzy-індекс побудовано: {len(self._exact_index)} унікальних назв")
    
    def load_local_ingredients(self):
        """Завантаження локальної бази інгредієнтів"""
        print("Завантаження локальної бази інгредієнтів...")
        
        # Спочатку пробуємо завантажити інгредієнти з JSON-файлу, якщо він є
        try:
            base_dir = os.path.dirname(__file__)
            data_path = os.path.join(base_dir, "data", "ingredients.json")
            if os.path.exists(data_path):
                with open(data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw_ingredients = data.get("ingredients", [])
                ingredients_from_file = []
                for ing in raw_ingredients:
                    if not isinstance(ing, dict):
                        continue
                    ing.setdefault("aliases", [])
                    ing.setdefault("risk_level", "unknown")
                    ing.setdefault("category", "unknown")
                    ing.setdefault("description", "")
                    ing.setdefault("source", "local")
                    ingredients_from_file.append(ing)
                if ingredients_from_file:
                    print(f"Завантажено {len(ingredients_from_file)} інгредієнтів з data/ingredients.json")
                    return ingredients_from_file
        except Exception as e:
            print(f"Не вдалося завантажити інгредієнти з JSON, використовую вбудований список: {e}")
        
        # Базовий список основних інгредієнтів (з повними псевдонімами)
        ingredients = [
            # === ВОДА ТА ОСНОВИ ===
            {
                "id": 1001, "name": "Aqua", "risk_level": "safe", "category": "solvent",
                "description": "Вода, основа косметичних засобів (INCI: Aqua)",
                "description_en": "Water, base of cosmetic products (INCI: Aqua)",
                "aliases": ["aqua", "вода", "water", "eau", "h2o", "purified water", 
                           "distilled water", "deionized water", "spring water", 
                           "маріс аква", "maris aqua", "дистильована вода", "очищена вода"],
                "source": "local"
            },
            {
                "id": 1002, "name": "Water", "risk_level": "safe", "category": "solvent",
                "description": "Очищена вода",
                "description_en": "Purified water",
                "aliases": ["water", "вода", "aqua", "eau", "purified h2o", "deionized h2o"],
                "source": "local"
            },
            
            # === ПАВ ТА ОЧИЩУЮЧІ ===
            {
                "id": 1003, "name": "Sodium Laureth Sulfate", "risk_level": "medium", "category": "surfactant",
                "description": "SLES, піноутворювач, може висушувати шкіру при частому використанні",
                "description_en": "SLES, foaming agent, may dry skin with frequent use",
                "aliases": ["sodium laureth sulfate", "sles", "натрію лаурет сульфат", 
                           "sls", "sodium lauryl ether sulfate", "sodium lauryl sulfate ether",
                           "содиум лаурет сульфат", "натрій лаурет сульфат"],
                "source": "local"
            },
            {
                "id": 1004, "name": "Sodium Lauryl Sulfate", "risk_level": "medium", "category": "surfactant",
                "description": "SLS, більш агресивний ніж SLES, може викликати подразнення",
                "description_en": "SLS, more aggressive than SLES, may cause irritation",
                "aliases": ["sodium lauryl sulfate", "sls", "натрію лауріл сульфат", 
                           "sodium dodecyl sulfate", "содиум лауріл сульфат",
                           "натрій лауріл сульфат", "sds"],
                "source": "local"
            },
            {
                "id": 1005, "name": "Cocamidopropyl Betaine", "risk_level": "low", "category": "surfactant",
                "description": "М'який ПАР з кокосової олії, підходить для чутливої шкіри",
                "description_en": "Mild surfactant from coconut oil, suitable for sensitive skin",
                "aliases": ["cocamidopropyl betaine", "копамідопропіл бетаїн", 
                           "coco betaine", "capb", "копамідопропил бетаин",
                           "cocamidopropylbetaine", "cocoamidopropyl betaine"],
                "source": "local"
            },
            {
                "id": 1006, "name": "Decyl Glucoside", "risk_level": "low", "category": "surfactant",
                "description": "Натуральний м'який ПАР з кокосової олії та кукурудзи",
                "description_en": "Natural mild surfactant from coconut oil and corn",
                "aliases": ["decyl glucoside", "децил глюкозид", "alkyl polyglucoside",
                           "децил глюкозід", "plant-based surfactant"],
                "source": "local"
            },
            {
                "id": 1007, "name": "Sodium Cocoyl Isethionate", "risk_level": "low", "category": "surfactant",
                "description": "Дуже м'який ПАР для делікатних засобів",
                "description_en": "Very mild surfactant for gentle products",
                "aliases": ["sodium cocoyl isethionate", "натрію кокоїл ізетіонат",
                           "sci", "soft surfactant", "кокоїл ізетіонат натрію"],
                "source": "local"
            },
            {
                "id": 1008, "name": "Coco Glucoside", "risk_level": "low", "category": "surfactant",
                "description": "Глюкозид з кокосової олії, біорозкладний",
                "description_en": "Coconut oil glucoside, biodegradable",
                "aliases": ["coco glucoside", "коко глюкозид", "coconut glucoside",
                           "кокосовий глюкозид", "alkyl polyglucoside"],
                "source": "local"
            },
            
            # === КОНСЕРВАНТИ ===
            # ВИСОКИЙ РИЗИК
            {
                "id": 1009, "name": "Formaldehyde", "risk_level": "high", "category": "preservative",
                "description": "Канцероген, заборонений у багатьох країнах",
                "description_en": "Carcinogen, banned in many countries",
                "aliases": ["formaldehyde", "формальдегід", "formalin", "methanal",
                           "формалін", "methyl aldehyde", "oxomethane"],
                "source": "local"
            },
            {
                "id": 1010, "name": "Methylisothiazolinone", "risk_level": "high", "category": "preservative",
                "description": "Сильніший алерген, обмежений в ЄС з 2017 року",
                "description_en": "Strong allergen, restricted in EU since 2017",
                "aliases": ["methylisothiazolinone", "мітілізотіазолінон", "mit", "mi", 
                           "kathon cg", "methylisothiazolin", "2-methyl-4-isothiazolin-3-one"],
                "source": "local"
            },
            {
                "id": 1011, "name": "Methylchloroisothiazolinone", "risk_level": "high", "category": "preservative",
                "description": "Сильний алерген, часто в комбінації з MIT",
                "description_en": "Strong allergen, often combined with MIT",
                "aliases": ["methylchloroisothiazolinone", "мітілхлороізотіазолінон", 
                           "mci", "cmit", "5-chloro-2-methyl-4-isothiazolin-3-one",
                           "chloromethylisothiazolinone"],
                "source": "local"
            },
            {
                "id": 1012, "name": "DMDM Hydantoin", "risk_level": "high", "category": "preservative",
                "description": "Виділяє формальдегід, алерген",
                "description_en": "Releases formaldehyde, allergen",
                "aliases": ["dmdm hydantoin", "дмдм гідантоїн", "dimethyl dimethyl hydantoin",
                           "формальдегід-виділяючий консервант"],
                "source": "local"
            },
            
            # ПОМІРНИЙ РИЗИК
            {
                "id": 1013, "name": "Methylparaben", "risk_level": "medium", "category": "preservative",
                "description": "Парабен, дозволений в ЄС до 0.4%, дослідження про гормональний вплив",
                "description_en": "Paraben, allowed in EU up to 0.4%, studies on hormonal effects",
                "aliases": ["methylparaben", "methyl paraben", "метилпарабен", "парабен", 
                           "e218", "n-methyl-4-hydroxybenzoate", "метил парабен"],
                "source": "local"
            },
            {
                "id": 1014, "name": "Propylparaben", "risk_level": "medium", "category": "preservative",
                "description": "Парабен, дозволений в ЄС до 0.14%",
                "description_en": "Paraben, allowed in EU up to 0.14%",
                "aliases": ["propylparaben", "propyl paraben", "пропилпарабен", "e216",
                           "n-propyl-4-hydroxybenzoate", "пропил парабен"],
                "source": "local"
            },
            {
                "id": 1015, "name": "Butylparaben", "risk_level": "medium", "category": "preservative",
                "description": "Парабен, обмежений в ЄС",
                "description_en": "Paraben, restricted in EU",
                "aliases": ["butylparaben", "butyl paraben", "бутилпарабен", 
                           "n-butyl-4-hydroxybenzoate", "бутил парабен"],
                "source": "local"
            },
            {
                "id": 1016, "name": "Phenoxyethanol", "risk_level": "medium", "category": "preservative",
                "description": "Широко використовуваний консервант, обмежений до 1% в ЄС",
                "description_en": "Widely used preservative, restricted to 1% in EU",
                "aliases": ["phenoxyethanol", "феноксиетанол", "2-phenoxyethanol",
                           "ethylene glycol monophenyl ether", "rose ether"],
                "source": "local"
            },
            
            # НИЗЬКИЙ РИЗИК
            {
                "id": 1017, "name": "Potassium Sorbate", "risk_level": "low", "category": "preservative",
                "description": "Сіль сорбінової кислоти, харчовий консервант",
                "description_en": "Sorbic acid salt, food-grade preservative",
                "aliases": ["potassium sorbate", "сорбат калію", "e202", 
                           "potassium (e,e)-hexa-2,4-dienoate"],
                "source": "local"
            },
            {
                "id": 1018, "name": "Sodium Benzoate", "risk_level": "low", "category": "preservative",
                "description": "Консервант, дозволений у косметиці до 0.5%",
                "description_en": "Preservative, allowed in cosmetics up to 0.5%",
                "aliases": ["sodium benzoate", "бензоат натрію", "e211",
                           "sodium salt of benzoic acid", "бензоат натрия"],
                "source": "local"
            },
            
            # === АРОМАТИЗАТОРИ ===
            {
                "id": 1019, "name": "Parfum", "risk_level": "medium", "category": "fragrance",
                "description": "Ароматизатор. Може викликати алергію у чутливих людей.",
                "description_en": "Fragrance. May cause allergic reactions in sensitive individuals.",
                "aliases": ["parfum", "fragrance", "aroma", "perfume", "парфум", 
                           "ароматизатор", "отдушка", "парфюмерна композиція", 
                           "fragrance mix", "духи", "аромат"],
                "source": "local"
            },
            {
                "id": 1020, "name": "Fragrance", "risk_level": "medium", "category": "fragrance",
                "description": "Ароматична композиція. Основний алерген у косметиці.",
                "description_en": "Fragrance composition. Major allergen in cosmetics.",
                "aliases": ["fragrance", "parfum", "aroma", "аромат", "запах",
                           "відтінок", "ессенція", "ефір", "парфюм"],
                "source": "local"
            },
            {
                "id": 1021, "name": "Limonene", "risk_level": "medium", "category": "fragrance",
                "description": "Ароматичне з'єднання, алерген, окислюється на повітрі",
                "description_en": "Aromatic compound, allergen, oxidizes in air",
                "aliases": ["limonene", "лімонен", "d-limonene", "цитрусовий терпен",
                           "1-methyl-4-(1-methylethenyl)cyclohexene"],
                "source": "local"
            },
            {
                "id": 1022, "name": "Linalool", "risk_level": "medium", "category": "fragrance",
                "description": "Ароматичне з'єднання, алерген при окисленні",
                "description_en": "Aromatic compound, allergen when oxidized",
                "aliases": ["linalool", "ліналоол", "3,7-dimethyl-1,6-octadien-3-ol",
                           "лавандова олія компонент", "кораліналоол"],
                "source": "local"
            },
            
            # === РОЗЧИННИКИ ТА СПИРТИ ===
            {
                "id": 1023, "name": "Alcohol Denat", "risk_level": "medium", "category": "solvent",
                "description": "Денатурований спирт. Висушує шкіру, може порушувати бар'єр.",
                "description_en": "Denatured alcohol. Dries skin, may impair barrier function.",
                "aliases": ["alcohol denat", "alcohol", "спирт", "денатурований спирт", 
                           "ethanol denatured", "ethyl alcohol denatured", 
                           "денатурат", "технічний спирт"],
                "source": "local"
            },
            {
                "id": 1024, "name": "Alcohol", "risk_level": "medium", "category": "solvent",
                "description": "Спирт, висушує шкіру, використовуйте помірно",
                "description_en": "Alcohol, dries skin, use moderately",
                "aliases": ["alcohol", "спирт", "ethanol", "ethyl alcohol", 
                           "етанол", "зерновий спирт", "винний спирт"],
                "source": "local"
            },
            {
                "id": 1025, "name": "Propylene Glycol", "risk_level": "medium", "category": "solvent",
                "description": "Розчинник та зволожувач. Може подразнювати чутливу шкіру.",
                "description_en": "Solvent and humectant. May irritate sensitive skin.",
                "aliases": ["propylene glycol", "пропіленгліколь", "пропілен гліколь", 
                           "pg", "1,2-propanediol", "пропандіол", "агент проникнення"],
                "source": "local"
            },
            {
                "id": 1026, "name": "Glycerin", "risk_level": "low", "category": "humectant",
                "description": "Гліцерин, натуральний зволожувач",
                "description_en": "Glycerin, natural humectant",
                "aliases": ["glycerin", "гліцерин", "glycerol", "glycerine", "e422",
                           "1,2,3-propanetriol", "гліцерол", "растительный глицерин"],
                "source": "local"
            },
            {
                "id": 1027, "name": "Butylene Glycol", "risk_level": "low", "category": "solvent",
                "description": "Розчинник, м'якіший ніж пропіленгліколь",
                "description_en": "Solvent, milder than propylene glycol",
                "aliases": ["butylene glycol", "бутиленгліколь", "1,3-butanediol",
                           "бутандіол", "bg", "butanediol"],
                "source": "local"
            },
            
            # === ЕМУЛЬГАТОРИ ===
            {
                "id": 1028, "name": "Cetearyl Alcohol", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор та загущувач, не висушує шкіру",
                "description_en": "Emulsifier and thickener, does not dry skin",
                "aliases": ["cetearyl alcohol", "цетеариловий спирт", "cetylstearyl alcohol",
                           "цетеарил алкохол", "емолент-емульгатор"],
                "source": "local"
            },
            {
                "id": 1029, "name": "Glyceryl Stearate", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор з гліцерину та стеаринової кислоти",
                "description_en": "Emulsifier from glycerin and stearic acid",
                "aliases": ["glyceryl stearate", "гліцерил стеарат", "glycerol monostearate",
                           "гліцерин моностеарат", "gms", "emulsifier gms"],
                "source": "local"
            },
            
            # === ПЕГ ТА ПОХІДНІ ===
            {
                "id": 1030, "name": "PEG-4", "risk_level": "low", "category": "emulsifier",
                "description": "Поліетиленгліколь, емульгатор",
                "description_en": "Polyethylene glycol, emulsifier",
                "aliases": ["peg-4", "peg", "поліетиленгліколь", "поліетилен гліколь", 
                           "polyethylene glycol", "macrogol", "пэг-4", "пег-4"],
                "source": "local"
            },
            {
                "id": 1031, "name": "PEG-4 Cocoate", "risk_level": "low", "category": "emulsifier",
                "description": "Ефір кокосової олії та ПЕГ-4",
                "description_en": "Coconut oil and PEG-4 ether",
                "aliases": ["peg-4 cocoate", "пег-4 кокоат", "polyethylene glycol-4 coconut ester",
                           "кокосовий ефір пег-4", "peg-4 coconut ester"],
                "source": "local"
            },
            
            # === ОЛІЇ ТА ЕМОЛЕНТИ ===
            {
                "id": 1032, "name": "Mineral Oil", "risk_level": "low", "category": "emollient",
                "description": "Мінеральна олія, окклюзійний агент. Безпечно, але може бути комедогенним для жирної шкіри.",
                "description_en": "Mineral oil, occlusive agent. Safe, but may be comedogenic for oily skin.",
                "aliases": ["mineral oil", "парафінове масло", "paraffinum liquidum", 
                           "вазелін", "petroleum oil", "вазелинове масло", 
                           "біле мінеральне масло", "liquid petroleum", "oil mineral"],
                "source": "local"
            },
            {
                "id": 1033, "name": "Petrolatum", "risk_level": "low", "category": "emollient",
                "description": "Вазелін, окклюзійний агент, захищає шкіру",
                "description_en": "Petroleum jelly, occlusive agent, protects skin",
                "aliases": ["petrolatum", "вазелін", "petroleum jelly", "soft paraffin",
                           "вазелин", "технічний вазелін", "медичний вазелін"],
                "source": "local"
            },
            {
                "id": 1034, "name": "Dimethicone", "risk_level": "low", "category": "emollient",
                "description": "Силікон, створює захисну плівку, некомедогенний",
                "description_en": "Silicone, creates protective film, non-comedogenic",
                "aliases": ["dimethicone", "диметикон", "силікон", "silicone", 
                           "polydimethylsiloxane", "pdmso", "діметикон", 
                           "силикон", "диметиконол"],
                "source": "local"
            },
            {
                "id": 1035, "name": "Cyclopentasiloxane", "risk_level": "low", "category": "emollient",
                "description": "Летючий силікон, не залишає жирного блиску",
                "description_en": "Volatile silicone, leaves no greasy residue",
                "aliases": ["cyclopentasiloxane", "циклопентасилоксан", "decamethylcyclopentasiloxane",
                           "d5", "cyclomethicone", "cyclic silicone"],
                "source": "local"
            },
            {
                "id": 1036, "name": "Squalane", "risk_level": "safe", "category": "emollient",
                "description": "Скваланан, легка олія, ідентична шкірному себуму",
                "description_en": "Squalane, lightweight oil, identical to skin sebum",
                "aliases": ["squalane", "скваланан", "perhydrosqualene", 
                           "гідрогенізований сквален", "олія сквалану"],
                "source": "local"
            },
            {
                "id": 1037, "name": "Jojoba Oil", "risk_level": "safe", "category": "emollient",
                "description": "Олія жожоба, близька до шкірного себуму",
                "description_en": "Jojoba oil, similar to skin sebum",
                "aliases": ["jojoba oil", "олія жожоба", "simmondsia chinensis oil",
                           "wax ester oil", "желтое масло жожоба", "холодного пресування жожоба"],
                "source": "local"
            },
            {
                "id": 1038, "name": "Argan Oil", "risk_level": "safe", "category": "emollient",
                "description": "Арганове масло, багате на вітамін Е",
                "description_en": "Argan oil, rich in vitamin E",
                "aliases": ["argan oil", "арганове масло", "argania spinosa oil",
                           "марокканське масло", "олія аргана", "аргановое масло"],
                "source": "local"
            },
            {
                "id": 1039, "name": "Caprylic/Capric Triglyceride", "risk_level": "low", "category": "emollient",
                "description": "Тригліцериди кокосової олії, легкий емолент",
                "description_en": "Coconut oil triglycerides, lightweight emollient",
                "aliases": ["caprylic/capric triglyceride", "каприлік/каприк тригліцерид",
                           "mct oil", "medium chain triglycerides", "кокосові тригліцериди"],
                "source": "local"
            },
            
            # === УФ-ФІЛЬТРИ ===
            # ВИСОКИЙ РИЗИК
            {
                "id": 1040, "name": "Oxybenzone", "risk_level": "high", "category": "UV filter",
                "description": "Бензофенон-3, ендокринний дизраптор, заборонений на Гаваях",
                "description_en": "Benzophenone-3, endocrine disruptor, banned in Hawaii",
                "aliases": ["oxybenzone", "оксибензон", "benzophenone-3", "бензофенон-3", 
                           "bp-3", "2-hydroxy-4-methoxybenzophenone", "оксибензон-3"],
                "source": "local"
            },
            {
                "id": 1041, "name": "Benzophenone-3", "risk_level": "high", "category": "UV filter",
                "description": "Оксибензон, ендокринний дизраптор",
                "description_en": "Oxybenzone, endocrine disruptor",
                "aliases": ["benzophenone-3", "бензофенон-3", "oxybenzone", "оксибензон",
                           "ср-3", "uv-absorber benzophenone"],
                "source": "local"
            },
            
            # ПОМІРНИЙ РИЗИК
            {
                "id": 1042, "name": "Avobenzone", "risk_level": "medium", "category": "UV filter",
                "description": "УФ-фільтр широкого спектра, може розкладатися на сонці",
                "description_en": "Broad-spectrum UV filter, may degrade in sunlight",
                "aliases": ["avobenzone", "авобензон", "butyl methoxydibenzoylmethane",
                           "parsol 1789", "uvinul a plus", "дибензоїлметан"],
                "source": "local"
            },
            {
                "id": 1043, "name": "Octinoxate", "risk_level": "medium", "category": "UV filter",
                "description": "УФ-фільтр, ендокринний дизраптор у високих концентраціях",
                "description_en": "UV filter, endocrine disruptor at high concentrations",
                "aliases": ["octinoxate", "октиноксат", "ethylhexyl methoxycinnamate",
                           "omc", "парасол mcx", "uv-absorber octinoxate"],
                "source": "local"
            },
            
            # НИЗЬКИЙ РИЗИК
            {
                "id": 1044, "name": "Titanium Dioxide", "risk_level": "low", "category": "UV filter",
                "description": "Мінеральний УФ-фільтр, безпечний, може залишати білий слід",
                "description_en": "Mineral UV filter, safe, may leave white cast",
                "aliases": ["titanium dioxide", "діоксид титану", "ci 77891", "tio2",
                           "титановые белила", "титаній діоксид", "пигмент білий 6"],
                "source": "local"
            },
            {
                "id": 1045, "name": "Zinc Oxide", "risk_level": "low", "category": "UV filter",
                "description": "Мінеральний УФ-фільтр, найбезпечніший, протизапальний",
                "description_en": "Mineral UV filter, safest, anti-inflammatory",
                "aliases": ["zinc oxide", "оксид цинку", "ci 77947", "zno",
                           "цинкова паста", "цинковый крем", "цинк оксид"],
                "source": "local"
            },
            
            # === АНТИБАКТЕРІАЛЬНІ ===
            {
                "id": 1046, "name": "Triclosan", "risk_level": "high", "category": "antibacterial",
                "description": "Антибактеріальний агент, сприяє резистентності, заборонений в ЄС",
                "description_en": "Antibacterial agent, promotes resistance, banned in EU",
                "aliases": ["triclosan", "триклозан", "2,4,4'-trichloro-2'-hydroxydiphenyl ether",
                           "антибактеріальний триклозан", "інгібітор бактерій"],
                "source": "local"
            },
            {
                "id": 1047, "name": "Triclocarban", "risk_level": "high", "category": "antibacterial",
                "description": "Антибактеріальний агент, аналогічно триклозану",
                "description_en": "Antibacterial agent, similar to triclosan",
                "aliases": ["triclocarban", "триклокарбан", "3,4,4'-trichlorocarbanilide",
                           "tcc", "антибактеріальний карбанілід"],
                "source": "local"
            },
            
            # === ХЕЛАТОРИ ===
            {
                "id": 1048, "name": "Tetrasodium EDTA", "risk_level": "medium", "category": "chelating agent",
                "description": "Хелатуючий агент, покращує піну, може подразнювати шкіру",
                "description_en": "Chelating agent, improves foam, may irritate skin",
                "aliases": ["tetrasodium edta", "тетранатрій едта", "едта-4на",
                           "ethylenediaminetetraacetic acid tetrasodium salt",
                           "хелатор", "хелатирующий агент"],
                "source": "local"
            },
            {
                "id": 1049, "name": "Disodium EDTA", "risk_level": "medium", "category": "chelating agent",
                "description": "Хелатуючий агент",
                "description_en": "Chelating agent",
                "aliases": ["disodium edta", "динатрій едта", "едта-2на",
                           "ethylenediaminetetraacetic acid disodium salt"],
                "source": "local"
            },
            
            # === РЕГУЛЯТОРИ PH ===
            {
                "id": 1050, "name": "Citric Acid", "risk_level": "low", "category": "pH adjuster",
                "description": "Лимонна кислота, регулятор pH, AHA у високих концентраціях",
                "description_en": "Citric acid, pH adjuster, AHA at high concentrations",
                "aliases": ["citric acid", "лимонна кислота", "сітілова кислота", 
                           "acidum citricum", "e330", "2-hydroxypropane-1,2,3-tricarboxylic acid",
                           "цитрикова кислота"],
                "source": "local"
            },
            {
                "id": 1051, "name": "Sodium Hydroxide", "risk_level": "high", "category": "pH adjuster",
                "description": "Луг, корозійний у чистому вигляді, безпечний у готових продуктах",
                "description_en": "Alkali, corrosive in pure form, safe in finished products",
                "aliases": ["sodium hydroxide", "гідроксид натрію", "каустична сода",
                           "луг", "едка", "naoh", "каустик", "технічна сода"],
                "source": "local"
            },
            {
                "id": 1052, "name": "Triethanolamine", "risk_level": "medium", "category": "pH adjuster",
                "description": "Регулятор pH, може утворювати нітрозаміни",
                "description_en": "pH adjuster, may form nitrosamines",
                "aliases": ["triethanolamine", "тріетаноламін", "tea",
                           "2,2',2''-nitrilotriethanol", "емульгатор tea", "tea база"],
                "source": "local"
            },
            
            # === НАТУРАЛЬНІ ЕКСТРАКТИ ===
            {
                "id": 1053, "name": "Aloe Barbadensis Leaf Juice", "risk_level": "safe", "category": "plant extract",
                "description": "Сік алое вера, заспокійливий, заживлюючий",
                "description_en": "Aloe vera juice, soothing, healing",
                "aliases": ["aloe barbadensis leaf juice", "сік алое вера", "aloe vera gel",
                           "алое барбаденсіс", "алое сік", "aloe extract", "гель алое"],
                "source": "local"
            },
            {
                "id": 1054, "name": "Camellia Sinensis Leaf Extract", "risk_level": "safe", "category": "plant extract",
                "description": "Екстракт зеленого чаю, антиоксидант",
                "description_en": "Green tea extract, antioxidant",
                "aliases": ["camellia sinensis leaf extract", "екстракт зеленого чаю",
                           "green tea extract", "чайний екстракт", "антиоксидант чаю"],
                "source": "local"
            },
            {
                "id": 1055, "name": "Chamomilla Recutita Flower Extract", "risk_level": "safe", "category": "plant extract",
                "description": "Екстракт ромашки, заспокійливий",
                "description_en": "Chamomile extract, soothing",
                "aliases": ["chamomilla recutita flower extract", "екстракт ромашки",
                           "chamomile extract", "ромашковий екстракт", "матрикарія екстракт"],
                "source": "local"
            },
            {
                "id": 1056, "name": "Centella Asiatica Extract", "risk_level": "safe", "category": "plant extract",
                "description": "Екстракт центелли азіатської, заживлює, заспокоює",
                "description_en": "Centella asiatica extract, healing, soothing",
                "aliases": ["centella asiatica extract", "екстракт центелли", "gotu kola extract",
                           "тігрова трава", "азіатська центелла", "madecassoside source"],
                "source": "local"
            },
            
            # === ВІТАМІНИ ТА АКТИВНІ ===
            {
                "id": 1057, "name": "Tocopherol", "risk_level": "safe", "category": "antioxidant",
                "description": "Вітамін Е, антиоксидант, стабілізатор",
                "description_en": "Vitamin E, antioxidant, stabilizer",
                "aliases": ["tocopherol", "токоферол", "vitamin e", "вітамін е",
                           "alpha-tocopherol", "d-alpha-tocopherol", "антиоксидант е"],
                "source": "local"
            },
            {
                "id": 1058, "name": "Ascorbic Acid", "risk_level": "safe", "category": "antioxidant",
                "description": "Вітамін С, антиоксидант, освітлює",
                "description_en": "Vitamin C, antioxidant, brightening",
                "aliases": ["ascorbic acid", "аскорбінова кислота", "vitamin c", "вітамін с",
                           "l-ascorbic acid", "антиоксидант с", "освітлювач с"],
                "source": "local"
            },
            {
                "id": 1059, "name": "Retinol", "risk_level": "medium", "category": "active",
                "description": "Вітамін А, антивіковий, може подразнювати, уникайте при вагітності",
                "description_en": "Vitamin A, anti-aging, may irritate, avoid during pregnancy",
                "aliases": ["retinol", "ретинол", "vitamin a", "вітамін а",
                           "all-trans-retinol", "антивіковий ретинол", "retin-a"],
                "source": "local"
            },
            {
                "id": 1060, "name": "Niacinamide", "risk_level": "safe", "category": "active",
                "description": "Ніацинамід, вітамін B3, покращує бар'єр, протизапальний",
                "description_en": "Niacinamide, vitamin B3, improves barrier, anti-inflammatory",
                "aliases": ["niacinamide", "ніацинамід", "nicotinamide", "вітамін b3", 
                           "вітамін b3", "nicotinic acid amide", "ніацинамід b3"],
                "source": "local"
            },
            {
                "id": 1061, "name": "Salicylic Acid", "risk_level": "medium", "category": "active",
                "description": "Саліцилова кислота, BHA, відлущувальний, для жирної шкіри",
                "description_en": "Salicylic acid, BHA, exfoliant, for oily skin",
                "aliases": ["salicylic acid", "саліцилова кислота", "beta hydroxy acid", 
                           "bha", "2-hydroxybenzoic acid", "відлущуючий bha"],
                "source": "local"
            },
            {
                "id": 1062, "name": "Glycolic Acid", "risk_level": "medium", "category": "active",
                "description": "Гліколева кислота, AHA, відлущувальний, підвищує чутливість до сонця",
                "description_en": "Glycolic acid, AHA, exfoliant, increases sun sensitivity",
                "aliases": ["glycolic acid", "гліколева кислота", "alpha hydroxy acid", 
                           "aha", "hydroxyacetic acid", "відлущуючий aha"],
                "source": "local"
            },
            {
                "id": 1063, "name": "Hyaluronic Acid", "risk_level": "safe", "category": "humectant",
                "description": "Гіалуронова кислота, зволожувач",
                "description_en": "Hyaluronic acid, moisturizer",
                "aliases": ["hyaluronic acid", "гіалуронова кислота", "sodium hyaluronate", 
                           "ha", "hyaluronan", "гіалуронат", "зволожувач ha"],
                "source": "local"
            },
            {
                "id": 1064, "name": "Ceramide NP", "risk_level": "safe", "category": "skin-identical",
                "description": "Церамід, відновлює шкірний бар'єр",
                "description_en": "Ceramide, restores skin barrier",
                "aliases": ["ceramide np", "церамід np", "ceramide 3", "бар'єрний церамід",
                           "шкірний ліпід", "natural moisturizing factor"],
                "source": "local"
            },
            {
                "id": 1065, "name": "Allantoin", "risk_level": "safe", "category": "soothing",
                "description": "Алантоїн, заспокійливий, заживлюючий",
                "description_en": "Allantoin, soothing, healing",
                "aliases": ["allantoin", "алантоїн", "5-ureidohydantoin", 
                           "заспокійливий агент", "регенеруючий алантоїн"],
                "source": "local"
            },
            {
                "id": 1066, "name": "Panthenol", "risk_level": "safe", "category": "soothing",
                "description": "Пантенол, провітамін B5, зволожує, заспокоює",
                "description_en": "Panthenol, provitamin B5, moisturizes, soothes",
                "aliases": ["panthenol", "пантенол", "provitamin b5", "d-panthenol",
                           "дексопантенол", "вітамін b5", "зволожувач b5"],
                "source": "local"
            },
            {
                "id": 1067, "name": "Bakuchiol", "risk_level": "safe", "category": "active",
                "description": "Натуральна альтернатива ретинолу, менш подразнювальна",
                "description_en": "Natural retinol alternative, less irritating",
                "aliases": ["bakuchiol", "бакучіол", "psoralea corylifolia extract",
                           "натуральний ретинол", "рослинний ретинол"],
                "source": "local"
            },
            {
                "id": 1068, "name": "Azelaic Acid", "risk_level": "medium", "category": "active",
                "description": "Азелаїнова кислота, для акне та розацеа",
                "description_en": "Azelaic acid, for acne and rosacea",
                "aliases": ["azelaic acid", "азелаїнова кислота", "nonanedioic acid",
                           "для акне", "для розацеа", "антивосполительная кислота"],
                "source": "local"
            },
            
            # === ПЛІВКОУТВОРЮВАЧІ ТА ПОЛІМЕРИ ===
            {
                "id": 1069, "name": "VP/VA Copolymer", "risk_level": "low", "category": "film former",
                "description": "Плівкоутворюючий полімер, фіксатор",
                "description_en": "Film-forming polymer, fixative",
                "aliases": ["vp/va copolymer", "vp va сополімер", "vinylpyrrolidone/vinyl acetate copolymer",
                           "полімер фіксатор", "стайлінг полімер"],
                "source": "local"
            },
            {
                "id": 1070, "name": "Acrylates Copolymer", "risk_level": "low", "category": "film former",
                "description": "Полімер, плівкоутворювач",
                "description_en": "Polymer, film-former",
                "aliases": ["acrylates copolymer", "акрилатний сополімер", "акриловий полімер",
                           "плівкоутворювач", "фіксуючий полімер"],
                "source": "local"
            },
            
            # === ЗАГУЩУВАЧІ ===
            {
                "id": 1071, "name": "Carbomer", "risk_level": "low", "category": "thickener",
                "description": "Загущувач, створює гелеву текстуру",
                "description_en": "Thickener, creates gel texture",
                "aliases": ["carbomer", "карбомер", "carbopol", "акриловий полімер",
                           "загущувач карбомер", "гельуючий агент"],
                "source": "local"
            },
            {
                "id": 1072, "name": "Xanthan Gum", "risk_level": "low", "category": "thickener",
                "description": "Натуральний загущувач з бактерій",
                "description_en": "Natural thickener from bacteria",
                "aliases": ["xanthan gum", "ксантанова камедь", "e415", "бактеріальна камедь",
                           "натуральний загущувач", "ксантан"],
                "source": "local"
            },
            
            # === ПІГМЕНТИ ===
            {
                "id": 1073, "name": "CI 77891", "risk_level": "low", "category": "pigment",
                "description": "Діоксид титану, білий пігмент, УФ-фільтр",
                "description_en": "Titanium dioxide, white pigment, UV filter",
                "aliases": ["ci 77891", "сі ай 77891", "titanium dioxide", "діоксид титану",
                           "білий пігмент", "титановий діоксид", "пигмент білий 6"],
                "source": "local"
            },
            {
                "id": 1074, "name": "Mica", "risk_level": "low", "category": "pigment",
                "description": "Слюда, перламутровий пігмент",
                "description_en": "Mica, pearlescent pigment",
                "aliases": ["mica", "слюда", "ci 77019", "muscovite",
                           "перламутровий пігмент", "сіяючий пігмент", "мінеральна слюда"],
                "source": "local"
            },
            
            # === ПРОТЕЇНИ ТА ЕКСТРАКТИ ===
            {
                "id": 1075, "name": "Hydrolyzed Silk Protein", "risk_level": "low", "category": "conditioning agent",
                "description": "Гідролізований шовковий протеїн, кондиціонер для волосся",
                "description_en": "Hydrolyzed silk protein, hair conditioner",
                "aliases": ["hydrolyzed silk protein", "гідролізований шовковий протеїн", 
                           "silk amino acids", "шовкові амінокислоти", "кондиціонер шовк"],
                "source": "local"
            },
            {
                "id": 1076, "name": "Hydrolyzed Collagen", "risk_level": "low", "category": "conditioning agent",
                "description": "Гідролізований колаген, зволожує",
                "description_en": "Hydrolyzed collagen, moisturizing",
                "aliases": ["hydrolyzed collagen", "гідролізований колаген", "collagen peptides",
                           "колагенові пептиди", "зволожуючий колаген"],
                "source": "local"
            },
            
            # === СОЛІ ТА МІНЕРАЛИ ===
            {
                "id": 1077, "name": "Sodium Chloride", "risk_level": "safe", "category": "viscosity controlling",
                "description": "Кухонна сіль, загущувач у шампунях",
                "description_en": "Table salt, thickener in shampoos",
                "aliases": ["sodium chloride", "хлорид натрію", "кухонна сіль", "сіль",
                           "nacl", "загущувач сіль", "поваренна сіль"],
                "source": "local"
            },
            
            # === СПЕЦІАЛЬНІ ДОДАТКИ ===
            {
                "id": 1078, "name": "Kojic Acid", "risk_level": "medium", "category": "active",
                "description": "Кодзієва кислота, освітлює, може подразнювати",
                "description_en": "Kojic acid, brightening, may irritate",
                "aliases": ["kojic acid", "кодзієва кислота", "5-hydroxy-2-hydroxymethyl-4-pyrone",
                           "освітлювач", "для гіперпігментації", "відбілювач"],
                "source": "local"
            },
            {
                "id": 1079, "name": "Arbutin", "risk_level": "low", "category": "active",
                "description": "Арбутин, освітлює гіперпігментацію",
                "description_en": "Arbutin, brightens hyperpigmentation",
                "aliases": ["arbutin", "арбутин", "hydroquinone-beta-d-glucopyranoside",
                           "натуральний освітлювач", "рослинний арбутин"],
                "source": "local"
            },
            
            # === ЕМУЛЬСИФІКАТОРИ ===
            {
                "id": 1080, "name": "Lecithin", "risk_level": "safe", "category": "emulsifier",
                "description": "Лецитин, натуральний емульгатор",
                "description_en": "Lecithin, natural emulsifier",
                "aliases": ["lecithin", "лецитин", "soy lecithin", "соєвий лецитин",
                           "натуральний емульгатор", "фосфоліпід"],
                "source": "local"
            },
            
            # === КОНСЕРВАНТИ ДРУГОГО ПОКОЛІННЯ ===
            {
                "id": 1081, "name": "Ethylhexylglycerin", "risk_level": "low", "category": "preservative",
                "description": "Консервант нового покоління",
                "description_en": "New-generation preservative",
                "aliases": ["ethylhexylglycerin", "етилгексилгліцерин", "octoxyglycerin",
                           "мягкий консервант", "консервант-емульгатор"],
                "source": "local"
            },
            
            # === АНТИПЕРСПІРАНТИ ===
            {
                "id": 1082, "name": "Aluminum Chlorohydrate", "risk_level": "medium", "category": "antiperspirant",
                "description": "Алюмінію хлоргідроксид, антиперспірант",
                "description_en": "Aluminum chlorohydrate, antiperspirant",
                "aliases": ["aluminum chlorohydrate", "алюмінію хлоргідроксид", "aluminum chlorhydroxide",
                           "антиперспірант", "зменшує потовиділення", "ach"],
                "source": "local"
            },
            
            # === ЕКО-ІНГРЕДІЄНТИ ===
            {
                "id": 1083, "name": "Bambusa Vulgaris Extract", "risk_level": "safe", "category": "plant extract",
                "description": "Екстракт бамбука, зволожує",
                "description_en": "Bamboo extract, moisturizing",
                "aliases": ["bambusa vulgaris extract", "екстракт бамбука", "bamboo extract",
                           "бамбуковий екстракт", "силіцій з бамбука"],
                "source": "local"
            },
            
            # === ФЕРМЕНТИ ===
            {
                "id": 1084, "name": "Papain", "risk_level": "low", "category": "enzyme",
                "description": "Папаїн, протеолітичний фермент, відлущує",
                "description_en": "Papain, proteolytic enzyme, exfoliating",
                "aliases": ["papain", "папаїн", "papaya enzyme", "фермент папаї",
                           "відлущуючий фермент", "ензимне пілінг"],
                "source": "local"
            },
            
            # === ВІТАМІНИ ГРУПИ B ===
            {
                "id": 1085, "name": "Biotin", "risk_level": "safe", "category": "vitamin",
                "description": "Біотин, вітамін B7, для волосся та нігтів",
                "description_en": "Biotin, vitamin B7, for hair and nails",
                "aliases": ["biotin", "біотин", "vitamin b7", "вітамін b7", "vitamin h",
                           "кофермент r", "для росту волосся"],
                "source": "local"
            },
            
            # === ПРЕБІОТИКИ ТА ПРОБІОТИКИ ===
            {
                "id": 1086, "name": "Inulin", "risk_level": "safe", "category": "prebiotic",
                "description": "Інулін, пребіотик",
                "description_en": "Inulin, prebiotic",
                "aliases": ["inulin", "інулін", "chicory root fiber", "цикорієвий інулін",
                           "пребіотик", "харчовий волокно"],
                "source": "local"
            },
            
            # === РОСЛИННІ МАСЛА ===
            {
                "id": 1087, "name": "Helianthus Annuus Seed Oil", "risk_level": "safe", "category": "emollient",
                "description": "Соняшникова олія, багата на вітамін Е",
                "description_en": "Sunflower oil, rich in vitamin E",
                "aliases": ["helianthus annuus seed oil", "соняшникова олія", "sunflower oil",
                           "масло соняшника", "олія соняшника", "багата вітаміном е"],
                "source": "local"
            },
            
            # === СПЕЦІАЛЬНІ СКЛАДОВІ ===
            {
                "id": 1088, "name": "Ubiquinone", "risk_level": "safe", "category": "antioxidant",
                "description": "Коензим Q10, антиоксидант, енергія клітин",
                "description_en": "Coenzyme Q10, antioxidant, cellular energy",
                "aliases": ["ubiquinone", "убіхінон", "coenzyme q10", "коензим q10",
                           "coq10", "енергія клітин", "антиоксидант q10"],
                "source": "local"
            },
            {
                "id": 1089, "name": "Caffeine", "risk_level": "safe", "category": "active",
                "description": "Кофеїн, зменшує набряки, тонізує",
                "description_en": "Caffeine, reduces puffiness, toning",
                "aliases": ["caffeine", "кофеїн", "1,3,7-trimethylxanthine", "для набряків",
                           "тонізатор", "звужує судини"],
                "source": "local"
            },
            
            # === СИНТЕТИЧНІ ЛІПІДИ ===
            {
                "id": 1090, "name": "Cetyl Palmitate", "risk_level": "low", "category": "emollient",
                "description": "Цетил пальмітат, емульгатор",
                "description_en": "Cetyl palmitate, emulsifier",
                "aliases": ["cetyl palmitate", "цетил пальмітат", "hexadecyl hexadecanoate",
                           "емульгатор", "восковий естер"],
                "source": "local"
            },
            
            # === ОСТАННІ ДОДАТКИ ===
            {
                "id": 1091, "name": "Bentonite", "risk_level": "low", "category": "thickener",
                "description": "Бентоніт, глина, загущувач",
                "description_en": "Bentonite, clay, thickener",
                "aliases": ["bentonite", "бентоніт", "montmorillonite clay", "глина",
                           "очищаюча глина", "маскувальна глина"],
                "source": "local"
            },
            {
                "id": 1092, "name": "Kaolin", "risk_level": "low", "category": "absorbent",
                "description": "Каолін, глина, абсорбент",
                "description_en": "Kaolin, clay, absorbent",
                "aliases": ["kaolin", "каолін", "china clay", "біла глина",
                           "абсорбуюча глина", "маскувальна глина"],
                "source": "local"
            },
            {
                "id": 1093, "name": "Silica", "risk_level": "low", "category": "absorbent",
                "description": "Кремнезем, матує, абсорбує",
                "description_en": "Silica, mattifies, absorbs",
                "aliases": ["silica", "кремнезем", "silicon dioxide", "діоксид кремнію",
                           "матирующий агент", "абсорбент", "сіліка"],
                "source": "local"
            },
            
            # Додаткові важливі інгредієнти для досягнення 100+
            {
                "id": 1094, "name": "Polysorbate 20", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор та солюбілізатор",
                "description_en": "Emulsifier and solubilizer",
                "aliases": ["polysorbate 20", "полісорбат 20", "tween 20", "емульгатор 20"],
                "source": "local"
            },
            {
                "id": 1095, "name": "Polysorbate 80", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор та солюбілізатор",
                "description_en": "Emulsifier and solubilizer",
                "aliases": ["polysorbate 80", "полісорбат 80", "tween 80", "емульгатор 80"],
                "source": "local"
            },
            {
                "id": 1096, "name": "Sorbitan Oleate", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор",
                "description_en": "Emulsifier",
                "aliases": ["sorbitan oleate", "сорбітан олеат", "span 80", "емульгатор олеат"],
                "source": "local"
            },
            {
                "id": 1097, "name": "Ceteareth-20", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор",
                "description_en": "Emulsifier",
                "aliases": ["ceteareth-20", "цетеарет-20", "емульгатор цетеарет"],
                "source": "local"
            },
            {
                "id": 1098, "name": "Steareth-20", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор",
                "description_en": "Emulsifier",
                "aliases": ["steareth-20", "стеарет-20", "емульгатор стеарет"],
                "source": "local"
            },
            {
                "id": 1099, "name": "PEG-100 Stearate", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор",
                "description_en": "Emulsifier",
                "aliases": ["peg-100 stearate", "пег-100 стеарат", "емульгатор пег-100"],
                "source": "local"
            },
            {
                "id": 1100, "name": "Lactic Acid", "risk_level": "low", "category": "pH adjuster",
                "description": "Молочна кислота, AHA, більш м'який ніж гліколевий",
                "description_en": "Lactic acid, AHA, milder than glycolic",
                "aliases": ["lactic acid", "молочна кислота", "aha", "alpha hydroxy acid",
                           "відлущуючий aha", "зволожувальний aha"],
                "source": "local"
            },
        ]
        
        # Додаємо ще інгредієнти для досягнення повного охоплення
        # У реальній реалізації тут будуть всі 500+ інгредієнтів з бази даних
        
        print(f"Завантажено {len(ingredients)} інгредієнтів з повними псевдонімами")
        return ingredients

    def load_common_fixes(self):
        """Завантаження виправлень помилок OCR та транскрипції"""
        print("Завантаження виправлень помилок...")
        fixes = {
            # Хімічні помилки OCR
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
            
            # Специфічні помилки з вашого OCR
            "sodlum": "sodium",
            "glycerln": "glycerin",
            "parfume": "parfum",
            "peg4": "peg-4",
            "edta.": "edta",
            "hydrotyzed": "hydrolyzed",
            "methylchlorcisothiazoline": "methylchloroisothiazolinone",
            
            # Українські варіанти та помилки транскрипції
            "гліцерин": "glycerin",
            "гіалуронова": "hyaluronic",
            "саліцилова": "salicylic",
            "ретинол": "retinol",
            "ніацинамід": "niacinamide",
            "оксид цинку": "zinc oxide",
            "діоксид титану": "titanium dioxide",
            "бензофенон": "oxybenzone",
            "парафінове масло": "mineral oil",
            "силікон": "silicone",
            "парабен": "paraben",
            "консервант": "preservative",
            "емульгатор": "emulsifier",
            "емолент": "emollient",
            "ароматизатор": "fragrance",
            "пінник": "surfactant",
            "пінноутворювач": "surfactant",
            "зволожувач": "humectant",
            "антиоксидант": "antioxidant",
            "відлущуючий": "exfoliant",
            "стабілізатор": "stabilizer",
            "пігмент": "pigment",
            "барвник": "colorant",
            "загущувач": "thickener",
            "розчинник": "solvent",
            "хелуючий": "chelating",
            "уф-фільтр": "uv filter",
            "сонцезахисний": "sunscreen",
            "антиперспірант": "antiperspirant",
            "дезодорант": "deodorant",
            "плівкоутворювач": "film former",
            "кондиціонер": "conditioner",
            "екстрант": "extract",
            "олія": "oil",
            "екстракт": "extract",
            "сік": "juice",
            "протеїн": "protein",
            "пептид": "peptide",
            "фермент": "enzyme",
            "вітамін": "vitamin",
            "мінерал": "mineral",
            "сіль": "salt",
            "кислота": "acid",
            "спирт": "alcohol",
            "воск": "wax",
            "гель": "gel",
            "крем": "cream",
            "лосьйон": "lotion",
            "лосьон": "lotion",
            "тонік": "tonic",
            "серум": "serum",
            "маска": "mask",
            "скраб": "scrub",
            "пілінг": "peeling",
            
            # Додаткові специфічні виправлення
            "алое": "aloe",
            "алое вера": "aloe vera",
            "жожоба": "jojoba",
            "аргана": "argan",
            "шипшина": "rosehip",
            "шипшини": "rosehip",
            "кокос": "coconut",
            "кокосова": "coconut",
            "соняшник": "sunflower",
            "соняшникова": "sunflower",
            "оливкова": "olive",
            "оливкове": "olive",
            "миндальна": "almond",
            "миндальное": "almond",
            "ланолин": "lanolin",
            "вазелін": "petrolatum",
            "парафін": "paraffin",
            "гліколева": "glycolic",
            "молочна": "lactic",
            "саліцилова": "salicylic",
            "азелаїнова": "azelaic",
            "гіалуронова": "hyaluronic",
            "аскорбінова": "ascorbic",
            "лимонна": "citric",
            "сорбінова": "sorbic",
            "бензойна": "benzoic",
            "сорбат": "sorbate",
            "бензоат": "benzoate",
            "цитрат": "citrate",
            "стеарат": "stearate",
            "пальмітат": "palmitate",
            "лаурат": "laurate",
            "олеат": "oleate",
            "гліцерат": "glycerate",
            "сульфат": "sulfate",
            "хлорид": "chloride",
            "гідроксид": "hydroxide",
            "оксид": "oxide",
            "діоксид": "dioxide",
            "карбонат": "carbonate",
            "силікат": "silicate",
            "фосфат": "phosphate",
            "ацетат": "acetate",
            "глюконат": "gluconate",
            "лактат": "lactate",
            "малат": "malate",
            "цитрат": "citrate",
            "тартрат": "tartrate",
            "саліцилат": "salicylate",
            "бензоат": "benzoate",
            "сорбат": "sorbate",
            "пропіонат": "propionate",
        }
        print(f"Завантажено {len(fixes)} виправлень помилок")
        return fixes
    
    def _create_not_found_response(self, ingredient_name):
        """Створення відповіді для незнайденого інгредієнта"""
        risk_level = "unknown"
        ingredient_lower = ingredient_name.lower()
        
        # Визначаємо ризик за ключовими словами
        if any(word in ingredient_lower for word in ['formaldehyde', 'isothiazolinone', 'triclosan', 'oxybenzone', 'benzophenone']):
            risk_level = "high"
        elif any(word in ingredient_lower for word in ['paraben', 'parfum', 'fragrance', 'alcohol', 'sulfate', 'glycol', 'triethanolamine', 'phenoxyethanol']):
            risk_level = "medium"
        elif any(word in ingredient_lower for word in ['glycerin', 'aqua', 'water', 'benzoate', 'dioxide', 'oxide', 'acid', 'oil', 'extract', 'butter']):
            risk_level = "low"
        elif any(word in ingredient_lower for word in ['aloe', 'vitamin', 'ceramide', 'panthenol', 'allantoin', 'centella']):
            risk_level = "safe"
        
        # Визначаємо категорію за ключовими словами
        category = "unknown"
        if any(word in ingredient_lower for word in ['sulfate', 'glucoside', 'betaine', 'surfactant']):
            category = "surfactant"
        elif any(word in ingredient_lower for word in ['paraben', 'phenoxy', 'benzoate', 'sorbate', 'preservative']):
            category = "preservative"
        elif any(word in ingredient_lower for word in ['parfum', 'fragrance', 'limonene', 'linalool', 'aroma']):
            category = "fragrance"
        elif any(word in ingredient_lower for word in ['alcohol', 'glycol', 'glycerin', 'solvent']):
            category = "solvent"
        elif any(word in ingredient_lower for word in ['oil', 'butter', 'squalane', 'dimethicone', 'silicone']):
            category = "emollient"
        elif any(word in ingredient_lower for word in ['uv', 'sunscreen', 'titanium', 'zinc', 'avobenzone']):
            category = "UV filter"
        elif any(word in ingredient_lower for word in ['acid', 'aha', 'bha', 'retinol', 'niacinamide']):
            category = "active"
        elif any(word in ingredient_lower for word in ['extract', 'juice', 'water']):
            category = "plant extract"
        elif any(word in ingredient_lower for word in ['polymer', 'copolymer', 'acrylate']):
            category = "film former"
        elif any(word in ingredient_lower for word in ['gum', 'carbomer', 'thickener']):
            category = "thickener"
        
        return {
            "name": ingredient_name,
            "risk_level": risk_level,
            "category": category,
            "description": f"Інгредієнт не знайдено в локальній базі. Оцінка на основі ключових слів.",
            "description_en": "Ingredient not found in local database. Estimated based on keywords.",
            "source": "not_found",
            "aliases": [],
            "context": "Автоматична оцінка на основі назви"
        }
    
    def is_potential_ingredient(self, text):
        """Перевірка, чи може текст бути інгредієнтом (ПОКРАЩЕНА версія)"""
        if not text or len(text) < 3:
            return False
        
        text_lower = text.lower().strip()
        
        # 1. Перевіряємо стоп-слова
        if text_lower in self.stop_words:
            return False
        
        # 2. Відсіюємо маркетингові фрази (занадто довгі тексти)
        if len(text) > 80:
            return False
        
        # 3. Перевіряємо формат INCI назв
        # INCI зазвичай: великі літери, можуть бути цифри/дефіси/пробіли
        words = text.split()
        
        # Якщо це одне слово або кілька слів через дефіс
        if len(words) == 1 or '-' in text:
            # Перевіряємо хімічні суфікси
            chemical_suffixes = ['ate', 'ide', 'one', 'ene', 'ol', 'ic', 'in', 'ose', 'ium', 'ate', 'ester', 'oil', 'acid', 'al', 'ane']
            for suffix in chemical_suffixes:
                if text_lower.endswith(suffix) and len(text) > 3:
                    return True
            
            # Перевіряємо наявність цифр (PEG-4, CI 77891)
            if re.search(r'\d', text):
                return True
            
            # Перевіряємо за словником інгредієнтів
            for ingredient in self.local_ingredients:
                if text_lower == ingredient['name'].lower():
                    return True
                for alias in ingredient.get('aliases', []):
                    if text_lower == alias.lower():
                        return True
        
        # 4. Перевіряємо багатословні INCI назви
        if len(words) >= 2 and len(words) <= 4:
            # Перевіряємо, чи не містить маркетингових слів
            marketing_words = ['продукція', 'косметична', 'гігієнічна', 'призначено', 
                             'зберігати', 'виготовлювач', 'росія', 'область', 'україна']
            if not any(marketing_word in text_lower for marketing_word in marketing_words):
                # Перевіряємо, чи містить латинські літери
                if re.search(r'[a-zA-Z]', text):
                    return True
        
        return False
    
    def extract_ingredient_candidates(self, text):
        """Виділення кандидатів на інгредієнти з тексту (ПОКРАЩЕНА версія)"""
        if not text:
            return []
        
        print(f"Виділення кандидатів з тексту ({len(text)} символів)")
        
        # 1. Знаходимо початок списку інгредієнтів
        composition_start = -1
        composition_patterns = [
            r'СКЛАД\s*[:\-]',
            r'INGREDIENTS\s*[:\-]',
            r'INCI\s*[:\-]',
            r'СОСТАВ\s*[:\-]',
            r'ІНГРЕДІЄНТИ\s*[:\-]',
            r'COMPOSITION\s*[:\-]',
            r'КОМПОЗИЦІЯ\s*[:\-]'
        ]
        
        for pattern in composition_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                composition_start = match.end()
                print(f"Знайдено розділ 'СКЛАД' у позиції {composition_start}")
                break
        
        # Якщо не знайшли заголовок, шукаємо рядок з INCI назвами
        if composition_start == -1:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if ',' in line and any(word in line.upper() for word in ['AQUA', 'SODIUM', 'GLYCERIN', 'PARFUM', 'WATER', 'ALCOHOL']):
                    composition_start = sum(len(l) + 1 for l in lines[:i])
                    print(f"Знайдено список інгредієнтів у рядку {i+1}")
                    break
        
        # 2. Виділяємо текст списку інгредієнтів
        if composition_start != -1:
            # Шукаємо кінець списку
            end_patterns = [
                r'\n\s*\d+\.',
                r'\n{2,}',
                r'\.\s*\n',
                r'Зберігати|Хранить',
                r'УМОВИ',
                r'ВИГОТОВЛЮВАЧ|ИЗГОТОВИТЕЛЬ',
                r'www\.|http://',
                r'©|™|®',
                r'ТЕРМІН|СРОК',
            ]
            
            end_pos = len(text)
            for pattern in end_patterns:
                match = re.search(pattern, text[composition_start:], re.IGNORECASE | re.MULTILINE)
                if match:
                    potential_end = composition_start + match.start()
                    if potential_end < end_pos:
                        end_pos = potential_end
            
            ingredients_text = text[composition_start:end_pos].strip()
            print(f"Виділено текст інгредієнтів: {len(ingredients_text)} символів")
        else:
            ingredients_text = text
            print("Розділ 'СКЛАД' не знайдено, використовуємо весь текст")
        
        # 3. Очищуємо текст
        ingredients_text = re.sub(r'[^\w\s.,;:\-–/()\n]', ' ', ingredients_text)
        ingredients_text = re.sub(r'\s+', ' ', ingredients_text)
        
        # 4. Розділяємо на інгредієнти
        candidates = []
        
        # Стратегія 1: Розділення за комами та крапками з комою
        items = re.split(r'[,;]', ingredients_text)
        
        for item in items:
            item = item.strip()
            if not item or len(item) < 3:
                continue
            
            # Пропускаємо маркетинговий текст
            item_lower = item.lower()
            marketing_keywords = [
                'продукція', 'косметична', 'гігієнічна', 'миюча',
                'крем-мило', 'рідке', 'гоСТ', 'призначено', 'зовнішнього',
                'застосування', 'зберігати', 'температурі', 'сонячних', 'променів',
                'виготовлювач', 'якість', 'гарант', 'область', 'район',
                'промити', 'чистою', 'водою', 'використовувати', 'випадку',
                'виникнення', 'алергічної', 'реакції', 'подразнення'
            ]
            
            if any(keyword in item_lower for keyword in marketing_keywords):
                continue
            
            # Перевіряємо, схоже на INCI назву
            has_latin = bool(re.search(r'[a-zA-Z]', item))
            has_cyrillic = bool(re.search(r'[а-яА-ЯіІїЇєЄ]', item))
            
            # Якщо є і латинські, і кириличні літери у короткому тексті - пропускаємо
            if has_latin and has_cyrillic and len(item) < 50:
                continue
            
            # Перевіряємо через is_potential_ingredient
            if self.is_potential_ingredient(item):
                candidates.append(item)
                print(f"Кандидат: '{item}'")
        
        # Стратегія 2: За переводами рядків (для складних випадків)
        if len(candidates) < 3:
            lines = ingredients_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 10 and self.is_potential_ingredient(line):
                    candidates.append(line)
        
        # Видаляємо дублікати
        unique_candidates = []
        seen = set()
        
        for candidate in candidates:
            candidate_lower = candidate.lower()
            if candidate_lower not in seen:
                seen.add(candidate_lower)
                unique_candidates.append(candidate)
        
        print(f"Знайдено {len(unique_candidates)} унікальних кандидатів")
        
        return unique_candidates
    
    def search_ingredient(self, ingredient_name):
        """Покращений пошук інгредієнта"""
        
        if not ingredient_name or not isinstance(ingredient_name, str):
            return self._create_not_found_response(ingredient_name)
        
        ingredient_name = ingredient_name.strip()
        
        # Перевірка кешу
        cache_key = ingredient_name.lower()
        if cache_key in self.search_cache:
            cached_result = self.search_cache[cache_key]
            cache_age = datetime.now() - cached_result['timestamp']
            if cache_age < timedelta(hours=24):
                return cached_result['data']
        
        # 1. Застосовуємо виправлення помилок
        cleaned_name = self.clean_text(ingredient_name)
        
        # 2. Пошук у локальній базі (спочатку оригінальне ім'я, потім очищене)
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
        
        # 3. Пошук у зовнішніх джерелах
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
        
        # 4. Якщо нічого не знайдено
        not_found_result = self._create_not_found_response(ingredient_name)
        self.search_cache[cache_key] = {
            'data': not_found_result,
            'timestamp': datetime.now(),
            'source': 'not_found'
        }
        return not_found_result
    
    def _search_local(self, ingredient_name):
        """Пошук у локальній базі з нечітким зіставленням (RapidFuzz)"""
        ingredient_lower = ingredient_name.lower().strip()
        
        if not ingredient_lower or len(ingredient_lower) < 2:
            return None

        # ─── Етап 1: Точне співпадіння через індекс (O(1)) ───
        exact = self._exact_index.get(ingredient_lower)
        if exact:
            return exact

        # ─── Етап 2: Часткове входження (substring match) ───
        if len(ingredient_lower) > 4:
            for name, ingredient in self._exact_index.items():
                if len(name) > 4 and (ingredient_lower in name or name in ingredient_lower):
                    return ingredient

        # ─── Етап 3: Нечіткий пошук через RapidFuzz ───
        if RAPIDFUZZ_AVAILABLE and len(ingredient_lower) >= 4:
            return self._fuzzy_search(ingredient_lower)

        return None

    def _fuzzy_search(self, query):
        """Нечіткий пошук інгредієнта за допомогою RapidFuzz.
        
        Використовує process.extractOne для ефективного пошуку найкращого
        збігу серед усіх назв та псевдонімів у індексі.
        
        Два етапи scoring:
          1. token_sort_ratio — стійкий до перестановки слів
             ('sodium laureth sulfate' ↔ 'laureth sulfate sodium')
          2. partial_ratio — для часткових збігів та помилок OCR
             ('glycerln' → 'glycerin', 'sodlum' → 'sodium')
        
        Порогові значення:
          - 85+ для коротких назв (≤10 символів) — жорсткіший поріг
          - 78+ для довших назв — м'якший, бо довгі INCI-назви складні
        """
        if not RAPIDFUZZ_AVAILABLE or not self._all_names:
            return None

        # Динамічний поріг: короткі назви потребують вищої точності
        threshold = 85 if len(query) <= 10 else 78

        # Етап 1: token_sort_ratio (найкращий для INCI-назв)
        result_token = process.extractOne(
            query,
            self._all_names,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold
        )
        
        # Етап 2: partial_ratio (для OCR-помилок типу 'glycerln' → 'glycerin')
        result_partial = process.extractOne(
            query,
            self._all_names,
            scorer=fuzz.partial_ratio,
            score_cutoff=threshold + 5  # трохи жорсткіший поріг для partial
        )
        
        # Вибираємо найкращий результат
        best_name = None
        best_score = 0
        
        if result_token and result_token[1] > best_score:
            best_name = result_token[0]
            best_score = result_token[1]
        
        if result_partial and result_partial[1] * 0.95 > best_score:
            best_name = result_partial[0]
            best_score = result_partial[1] * 0.95
        
        if best_name and best_name in self._exact_index:
            ingredient = self._exact_index[best_name]
            print(f"  ✓ Fuzzy match: '{query}' → '{ingredient['name']}' "
                  f"(via '{best_name}', score: {best_score:.0f}%)")
            return ingredient
        
        return None
    
    def clean_text(self, text):
        """Очищення тексту перед пошуком"""
        if not text:
            return ""
        
        text = text.lower()
        text = re.sub(r'[^a-zA-Z0-9а-яА-ЯіІїЇєЄ\s\-.,]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Застосовуємо виправлення помилок
        for wrong, correct in self.common_fixes.items():
            if wrong.lower() in text:
                text = text.replace(wrong.lower(), correct.lower())
        
        return text.strip()
    
    def find_ingredients(self, text):
        """Покращена функція пошуку інгредієнтів"""
        if not text or not isinstance(text, str):
            print("Текст для аналізу порожній або не є рядком")
            return []
        
        print(f"Пошук інгредієнтів у тексті")
        
        # 1. Виділяємо кандидатів
        candidates = self.extract_ingredient_candidates(text)
        
        # 2. Шукаємо кожного кандидата
        found_ingredients = []
        seen_names = set()
        
        for candidate in candidates:
            ingredient = self.search_ingredient(candidate)
            
            if ingredient['name'] not in seen_names:
                found_ingredients.append(ingredient)
                seen_names.add(ingredient['name'])
                print(f"Знайдено: {ingredient['name']} (ризик: {ingredient['risk_level']})")
        
        print(f"ПІДСУМОК: знайдено {len(found_ingredients)} інгредієнтів")
        
        # 3. Статистика за ризиками
        risk_stats = {'high': 0, 'medium': 0, 'low': 0, 'safe': 0, 'unknown': 0}
        
        for ing in found_ingredients:
            risk = ing.get('risk_level', 'unknown')
            if risk in risk_stats:
                risk_stats[risk] += 1
        
        print(f"Статистика ризиків: високий {risk_stats['high']} помірний {risk_stats['medium']} низький {risk_stats['low']} безпечний {risk_stats['safe']} невідомий {risk_stats['unknown']}")
        
        return found_ingredients


class ExternalDataFetcher:
    """Клас для отримання даних із зовнішніх відкритих баз інгредієнтів.
    
    Підтримувані джерела:
      1. Open Beauty Facts — відкрита база косметичних інгредієнтів
         (https://world.openbeautyfacts.org) — найбільш релевантна для косметики
      2. PubChem — база хімічних сполук від NIH
         (https://pubchem.ncbi.nlm.nih.gov) — для хімічної класифікації
      3. CIR (Chemical Identifier Resolver) від NIH/NCI —
         для перевірки валідності INCI-назв
    
    Результати кешуються в SQLite на 7 днів, щоб не перевантажувати API.
    """
    
    def __init__(self, cache_dir='data_cache'):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'external_cache.db')
        os.makedirs(cache_dir, exist_ok=True)
        self.init_cache()
        
        # Таймаут для HTTP-запитів
        self.timeout = 8
        
        # Маппінг функцій інгредієнтів → рівень ризику
        self._function_risk_map = {
            # Високий ризик
            'antimicrobial': 'high', 'preservative': 'medium',
            'uv absorber': 'medium', 'uv filter': 'medium',
            # Помірний ризик
            'surfactant': 'medium', 'emulsifying': 'medium',
            'fragrance': 'medium', 'perfuming': 'medium',
            'denaturant': 'medium',
            # Низький ризик
            'emollient': 'low', 'moisturising': 'low', 'humectant': 'low',
            'skin conditioning': 'low', 'hair conditioning': 'low',
            'viscosity controlling': 'low', 'emulsion stabilising': 'low',
            'antioxidant': 'low', 'chelating': 'low',
            'buffering': 'low', 'ph adjuster': 'low',
            # Безпечні
            'solvent': 'safe', 'skin protecting': 'safe',
            'tonic': 'safe', 'cleansing': 'low',
        }
        
        print(f"[ExternalData] Ініціалізовано, кеш: {self.cache_file}")
        
    def init_cache(self):
        """Ініціалізація SQLite кешу"""
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
        """Пошук інгредієнта у зовнішніх джерелах.
        
        Послідовність пошуку:
          1. Кеш (SQLite, TTL 7 днів)
          2. Open Beauty Facts (спеціалізована база косметики)
          3. PubChem (загальна база хімічних сполук)
        """
        if not ingredient_name or len(ingredient_name.strip()) < 3:
            return None
        
        ingredient_name = ingredient_name.strip()
        
        # 1. Перевіряємо кеш
        cached = self._get_from_cache(ingredient_name)
        if cached:
            print(f"[ExternalData] Кеш: {ingredient_name}")
            return cached
        
        # 2. Перевірка доступу до мережі
        if not self._check_network():
            return None
        
        # 3. Open Beauty Facts
        result = self._search_open_beauty_facts(ingredient_name)
        
        # 4. PubChem
        if not result:
            result = self._search_pubchem(ingredient_name)
        
        # 5. Зберігаємо в кеш
        if result:
            self._save_to_cache(ingredient_name, result)
        
        return result
    
    def _check_network(self):
        """Швидка перевірка доступу до мережі"""
        try:
            requests.head("https://world.openbeautyfacts.org", timeout=3)
            return True
        except (requests.ConnectionError, requests.Timeout):
            print("[ExternalData] Немає доступу до мережі")
            return False
    
    def _search_open_beauty_facts(self, ingredient_name):
        """Пошук у Open Beauty Facts — відкрита база косметичних продуктів.
        
        Open Beauty Facts містить дані про косметичні продукти з усього світу,
        включаючи повні списки інгредієнтів. API дозволяє шукати за назвою
        інгредієнта та отримувати інформацію про його функції.
        
        Endpoint: GET /api/v2/search?ingredients_tags={name}
        """
        try:
            # Нормалізуємо назву для API
            search_name = ingredient_name.lower().replace(' ', '-')
            
            url = (f"https://world.openbeautyfacts.org/api/v2/search?"
                   f"ingredients_tags={search_name}&"
                   f"fields=product_name,ingredients&"
                   f"page_size=5&json=1")
            
            print(f"[OpenBeautyFacts] Запит: {ingredient_name}")
            response = requests.get(url, timeout=self.timeout, headers={
                'User-Agent': 'Skipley/1.0 (cosmetic ingredient checker)'
            })
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            products = data.get('products', [])
            
            if not products:
                # Спробуємо пошук через текстовий запит
                return self._search_obf_text(ingredient_name)
            
            # Аналізуємо знайдені продукти для визначення категорії
            ingredient_lower = ingredient_name.lower()
            category = self._classify_by_name(ingredient_lower)
            risk_level = self._assess_risk_by_name(ingredient_lower)
            
            return {
                "name": ingredient_name,
                "risk_level": risk_level,
                "category": category,
                "description": f"Косметичний інгредієнт, знайдений у {len(products)} продуктах",
                "description_en": f"Cosmetic ingredient found in {len(products)} products",
                "source": "openbeautyfacts",
                "aliases": [],
                "context": f"Дані з Open Beauty Facts ({len(products)} продуктів)"
            }
            
        except requests.Timeout:
            print(f"[OpenBeautyFacts] Таймаут для {ingredient_name}")
            return None
        except Exception as e:
            print(f"[OpenBeautyFacts] Помилка: {e}")
            return None
    
    def _search_obf_text(self, ingredient_name):
        """Текстовий пошук в Open Beauty Facts."""
        try:
            url = (f"https://world.openbeautyfacts.org/cgi/search.pl?"
                   f"search_terms={ingredient_name}&"
                   f"search_simple=1&action=process&json=1&page_size=3")
            
            response = requests.get(url, timeout=self.timeout, headers={
                'User-Agent': 'Skipley/1.0'
            })
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            count = data.get('count', 0)
            
            if count == 0:
                return None
            
            ingredient_lower = ingredient_name.lower()
            return {
                "name": ingredient_name,
                "risk_level": self._assess_risk_by_name(ingredient_lower),
                "category": self._classify_by_name(ingredient_lower),
                "description": f"Інгредієнт знайдено у {count} косметичних продуктах",
                "description_en": f"Ingredient found in {count} cosmetic products",
                "source": "openbeautyfacts",
                "aliases": [],
                "context": f"Open Beauty Facts: {count} продуктів"
            }
        except Exception as e:
            print(f"[OpenBeautyFacts] Текстовий пошук — помилка: {e}")
            return None
    
    def _search_pubchem(self, ingredient_name):
        """Пошук у PubChem — база хімічних сполук від NIH.
        
        PubChem REST API повертає детальну інформацію про хімічну сполуку,
        включаючи молекулярну формулу, масу, IUPAC-назву та синоніми.
        
        Endpoint: GET /rest/pug/compound/name/{name}/JSON
        """
        try:
            # Кодуємо назву для URL
            encoded_name = requests.utils.quote(ingredient_name)
            url = (f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/"
                   f"compound/name/{encoded_name}/JSON")
            
            print(f"[PubChem] Запит: {ingredient_name}")
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            compounds = data.get('PC_Compounds', [])
            
            if not compounds:
                return None
            
            compound = compounds[0]
            cid = compound.get('id', {}).get('id', {}).get('cid', '')
            
            # Витягуємо IUPAC-назву та молекулярну формулу
            iupac_name = ''
            mol_formula = ''
            for prop in compound.get('props', []):
                urn = prop.get('urn', {})
                label = urn.get('label', '')
                if label == 'IUPAC Name' and urn.get('name') == 'Preferred':
                    iupac_name = prop.get('value', {}).get('sval', '')
                elif label == 'Molecular Formula':
                    mol_formula = prop.get('value', {}).get('sval', '')
            
            ingredient_lower = ingredient_name.lower()
            risk_level = self._assess_risk_by_name(ingredient_lower)
            category = self._classify_by_name(ingredient_lower)
            
            description = f"Хімічна сполука (PubChem CID: {cid})"
            description_en = f"Chemical compound (PubChem CID: {cid})"
            if mol_formula:
                description += f", формула: {mol_formula}"
                description_en += f", formula: {mol_formula}"
            if iupac_name and iupac_name != ingredient_name:
                description += f", IUPAC: {iupac_name[:80]}"
                description_en += f", IUPAC: {iupac_name[:80]}"
            
            return {
                "name": ingredient_name,
                "risk_level": risk_level,
                "category": category,
                "description": description,
                "description_en": description_en,
                "source": "pubchem",
                "aliases": [],
                "context": f"PubChem CID: {cid}"
            }
            
        except requests.Timeout:
            print(f"[PubChem] Таймаут для {ingredient_name}")
            return None
        except Exception as e:
            print(f"[PubChem] Помилка: {e}")
            return None
    
    def _classify_by_name(self, name_lower):
        """Класифікація інгредієнта за його INCI-назвою."""
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
    
    def _assess_risk_by_name(self, name_lower):
        """Оцінка ризику за назвою INCI-інгредієнта."""
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
        elif any(kw in name_lower for kw in medium_risk):
            return 'medium'
        elif any(kw in name_lower for kw in safe_risk):
            return 'safe'
        elif any(kw in name_lower for kw in low_risk):
            return 'low'
        return 'unknown'
    
    def _get_from_cache(self, ingredient_name):
        """Отримання з кешу (TTL: 7 днів)"""
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
        except Exception as e:
            print(f"[Cache] Помилка читання: {e}")
            return None
    
    def _save_to_cache(self, ingredient_name, data):
        """Збереження в кеш"""
        try:
            conn = sqlite3.connect(self.cache_file)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO ingredients_cache "
                "(name, data, source, last_updated) "
                "VALUES (?, ?, ?, datetime('now'))",
                (ingredient_name.lower(), json.dumps(data, ensure_ascii=False),
                 data.get('source', 'unknown'))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Cache] Помилка збереження: {e}")