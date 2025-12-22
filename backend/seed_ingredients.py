import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Ingredient, Scan
from datetime import datetime
import random
import json

# ОБНОВЛЕННЫЙ СПИСОК ИНГРЕДИЕНТОВ С ПРАКТИЧНОЙ ОЦЕНКОЙ РИСКОВ
COMMON_COSMETIC_INGREDIENTS = [
    # === Вода и основы ===
    {"name": "Aqua", "risk_level": "safe", "category": "solvent", 
     "description": "Вода, основа косметических средств"},
    {"name": "Water", "risk_level": "safe", "category": "solvent", 
     "description": "Вода"},
    
    # === ПАВы и очищающие (пересмотренные оценки) ===
    {"name": "Sodium Laureth Sulfate", "risk_level": "medium", "category": "surfactant", 
     "description": "ПАВ, пенообразователь. Может сушить кожу при частом использовании"},
    {"name": "Sodium Lauryl Sulfate", "risk_level": "medium", "category": "surfactant", 
     "description": "SLS, более агрессивный чем SLES, может вызывать раздражение"},
    {"name": "Cocamidopropyl Betaine", "risk_level": "low", "category": "surfactant", 
     "description": "Мягкий ПАВ из кокосового масла, подходит для чувствительной кожи"},
    {"name": "Decyl Glucoside", "risk_level": "low", "category": "surfactant", 
     "description": "Натуральный мягкий ПАВ из кокосового масла и кукурузы"},
    {"name": "Sodium Coco-Sulfate", "risk_level": "medium", "category": "surfactant", 
     "description": "ПАВ из кокосового масла, умеренный риск раздражения"},
    {"name": "Disodium Laureth Sulfosuccinate", "risk_level": "low", "category": "surfactant", 
     "description": "Очень мягкий ПАВ, подходит для деликатной кожи"},
    {"name": "Coco Glucoside", "risk_level": "low", "category": "surfactant", 
     "description": "Натуральный мягкий ПАВ, биоразлагаемый"},
    {"name": "Lauryl Glucoside", "risk_level": "low", "category": "surfactant", 
     "description": "Мягкий ПАВ из кокосового масла"},
    
    # === КОНСЕРВАНТЫ (пересмотренные оценки) ===
    # ВЫСОКИЙ РИСК - доказанная опасность
    {"name": "Formaldehyde", "risk_level": "high", "category": "preservative", 
     "description": "Канцероген, запрещен во многих странах"},
    {"name": "Methylisothiazolinone", "risk_level": "high", "category": "preservative", 
     "description": "Сильнейший аллерген, ограничен в ЕС с 2017"},
    {"name": "Methylchloroisothiazolinone", "risk_level": "high", "category": "preservative", 
     "description": "Сильный аллерген, часто в комбинации с MIT"},
    {"name": "DMDM Hydantoin", "risk_level": "high", "category": "preservative", 
     "description": "Высвобождает формальдегид, аллерген"},
    {"name": "Quaternium-15", "risk_level": "high", "category": "preservative", 
     "description": "Высвобождает формальдегид"},
    
    # СРЕДНИЙ РИСК - спорные, но широко используемые
    {"name": "Methylparaben", "risk_level": "medium", "category": "preservative", 
     "description": "Парабен, разрешен в ЕС до 0.4%, исследования о гормональном влиянии"},
    {"name": "Propylparaben", "risk_level": "medium", "category": "preservative", 
     "description": "Парабен, разрешен в ЕС до 0.14%"},
    {"name": "Butylparaben", "risk_level": "medium", "category": "preservative", 
     "description": "Парабен, ограничен в ЕС"},
    {"name": "Ethylparaben", "risk_level": "medium", "category": "preservative", 
     "description": "Парабен, считается наиболее безопасным в группе"},
    {"name": "Phenoxyethanol", "risk_level": "medium", "category": "preservative", 
     "description": "Широко используемый консервант, ограничен до 1% в ЕС"},
    {"name": "Benzyl Alcohol", "risk_level": "medium", "category": "preservative", 
     "description": "Консервант и растворитель, может раздражать чувствительную кожу"},
    
    # НИЗКИЙ РИСК - относительно безопасные
    {"name": "Potassium Sorbate", "risk_level": "low", "category": "preservative", 
     "description": "Соль сорбиновой кислоты, пищевой консервант"},
    {"name": "Sodium Benzoate", "risk_level": "low", "category": "preservative", 
     "description": "Консервант, разрешен в косметике до 0.5%"},
    {"name": "Sorbic Acid", "risk_level": "low", "category": "preservative", 
     "description": "Натуральный консервант из ягод рябины"},
    {"name": "Benzoic Acid", "risk_level": "low", "category": "preservative", 
     "description": "Натуральный консервант"},
    
    # === АРОМАТИЗАТОРЫ (пересмотренные - medium вместо high) ===
    {"name": "Parfum", "risk_level": "medium", "category": "fragrance", 
     "description": "Ароматизатор. Может вызывать аллергию у чувствительных людей. Присутствует в 80% косметики."},
    {"name": "Fragrance", "risk_level": "medium", "category": "fragrance", 
     "description": "Ароматическая композиция. Основной аллерген в косметике."},
    {"name": "Limonene", "risk_level": "medium", "category": "fragrance", 
     "description": "Ароматическое соединение, аллерген, окисляется на воздухе"},
    {"name": "Linalool", "risk_level": "medium", "category": "fragrance", 
     "description": "Ароматическое соединение, аллерген при окислении"},
    {"name": "Geraniol", "risk_level": "medium", "category": "fragrance", 
     "description": "Ароматическое соединение, аллерген"},
    {"name": "Citronellol", "risk_level": "medium", "category": "fragrance", 
     "description": "Ароматическое соединение, аллерген"},
    {"name": "Citral", "risk_level": "medium", "category": "fragrance", 
     "description": "Ароматическое соединение, аллерген"},
    
    # === Растворители и спирты ===
    {"name": "Alcohol Denat", "risk_level": "medium", "category": "solvent", 
     "description": "Денатурированный спирт. Сушит кожу, может нарушать барьер."},
    {"name": "Alcohol", "risk_level": "medium", "category": "solvent", 
     "description": "Спирт, сушит кожу, используйте умеренно"},
    {"name": "Ethanol", "risk_level": "medium", "category": "solvent", 
     "description": "Этиловый спирт, может сушить кожу"},
    {"name": "Isopropyl Alcohol", "risk_level": "medium", "category": "solvent", 
     "description": "Изопропиловый спирт, сильный растворитель"},
    {"name": "Propylene Glycol", "risk_level": "medium", "category": "solvent", 
     "description": "Растворитель и увлажнитель. Может раздражать чувствительную кожу."},
    {"name": "Butylene Glycol", "risk_level": "low", "category": "solvent", 
     "description": "Растворитель, более мягкий чем пропиленгликоль"},
    {"name": "Glycerin", "risk_level": "low", "category": "humectant", 
     "description": "Увлажнитель, безопасный и эффективный"},
    {"name": "Glycerol", "risk_level": "low", "category": "humectant", 
     "description": "Глицерин, натуральный увлажнитель"},
    
    # === Эмульгаторы ===
    {"name": "Cetearyl Alcohol", "risk_level": "low", "category": "emulsifier", 
     "description": "Эмульгатор и загуститель, не сушит кожу"},
    {"name": "Glyceryl Stearate", "risk_level": "low", "category": "emulsifier", 
     "description": "Эмульгатор из глицерина и стеариновой кислоты"},
    {"name": "Polysorbate 20", "risk_level": "low", "category": "emulsifier", 
     "description": "Эмульгатор, безопасный для кожи"},
    {"name": "Polysorbate 60", "risk_level": "low", "category": "emulsifier", 
     "description": "Эмульгатор"},
    {"name": "Polysorbate 80", "risk_level": "low", "category": "emulsifier", 
     "description": "Эмульгатор"},
    {"name": "Sorbitan Stearate", "risk_level": "low", "category": "emulsifier", 
     "description": "Эмульгатор"},
    {"name": "Ceteareth-20", "risk_level": "low", "category": "emulsifier", 
     "description": "Эмульгатор"},
    
    # === ПЭГ и производные ===
    {"name": "PEG-4", "risk_level": "low", "category": "emulsifier", 
     "description": "Полиэтиленгликоль, эмульгатор"},
    {"name": "PEG-8", "risk_level": "low", "category": "emulsifier", 
     "description": "Полиэтиленгликоль"},
    {"name": "PEG-12", "risk_level": "low", "category": "emulsifier", 
     "description": "Полиэтиленгликоль"},
    {"name": "PEG-40", "risk_level": "low", "category": "emulsifier", 
     "description": "Полиэтиленгликоль, эмульгатор"},
    {"name": "PEG-100", "risk_level": "low", "category": "emulsifier", 
     "description": "Полиэтиленгликоль"},
    {"name": "PEG-4 Cocoate", "risk_level": "low", "category": "emulsifier", 
     "description": "Эфир кокосового масла и ПЭГ-4"},
    
    # === Масла и эмоленты ===
    {"name": "Mineral Oil", "risk_level": "low", "category": "emollient", 
     "description": "Минеральное масло, окклюзивный агент. Безопасно, но может быть комедогенным для жирной кожи."},
    {"name": "Paraffinum Liquidum", "risk_level": "low", "category": "emollient", 
     "description": "Жидкий парафин, окклюзив"},
    {"name": "Petrolatum", "risk_level": "low", "category": "emollient", 
     "description": "Вазелин, окклюзивный агент, защищает кожу"},
    {"name": "Caprylic/Capric Triglyceride", "risk_level": "low", "category": "emollient", 
     "description": "Триглицериды кокосового масла, легкий эмолент"},
    {"name": "Cetyl Alcohol", "risk_level": "low", "category": "emollient", 
     "description": "Жирный спирт, эмолент, не сушит кожу"},
    {"name": "Stearyl Alcohol", "risk_level": "low", "category": "emollient", 
     "description": "Жирный спирт, эмолент"},
    {"name": "Isopropyl Myristate", "risk_level": "medium", "category": "emollient", 
     "description": "Эмолент, может быть комедогенным для склонной к акне кожи"},
    {"name": "Isopropyl Palmitate", "risk_level": "medium", "category": "emollient", 
     "description": "Эмолент, может забивать поры"},
    
    # === Силиконы ===
    {"name": "Dimethicone", "risk_level": "low", "category": "emollient", 
     "description": "Силикон, создает защитную пленку, некомедогенный"},
    {"name": "Cyclopentasiloxane", "risk_level": "low", "category": "emollient", 
     "description": "Летучий силикон, не оставляет жирного блеска"},
    {"name": "Cyclohexasiloxane", "risk_level": "low", "category": "emollient", 
     "description": "Летучий силикон"},
    {"name": "Phenyl Trimethicone", "risk_level": "low", "category": "emollient", 
     "description": "Силикон с УФ-защитными свойствами"},
    {"name": "Amodimethicone", "risk_level": "low", "category": "emollient", 
     "description": "Силикон для волос, кондиционирующий агент"},
    
    # === УФ-фильтры ===
    # ВЫСОКИЙ РИСК
    {"name": "Oxybenzone", "risk_level": "high", "category": "UV filter", 
     "description": "Бензофенон-3, эндокринный дизраптор, запрещен на Гавайях"},
    {"name": "Benzophenone-3", "risk_level": "high", "category": "UV filter", 
     "description": "Оксибензон, эндокринный дизраптор"},
    
    # СРЕДНИЙ РИСК
    {"name": "Avobenzone", "risk_level": "medium", "category": "UV filter", 
     "description": "УФ-фильтр широкого спектра, может разлагаться на солнце"},
    {"name": "Octinoxate", "risk_level": "medium", "category": "UV filter", 
     "description": "УФ-фильтр, эндокринный дизраптор в высоких концентрациях"},
    {"name": "Octocrylene", "risk_level": "medium", "category": "UV filter", 
     "description": "УФ-фильтр, может вызывать аллергию"},
    {"name": "Homosalate", "risk_level": "medium", "category": "UV filter", 
     "description": "УФ-фильтр, может проникать в кожу"},
    {"name": "Octisalate", "risk_level": "medium", "category": "UV filter", 
     "description": "УФ-фильтр"},
    
    # НИЗКИЙ РИСК
    {"name": "Titanium Dioxide", "risk_level": "low", "category": "UV filter", 
     "description": "Минеральный УФ-фильтр, безопасен, может оставлять белый след"},
    {"name": "Zinc Oxide", "risk_level": "low", "category": "UV filter", 
     "description": "Минеральный УФ-фильтр, самый безопасный, противовоспалительный"},
    
    # === Антибактериальные ===
    {"name": "Triclosan", "risk_level": "high", "category": "antibacterial", 
     "description": "Антибактериальный агент, способствует резистентности, запрещен в ЕС"},
    {"name": "Triclocarban", "risk_level": "high", "category": "antibacterial", 
     "description": "Антибактериальный агент, аналогично триклозану"},
    
    # === Хелаторы ===
    {"name": "Tetrasodium EDTA", "risk_level": "medium", "category": "chelating agent", 
     "description": "Хелатирующий агент, улучшает пену, может раздражать кожу"},
    {"name": "Disodium EDTA", "risk_level": "medium", "category": "chelating agent", 
     "description": "Хелатирующий агент"},
    
    # === Регуляторы pH ===
    {"name": "Citric Acid", "risk_level": "low", "category": "pH adjuster", 
     "description": "Лимонная кислота, регулятор pH, AHA в высоких концентрациях"},
    {"name": "Sodium Hydroxide", "risk_level": "high", "category": "pH adjuster", 
     "description": "Щелочь, коррозионный в чистом виде, безопасен в готовых продуктах"},
    {"name": "Triethanolamine", "risk_level": "medium", "category": "pH adjuster", 
     "description": "Регулятор pH, может образовывать нитрозамины"},
    
    # === Натуральные ингредиенты ===
    {"name": "Aloe Barbadensis Leaf Juice", "risk_level": "safe", "category": "plant extract", 
     "description": "Сок алоэ вера, успокаивающее, заживляющее"},
    {"name": "Camellia Sinensis Leaf Extract", "risk_level": "safe", "category": "plant extract", 
     "description": "Экстракт зеленого чая, антиоксидант"},
    {"name": "Chamomilla Recutita Flower Extract", "risk_level": "safe", "category": "plant extract", 
     "description": "Экстракт ромашки, успокаивающее"},
    {"name": "Rosmarinus Officinalis Leaf Extract", "risk_level": "safe", "category": "plant extract", 
     "description": "Экстракт розмарина, антиоксидант"},
    {"name": "Calendula Officinalis Flower Extract", "risk_level": "safe", "category": "plant extract", 
     "description": "Экстракт календулы, успокаивающее"},
    {"name": "Lavandula Angustifolia Oil", "risk_level": "low", "category": "essential oil", 
     "description": "Масло лаванды, аромат, успокаивающее"},
    {"name": "Melaleuca Alternifolia Leaf Oil", "risk_level": "low", "category": "essential oil", 
     "description": "Масло чайного дерева, антибактериальное, может раздражать в чистом виде"},
    {"name": "Citrus Aurantium Dulcis Peel Oil", "risk_level": "medium", "category": "essential oil", 
     "description": "Апельсиновое масло, фотосенсибилизатор, избегайте перед солнцем"},
    
    # === Витамины и активные ===
    {"name": "Tocopherol", "risk_level": "safe", "category": "antioxidant", 
     "description": "Витамин Е, антиоксидант, стабилизатор"},
    {"name": "Ascorbic Acid", "risk_level": "safe", "category": "antioxidant", 
     "description": "Витамин С, антиоксидант, осветляет"},
    {"name": "Retinol", "risk_level": "medium", "category": "active", 
     "description": "Витамин А, антивозрастной, может раздражать, избегайте при беременности"},
    {"name": "Niacinamide", "risk_level": "safe", "category": "active", 
     "description": "Ниацинамид, витамин B3, улучшает барьер, противовоспалительный"},
    {"name": "Salicylic Acid", "risk_level": "medium", "category": "active", 
     "description": "Салициловая кислота, BHA, отшелушивающее, для жирной кожи"},
    {"name": "Glycolic Acid", "risk_level": "medium", "category": "active", 
     "description": "Гликолевая кислота, AHA, отшелушивающее, повышает чувствительность к солнцу"},
    {"name": "Lactic Acid", "risk_level": "low", "category": "active", 
     "description": "Молочная кислота, AHA, более мягкий чем гликолевый"},
    {"name": "Hyaluronic Acid", "risk_level": "safe", "category": "humectant", 
     "description": "Гиалуроновая кислота, увлажнитель"},
    {"name": "Ceramide NP", "risk_level": "safe", "category": "skin-identical", 
     "description": "Церамид, восстанавливает кожный барьер"},
    {"name": "Allantoin", "risk_level": "safe", "category": "soothing", 
     "description": "Аллантоин, успокаивающее, заживляющее"},
    {"name": "Panthenol", "risk_level": "safe", "category": "soothing", 
     "description": "Пантенол, провитамин B5, увлажняет, успокаивает"},
    
    # === Пленкообразователи и полимеры ===
    {"name": "VP/VA Copolymer", "risk_level": "low", "category": "film former", 
     "description": "Пленкообразующий полимер, фиксатор"},
    {"name": "Acrylates Copolymer", "risk_level": "low", "category": "film former", 
     "description": "Полимер, пленкообразователь"},
    {"name": "Styrene/Acrylates Copolymer", "risk_level": "low", "category": "film former", 
     "description": "Полимер"},
    {"name": "Styrene Acrylates Copolymer", "risk_level": "low", "category": "film former", 
     "description": "Полимер"},
    
    # === Загустители ===
    {"name": "Carbomer", "risk_level": "low", "category": "thickener", 
     "description": "Загуститель, создает гелевую текстуру"},
    {"name": "Xanthan Gum", "risk_level": "low", "category": "thickener", 
     "description": "Натуральный загуститель из бактерий"},
    {"name": "Hydroxyethylcellulose", "risk_level": "low", "category": "thickener", 
     "description": "Загуститель из целлюлозы"},
    {"name": "Acrylates/C10-30 Alkyl Acrylate Crosspolymer", "risk_level": "low", "category": "thickener", 
     "description": "Загуститель, эмульгатор"},
    
    # === Пигменты ===
    {"name": "CI 77891", "risk_level": "low", "category": "pigment", 
     "description": "Диоксид титана, белый пигмент, УФ-фильтр"},
    {"name": "CI 77491", "risk_level": "low", "category": "pigment", 
     "description": "Оксид железа, красный пигмент"},
    {"name": "CI 77492", "risk_level": "low", "category": "pigment", 
     "description": "Оксид железа, желтый пигмент"},
    {"name": "CI 77499", "risk_level": "low", "category": "pigment", 
     "description": "Оксид железа, черный пигмент"},
    {"name": "Mica", "risk_level": "low", "category": "pigment", 
     "description": "Слюда, перламутровый пигмент"},
    
    # === Дополнительные консерванты ===
    {"name": "Dehydroacetic Acid", "risk_level": "low", "category": "preservative", 
     "description": "Консервант, фунгицид"},
    {"name": "Benzalkonium Chloride", "risk_level": "medium", "category": "preservative", 
     "description": "Консервант и антисептик, может раздражать"},
    {"name": "Chlorhexidine Digluconate", "risk_level": "medium", "category": "antiseptic", 
     "description": "Антисептик, для лечения акне"},
    
    # === Протеины и экстракты ===
    {"name": "Hydrolyzed Silk Protein", "risk_level": "low", "category": "conditioning agent", 
     "description": "Гидролизованный шелковый протеин, кондиционер для волос"},
    {"name": "Hydrolyzed Wheat Protein", "risk_level": "low", "category": "conditioning agent", 
     "description": "Гидролизованный пшеничный протеин, увлажняет"},
    {"name": "Hydrolyzed Collagen", "risk_level": "low", "category": "conditioning agent", 
     "description": "Гидролизованный коллаген, увлажняет"},
    
    # === Соли и минералы ===
    {"name": "Sodium Chloride", "risk_level": "safe", "category": "viscosity controlling", 
     "description": "Поваренная соль, загуститель в шампунях"},
    {"name": "Magnesium Sulfate", "risk_level": "safe", "category": "viscosity controlling", 
     "description": "Сульфат магния, английская соль"},
    {"name": "Calcium Carbonate", "risk_level": "safe", "category": "abrasive", 
     "description": "Карбонат кальция, мягкий абразив в скрабах"},
    
    # === Новые важные ингредиенты ===
    {"name": "Squalane", "risk_level": "safe", "category": "emollient", 
     "description": "Скваланан, легкое масло, идентично кожному себуму"},
    {"name": "N-Acetyl Glucosamine", "risk_level": "safe", "category": "active", 
     "description": "Увлажнитель, осветляет гиперпигментацию"},
    {"name": "Centella Asiatica Extract", "risk_level": "safe", "category": "plant extract", 
     "description": "Экстракт центеллы азиатской, заживляет, успокаивает"},
    {"name": "Madecassoside", "risk_level": "safe", "category": "active", 
     "description": "Активный компонент центеллы, противовоспалительный"},
    {"name": "Azelaic Acid", "risk_level": "medium", "category": "active", 
     "description": "Азелаиновая кислота, для акне и розацеа"},
    {"name": "Bakuchiol", "risk_level": "safe", "category": "active", 
     "description": "Натуральная альтернатива ретинолу, менее раздражающая"},
]

