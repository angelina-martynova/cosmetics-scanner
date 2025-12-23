import re
import json
import requests
from datetime import datetime, timedelta
import sqlite3
import os
import traceback


class IngredientChecker:
    def __init__(self, use_cache=True, fallback_to_local=True):
        print("🔄 Ініціалізація IngredientChecker...")
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
        
        print(f"✅ IngredientChecker ініціалізований: {len(self.local_ingredients)} інгредієнтів у базі")
    
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
    
    def load_local_ingredients(self):
        """Завантаження локальної бази інгредієнтів"""
        print("📚 Завантаження локальної бази інгредієнтів...")
        
        # Базовий список основних інгредієнтів (з повними псевдонімами)
        ingredients = [
            # === ВОДА ТА ОСНОВИ ===
            {
                "id": 1001, "name": "Aqua", "risk_level": "safe", "category": "solvent",
                "description": "Вода, основа косметичних засобів (INCI: Aqua)",
                "aliases": ["aqua", "вода", "water", "eau", "h2o", "purified water", 
                           "distilled water", "deionized water", "spring water", 
                           "маріс аква", "maris aqua", "дистильована вода", "очищена вода"],
                "source": "local"
            },
            {
                "id": 1002, "name": "Water", "risk_level": "safe", "category": "solvent",
                "description": "Очищена вода",
                "aliases": ["water", "вода", "aqua", "eau", "purified h2o", "deionized h2o"],
                "source": "local"
            },
            
            # === ПАВ ТА ОЧИЩУЮЧІ ===
            {
                "id": 1003, "name": "Sodium Laureth Sulfate", "risk_level": "medium", "category": "surfactant",
                "description": "SLES, піноутворювач, може висушувати шкіру при частому використанні",
                "aliases": ["sodium laureth sulfate", "sles", "натрію лаурет сульфат", 
                           "sls", "sodium lauryl ether sulfate", "sodium lauryl sulfate ether",
                           "содиум лаурет сульфат", "натрій лаурет сульфат"],
                "source": "local"
            },
            {
                "id": 1004, "name": "Sodium Lauryl Sulfate", "risk_level": "medium", "category": "surfactant",
                "description": "SLS, більш агресивний ніж SLES, може викликати подразнення",
                "aliases": ["sodium lauryl sulfate", "sls", "натрію лауріл сульфат", 
                           "sodium dodecyl sulfate", "содиум лауріл сульфат",
                           "натрій лауріл сульфат", "sds"],
                "source": "local"
            },
            {
                "id": 1005, "name": "Cocamidopropyl Betaine", "risk_level": "low", "category": "surfactant",
                "description": "М'який ПАР з кокосової олії, підходить для чутливої шкіри",
                "aliases": ["cocamidopropyl betaine", "копамідопропіл бетаїн", 
                           "coco betaine", "capb", "копамідопропил бетаин",
                           "cocamidopropylbetaine", "cocoamidopropyl betaine"],
                "source": "local"
            },
            {
                "id": 1006, "name": "Decyl Glucoside", "risk_level": "low", "category": "surfactant",
                "description": "Натуральний м'який ПАР з кокосової олії та кукурудзи",
                "aliases": ["decyl glucoside", "децил глюкозид", "alkyl polyglucoside",
                           "децил глюкозід", "plant-based surfactant"],
                "source": "local"
            },
            {
                "id": 1007, "name": "Sodium Cocoyl Isethionate", "risk_level": "low", "category": "surfactant",
                "description": "Дуже м'який ПАР для делікатних засобів",
                "aliases": ["sodium cocoyl isethionate", "натрію кокоїл ізетіонат",
                           "sci", "soft surfactant", "кокоїл ізетіонат натрію"],
                "source": "local"
            },
            {
                "id": 1008, "name": "Coco Glucoside", "risk_level": "low", "category": "surfactant",
                "description": "Глюкозид з кокосової олії, біорозкладний",
                "aliases": ["coco glucoside", "коко глюкозид", "coconut glucoside",
                           "кокосовий глюкозид", "alkyl polyglucoside"],
                "source": "local"
            },
            
            # === КОНСЕРВАНТИ ===
            # ВИСОКИЙ РИЗИК
            {
                "id": 1009, "name": "Formaldehyde", "risk_level": "high", "category": "preservative",
                "description": "Канцероген, заборонений у багатьох країнах",
                "aliases": ["formaldehyde", "формальдегід", "formalin", "methanal",
                           "формалін", "methyl aldehyde", "oxomethane"],
                "source": "local"
            },
            {
                "id": 1010, "name": "Methylisothiazolinone", "risk_level": "high", "category": "preservative",
                "description": "Сильніший алерген, обмежений в ЄС з 2017 року",
                "aliases": ["methylisothiazolinone", "мітілізотіазолінон", "mit", "mi", 
                           "kathon cg", "methylisothiazolin", "2-methyl-4-isothiazolin-3-one"],
                "source": "local"
            },
            {
                "id": 1011, "name": "Methylchloroisothiazolinone", "risk_level": "high", "category": "preservative",
                "description": "Сильний алерген, часто в комбінації з MIT",
                "aliases": ["methylchloroisothiazolinone", "мітілхлороізотіазолінон", 
                           "mci", "cmit", "5-chloro-2-methyl-4-isothiazolin-3-one",
                           "chloromethylisothiazolinone"],
                "source": "local"
            },
            {
                "id": 1012, "name": "DMDM Hydantoin", "risk_level": "high", "category": "preservative",
                "description": "Виділяє формальдегід, алерген",
                "aliases": ["dmdm hydantoin", "дмдм гідантоїн", "dimethyl dimethyl hydantoin",
                           "формальдегід-виділяючий консервант"],
                "source": "local"
            },
            
            # ПОМІРНИЙ РИЗИК
            {
                "id": 1013, "name": "Methylparaben", "risk_level": "medium", "category": "preservative",
                "description": "Парабен, дозволений в ЄС до 0.4%, дослідження про гормональний вплив",
                "aliases": ["methylparaben", "methyl paraben", "метилпарабен", "парабен", 
                           "e218", "n-methyl-4-hydroxybenzoate", "метил парабен"],
                "source": "local"
            },
            {
                "id": 1014, "name": "Propylparaben", "risk_level": "medium", "category": "preservative",
                "description": "Парабен, дозволений в ЄС до 0.14%",
                "aliases": ["propylparaben", "propyl paraben", "пропилпарабен", "e216",
                           "n-propyl-4-hydroxybenzoate", "пропил парабен"],
                "source": "local"
            },
            {
                "id": 1015, "name": "Butylparaben", "risk_level": "medium", "category": "preservative",
                "description": "Парабен, обмежений в ЄС",
                "aliases": ["butylparaben", "butyl paraben", "бутилпарабен", 
                           "n-butyl-4-hydroxybenzoate", "бутил парабен"],
                "source": "local"
            },
            {
                "id": 1016, "name": "Phenoxyethanol", "risk_level": "medium", "category": "preservative",
                "description": "Широко використовуваний консервант, обмежений до 1% в ЄС",
                "aliases": ["phenoxyethanol", "феноксиетанол", "2-phenoxyethanol",
                           "ethylene glycol monophenyl ether", "rose ether"],
                "source": "local"
            },
            
            # НИЗЬКИЙ РИЗИК
            {
                "id": 1017, "name": "Potassium Sorbate", "risk_level": "low", "category": "preservative",
                "description": "Сіль сорбінової кислоти, харчовий консервант",
                "aliases": ["potassium sorbate", "сорбат калію", "e202", 
                           "potassium (e,e)-hexa-2,4-dienoate"],
                "source": "local"
            },
            {
                "id": 1018, "name": "Sodium Benzoate", "risk_level": "low", "category": "preservative",
                "description": "Консервант, дозволений у косметиці до 0.5%",
                "aliases": ["sodium benzoate", "бензоат натрію", "e211",
                           "sodium salt of benzoic acid", "бензоат натрия"],
                "source": "local"
            },
            
            # === АРОМАТИЗАТОРИ ===
            {
                "id": 1019, "name": "Parfum", "risk_level": "medium", "category": "fragrance",
                "description": "Ароматизатор. Може викликати алергію у чутливих людей.",
                "aliases": ["parfum", "fragrance", "aroma", "perfume", "парфум", 
                           "ароматизатор", "отдушка", "парфюмерна композиція", 
                           "fragrance mix", "духи", "аромат"],
                "source": "local"
            },
            {
                "id": 1020, "name": "Fragrance", "risk_level": "medium", "category": "fragrance",
                "description": "Ароматична композиція. Основний алерген у косметиці.",
                "aliases": ["fragrance", "parfum", "aroma", "аромат", "запах",
                           "відтінок", "ессенція", "ефір", "парфюм"],
                "source": "local"
            },
            {
                "id": 1021, "name": "Limonene", "risk_level": "medium", "category": "fragrance",
                "description": "Ароматичне з'єднання, алерген, окислюється на повітрі",
                "aliases": ["limonene", "лімонен", "d-limonene", "цитрусовий терпен",
                           "1-methyl-4-(1-methylethenyl)cyclohexene"],
                "source": "local"
            },
            {
                "id": 1022, "name": "Linalool", "risk_level": "medium", "category": "fragrance",
                "description": "Ароматичне з'єднання, алерген при окисленні",
                "aliases": ["linalool", "ліналоол", "3,7-dimethyl-1,6-octadien-3-ol",
                           "лавандова олія компонент", "кораліналоол"],
                "source": "local"
            },
            
            # === РОЗЧИННИКИ ТА СПИРТИ ===
            {
                "id": 1023, "name": "Alcohol Denat", "risk_level": "medium", "category": "solvent",
                "description": "Денатурований спирт. Висушує шкіру, може порушувати бар'єр.",
                "aliases": ["alcohol denat", "alcohol", "спирт", "денатурований спирт", 
                           "ethanol denatured", "ethyl alcohol denatured", 
                           "денатурат", "технічний спирт"],
                "source": "local"
            },
            {
                "id": 1024, "name": "Alcohol", "risk_level": "medium", "category": "solvent",
                "description": "Спирт, висушує шкіру, використовуйте помірно",
                "aliases": ["alcohol", "спирт", "ethanol", "ethyl alcohol", 
                           "етанол", "зерновий спирт", "винний спирт"],
                "source": "local"
            },
            {
                "id": 1025, "name": "Propylene Glycol", "risk_level": "medium", "category": "solvent",
                "description": "Розчинник та зволожувач. Може подразнювати чутливу шкіру.",
                "aliases": ["propylene glycol", "пропіленгліколь", "пропілен гліколь", 
                           "pg", "1,2-propanediol", "пропандіол", "агент проникнення"],
                "source": "local"
            },
            {
                "id": 1026, "name": "Glycerin", "risk_level": "low", "category": "humectant",
                "description": "Гліцерин, натуральний зволожувач",
                "aliases": ["glycerin", "гліцерин", "glycerol", "glycerine", "e422",
                           "1,2,3-propanetriol", "гліцерол", "растительный глицерин"],
                "source": "local"
            },
            {
                "id": 1027, "name": "Butylene Glycol", "risk_level": "low", "category": "solvent",
                "description": "Розчинник, м'якіший ніж пропіленгліколь",
                "aliases": ["butylene glycol", "бутиленгліколь", "1,3-butanediol",
                           "бутандіол", "bg", "butanediol"],
                "source": "local"
            },
            
            # === ЕМУЛЬГАТОРИ ===
            {
                "id": 1028, "name": "Cetearyl Alcohol", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор та загущувач, не висушує шкіру",
                "aliases": ["cetearyl alcohol", "цетеариловий спирт", "cetylstearyl alcohol",
                           "цетеарил алкохол", "емолент-емульгатор"],
                "source": "local"
            },
            {
                "id": 1029, "name": "Glyceryl Stearate", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор з гліцерину та стеаринової кислоти",
                "aliases": ["glyceryl stearate", "гліцерил стеарат", "glycerol monostearate",
                           "гліцерин моностеарат", "gms", "emulsifier gms"],
                "source": "local"
            },
            
            # === ПЕГ ТА ПОХІДНІ ===
            {
                "id": 1030, "name": "PEG-4", "risk_level": "low", "category": "emulsifier",
                "description": "Поліетиленгліколь, емульгатор",
                "aliases": ["peg-4", "peg", "поліетиленгліколь", "поліетилен гліколь", 
                           "polyethylene glycol", "macrogol", "пэг-4", "пег-4"],
                "source": "local"
            },
            {
                "id": 1031, "name": "PEG-4 Cocoate", "risk_level": "low", "category": "emulsifier",
                "description": "Ефір кокосової олії та ПЕГ-4",
                "aliases": ["peg-4 cocoate", "пег-4 кокоат", "polyethylene glycol-4 coconut ester",
                           "кокосовий ефір пег-4", "peg-4 coconut ester"],
                "source": "local"
            },
            
            # === ОЛІЇ ТА ЕМОЛЕНТИ ===
            {
                "id": 1032, "name": "Mineral Oil", "risk_level": "low", "category": "emollient",
                "description": "Мінеральна олія, окклюзійний агент. Безпечно, але може бути комедогенним для жирної шкіри.",
                "aliases": ["mineral oil", "парафінове масло", "paraffinum liquidum", 
                           "вазелін", "petroleum oil", "вазелинове масло", 
                           "біле мінеральне масло", "liquid petroleum", "oil mineral"],
                "source": "local"
            },
            {
                "id": 1033, "name": "Petrolatum", "risk_level": "low", "category": "emollient",
                "description": "Вазелін, окклюзійний агент, захищає шкіру",
                "aliases": ["petrolatum", "вазелін", "petroleum jelly", "soft paraffin",
                           "вазелин", "технічний вазелін", "медичний вазелін"],
                "source": "local"
            },
            {
                "id": 1034, "name": "Dimethicone", "risk_level": "low", "category": "emollient",
                "description": "Силікон, створює захисну плівку, некомедогенний",
                "aliases": ["dimethicone", "диметикон", "силікон", "silicone", 
                           "polydimethylsiloxane", "pdmso", "діметикон", 
                           "силикон", "диметиконол"],
                "source": "local"
            },
            {
                "id": 1035, "name": "Cyclopentasiloxane", "risk_level": "low", "category": "emollient",
                "description": "Летючий силікон, не залишає жирного блиску",
                "aliases": ["cyclopentasiloxane", "циклопентасилоксан", "decamethylcyclopentasiloxane",
                           "d5", "cyclomethicone", "cyclic silicone"],
                "source": "local"
            },
            {
                "id": 1036, "name": "Squalane", "risk_level": "safe", "category": "emollient",
                "description": "Скваланан, легка олія, ідентична шкірному себуму",
                "aliases": ["squalane", "скваланан", "perhydrosqualene", 
                           "гідрогенізований сквален", "олія сквалану"],
                "source": "local"
            },
            {
                "id": 1037, "name": "Jojoba Oil", "risk_level": "safe", "category": "emollient",
                "description": "Олія жожоба, близька до шкірного себуму",
                "aliases": ["jojoba oil", "олія жожоба", "simmondsia chinensis oil",
                           "wax ester oil", "желтое масло жожоба", "холодного пресування жожоба"],
                "source": "local"
            },
            {
                "id": 1038, "name": "Argan Oil", "risk_level": "safe", "category": "emollient",
                "description": "Арганове масло, багате на вітамін Е",
                "aliases": ["argan oil", "арганове масло", "argania spinosa oil",
                           "марокканське масло", "олія аргана", "аргановое масло"],
                "source": "local"
            },
            {
                "id": 1039, "name": "Caprylic/Capric Triglyceride", "risk_level": "low", "category": "emollient",
                "description": "Тригліцериди кокосової олії, легкий емолент",
                "aliases": ["caprylic/capric triglyceride", "каприлік/каприк тригліцерид",
                           "mct oil", "medium chain triglycerides", "кокосові тригліцериди"],
                "source": "local"
            },
            
            # === УФ-ФІЛЬТРИ ===
            # ВИСОКИЙ РИЗИК
            {
                "id": 1040, "name": "Oxybenzone", "risk_level": "high", "category": "UV filter",
                "description": "Бензофенон-3, ендокринний дизраптор, заборонений на Гаваях",
                "aliases": ["oxybenzone", "оксибензон", "benzophenone-3", "бензофенон-3", 
                           "bp-3", "2-hydroxy-4-methoxybenzophenone", "оксибензон-3"],
                "source": "local"
            },
            {
                "id": 1041, "name": "Benzophenone-3", "risk_level": "high", "category": "UV filter",
                "description": "Оксибензон, ендокринний дизраптор",
                "aliases": ["benzophenone-3", "бензофенон-3", "oxybenzone", "оксибензон",
                           "ср-3", "uv-absorber benzophenone"],
                "source": "local"
            },
            
            # ПОМІРНИЙ РИЗИК
            {
                "id": 1042, "name": "Avobenzone", "risk_level": "medium", "category": "UV filter",
                "description": "УФ-фільтр широкого спектра, може розкладатися на сонці",
                "aliases": ["avobenzone", "авобензон", "butyl methoxydibenzoylmethane",
                           "parsol 1789", "uvinul a plus", "дибензоїлметан"],
                "source": "local"
            },
            {
                "id": 1043, "name": "Octinoxate", "risk_level": "medium", "category": "UV filter",
                "description": "УФ-фільтр, ендокринний дизраптор у високих концентраціях",
                "aliases": ["octinoxate", "октиноксат", "ethylhexyl methoxycinnamate",
                           "omc", "парасол mcx", "uv-absorber octinoxate"],
                "source": "local"
            },
            
            # НИЗЬКИЙ РИЗИК
            {
                "id": 1044, "name": "Titanium Dioxide", "risk_level": "low", "category": "UV filter",
                "description": "Мінеральний УФ-фільтр, безпечний, може залишати білий слід",
                "aliases": ["titanium dioxide", "діоксид титану", "ci 77891", "tio2",
                           "титановые белила", "титаній діоксид", "пигмент білий 6"],
                "source": "local"
            },
            {
                "id": 1045, "name": "Zinc Oxide", "risk_level": "low", "category": "UV filter",
                "description": "Мінеральний УФ-фільтр, найбезпечніший, протизапальний",
                "aliases": ["zinc oxide", "оксид цинку", "ci 77947", "zno",
                           "цинкова паста", "цинковый крем", "цинк оксид"],
                "source": "local"
            },
            
            # === АНТИБАКТЕРІАЛЬНІ ===
            {
                "id": 1046, "name": "Triclosan", "risk_level": "high", "category": "antibacterial",
                "description": "Антибактеріальний агент, сприяє резистентності, заборонений в ЄС",
                "aliases": ["triclosan", "триклозан", "2,4,4'-trichloro-2'-hydroxydiphenyl ether",
                           "антибактеріальний триклозан", "інгібітор бактерій"],
                "source": "local"
            },
            {
                "id": 1047, "name": "Triclocarban", "risk_level": "high", "category": "antibacterial",
                "description": "Антибактеріальний агент, аналогічно триклозану",
                "aliases": ["triclocarban", "триклокарбан", "3,4,4'-trichlorocarbanilide",
                           "tcc", "антибактеріальний карбанілід"],
                "source": "local"
            },
            
            # === ХЕЛАТОРИ ===
            {
                "id": 1048, "name": "Tetrasodium EDTA", "risk_level": "medium", "category": "chelating agent",
                "description": "Хелатуючий агент, покращує піну, може подразнювати шкіру",
                "aliases": ["tetrasodium edta", "тетранатрій едта", "едта-4na",
                           "ethylenediaminetetraacetic acid tetrasodium salt",
                           "хелатор", "хелатирующий агент"],
                "source": "local"
            },
            {
                "id": 1049, "name": "Disodium EDTA", "risk_level": "medium", "category": "chelating agent",
                "description": "Хелатуючий агент",
                "aliases": ["disodium edta", "динатрій едта", "едта-2na",
                           "ethylenediaminetetraacetic acid disodium salt"],
                "source": "local"
            },
            
            # === РЕГУЛЯТОРИ PH ===
            {
                "id": 1050, "name": "Citric Acid", "risk_level": "low", "category": "pH adjuster",
                "description": "Лимонна кислота, регулятор pH, AHA у високих концентраціях",
                "aliases": ["citric acid", "лимонна кислота", "сітілова кислота", 
                           "acidum citricum", "e330", "2-hydroxypropane-1,2,3-tricarboxylic acid",
                           "цитрикова кислота"],
                "source": "local"
            },
            {
                "id": 1051, "name": "Sodium Hydroxide", "risk_level": "high", "category": "pH adjuster",
                "description": "Луг, корозійний у чистому вигляді, безпечний у готових продуктах",
                "aliases": ["sodium hydroxide", "гідроксид натрію", "каустична сода",
                           "луг", "едка", "naoh", "каустик", "технічна сода"],
                "source": "local"
            },
            {
                "id": 1052, "name": "Triethanolamine", "risk_level": "medium", "category": "pH adjuster",
                "description": "Регулятор pH, може утворювати нітрозаміни",
                "aliases": ["triethanolamine", "тріетаноламін", "tea",
                           "2,2',2''-nitrilotriethanol", "емульгатор tea", "tea база"],
                "source": "local"
            },
            
            # === НАТУРАЛЬНІ ЕКСТРАКТИ ===
            {
                "id": 1053, "name": "Aloe Barbadensis Leaf Juice", "risk_level": "safe", "category": "plant extract",
                "description": "Сік алое вера, заспокійливий, заживлюючий",
                "aliases": ["aloe barbadensis leaf juice", "сік алое вера", "aloe vera gel",
                           "алое барбаденсіс", "алое сік", "aloe extract", "гель алое"],
                "source": "local"
            },
            {
                "id": 1054, "name": "Camellia Sinensis Leaf Extract", "risk_level": "safe", "category": "plant extract",
                "description": "Екстракт зеленого чаю, антиоксидант",
                "aliases": ["camellia sinensis leaf extract", "екстракт зеленого чаю",
                           "green tea extract", "чайний екстракт", "антиоксидант чаю"],
                "source": "local"
            },
            {
                "id": 1055, "name": "Chamomilla Recutita Flower Extract", "risk_level": "safe", "category": "plant extract",
                "description": "Екстракт ромашки, заспокійливий",
                "aliases": ["chamomilla recutita flower extract", "екстракт ромашки",
                           "chamomile extract", "ромашковий екстракт", "матрикарія екстракт"],
                "source": "local"
            },
            {
                "id": 1056, "name": "Centella Asiatica Extract", "risk_level": "safe", "category": "plant extract",
                "description": "Екстракт центелли азіатської, заживлює, заспокоює",
                "aliases": ["centella asiatica extract", "екстракт центелли", "gotu kola extract",
                           "тігрова трава", "азіатська центелла", "madecassoside source"],
                "source": "local"
            },
            
            # === ВІТАМІНИ ТА АКТИВНІ ===
            {
                "id": 1057, "name": "Tocopherol", "risk_level": "safe", "category": "antioxidant",
                "description": "Вітамін Е, антиоксидант, стабілізатор",
                "aliases": ["tocopherol", "токоферол", "vitamin e", "вітамін е",
                           "alpha-tocopherol", "d-alpha-tocopherol", "антиоксидант e"],
                "source": "local"
            },
            {
                "id": 1058, "name": "Ascorbic Acid", "risk_level": "safe", "category": "antioxidant",
                "description": "Вітамін С, антиоксидант, освітлює",
                "aliases": ["ascorbic acid", "аскорбінова кислота", "vitamin c", "вітамін с",
                           "l-ascorbic acid", "антиоксидант c", "освітлювач с"],
                "source": "local"
            },
            {
                "id": 1059, "name": "Retinol", "risk_level": "medium", "category": "active",
                "description": "Вітамін А, антивіковий, може подразнювати, уникайте при вагітності",
                "aliases": ["retinol", "ретинол", "vitamin a", "вітамін а",
                           "all-trans-retinol", "антивіковий ретинол", "retin-a"],
                "source": "local"
            },
            {
                "id": 1060, "name": "Niacinamide", "risk_level": "safe", "category": "active",
                "description": "Ніацинамід, вітамін B3, покращує бар'єр, протизапальний",
                "aliases": ["niacinamide", "ніацинамід", "nicotinamide", "вітамін b3", 
                           "вітамін b3", "nicotinic acid amide", "ніацинамід b3"],
                "source": "local"
            },
            {
                "id": 1061, "name": "Salicylic Acid", "risk_level": "medium", "category": "active",
                "description": "Саліцилова кислота, BHA, відлущувальний, для жирної шкіри",
                "aliases": ["salicylic acid", "саліцилова кислота", "beta hydroxy acid", 
                           "bha", "2-hydroxybenzoic acid", "відлущуючий bha"],
                "source": "local"
            },
            {
                "id": 1062, "name": "Glycolic Acid", "risk_level": "medium", "category": "active",
                "description": "Гліколева кислота, AHA, відлущувальний, підвищує чутливість до сонця",
                "aliases": ["glycolic acid", "гліколева кислота", "alpha hydroxy acid", 
                           "aha", "hydroxyacetic acid", "відлущуючий aha"],
                "source": "local"
            },
            {
                "id": 1063, "name": "Hyaluronic Acid", "risk_level": "safe", "category": "humectant",
                "description": "Гіалуронова кислота, зволожувач",
                "aliases": ["hyaluronic acid", "гіалуронова кислота", "sodium hyaluronate", 
                           "ha", "hyaluronan", "гіалуронат", "зволожувач ha"],
                "source": "local"
            },
            {
                "id": 1064, "name": "Ceramide NP", "risk_level": "safe", "category": "skin-identical",
                "description": "Церамід, відновлює шкірний бар'єр",
                "aliases": ["ceramide np", "церамід np", "ceramide 3", "бар'єрний церамід",
                           "шкірний ліпід", "natural moisturizing factor"],
                "source": "local"
            },
            {
                "id": 1065, "name": "Allantoin", "risk_level": "safe", "category": "soothing",
                "description": "Алантоїн, заспокійливий, заживлюючий",
                "aliases": ["allantoin", "алантоїн", "5-ureidohydantoin", 
                           "заспокійливий агент", "регенеруючий алантоїн"],
                "source": "local"
            },
            {
                "id": 1066, "name": "Panthenol", "risk_level": "safe", "category": "soothing",
                "description": "Пантенол, провітамін B5, зволожує, заспокоює",
                "aliases": ["panthenol", "пантенол", "provitamin b5", "d-panthenol",
                           "дексопантенол", "вітамін b5", "зволожувач b5"],
                "source": "local"
            },
            {
                "id": 1067, "name": "Bakuchiol", "risk_level": "safe", "category": "active",
                "description": "Натуральна альтернатива ретинолу, менш подразнювальна",
                "aliases": ["bakuchiol", "бакучіол", "psoralea corylifolia extract",
                           "натуральний ретинол", "рослинний ретинол"],
                "source": "local"
            },
            {
                "id": 1068, "name": "Azelaic Acid", "risk_level": "medium", "category": "active",
                "description": "Азелаїнова кислота, для акне та розацеа",
                "aliases": ["azelaic acid", "азелаїнова кислота", "nonanedioic acid",
                           "для акне", "для розацеа", "антивосполительная кислота"],
                "source": "local"
            },
            
            # === ПЛІВКОУТВОРЮВАЧІ ТА ПОЛІМЕРИ ===
            {
                "id": 1069, "name": "VP/VA Copolymer", "risk_level": "low", "category": "film former",
                "description": "Плівкоутворюючий полімер, фіксатор",
                "aliases": ["vp/va copolymer", "vp va сополімер", "vinylpyrrolidone/vinyl acetate copolymer",
                           "полімер фіксатор", "стайлінг полімер"],
                "source": "local"
            },
            {
                "id": 1070, "name": "Acrylates Copolymer", "risk_level": "low", "category": "film former",
                "description": "Полімер, плівкоутворювач",
                "aliases": ["acrylates copolymer", "акрилатний сополімер", "акриловий полімер",
                           "плівкоутворювач", "фіксуючий полімер"],
                "source": "local"
            },
            
            # === ЗАГУЩУВАЧІ ===
            {
                "id": 1071, "name": "Carbomer", "risk_level": "low", "category": "thickener",
                "description": "Загущувач, створює гелеву текстуру",
                "aliases": ["carbomer", "карбомер", "carbopol", "акриловий полімер",
                           "загущувач карбомер", "гельуючий агент"],
                "source": "local"
            },
            {
                "id": 1072, "name": "Xanthan Gum", "risk_level": "low", "category": "thickener",
                "description": "Натуральний загущувач з бактерій",
                "aliases": ["xanthan gum", "ксантанова камедь", "e415", "бактеріальна камедь",
                           "натуральний загущувач", "ксантан"],
                "source": "local"
            },
            
            # === ПІГМЕНТИ ===
            {
                "id": 1073, "name": "CI 77891", "risk_level": "low", "category": "pigment",
                "description": "Діоксид титану, білий пігмент, УФ-фільтр",
                "aliases": ["ci 77891", "сі ай 77891", "titanium dioxide", "діоксид титану",
                           "білий пігмент", "титановий діоксид", "пигмент білий 6"],
                "source": "local"
            },
            {
                "id": 1074, "name": "Mica", "risk_level": "low", "category": "pigment",
                "description": "Слюда, перламутровий пігмент",
                "aliases": ["mica", "слюда", "ci 77019", "muscovite",
                           "перламутровий пігмент", "сіяючий пігмент", "мінеральна слюда"],
                "source": "local"
            },
            
            # === ПРОТЕЇНИ ТА ЕКСТРАКТИ ===
            {
                "id": 1075, "name": "Hydrolyzed Silk Protein", "risk_level": "low", "category": "conditioning agent",
                "description": "Гідролізований шовковий протеїн, кондиціонер для волосся",
                "aliases": ["hydrolyzed silk protein", "гідролізований шовковий протеїн", 
                           "silk amino acids", "шовкові амінокислоти", "кондиціонер шовк"],
                "source": "local"
            },
            {
                "id": 1076, "name": "Hydrolyzed Collagen", "risk_level": "low", "category": "conditioning agent",
                "description": "Гідролізований колаген, зволожує",
                "aliases": ["hydrolyzed collagen", "гідролізований колаген", "collagen peptides",
                           "колагенові пептиди", "зволожуючий колаген"],
                "source": "local"
            },
            
            # === СОЛІ ТА МІНЕРАЛИ ===
            {
                "id": 1077, "name": "Sodium Chloride", "risk_level": "safe", "category": "viscosity controlling",
                "description": "Кухонна сіль, загущувач у шампунях",
                "aliases": ["sodium chloride", "хлорид натрію", "кухонна сіль", "сіль",
                           "nacl", "загущувач сіль", "поваренна сіль"],
                "source": "local"
            },
            
            # === СПЕЦІАЛЬНІ ДОДАТКИ ===
            {
                "id": 1078, "name": "Kojic Acid", "risk_level": "medium", "category": "active",
                "description": "Кодзієва кислота, освітлює, може подразнювати",
                "aliases": ["kojic acid", "кодзієва кислота", "5-hydroxy-2-hydroxymethyl-4-pyrone",
                           "освітлювач", "для гіперпігментації", "відбілювач"],
                "source": "local"
            },
            {
                "id": 1079, "name": "Arbutin", "risk_level": "low", "category": "active",
                "description": "Арбутин, освітлює гіперпігментацію",
                "aliases": ["arbutin", "арбутин", "hydroquinone-beta-d-glucopyranoside",
                           "натуральний освітлювач", "рослинний арбутин"],
                "source": "local"
            },
            
            # === ЕМУЛЬСИФІКАТОРИ ===
            {
                "id": 1080, "name": "Lecithin", "risk_level": "safe", "category": "emulsifier",
                "description": "Лецитин, натуральний емульгатор",
                "aliases": ["lecithin", "лецитин", "soy lecithin", "соєвий лецитин",
                           "натуральний емульгатор", "фосфоліпід"],
                "source": "local"
            },
            
            # === КОНСЕРВАНТИ ДРУГОГО ПОКОЛІННЯ ===
            {
                "id": 1081, "name": "Ethylhexylglycerin", "risk_level": "low", "category": "preservative",
                "description": "Консервант нового покоління",
                "aliases": ["ethylhexylglycerin", "етилгексилгліцерин", "octoxyglycerin",
                           "мягкий консервант", "консервант-емульгатор"],
                "source": "local"
            },
            
            # === АНТИПЕРСПІРАНТИ ===
            {
                "id": 1082, "name": "Aluminum Chlorohydrate", "risk_level": "medium", "category": "antiperspirant",
                "description": "Алюмінію хлоргідроксид, антиперспірант",
                "aliases": ["aluminum chlorohydrate", "алюмінію хлоргідроксид", "aluminum chlorhydroxide",
                           "антиперспірант", "зменшує потовиділення", "ach"],
                "source": "local"
            },
            
            # === ЕКО-ІНГРЕДІЄНТИ ===
            {
                "id": 1083, "name": "Bambusa Vulgaris Extract", "risk_level": "safe", "category": "plant extract",
                "description": "Екстракт бамбука, зволожує",
                "aliases": ["bambusa vulgaris extract", "екстракт бамбука", "bamboo extract",
                           "бамбуковий екстракт", "силіцій з бамбука"],
                "source": "local"
            },
            
            # === ФЕРМЕНТИ ===
            {
                "id": 1084, "name": "Papain", "risk_level": "low", "category": "enzyme",
                "description": "Папаїн, протеолітичний фермент, відлущує",
                "aliases": ["papain", "папаїн", "papaya enzyme", "фермент папаї",
                           "відлущуючий фермент", "ензимне пілінг"],
                "source": "local"
            },
            
            # === ВІТАМІНИ ГРУПИ B ===
            {
                "id": 1085, "name": "Biotin", "risk_level": "safe", "category": "vitamin",
                "description": "Біотин, вітамін B7, для волосся та нігтів",
                "aliases": ["biotin", "біотин", "vitamin b7", "вітамін b7", "vitamin h",
                           "кофермент r", "для росту волосся"],
                "source": "local"
            },
            
            # === ПРЕБІОТИКИ ТА ПРОБІОТИКИ ===
            {
                "id": 1086, "name": "Inulin", "risk_level": "safe", "category": "prebiotic",
                "description": "Інулін, пребіотик",
                "aliases": ["inulin", "інулін", "chicory root fiber", "цикорієвий інулін",
                           "пребіотик", "харчовий волокно"],
                "source": "local"
            },
            
            # === РОСЛИННІ МАСЛА ===
            {
                "id": 1087, "name": "Helianthus Annuus Seed Oil", "risk_level": "safe", "category": "emollient",
                "description": "Соняшникова олія, багата на вітамін Е",
                "aliases": ["helianthus annuus seed oil", "соняшникова олія", "sunflower oil",
                           "масло соняшника", "олія соняшника", "багата вітаміном е"],
                "source": "local"
            },
            
            # === СПЕЦІАЛЬНІ СКЛАДОВІ ===
            {
                "id": 1088, "name": "Ubiquinone", "risk_level": "safe", "category": "antioxidant",
                "description": "Коензим Q10, антиоксидант, енергія клітин",
                "aliases": ["ubiquinone", "убіхінон", "coenzyme q10", "коензим q10",
                           "coq10", "енергія клітин", "антиоксидант q10"],
                "source": "local"
            },
            {
                "id": 1089, "name": "Caffeine", "risk_level": "safe", "category": "active",
                "description": "Кофеїн, зменшує набряки, тонізує",
                "aliases": ["caffeine", "кофеїн", "1,3,7-trimethylxanthine", "для набряків",
                           "тонізатор", "звужує судини"],
                "source": "local"
            },
            
            # === СИНТЕТИЧНІ ЛІПІДИ ===
            {
                "id": 1090, "name": "Cetyl Palmitate", "risk_level": "low", "category": "emollient",
                "description": "Цетил пальмітат, емульгатор",
                "aliases": ["cetyl palmitate", "цетил пальмітат", "hexadecyl hexadecanoate",
                           "емульгатор", "восковий естер"],
                "source": "local"
            },
            
            # === ОСТАННІ ДОДАТКИ ===
            {
                "id": 1091, "name": "Bentonite", "risk_level": "low", "category": "thickener",
                "description": "Бентоніт, глина, загущувач",
                "aliases": ["bentonite", "бентоніт", "montmorillonite clay", "глина",
                           "очищаюча глина", "маскувальна глина"],
                "source": "local"
            },
            {
                "id": 1092, "name": "Kaolin", "risk_level": "low", "category": "absorbent",
                "description": "Каолін, глина, абсорбент",
                "aliases": ["kaolin", "каолін", "china clay", "біла глина",
                           "абсорбуюча глина", "маскувальна глина"],
                "source": "local"
            },
            {
                "id": 1093, "name": "Silica", "risk_level": "low", "category": "absorbent",
                "description": "Кремнезем, матує, абсорбує",
                "aliases": ["silica", "кремнезем", "silicon dioxide", "діоксид кремнію",
                           "матирующий агент", "абсорбент", "сіліка"],
                "source": "local"
            },
            
            # Додаткові важливі інгредієнти для досягнення 100+
            {
                "id": 1094, "name": "Polysorbate 20", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор та солюбілізатор",
                "aliases": ["polysorbate 20", "полісорбат 20", "tween 20", "емульгатор 20"],
                "source": "local"
            },
            {
                "id": 1095, "name": "Polysorbate 80", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор та солюбілізатор",
                "aliases": ["polysorbate 80", "полісорбат 80", "tween 80", "емульгатор 80"],
                "source": "local"
            },
            {
                "id": 1096, "name": "Sorbitan Oleate", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор",
                "aliases": ["sorbitan oleate", "сорбітан олеат", "span 80", "емульгатор олеат"],
                "source": "local"
            },
            {
                "id": 1097, "name": "Ceteareth-20", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор",
                "aliases": ["ceteareth-20", "цетеарет-20", "емульгатор цетеарет"],
                "source": "local"
            },
            {
                "id": 1098, "name": "Steareth-20", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор",
                "aliases": ["steareth-20", "стеарет-20", "емульгатор стеарет"],
                "source": "local"
            },
            {
                "id": 1099, "name": "PEG-100 Stearate", "risk_level": "low", "category": "emulsifier",
                "description": "Емульгатор",
                "aliases": ["peg-100 stearate", "пег-100 стеарат", "емульгатор пег-100"],
                "source": "local"
            },
            {
                "id": 1100, "name": "Lactic Acid", "risk_level": "low", "category": "pH adjuster",
                "description": "Молочна кислота, AHA, більш м'який ніж гліколевий",
                "aliases": ["lactic acid", "молочна кислота", "aha", "alpha hydroxy acid",
                           "відлущуючий aha", "зволожувальний aha"],
                "source": "local"
            },
        ]
        
        # Додаємо ще інгредієнти для досягнення повного охоплення
        # У реальній реалізації тут будуть всі 500+ інгредієнтів з бази даних
        
        print(f"✅ Завантажено {len(ingredients)} інгредієнтів з повними псевдонімами")
        return ingredients

    def load_common_fixes(self):
        """Завантаження виправлень помилок OCR та транскрипції"""
        print("🔧 Завантаження виправлень помилок...")
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
        print(f"✅ Завантажено {len(fixes)} виправлень помилок")
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
        
        print(f"\n🧪 Виділення кандидатів з тексту ({len(text)} символів)")
        
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
                print(f"   ✅ Знайдено розділ 'СКЛАД' у позиції {composition_start}")
                break
        
        # Якщо не знайшли заголовок, шукаємо рядок з INCI назвами
        if composition_start == -1:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if ',' in line and any(word in line.upper() for word in ['AQUA', 'SODIUM', 'GLYCERIN', 'PARFUM', 'WATER', 'ALCOHOL']):
                    composition_start = sum(len(l) + 1 for l in lines[:i])
                    print(f"   ✅ Знайдено список інгредієнтів у рядку {i+1}")
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
            print(f"   📊 Виділено текст інгредієнтів: {len(ingredients_text)} символів")
        else:
            ingredients_text = text
            print("   ℹ️ Розділ 'СКЛАД' не знайдено, використовуємо весь текст")
        
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
                print(f"   🧪 Кандидат: '{item}'")
        
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
        
        print(f"📊 Знайдено {len(unique_candidates)} унікальних кандидатів")
        
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
        """Пошук у локальній базі"""
        ingredient_lower = ingredient_name.lower()
        
        for ingredient in self.local_ingredients:
            # Перевіряємо точне співпадіння з назвою
            if ingredient_lower == ingredient['name'].lower():
                return ingredient
            
            # Перевіряємо співпадіння з псевдонімами
            for alias in ingredient.get('aliases', []):
                if ingredient_lower == alias.lower():
                    return ingredient
            
            # Перевіряємо часткове співпадіння (для покращеного пошуку)
            if ingredient_lower in ingredient['name'].lower() or ingredient['name'].lower() in ingredient_lower:
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
            print("⚠️ Текст для аналізу порожній або не є рядком")
            return []
        
        print(f"\n🔍 Пошук інгредієнтів у тексті")
        
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
                risk_icon = "🔴" if ingredient['risk_level'] == 'high' else \
                           "🟠" if ingredient['risk_level'] == 'medium' else \
                           "🟡" if ingredient['risk_level'] == 'low' else \
                           "🟢" if ingredient['risk_level'] == 'safe' else "⚫"
                print(f"✅ {risk_icon} Знайдено: {ingredient['name']} (ризик: {ingredient['risk_level']})")
        
        print(f"📊 ПІДСУМОК: знайдено {len(found_ingredients)} інгредієнтів")
        
        # 3. Статистика за ризиками
        risk_stats = {'high': 0, 'medium': 0, 'low': 0, 'safe': 0, 'unknown': 0}
        
        for ing in found_ingredients:
            risk = ing.get('risk_level', 'unknown')
            if risk in risk_stats:
                risk_stats[risk] += 1
        
        print(f"📈 Статистика ризиків: 🔴 {risk_stats['high']} 🟠 {risk_stats['medium']} 🟡 {risk_stats['low']} 🟢 {risk_stats['safe']} ⚫ {risk_stats['unknown']}")
        
        return found_ingredients


