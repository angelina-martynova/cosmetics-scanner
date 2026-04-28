# migrate_aliases.py
"""
Скрипт міграції хардкоджених словників у базу даних.

Переносить:
  1. COMMON_ALIASES (checker.py) → таблиця ingredient_aliases (alias_type='common')
  2. common_fixes (checker.py)   → таблиця ingredient_aliases (alias_type='ocr_fix' або 'translation')
  3. ewg_scores (checker.py)     → поле ingredients.ewg_score

Запуск:
  python migrate_aliases.py

Безпечно запускати повторно — пропускає вже існуючі записи.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# 1. COMMON_ALIASES — побутові синоніми, переклади, скорочення
# ═══════════════════════════════════════════════════════════════════
COMMON_ALIASES = {
    # --- Aqua / Вода ---
    "aqua":              {"target": "Aqua", "type": "inci",         "lang": "en"},
    "вода":              {"target": "Aqua", "type": "translation",  "lang": "uk"},
    "water":             {"target": "Aqua", "type": "inci",         "lang": "en"},
    "eau":               {"target": "Aqua", "type": "inci",         "lang": "fr"},
    "h2o":               {"target": "Aqua", "type": "abbreviation", "lang": None},
    "purified water":    {"target": "Aqua", "type": "inci",         "lang": "en"},
    "distilled water":   {"target": "Aqua", "type": "inci",         "lang": "en"},
    "deionized water":   {"target": "Aqua", "type": "inci",         "lang": "en"},
    "spring water":      {"target": "Aqua", "type": "inci",         "lang": "en"},

    # --- Glycerin ---
    "glycerin":          {"target": "Glycerin", "type": "inci",         "lang": "en"},
    "гліцерин":          {"target": "Glycerin", "type": "translation",  "lang": "uk"},
    "glycerol":          {"target": "Glycerin", "type": "inci",         "lang": "en"},
    "glycerine":         {"target": "Glycerin", "type": "inci",         "lang": "en"},
    "e422":              {"target": "Glycerin", "type": "e_code",       "lang": None},

    # --- Sodium Laureth Sulfate ---
    "sodium laureth sulfate":      {"target": "Sodium Laureth Sulfate", "type": "inci",        "lang": "en"},
    "sles":                        {"target": "Sodium Laureth Sulfate", "type": "abbreviation", "lang": None},
    "натрію лаурет сульфат":       {"target": "Sodium Laureth Sulfate", "type": "translation",  "lang": "uk"},
    "натрій лаурет сульфат":       {"target": "Sodium Laureth Sulfate", "type": "translation",  "lang": "uk"},

    # --- Sodium Lauryl Sulfate ---
    "sodium lauryl sulfate":       {"target": "Sodium Lauryl Sulfate", "type": "inci",        "lang": "en"},
    "sls":                         {"target": "Sodium Lauryl Sulfate", "type": "abbreviation", "lang": None},
    "натрію лауріл сульфат":       {"target": "Sodium Lauryl Sulfate", "type": "translation",  "lang": "uk"},
    "натрій лауріл сульфат":       {"target": "Sodium Lauryl Sulfate", "type": "translation",  "lang": "uk"},

    # --- Parfum ---
    "parfum":            {"target": "Parfum", "type": "inci",        "lang": "en"},
    "fragrance":         {"target": "Parfum", "type": "inci",        "lang": "en"},
    "aroma":             {"target": "Parfum", "type": "inci",        "lang": "en"},
    "perfume":           {"target": "Parfum", "type": "common",      "lang": "en"},
    "парфум":            {"target": "Parfum", "type": "translation",  "lang": "uk"},
    "ароматизатор":      {"target": "Parfum", "type": "translation",  "lang": "uk"},
    "отдушка":           {"target": "Parfum", "type": "translation",  "lang": "ru"},

    # --- Cocamidopropyl Betaine ---
    "cocamidopropyl betaine":      {"target": "Cocamidopropyl Betaine", "type": "inci",       "lang": "en"},
    "копамідопропіл бетаїн":       {"target": "Cocamidopropyl Betaine", "type": "translation", "lang": "uk"},
    "coco betaine":                {"target": "Cocamidopropyl Betaine", "type": "common",     "lang": "en"},

    # --- Phenoxyethanol ---
    "phenoxyethanol":    {"target": "Phenoxyethanol", "type": "inci",       "lang": "en"},
    "феноксиетанол":     {"target": "Phenoxyethanol", "type": "translation", "lang": "uk"},

    # --- Methylparaben ---
    "methylparaben":     {"target": "Methylparaben", "type": "inci",       "lang": "en"},
    "метилпарабен":      {"target": "Methylparaben", "type": "translation", "lang": "uk"},
    "e218":              {"target": "Methylparaben", "type": "e_code",     "lang": None},

    # --- Propylene Glycol ---
    "propylene glycol":  {"target": "Propylene Glycol", "type": "inci",        "lang": "en"},
    "пропіленгліколь":   {"target": "Propylene Glycol", "type": "translation",  "lang": "uk"},
    "пропілен гліколь":  {"target": "Propylene Glycol", "type": "translation",  "lang": "uk"},
    "pg":                {"target": "Propylene Glycol", "type": "abbreviation", "lang": None},

    # --- Alcohol Denat ---
    "alcohol denat":             {"target": "Alcohol Denat", "type": "inci",       "lang": "en"},
    "спирт денатурований":       {"target": "Alcohol Denat", "type": "translation", "lang": "uk"},
    "денатурований спирт":       {"target": "Alcohol Denat", "type": "translation", "lang": "uk"},

    # --- Dimethicone ---
    "dimethicone":       {"target": "Dimethicone", "type": "inci",       "lang": "en"},
    "диметикон":         {"target": "Dimethicone", "type": "translation", "lang": "uk"},
    "силікон":           {"target": "Dimethicone", "type": "common",     "lang": "uk"},

    # --- Mineral Oil ---
    "mineral oil":           {"target": "Mineral Oil", "type": "inci",       "lang": "en"},
    "парафінове масло":      {"target": "Mineral Oil", "type": "translation", "lang": "uk"},
    "paraffinum liquidum":   {"target": "Mineral Oil", "type": "inci",       "lang": "en"},

    # --- Titanium Dioxide ---
    "titanium dioxide":  {"target": "Titanium Dioxide", "type": "inci",       "lang": "en"},
    "діоксид титану":    {"target": "Titanium Dioxide", "type": "translation", "lang": "uk"},
    "ci 77891":          {"target": "Titanium Dioxide", "type": "abbreviation","lang": None},

    # --- Zinc Oxide ---
    "zinc oxide":        {"target": "Zinc Oxide", "type": "inci",       "lang": "en"},
    "оксид цинку":       {"target": "Zinc Oxide", "type": "translation", "lang": "uk"},

    # --- Tocopherol ---
    "tocopherol":        {"target": "Tocopherol", "type": "inci",       "lang": "en"},
    "токоферол":         {"target": "Tocopherol", "type": "translation", "lang": "uk"},
    "vitamin e":         {"target": "Tocopherol", "type": "common",     "lang": "en"},
    "вітамін е":         {"target": "Tocopherol", "type": "common",     "lang": "uk"},

    # --- Ascorbic Acid ---
    "ascorbic acid":         {"target": "Ascorbic Acid", "type": "inci",       "lang": "en"},
    "аскорбінова кислота":   {"target": "Ascorbic Acid", "type": "translation", "lang": "uk"},
    "vitamin c":             {"target": "Ascorbic Acid", "type": "common",     "lang": "en"},
    "вітамін с":             {"target": "Ascorbic Acid", "type": "common",     "lang": "uk"},

    # --- Retinol ---
    "retinol":           {"target": "Retinol", "type": "inci",       "lang": "en"},
    "ретинол":           {"target": "Retinol", "type": "translation", "lang": "uk"},
    "vitamin a":         {"target": "Retinol", "type": "common",     "lang": "en"},
    "вітамін а":         {"target": "Retinol", "type": "common",     "lang": "uk"},

    # --- Niacinamide ---
    "niacinamide":       {"target": "Niacinamide", "type": "inci",       "lang": "en"},
    "ніацинамід":        {"target": "Niacinamide", "type": "translation", "lang": "uk"},
    "nicotinamide":      {"target": "Niacinamide", "type": "inci",       "lang": "en"},

    # --- Salicylic Acid ---
    "salicylic acid":        {"target": "Salicylic Acid", "type": "inci",        "lang": "en"},
    "саліцилова кислота":    {"target": "Salicylic Acid", "type": "translation",  "lang": "uk"},
    "bha":                   {"target": "Salicylic Acid", "type": "abbreviation", "lang": None},

    # --- Hyaluronic Acid ---
    "hyaluronic acid":       {"target": "Hyaluronic Acid", "type": "inci",        "lang": "en"},
    "гіалуронова кислота":   {"target": "Hyaluronic Acid", "type": "translation",  "lang": "uk"},
    "sodium hyaluronate":    {"target": "Hyaluronic Acid", "type": "inci",        "lang": "en"},

    # --- Allantoin ---
    "allantoin":         {"target": "Allantoin", "type": "inci",       "lang": "en"},
    "алантоїн":          {"target": "Allantoin", "type": "translation", "lang": "uk"},

    # --- Panthenol ---
    "panthenol":         {"target": "Panthenol", "type": "inci",       "lang": "en"},
    "пантенол":          {"target": "Panthenol", "type": "translation", "lang": "uk"},

    # --- Aloe ---
    "aloe barbadensis leaf juice": {"target": "Aloe Barbadensis Leaf Juice", "type": "inci",       "lang": "en"},
    "сік алое вера":               {"target": "Aloe Barbadensis Leaf Juice", "type": "translation", "lang": "uk"},
    "aloe vera gel":               {"target": "Aloe Barbadensis Leaf Juice", "type": "common",     "lang": "en"},
}


# ═══════════════════════════════════════════════════════════════════
# 2. OCR-ВИПРАВЛЕННЯ та ПЕРЕКЛАДИ ОКРЕМИХ СЛІВ
#    (з checker.py → load_common_fixes)
#    Деякі є цілими інгредієнтами, деякі — частинами слів.
#    Ми беремо тільки ті, що є повними назвами інгредієнтів.
# ═══════════════════════════════════════════════════════════════════
OCR_FIXES_FULL_NAMES = {
    # OCR-спотворення цілих назв
    "methytisctvazuivare":          {"target": "Methylisothiazolinone",          "type": "ocr_fix"},
    "methylisothiazolino":          {"target": "Methylisothiazolinone",          "type": "ocr_fix"},
    "methylchloroiscthiazoline":    {"target": "Methylchloroisothiazolinone",    "type": "ocr_fix"},
    "methylchloroisothiazolino":    {"target": "Methylchloroisothiazolinone",    "type": "ocr_fix"},
    "methylchlorcisothiazoline":    {"target": "Methylchloroisothiazolinone",    "type": "ocr_fix"},
    "sodlum":                       {"target": "Sodium",                         "type": "ocr_fix"},
    "glycerln":                     {"target": "Glycerin",                       "type": "ocr_fix"},
    "parfume":                      {"target": "Parfum",                         "type": "ocr_fix"},
    "peg4":                         {"target": "PEG-4",                          "type": "ocr_fix"},
    "edta.":                        {"target": "EDTA",                           "type": "ocr_fix"},
    "hydrotyzed":                   {"target": "Hydrolyzed",                     "type": "ocr_fix"},
    "аqua":                         {"target": "Aqua",                           "type": "ocr_fix"},

    # Переклади цілих назв (uk → INCI)
    "тетрасодіум":       {"target": "Tetrasodium",         "type": "translation", "lang": "uk"},
    "едта":              {"target": "EDTA",                 "type": "translation", "lang": "uk"},
    "парфюм":            {"target": "Parfum",               "type": "translation", "lang": "ru"},
    "формалдегид":       {"target": "Formaldehyde",         "type": "translation", "lang": "uk"},
    "бензофенон":        {"target": "Oxybenzone",           "type": "translation", "lang": "uk"},
    "глицерина":         {"target": "Glycerin",             "type": "translation", "lang": "ru"},
    "полиэтиленгликоль": {"target": "Polyethylene Glycol",  "type": "translation", "lang": "ru"},
    "поліетиленгліколь":  {"target": "Polyethylene Glycol",  "type": "translation", "lang": "uk"},
    "триклозан":         {"target": "Triclosan",            "type": "translation", "lang": "uk"},
    "пропіленгліколь":   {"target": "Propylene Glycol",     "type": "translation", "lang": "uk"},
    "диметикон":         {"target": "Dimethicone",          "type": "translation", "lang": "uk"},
    "циклометикон":      {"target": "Cyclomethicone",       "type": "translation", "lang": "uk"},
    "вазелін":           {"target": "Petrolatum",           "type": "translation", "lang": "uk"},

    # Переклади назв олій та екстрактів
    "алое":              {"target": "Aloe",                 "type": "translation", "lang": "uk"},
    "алое вера":         {"target": "Aloe Vera",            "type": "translation", "lang": "uk"},
    "жожоба":            {"target": "Jojoba",               "type": "translation", "lang": "uk"},
    "аргана":            {"target": "Argan",                "type": "translation", "lang": "uk"},
    "шипшина":           {"target": "Rosehip",              "type": "translation", "lang": "uk"},
    "шипшини":           {"target": "Rosehip",              "type": "translation", "lang": "uk"},
    "кокосова":          {"target": "Coconut",              "type": "translation", "lang": "uk"},
    "соняшникова":       {"target": "Sunflower",            "type": "translation", "lang": "uk"},
    "оливкова":          {"target": "Olive",                "type": "translation", "lang": "uk"},
    "оливкове":          {"target": "Olive",                "type": "translation", "lang": "uk"},
    "ланолин":           {"target": "Lanolin",              "type": "translation", "lang": "uk"},

    # Переклади назв кислот
    "гліколева":         {"target": "Glycolic",             "type": "translation", "lang": "uk"},
    "молочна":           {"target": "Lactic",               "type": "translation", "lang": "uk"},
    "саліцилова":        {"target": "Salicylic",            "type": "translation", "lang": "uk"},
    "азелаїнова":        {"target": "Azelaic",              "type": "translation", "lang": "uk"},
    "гіалуронова":       {"target": "Hyaluronic",           "type": "translation", "lang": "uk"},
    "аскорбінова":       {"target": "Ascorbic",             "type": "translation", "lang": "uk"},
    "лимонна":           {"target": "Citric",               "type": "translation", "lang": "uk"},
    "сорбінова":         {"target": "Sorbic",               "type": "translation", "lang": "uk"},
    "бензойна":          {"target": "Benzoic",              "type": "translation", "lang": "uk"},

    # Переклади хімічних суфіксів / солей
    "сорбат":            {"target": "Sorbate",              "type": "translation", "lang": "uk"},
    "бензоат":           {"target": "Benzoate",             "type": "translation", "lang": "uk"},
    "цитрат":            {"target": "Citrate",              "type": "translation", "lang": "uk"},
    "стеарат":           {"target": "Stearate",             "type": "translation", "lang": "uk"},
    "пальмітат":         {"target": "Palmitate",            "type": "translation", "lang": "uk"},
    "лаурат":            {"target": "Laurate",              "type": "translation", "lang": "uk"},
    "олеат":             {"target": "Oleate",               "type": "translation", "lang": "uk"},
    "сульфат":           {"target": "Sulfate",              "type": "translation", "lang": "uk"},
    "хлорид":            {"target": "Chloride",             "type": "translation", "lang": "uk"},
    "гідроксид":         {"target": "Hydroxide",            "type": "translation", "lang": "uk"},
    "оксид":             {"target": "Oxide",                "type": "translation", "lang": "uk"},
    "діоксид":           {"target": "Dioxide",              "type": "translation", "lang": "uk"},
    "карбонат":          {"target": "Carbonate",            "type": "translation", "lang": "uk"},
    "фосфат":            {"target": "Phosphate",            "type": "translation", "lang": "uk"},
    "ацетат":            {"target": "Acetate",              "type": "translation", "lang": "uk"},
    "глюконат":          {"target": "Gluconate",            "type": "translation", "lang": "uk"},
    "лактат":            {"target": "Lactate",              "type": "translation", "lang": "uk"},
}


# ═══════════════════════════════════════════════════════════════════
# 3. EWG-ПОДІБНІ СКОРИ → поле ingredients.ewg_score
# ═══════════════════════════════════════════════════════════════════
EWG_SCORES = {
    "Oxybenzone": 8,
    "Benzophenone-3": 8,
    "Triclosan": 7,
    "Formaldehyde": 10,
    "DMDM Hydantoin": 8,
    "Quaternium-15": 8,
    "Methylisothiazolinone": 7,
    "Methylchloroisothiazolinone": 7,
    "Parfum": 8,
    "Fragrance": 8,
    "Sodium Laureth Sulfate": 3,
    "Sodium Lauryl Sulfate": 5,
    "Propylene Glycol": 4,
    "Phenoxyethanol": 4,
    "Mineral Oil": 2,
    "Dimethicone": 3,
    "Alcohol Denat": 6,
    "Talc": 4,
    "Retinol": 7,
    "Salicylic Acid": 4,
    "Titanium Dioxide": 2,
    "Zinc Oxide": 1,
    "Ascorbic Acid": 1,
    "Tocopherol": 1,
    "Niacinamide": 1,
    "Hyaluronic Acid": 1,
    "Aloe Barbadensis Leaf Juice": 1,
    "Squalane": 1,
}


# ═══════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ МІГРАЦІЇ
# ═══════════════════════════════════════════════════════════════════
def migrate():
    # Імпортуємо з нового models.py (має лежати поруч)
    # Якщо models.py ще не підключений до app.py — тимчасово імпортуємо старий app
    try:
        from models import db, Ingredient, IngredientAlias
    except ImportError:
        print("УВАГА: models.py не знайдено. Імпортую моделі зі старого app.py")
        from app import db, Ingredient
        # IngredientAlias може не існувати у старій версії
        try:
            from app import IngredientAlias
        except ImportError:
            print("ПОМИЛКА: таблиця IngredientAlias не існує. "
                  "Спочатку підключіть models.py до app.py і запустіть db.create_all()")
            return

    from app import app

    with app.app_context():
        # Переконуємось, що таблиці створені
        db.create_all()

        # --- Крок 1: Індекс існуючих інгредієнтів ---
        all_ingredients = Ingredient.query.all()
        name_to_ingredient = {ing.name.lower(): ing for ing in all_ingredients}
        print(f"Знайдено {len(name_to_ingredient)} інгредієнтів у БД")

        # --- Крок 2: Індекс існуючих аліасів ---
        existing_aliases = set()
        try:
            for alias in IngredientAlias.query.all():
                existing_aliases.add(alias.alias_lower)
        except Exception:
            pass
        print(f"Існуючих аліасів: {len(existing_aliases)}")

        # --- Крок 3: Міграція COMMON_ALIASES ---
        aliases_added = 0
        aliases_skipped = 0

        for alias_text, info in COMMON_ALIASES.items():
            alias_lower = alias_text.lower().strip()

            if alias_lower in existing_aliases:
                aliases_skipped += 1
                continue

            target_name = info["target"]
            target_lower = target_name.lower()

            ingredient = name_to_ingredient.get(target_lower)
            if not ingredient:
                # Спроба часткового збігу
                for name, ing in name_to_ingredient.items():
                    if target_lower in name or name in target_lower:
                        ingredient = ing
                        break

            if not ingredient:
                print(f"  ⚠ Цільовий інгредієнт '{target_name}' не знайдено в БД, пропускаю alias '{alias_text}'")
                aliases_skipped += 1
                continue

            new_alias = IngredientAlias(
                ingredient_id=ingredient.id,
                alias=alias_text,
                alias_lower=alias_lower,
                alias_type=info.get("type", "common"),
                language=info.get("lang"),
                created_at=datetime.utcnow(),
            )
            db.session.add(new_alias)
            existing_aliases.add(alias_lower)
            aliases_added += 1

        db.session.commit()
        print(f"COMMON_ALIASES: додано {aliases_added}, пропущено {aliases_skipped}")

        # --- Крок 4: Міграція OCR_FIXES ---
        ocr_added = 0
        ocr_skipped = 0

        for alias_text, info in OCR_FIXES_FULL_NAMES.items():
            alias_lower = alias_text.lower().strip()

            if alias_lower in existing_aliases:
                ocr_skipped += 1
                continue

            target_name = info["target"]
            target_lower = target_name.lower()

            ingredient = name_to_ingredient.get(target_lower)
            if not ingredient:
                for name, ing in name_to_ingredient.items():
                    if target_lower in name or name in target_lower:
                        ingredient = ing
                        break

            if not ingredient:
                # Для OCR-фіксів та перекладів окремих слів (Sulfate, Chloride тощо)
                # це нормально — вони не є повними назвами інгредієнтів
                ocr_skipped += 1
                continue

            alias_type = info.get("type", "ocr_fix")
            lang = info.get("lang")

            new_alias = IngredientAlias(
                ingredient_id=ingredient.id,
                alias=alias_text,
                alias_lower=alias_lower,
                alias_type=alias_type,
                language=lang,
                created_at=datetime.utcnow(),
            )
            db.session.add(new_alias)
            existing_aliases.add(alias_lower)
            ocr_added += 1

        db.session.commit()
        print(f"OCR_FIXES: додано {ocr_added}, пропущено {ocr_skipped}")

        # --- Крок 5: Міграція EWG Scores ---
        ewg_updated = 0
        ewg_skipped = 0

        for ingredient_name, score in EWG_SCORES.items():
            target_lower = ingredient_name.lower()
            ingredient = name_to_ingredient.get(target_lower)

            if not ingredient:
                ewg_skipped += 1
                continue

            if ingredient.ewg_score is None or ingredient.ewg_score != score:
                ingredient.ewg_score = score
                if not ingredient.source_of_risk_assessment:
                    ingredient.source_of_risk_assessment = "EWG"
                ewg_updated += 1
            else:
                ewg_skipped += 1

        db.session.commit()
        print(f"EWG Scores: оновлено {ewg_updated}, пропущено {ewg_skipped}")

        # --- Фінальна статистика ---
        total_aliases = IngredientAlias.query.count()
        total_with_ewg = Ingredient.query.filter(Ingredient.ewg_score.isnot(None)).count()

        print("\n" + "=" * 60)
        print("МІГРАЦІЯ ЗАВЕРШЕНА")
        print(f"  Аліасів у БД:                {total_aliases}")
        print(f"  Інгредієнтів з EWG-скором:   {total_with_ewg}")
        print("=" * 60)

        # Приклад перевірки
        print("\nПриклад: аліаси для 'Glycerin':")
        glycerin = name_to_ingredient.get("glycerin")
        if glycerin:
            for alias in glycerin.aliases.all():
                print(f"  '{alias.alias}' (тип: {alias.alias_type}, мова: {alias.language})")


if __name__ == "__main__":
    migrate()