def seed_database():
    """Наполнение базы данных основными ингредиентами и тестовыми данными"""
    
    with app.app_context():
        print("🌱 Наполнение базы данных Cosmetics Scanner...")
        print("=" * 60)
        
        # ОПЦИЯ: Очистка старых данных (раскомментируйте если нужно)
        # print("\n🗑️ Очистка старых данных...")
        # Scan.query.delete()
        # Ingredient.query.delete()
        # db.session.commit()
        # print("✅ Старые данные удалены")
        
        # 1. Добавление 150+ частых ингредиентов
        print(f"\n🧪 Добавление частых ингредиентов ({len(COMMON_COSMETIC_INGREDIENTS)})...")
        
        ingredients_added = 0
        ingredients_updated = 0
        
        for ingredient_data in COMMON_COSMETIC_INGREDIENTS:
            # Проверяем, существует ли уже
            existing = Ingredient.query.filter_by(name=ingredient_data['name']).first()
            
            if not existing:
                # Создаем новый ингредиент
                ingredient = Ingredient(
                    name=ingredient_data['name'],
                    risk_level=ingredient_data['risk_level'],
                    category=ingredient_data['category'],
                    description=ingredient_data['description'],
                    created_at=datetime.utcnow()
                )
                db.session.add(ingredient)
                ingredients_added += 1
                if ingredients_added % 20 == 0:
                    print(f"  Добавлено: {ingredients_added}...")
            else:
                # Обновляем существующий (если нужно)
                existing.risk_level = ingredient_data['risk_level']
                existing.category = ingredient_data['category']
                existing.description = ingredient_data['description']
                ingredients_updated += 1
        
        db.session.commit()
        print(f"✅ Добавлено: {ingredients_added}, Обновлено: {ingredients_updated}")
        
        # 2. Тестовые пользователи
        print("\n👤 Создание тестовых пользователей...")
        
        # Администратор
        admin_user = User.query.filter_by(email="admin@cosmetics.com").first()
        if not admin_user:
            admin_user = User(email="admin@cosmetics.com", role="admin")
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            print("✅ Создан администратор: admin@cosmetics.com / admin123")
        else:
            print("ℹ️ Администратор уже существует")
        
        # Пользователь
        test_user = User.query.filter_by(email="user@example.com").first()
        if not test_user:
            test_user = User(email="user@example.com", role="user")
            test_user.set_password("user123")
            db.session.add(test_user)
            print("✅ Создан пользователь: user@example.com / user123")
        else:
            print("ℹ️ Пользователь уже существует")
        
        db.session.commit()
        
        # 3. Тестовые сканирования (опционально)
        create_test_scans = True  # Поставьте True если нужны тестовые сканы
        
        if create_test_scans and test_user:
            print("\n🔍 Создание тестовых сканирований...")
            
            test_scans = [
                {
                    "text": "Состав: Aqua, Sodium Laureth Sulfate, Cocamidopropyl Betaine, Glycerin, Parfum, PEG-4 Cocoate, Styrene Acrylates Copolymer, Coco Glucoside, Tetrasodium EDTA, Hydrolyzed Silk Protein, Citric Acid",
                    "title": "Мягкое крем-мыло",
                    "expected_status": "warning"  # Parfum medium + SLES medium
                },
                {
                    "text": "Ingredients: Aqua, Formaldehyde, Alcohol Denat, Fragrance, Mineral Oil, Propylene Glycol, Methylisothiazolinone",
                    "title": "Опасный лосьон",
                    "expected_status": "danger"  # Formaldehyde high + MIT high
                },
                {
                    "text": "INCI: Aqua, Dimethicone, Cyclopentasiloxane, Zinc Oxide, Titanium Dioxide, Tocopherol, Glycerin",
                    "title": "Безопасный солнцезащитный крем",
                    "expected_status": "safe"  # Все low/safe
                },
                {
                    "text": "Состав: Алое вера, Глицерин, Аллантоин, Пантенол, Ниацинамид, Гиалуроновая кислота, Скваланан",
                    "title": "Натуральный увлажняющий крем",
                    "expected_status": "safe"  # Все safe
                },
                {
                    "text": "Sodium Benzoate, Potassium Sorbate, Citric Acid, Aqua, Sodium Hydroxide (для pH коррекции)",
                    "title": "Продукт с безопасными консервантами",
                    "expected_status": "warning"  # NaOH high
                },
            ]
            
            from checker import IngredientChecker
            checker = IngredientChecker()
            
            scans_created = 0
            for i, test_data in enumerate(test_scans):
                detected = checker.find_ingredients(test_data["text"])
                
                ingredients_for_json = []
                for ing in detected:
                    if isinstance(ing, dict):
                        ingredients_for_json.append({
                            'id': ing.get('id', 0),
                            'name': ing.get('name', ''),
                            'risk_level': ing.get('risk_level', 'medium'),
                            'category': ing.get('category', ''),
                            'description': ing.get('description', '')
                        })
                
                # Определяем статус безопасности по новой логике
                from app import calculate_safety_status_with_message
                safety_info = calculate_safety_status_with_message(detected)
                
                scan = Scan(
                    user_id=test_user.id,
                    input_type=random.choice(['manual', 'camera']),
                    input_method=random.choice(['text', 'device']),
                    original_text=test_data["text"],
                    safety_status=safety_info['status'],
                    safety_message=safety_info['message'],
                    contains_unknown=safety_info['contains_unknown'],
                    unknown_count=safety_info['unknown_count'],
                    ingredients_detected=ingredients_for_json,
                    created_at=datetime.utcnow()
                )
                db.session.add(scan)
                scans_created += 1
                print(f"  📄 Создан тестовый скан #{i+1}: {test_data['title']} -> {safety_info['status']}")
            
            db.session.commit()
            print(f"✅ Создано тестовых сканирований: {scans_created}")
        
        # 4. Статистика
        print("\n📊 ФИНАЛЬНАЯ СТАТИСТИКА БАЗЫ:")
        print(f"   👥 Пользователей: {User.query.count()}")
        print(f"   🧪 Ингредиентов: {Ingredient.query.count()}")
        print(f"   🔍 Сканирований: {Scan.query.count()}")
        
        # Статистика по категориям
        print("\n📈 СТАТИСТИКА ПО КАТЕГОРИЯМ:")
        from sqlalchemy import func
        category_stats = db.session.query(
            Ingredient.category, 
            func.count(Ingredient.id)
        ).group_by(Ingredient.category).order_by(func.count(Ingredient.id).desc()).all()
        
        for category, count in category_stats:
            if category:
                print(f"   • {category}: {count}")
        
        # Статистика по уровню риска
        print("\n⚠️  СТАТИСТИКА ПО РИСКУ:")
        risk_stats = db.session.query(
            Ingredient.risk_level, 
            func.count(Ingredient.id)
        ).group_by(Ingredient.risk_level).order_by(func.count(Ingredient.id).desc()).all()
        
        risk_icons = {
            'safe': '🟢',
            'low': '🟡', 
            'medium': '🟠',
            'high': '🔴',
            'unknown': '⚫'
        }
        
        for risk, count in risk_stats:
            if risk:
                icon = risk_icons.get(risk, '⚪')
                print(f"   {icon} {risk}: {count}")
        
        # Примеры продуктов с разным уровнем риска
        print("\n🧪 ПРИМЕРЫ ОЦЕНКИ ПРОДУКТОВ:")
        print("   🔴 HIGH: Формальдегид, Оксибензон, Триклозан")
        print("   🟠 MEDIUM: Парфюм, Парабены, Спирт, SLES")
        print("   🟡 LOW: Глицерин, Диметикон, Бензоат натрия")
        print("   🟢 SAFE: Вода, Алоэ вера, Витамины, Гиалуроновая кислота")
        
        print("\n" + "=" * 60)
        print("🎉 БАЗА ДАННЫХ ОБНОВЛЕНА С НОВОЙ СИСТЕМОЙ ОЦЕНКИ!")
        print("=" * 60)
        
        print("\n🔧 ОСНОВНЫЕ ИЗМЕНЕНИЯ:")
        print("   1. Parfum/Fragrance: HIGH → MEDIUM (практичный подход)")
        print("   2. Sodium Benzoate: UNKNOWN → LOW (безопасный консервант)")
        print("   3. Mineral Oil: LOW (безопасно, но может быть комедогенным)")
        print("   4. Более реалистичные оценки для широко используемых ингредиентов")
        
        print("\n📱 ТЕСТОВЫЕ УЧЕТНЫЕ ЗАПИСИ:")
        print("   👤 Пользователь: user@example.com / user123")
        print("   👑 Администратор: admin@cosmetics.com / admin123")
        
        print("\n⚠️  Для очистки базы данных:")
        print('   python -c "from app import app, db; with app.app_context(): db.drop_all(); db.create_all()"')
        
        return True

if __name__ == "__main__":
    seed_database()