class ExternalDataFetcher:
    """Клас для отримання даних із зовнішніх джерел"""
    
    def __init__(self, cache_dir='data_cache'):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'external_cache.db')
        os.makedirs(cache_dir, exist_ok=True)
        self.init_cache()
        print(f"✅ ExternalDataFetcher ініціалізований, кеш: {self.cache_file}")
        
    def init_cache(self):
        """Ініціалізація кешу"""
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
        """Пошук інгредієнта у зовнішніх джерелах"""
        
        # 1. Перевіряємо кеш
        cached = self._get_from_cache(ingredient_name)
        if cached:
            return cached
        
        # 2. Пробуємо різні джерела
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
            print(f"⚠️ Немає доступу до інтернету, пропускаємо зовнішні джерела")
            return None
    
    def _search_cosing(self, ingredient_name):
        """Пошук у базі CosIng ЄС"""
        try:
            print(f"🔗 Запит до CosIng API: {ingredient_name}")
            
            # Заглушка для демонстрації
            if 'paraben' in ingredient_name.lower():
                return {
                    "name": ingredient_name,
                    "risk_level": "medium",
                    "category": "preservative",
                    "description": "Консервант парабенового ряду.",
                    "source": "cosing",
                    "aliases": [],
                    "context": "Обмеження ЄС: до 0.4%"
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Помилка CosIng API: {e}")
            return None
    
    def _search_openfoodfacts(self, ingredient_name):
        """Пошук у Open Food Facts"""
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
                        "description": "Харчовий інгредієнт",
                        "source": "openfoodfacts",
                        "aliases": [],
                        "context": "Дані з Open Food Facts"
                    }
            
            return None
            
        except Exception as e:
            print(f"❌ Помилка Open Food Facts API: {e}")
            return None
    
    def _search_pubchem(self, ingredient_name):
        """Пошук у PubChem"""
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
                    "description": f"Хімічне з'єднання: {ingredient_name}",
                    "source": "pubchem",
                    "aliases": [],
                    "context": "Автоматична оцінка на основі назви"
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Помилка PubChem API: {e}")
            return None
    
    def _get_from_cache(self, ingredient_name):
        """Отримання з кешу"""
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
            print(f"❌ Помилка читання кешу: {e}")
            return None
    
    def _save_to_cache(self, ingredient_name, data):
        """Збереження в кеш"""
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
            print(f"❌ Помилка збереження в кеш: {e}")