import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Ingredient, Scan
from datetime import datetime
import random
import json

# Список из ~100 самых частых ингредиентов косметики
COMMON_COSMETIC_INGREDIENTS = [
    # Вода и основы
    {"name": "Aqua", "risk_level": "safe", "category": "solvent", "description": "Вода, основа косметических средств"},
    {"name": "Water", "risk_level": "safe", "category": "solvent", "description": "Вода"},
    
    # ПАВы и очищающие
    {"name": "Sodium Laureth Sulfate", "risk_level": "medium", "category": "surfactant", "description": "Поверхностно-активное вещество, пенообразователь"},
    {"name": "Sodium Lauryl Sulfate", "risk_level": "medium", "category": "surfactant", "description": "SLS, сильный пенообразователь"},
    {"name": "Cocamidopropyl Betaine", "risk_level": "low", "category": "surfactant", "description": "Мягкий ПАВ из кокосового масла"},
    {"name": "Decyl Glucoside", "risk_level": "low", "category": "surfactant", "description": "Натуральный мягкий ПАВ"},
    {"name": "Sodium Coco-Sulfate", "risk_level": "medium", "category": "surfactant", "description": "ПАВ из кокосового масла"},
    {"name": "Disodium Laureth Sulfosuccinate", "risk_level": "low", "category": "surfactant", "description": "Мягкий ПАВ"},
    
    # Консерванты
    {"name": "Methylparaben", "risk_level": "medium", "category": "preservative", "description": "Консервант парабенового ряда"},
    {"name": "Propylparaben", "risk_level": "medium", "category": "preservative", "description": "Консервант парабенового ряда"},
    {"name": "Butylparaben", "risk_level": "medium", "category": "preservative", "description": "Консервант парабенового ряда"},
    {"name": "Ethylparaben", "risk_level": "medium", "category": "preservative", "description": "Консервант парабенового ряда"},
    {"name": "Phenoxyethanol", "risk_level": "medium", "category": "preservative", "description": "Широко используемый консервант"},
    {"name": "Benzyl Alcohol", "risk_level": "medium", "category": "preservative", "description": "Консервант и растворитель"},
    {"name": "Potassium Sorbate", "risk_level": "low", "category": "preservative", "description": "Консервант, соль сорбиновой кислоты"},
    {"name": "Sodium Benzoate", "risk_level": "low", "category": "preservative", "description": "Консервант"},
    {"name": "Formaldehyde", "risk_level": "high", "category": "preservative", "description": "Формальдегид, канцероген"},
    {"name": "Methylisothiazolinone", "risk_level": "high", "category": "preservative", "description": "Сильный аллерген, консервант"},
    {"name": "Methylchloroisothiazolinone", "risk_level": "high", "category": "preservative", "description": "Консервант, аллерген"},
    {"name": "Imidazolidinyl Urea", "risk_level": "medium", "category": "preservative", "description": "Консервант, высвобождает формальдегид"},
    {"name": "Diazolidinyl Urea", "risk_level": "medium", "category": "preservative", "description": "Консервант"},
    {"name": "DMDM Hydantoin", "risk_level": "high", "category": "preservative", "description": "Консервант, формальдегид-высвобождающий"},
    
    # Ароматизаторы
    {"name": "Parfum", "risk_level": "high", "category": "fragrance", "description": "Ароматизатор, аллерген"},
    {"name": "Fragrance", "risk_level": "high", "category": "fragrance", "description": "Ароматизатор"},
    {"name": "Limonene", "risk_level": "medium", "category": "fragrance", "description": "Ароматическое соединение"},
    {"name": "Linalool", "risk_level": "medium", "category": "fragrance", "description": "Ароматическое соединение"},
    {"name": "Geraniol", "risk_level": "medium", "category": "fragrance", "description": "Ароматическое соединение"},
    {"name": "Citronellol", "risk_level": "medium", "category": "fragrance", "description": "Ароматическое соединение"},
    
    # Растворители и спирты
    {"name": "Alcohol", "risk_level": "medium", "category": "solvent", "description": "Спирт, сушит кожу"},
    {"name": "Alcohol Denat", "risk_level": "medium", "category": "solvent", "description": "Денатурированный спирт"},
    {"name": "Ethanol", "risk_level": "medium", "category": "solvent", "description": "Этиловый спирт"},
    {"name": "Isopropyl Alcohol", "risk_level": "medium", "category": "solvent", "description": "Изопропиловый спирт"},
    {"name": "Propylene Glycol", "risk_level": "medium", "category": "solvent", "description": "Растворитель, увлажнитель"},
    {"name": "Butylene Glycol", "risk_level": "low", "category": "solvent", "description": "Растворитель"},
    {"name": "Glycerin", "risk_level": "low", "category": "humectant", "description": "Увлажнитель"},
    {"name": "Glycerol", "risk_level": "low", "category": "humectant", "description": "Глицерин, увлажнитель"},
    
    # Эмульгаторы
    {"name": "Cetearyl Alcohol", "risk_level": "low", "category": "emulsifier", "description": "Эмульгатор и загуститель"},
    {"name": "Glyceryl Stearate", "risk_level": "low", "category": "emulsifier", "description": "Эмульгатор"},
    {"name": "Polysorbate 20", "risk_level": "low", "category": "emulsifier", "description": "Эмульгатор"},
    {"name": "Polysorbate 60", "risk_level": "low", "category": "emulsifier", "description": "Эмульгатор"},
    {"name": "Polysorbate 80", "risk_level": "low", "category": "emulsifier", "description": "Эмульгатор"},
    {"name": "Sorbitan Stearate", "risk_level": "low", "category": "emulsifier", "description": "Эмульгатор"},
    {"name": "Ceteareth-20", "risk_level": "low", "category": "emulsifier", "description": "Эмульгатор"},
    
    # ПЭГ и производные
    {"name": "PEG-4", "risk_level": "low", "category": "emulsifier", "description": "Полиэтиленгликоль"},
    {"name": "PEG-8", "risk_level": "low", "category": "emulsifier", "description": "Полиэтиленгликоль"},
    {"name": "PEG-12", "risk_level": "low", "category": "emulsifier", "description": "Полиэтиленгликоль"},
    {"name": "PEG-40", "risk_level": "low", "category": "emulsifier", "description": "Полиэтиленгликоль"},
    {"name": "PEG-100", "risk_level": "low", "category": "emulsifier", "description": "Полиэтиленгликоль"},
    {"name": "PEG-4 Cocoate", "risk_level": "low", "category": "emulsifier", "description": "Эфир кокосового масла и ПЭГ-4"},
    
    # Масла и эмоленты
    {"name": "Mineral Oil", "risk_level": "low", "category": "emollient", "description": "Минеральное масло"},
    {"name": "Paraffinum Liquidum", "risk_level": "low", "category": "emollient", "description": "Жидкий парафин"},
    {"name": "Petrolatum", "risk_level": "low", "category": "emollient", "description": "Вазелин"},
    {"name": "Caprylic/Capric Triglyceride", "risk_level": "low", "category": "emollient", "description": "Триглицериды кокосового масла"},
    {"name": "Cetyl Alcohol", "risk_level": "low", "category": "emollient", "description": "Жирный спирт"},
    {"name": "Stearyl Alcohol", "risk_level": "low", "category": "emollient", "description": "Жирный спирт"},
    {"name": "Isopropyl Myristate", "risk_level": "medium", "category": "emollient", "description": "Эмолент, может комедогенный"},
    {"name": "Isopropyl Palmitate", "risk_level": "medium", "category": "emollient", "description": "Эмолент"},
    
    # Силиконы
    {"name": "Dimethicone", "risk_level": "low", "category": "emollient", "description": "Силикон, смягчает кожу"},
    {"name": "Cyclopentasiloxane", "risk_level": "low", "category": "emollient", "description": "Летучий силикон"},
    {"name": "Cyclohexasiloxane", "risk_level": "low", "category": "emollient", "description": "Силикон"},
    {"name": "Phenyl Trimethicone", "risk_level": "low", "category": "emollient", "description": "Силикон"},
    {"name": "Amodimethicone", "risk_level": "low", "category": "emollient", "description": "Силикон для волос"},
    
    # УФ-фильтры
    {"name": "Oxybenzone", "risk_level": "high", "category": "UV filter", "description": "Химический УФ-фильтр, эндокринный дизраптор"},
    {"name": "Avobenzone", "risk_level": "medium", "category": "UV filter", "description": "УФ-фильтр"},
    {"name": "Octinoxate", "risk_level": "medium", "category": "UV filter", "description": "УФ-фильтр"},
    {"name": "Octocrylene", "risk_level": "medium", "category": "UV filter", "description": "УФ-фильтр"},
    {"name": "Homosalate", "risk_level": "medium", "category": "UV filter", "description": "УФ-фильтр"},
    {"name": "Octisalate", "risk_level": "medium", "category": "UV filter", "description": "УФ-фильтр"},
    {"name": "Titanium Dioxide", "risk_level": "low", "category": "UV filter", "description": "Минеральный УФ-фильтр"},
    {"name": "Zinc Oxide", "risk_level": "low", "category": "UV filter", "description": "Минеральный УФ-фильтр"},
    {"name": "Benzophenone-3", "risk_level": "high", "category": "UV filter", "description": "Бензофенон-3, УФ-фильтр"},
    
    # Антибактериальные
    {"name": "Triclosan", "risk_level": "high", "category": "antibacterial", "description": "Антибактериальный агент, резистентность"},
    {"name": "Triclocarban", "risk_level": "high", "category": "antibacterial", "description": "Антибактериальный агент"},
    
    # Хелаторы
    {"name": "Tetrasodium EDTA", "risk_level": "medium", "category": "chelating agent", "description": "Хелатирующий агент"},
    {"name": "Disodium EDTA", "risk_level": "medium", "category": "chelating agent", "description": "Хелатирующий агент"},
    
    # Регуляторы pH
    {"name": "Citric Acid", "risk_level": "low", "category": "pH adjuster", "description": "Лимонная кислота, регулятор pH"},
    {"name": "Sodium Hydroxide", "risk_level": "high", "category": "pH adjuster", "description": "Щелочь, регулятор pH"},
    {"name": "Triethanolamine", "risk_level": "medium", "category": "pH adjuster", "description": "Регулятор pH"},
    
    # Натуральные ингредиенты
    {"name": "Aloe Barbadensis Leaf Juice", "risk_level": "safe", "category": "plant extract", "description": "Сок алоэ вера, успокаивающее"},
    {"name": "Camellia Sinensis Leaf Extract", "risk_level": "safe", "category": "plant extract", "description": "Экстракт зеленого чая, антиоксидант"},
    {"name": "Chamomilla Recutita Flower Extract", "risk_level": "safe", "category": "plant extract", "description": "Экстракт ромашки, успокаивающее"},
    {"name": "Rosmarinus Officinalis Leaf Extract", "risk_level": "safe", "category": "plant extract", "description": "Экстракт розмарина, антиоксидант"},
    {"name": "Calendula Officinalis Flower Extract", "risk_level": "safe", "category": "plant extract", "description": "Экстракт календулы, успокаивающее"},
    {"name": "Lavandula Angustifolia Oil", "risk_level": "low", "category": "essential oil", "description": "Масло лаванды, аромат"},
    {"name": "Melaleuca Alternifolia Leaf Oil", "risk_level": "low", "category": "essential oil", "description": "Масло чайного дерева, антибактериальное"},
    {"name": "Citrus Aurantium Dulcis Peel Oil", "risk_level": "medium", "category": "essential oil", "description": "Апельсиновое масло, фотосенсибилизатор"},
    
    # Витамины и активные
    {"name": "Tocopherol", "risk_level": "safe", "category": "antioxidant", "description": "Витамин Е, антиоксидант"},
    {"name": "Ascorbic Acid", "risk_level": "safe", "category": "antioxidant", "description": "Витамин С, антиоксидант"},
    {"name": "Retinol", "risk_level": "medium", "category": "active", "description": "Витамин А, ретинол"},
    {"name": "Niacinamide", "risk_level": "safe", "category": "active", "description": "Ниацинамид, витамин B3"},
    {"name": "Salicylic Acid", "risk_level": "medium", "category": "active", "description": "Салициловая кислота, отшелушивающее"},
    {"name": "Glycolic Acid", "risk_level": "medium", "category": "active", "description": "Гликолевая кислота, AHA"},
    {"name": "Lactic Acid", "risk_level": "low", "category": "active", "description": "Молочная кислота, AHA"},
    {"name": "Hyaluronic Acid", "risk_level": "safe", "category": "humectant", "description": "Гиалуроновая кислота, увлажнитель"},
    {"name": "Ceramide NP", "risk_level": "safe", "category": "skin-identical", "description": "Церамид, восстанавливает барьер"},
    {"name": "Allantoin", "risk_level": "safe", "category": "soothing", "description": "Аллантоин, успокаивающее"},
    {"name": "Panthenol", "risk_level": "safe", "category": "soothing", "description": "Пантенол, провитамин B5"},
    
    # Пленкообразователи и полимеры
    {"name": "VP/VA Copolymer", "risk_level": "low", "category": "film former", "description": "Пленкообразующий полимер"},
    {"name": "Acrylates Copolymer", "risk_level": "low", "category": "film former", "description": "Полимер"},
    {"name": "Styrene/Acrylates Copolymer", "risk_level": "low", "category": "film former", "description": "Полимер"},
    {"name": "Styrene Acrylates Copolymer", "risk_level": "low", "category": "film former", "description": "Полимер"},
    
    # Загустители
    {"name": "Carbomer", "risk_level": "low", "category": "thickener", "description": "Загуститель"},
    {"name": "Xanthan Gum", "risk_level": "low", "category": "thickener", "description": "Натуральный загуститель"},
    {"name": "Hydroxyethylcellulose", "risk_level": "low", "category": "thickener", "description": "Загуститель"},
    {"name": "Acrylates/C10-30 Alkyl Acrylate Crosspolymer", "risk_level": "low", "category": "thickener", "description": "Загуститель"},
    
    # Пигменты
    {"name": "CI 77891", "risk_level": "low", "category": "pigment", "description": "Диоксид титана, белый пигмент"},
    {"name": "CI 77491", "risk_level": "low", "category": "pigment", "description": "Оксид железа, красный пигмент"},
    {"name": "CI 77492", "risk_level": "low", "category": "pigment", "description": "Оксид железа, желтый пигмент"},
    {"name": "CI 77499", "risk_level": "low", "category": "pigment", "description": "Оксид железа, черный пигмент"},
    {"name": "Mica", "risk_level": "low", "category": "pigment", "description": "Слюда, перламутровый пигмент"},
    
    # Дополнительные
    {"name": "Sorbic Acid", "risk_level": "low", "category": "preservative", "description": "Сорбиновая кислота"},
    {"name": "Dehydroacetic Acid", "risk_level": "low", "category": "preservative", "description": "Консервант"},
    {"name": "Benzalkonium Chloride", "risk_level": "medium", "category": "preservative", "description": "Консервант и антисептик"},
    {"name": "Chlorhexidine Digluconate", "risk_level": "medium", "category": "antiseptic", "description": "Антисептик"},
    
    # Протеины и экстракты
    {"name": "Hydrolyzed Silk Protein", "risk_level": "low", "category": "conditioning agent", "description": "Гидролизованный шелковый протеин"},
    {"name": "Hydrolyzed Wheat Protein", "risk_level": "low", "category": "conditioning agent", "description": "Гидролизованный пшеничный протеин"},
    {"name": "Hydrolyzed Collagen", "risk_level": "low", "category": "conditioning agent", "description": "Гидролизованный коллаген"},
    
    # Глюкозиды
    {"name": "Coco Glucoside", "risk_level": "low", "category": "surfactant", "description": "Мягкий ПАВ из кокосового масла"},
    {"name": "Lauryl Glucoside", "risk_level": "low", "category": "surfactant", "description": "Мягкий ПАВ"},
    
    # Соли и минералы
    {"name": "Sodium Chloride", "risk_level": "safe", "category": "viscosity controlling", "description": "Поваренная соль, загуститель"},
    {"name": "Magnesium Sulfate", "risk_level": "safe", "category": "viscosity controlling", "description": "Сульфат магния"},
    {"name": "Calcium Carbonate", "risk_level": "safe", "category": "abrasive", "description": "Карбонат кальция, абразив"},
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
        
        # 1. Добавление 100+ частых ингредиентов
        print("\n🧪 Добавление частых ингредиентов (100+)...")
        
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
                print(f"  ✅ Добавлен: {ingredient_data['name']}")
            else:
                # Обновляем существующий (если нужно)
                existing.risk_level = ingredient_data['risk_level']
                existing.category = ingredient_data['category']
                existing.description = ingredient_data['description']
                ingredients_updated += 1
                print(f"  🔄 Обновлен: {ingredient_data['name']}")
        
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
        
        # 3. Тестовые сканирования (если нужно)
        create_test_scans = False  # Поставьте True если нужны тестовые сканы
        
        if create_test_scans and test_user:
            print("\n🔍 Создание тестовых сканирований...")
            
            test_scans = [
                {
                    "text": "Состав: Aqua, Sodium Laureth Sulfate, Cocamidopropyl Betaine, Glycerin, Parfum, PEG-4 Cocoate, Styrene Acrylates Copolymer, Coco Glucoside, Tetrasodium EDTA, Hydrolyzed Silk Protein, Citric Acid, Methylchloroisothiazolinone/Methylisothiazolinone",
                    "title": "Крем-мыло мягкое",
                },
                {
                    "text": "Ingredients: Water, Formaldehyde, Alcohol Denat, Fragrance, Mineral Oil, Propylene Glycol",
                    "title": "Лосьон для тела",
                },
                {
                    "text": "INCI: Dimethicone, Cyclopentasiloxane, Oxybenzone, Avobenzone, Homosalate, Tocopherol",
                    "title": "Солнцезащитный крем",
                },
                {
                    "text": "Состав: Алое вера, Глицерин, Аллантоин, Пантенол, Салициловая кислота, Цинка оксид",
                    "title": "Натуральный крем",
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
                
                # Определяем статус безопасности
                safety_status = 'safe'
                if ingredients_for_json:
                    high_risk_count = sum(1 for ing in ingredients_for_json 
                                        if ing.get('risk_level') == 'high')
                    if high_risk_count > 0:
                        safety_status = 'danger'
                    else:
                        safety_status = 'warning'
                
                scan = Scan(
                    user_id=test_user.id,
                    input_type=random.choice(['manual', 'camera']),
                    input_method=random.choice(['text', 'device']),
                    original_text=test_data["text"],
                    safety_status=safety_status,
                    ingredients_detected=ingredients_for_json,
                    created_at=datetime.utcnow()
                )
                db.session.add(scan)
                scans_created += 1
                print(f"  📄 Создан тестовый скан #{i+1}")
            
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
        
        for risk, count in risk_stats:
            if risk:
                risk_icon = "🟢" if risk == "safe" else "🟡" if risk == "low" else "🟠" if risk == "medium" else "🔴"
                print(f"   {risk_icon} {risk}: {count}")
        
        print("\n" + "=" * 60)
        print("🎉 БАЗА ДАННЫХ ГОТОВА К РАБОТЕ!")
        print("=" * 60)
        
        print("\n🔧 ДЛЯ ЗАПУСКА:")
        print("   1. Запустите: python app.py")
        print("   2. Откройте: http://localhost:5000")
        print("   3. Войдите как: user@example.com / user123")
        
        print("\n📱 ТЕСТОВЫЕ УЧЕТНЫЕ ЗАПИСИ:")
        print("   👤 Пользователь: user@example.com / user123")
        print("   👑 Администратор: admin@cosmetics.com / admin123")
        
        print("\n⚠️  Для очистки базы данных:")
        print('   python -c "from app import app, db; with app.app_context(): db.drop_all(); db.create_all()"')
        
        print("\n🔗 API endpoints:")
        print("   /api/ingredients/count - количество ингредиентов")
        print("   /api/ingredients/list - список ингредиентов")
        print("   /api/analyze - анализ фото")
        print("   /api/analyze_text - анализ текста")
        
        return True

if __name__ == "__main__":
    seed_database()