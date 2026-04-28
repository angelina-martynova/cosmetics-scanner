# seed_ingredients.py (v2 — розширений)
"""
Скрипт для наповнення бази даних інгредієнтів.

Версія 2 — заповнює розширені поля моделі Ingredient:
  inci_name, cas_number, ewg_score, eu_max_concentration,
  eu_regulation_annex, is_banned_eu, description_en,
  source_of_risk_assessment, verified.

Запуск:
  python seed_ingredients.py

Безпечно для повторного запуску — оновлює існуючі записи.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

# ═══════════════════════════════════════════════════════════════════
# СПИСОК ІНГРЕДІЄНТІВ (з розширеними полями)
#
# Кожен запис може мати:
#   name               — основна назва (required, unique)
#   inci_name          — канонічна INCI-назва (якщо відрізняється)
#   risk_level         — safe / low / medium / high
#   category           — функціональна категорія
#   description        — опис українською
#   description_en     — опис англійською
#   cas_number         — CAS Registry Number
#   ewg_score          — EWG Skin Deep Score (1-10)
#   eu_max_concentration — максимальна концентрація за EU Reg. 1223/2009
#   eu_regulation_annex  — II (заборонено), III-VI (обмеження)
#   is_banned_eu       — True якщо заборонено в ЄС
#   source_of_risk_assessment — джерело оцінки
# ═══════════════════════════════════════════════════════════════════

INGREDIENTS = [
    # ══════════════════════════════════════════════════════════
    # ВОДА ТА ОСНОВИ
    # ══════════════════════════════════════════════════════════
    {"name": "Aqua", "inci_name": "Aqua", "risk_level": "safe", "category": "solvent",
     "description": "Вода, основа косметичних засобів (INCI: Aqua)",
     "description_en": "Water, base of cosmetic products",
     "cas_number": "7732-18-5", "ewg_score": 1,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Water", "inci_name": "Aqua", "risk_level": "safe", "category": "solvent",
     "description": "Очищена вода",
     "description_en": "Purified water",
     "cas_number": "7732-18-5", "ewg_score": 1},

    # ══════════════════════════════════════════════════════════
    # ЗВОЛОЖУВАЧІ (HUMECTANTS)
    # ══════════════════════════════════════════════════════════
    {"name": "Glycerin", "inci_name": "Glycerin", "risk_level": "low", "category": "humectant",
     "description": "Гліцерин, натуральний зволожувач, безпечний та ефективний",
     "description_en": "Glycerin, natural humectant, safe and effective",
     "cas_number": "56-81-5", "ewg_score": 1,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Sorbitol", "inci_name": "Sorbitol", "risk_level": "low", "category": "humectant",
     "description": "Зволожувач, гумектант",
     "description_en": "Humectant, moisturizing agent",
     "cas_number": "50-70-4", "ewg_score": 1},

    {"name": "Hyaluronic Acid", "inci_name": "Hyaluronic Acid", "risk_level": "safe", "category": "active",
     "description": "Гіалуронова кислота, потужний зволожувач, утримує вологу у шкірі",
     "description_en": "Hyaluronic acid, powerful humectant, retains moisture in skin",
     "cas_number": "9004-61-9", "ewg_score": 1,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Sodium Hyaluronate", "inci_name": "Sodium Hyaluronate", "risk_level": "safe", "category": "active",
     "description": "Сіль гіалуронової кислоти, легше проникає у шкіру",
     "description_en": "Sodium salt of hyaluronic acid, better skin penetration",
     "cas_number": "9067-32-7", "ewg_score": 1},

    {"name": "Urea", "inci_name": "Urea", "risk_level": "low", "category": "humectant",
     "description": "Сечовина, зволожувач та кератолітик",
     "description_en": "Urea, humectant and keratolytic agent",
     "cas_number": "57-13-6", "ewg_score": 1},

    # ══════════════════════════════════════════════════════════
    # ПАВ (SURFACTANTS)
    # ══════════════════════════════════════════════════════════

    # Аніонні (агресивніші)
    {"name": "Sodium Laureth Sulfate", "inci_name": "Sodium Laureth Sulfate",
     "risk_level": "medium", "category": "surfactant",
     "description": "SLES, піноутворювач, може висушувати шкіру при частому використанні",
     "description_en": "SLES, foaming agent, may dry skin with frequent use",
     "cas_number": "9004-82-4", "ewg_score": 3,
     "source_of_risk_assessment": "EWG"},

    {"name": "Sodium Lauryl Sulfate", "inci_name": "Sodium Lauryl Sulfate",
     "risk_level": "medium", "category": "surfactant",
     "description": "SLS, агресивніший за SLES, може подразнювати шкіру",
     "description_en": "SLS, more aggressive than SLES, can irritate skin",
     "cas_number": "151-21-3", "ewg_score": 5,
     "source_of_risk_assessment": "EWG"},

    {"name": "Ammonium Lauryl Sulfate", "inci_name": "Ammonium Lauryl Sulfate",
     "risk_level": "medium", "category": "surfactant",
     "description": "ALS, аналог SLS з амонієм",
     "description_en": "ALS, ammonium analog of SLS",
     "cas_number": "2235-54-3", "ewg_score": 4},

    # М'які ПАВ
    {"name": "Cocamidopropyl Betaine", "inci_name": "Cocamidopropyl Betaine",
     "risk_level": "low", "category": "surfactant",
     "description": "М'який ПАВ з кокосової олії, підходить для чутливої шкіри",
     "description_en": "Mild coconut-derived surfactant, suitable for sensitive skin",
     "cas_number": "61789-40-0", "ewg_score": 1,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Decyl Glucoside", "inci_name": "Decyl Glucoside",
     "risk_level": "low", "category": "surfactant",
     "description": "Натуральний м'який ПАВ з кокосової олії та кукурудзи",
     "description_en": "Natural mild surfactant from coconut oil and corn",
     "cas_number": "68515-73-1", "ewg_score": 1},

    {"name": "Coco Glucoside", "inci_name": "Coco-Glucoside",
     "risk_level": "low", "category": "surfactant",
     "description": "Глюкозид з кокосової олії, біорозкладний",
     "description_en": "Coconut-derived glucoside, biodegradable",
     "cas_number": "110615-47-9", "ewg_score": 1},

    {"name": "Sodium Cocoyl Isethionate", "inci_name": "Sodium Cocoyl Isethionate",
     "risk_level": "low", "category": "surfactant",
     "description": "Дуже м'який ПАВ для делікатних засобів",
     "description_en": "Very mild surfactant for delicate products",
     "cas_number": "61789-32-0", "ewg_score": 1},

    {"name": "Sodium Lauroyl Sarcosinate", "inci_name": "Sodium Lauroyl Sarcosinate",
     "risk_level": "low", "category": "surfactant",
     "description": "М'який аніонний ПАВ, підходить для чутливої шкіри",
     "description_en": "Mild anionic surfactant, suitable for sensitive skin",
     "cas_number": "137-16-6", "ewg_score": 1},

    # ══════════════════════════════════════════════════════════
    # КОНСЕРВАНТИ (PRESERVATIVES)
    # ══════════════════════════════════════════════════════════

    # --- ВИСОКИЙ РИЗИК (заборонені або сильно обмежені в ЄС) ---
    {"name": "Formaldehyde", "inci_name": "Formaldehyde",
     "risk_level": "high", "category": "preservative",
     "description": "Канцероген, заборонений як консервант у ЄС (Annex II)",
     "description_en": "Carcinogen, banned as preservative in EU (Annex II)",
     "cas_number": "50-00-0", "ewg_score": 10,
     "is_banned_eu": True, "eu_regulation_annex": "II",
     "source_of_risk_assessment": "SCCS"},

    {"name": "Methylisothiazolinone", "inci_name": "Methylisothiazolinone",
     "risk_level": "high", "category": "preservative",
     "description": "MIT, сильний алерген, заборонений у незмивних засобах в ЄС з 2017",
     "description_en": "MIT, strong allergen, banned in leave-on products in EU since 2017",
     "cas_number": "2682-20-4", "ewg_score": 7,
     "eu_max_concentration": "0.0015% (тільки rinse-off)", "eu_regulation_annex": "V",
     "source_of_risk_assessment": "SCCS"},

    {"name": "Methylchloroisothiazolinone", "inci_name": "Methylchloroisothiazolinone",
     "risk_level": "high", "category": "preservative",
     "description": "MCI, сильний алерген, часто в комбінації з MIT",
     "description_en": "MCI, strong allergen, often combined with MIT",
     "cas_number": "26172-55-4", "ewg_score": 7,
     "eu_max_concentration": "0.0015% (MCI/MI 3:1, тільки rinse-off)", "eu_regulation_annex": "V",
     "source_of_risk_assessment": "SCCS"},

    {"name": "DMDM Hydantoin", "inci_name": "DMDM Hydantoin",
     "risk_level": "high", "category": "preservative",
     "description": "Виділяє формальдегід, алерген",
     "description_en": "Formaldehyde releaser, allergen",
     "cas_number": "6440-58-0", "ewg_score": 8,
     "source_of_risk_assessment": "EWG"},

    {"name": "Quaternium-15", "inci_name": "Quaternium-15",
     "risk_level": "high", "category": "preservative",
     "description": "Виділяє формальдегід",
     "description_en": "Formaldehyde releaser",
     "cas_number": "4080-31-3", "ewg_score": 8,
     "source_of_risk_assessment": "EWG"},

    {"name": "Imidazolidinyl Urea", "inci_name": "Imidazolidinyl Urea",
     "risk_level": "high", "category": "preservative",
     "description": "Виділяє формальдегід",
     "description_en": "Formaldehyde releaser",
     "cas_number": "39236-46-9", "ewg_score": 7},

    {"name": "Diazolidinyl Urea", "inci_name": "Diazolidinyl Urea",
     "risk_level": "high", "category": "preservative",
     "description": "Виділяє формальдегід",
     "description_en": "Formaldehyde releaser",
     "cas_number": "78491-02-8", "ewg_score": 7},

    {"name": "Triclosan", "inci_name": "Triclosan",
     "risk_level": "high", "category": "preservative",
     "description": "Антибактеріальний засіб, заборонений у деяких країнах, ендокринний дисраптор",
     "description_en": "Antibacterial agent, banned in some countries, endocrine disruptor",
     "cas_number": "3380-34-5", "ewg_score": 7,
     "is_banned_eu": True, "eu_regulation_annex": "II",
     "source_of_risk_assessment": "SCCS"},

    # --- ПОМІРНИЙ РИЗИК ---
    {"name": "Methylparaben", "inci_name": "Methylparaben",
     "risk_level": "medium", "category": "preservative",
     "description": "Парабен, дозволений в ЄС до 0.4%, дискусії щодо гормонального впливу",
     "description_en": "Paraben, allowed in EU up to 0.4%, debated hormonal effects",
     "cas_number": "99-76-3", "ewg_score": 4,
     "eu_max_concentration": "0.4% (окремо), 0.8% (суміш)", "eu_regulation_annex": "V",
     "source_of_risk_assessment": "SCCS"},

    {"name": "Propylparaben", "inci_name": "Propylparaben",
     "risk_level": "medium", "category": "preservative",
     "description": "Парабен, дозволений в ЄС до 0.14%",
     "description_en": "Paraben, allowed in EU up to 0.14%",
     "cas_number": "94-13-3", "ewg_score": 5,
     "eu_max_concentration": "0.14%", "eu_regulation_annex": "V",
     "source_of_risk_assessment": "SCCS"},

    {"name": "Butylparaben", "inci_name": "Butylparaben",
     "risk_level": "medium", "category": "preservative",
     "description": "Парабен, обмежений в ЄС до 0.14%",
     "description_en": "Paraben, restricted in EU to 0.14%",
     "cas_number": "94-26-8", "ewg_score": 6,
     "eu_max_concentration": "0.14%", "eu_regulation_annex": "V",
     "source_of_risk_assessment": "SCCS"},

    {"name": "Phenoxyethanol", "inci_name": "Phenoxyethanol",
     "risk_level": "medium", "category": "preservative",
     "description": "Широко використовуваний консервант, обмежений до 1% в ЄС",
     "description_en": "Widely used preservative, limited to 1% in EU",
     "cas_number": "122-99-6", "ewg_score": 4,
     "eu_max_concentration": "1%", "eu_regulation_annex": "V",
     "source_of_risk_assessment": "SCCS"},

    {"name": "Benzyl Alcohol", "inci_name": "Benzyl Alcohol",
     "risk_level": "medium", "category": "preservative",
     "description": "Консервант та розчинник, може подразнювати чутливу шкіру",
     "description_en": "Preservative and solvent, may irritate sensitive skin",
     "cas_number": "100-51-6", "ewg_score": 3,
     "eu_max_concentration": "1%", "eu_regulation_annex": "V"},

    # --- НИЗЬКИЙ РИЗИК ---
    {"name": "Potassium Sorbate", "inci_name": "Potassium Sorbate",
     "risk_level": "low", "category": "preservative",
     "description": "Сіль сорбінової кислоти, харчовий консервант",
     "description_en": "Potassium salt of sorbic acid, food-grade preservative",
     "cas_number": "24634-61-5", "ewg_score": 1,
     "eu_max_concentration": "0.6%", "eu_regulation_annex": "V"},

    {"name": "Sodium Benzoate", "inci_name": "Sodium Benzoate",
     "risk_level": "low", "category": "preservative",
     "description": "Консервант, дозволений у косметиці до 0.5%",
     "description_en": "Preservative, allowed in cosmetics up to 0.5%",
     "cas_number": "532-32-1", "ewg_score": 1,
     "eu_max_concentration": "2.5% (0.5% для кислоти)", "eu_regulation_annex": "V"},

    {"name": "Ethylhexylglycerin", "inci_name": "Ethylhexylglycerin",
     "risk_level": "low", "category": "preservative",
     "description": "Консервант-бустер та пом'якшувач шкіри",
     "description_en": "Preservative booster and skin conditioner",
     "cas_number": "70445-33-9", "ewg_score": 1},

    # ══════════════════════════════════════════════════════════
    # АРОМАТИЗАТОРИ (FRAGRANCE)
    # ══════════════════════════════════════════════════════════
    {"name": "Parfum", "inci_name": "Parfum",
     "risk_level": "medium", "category": "fragrance",
     "description": "Ароматизатор. Може містити алергени. Присутній у 80% косметики.",
     "description_en": "Fragrance. May contain allergens. Present in 80% of cosmetics.",
     "ewg_score": 8,
     "source_of_risk_assessment": "EWG"},

    {"name": "Limonene", "inci_name": "Limonene",
     "risk_level": "medium", "category": "fragrance",
     "description": "Ароматичне з'єднання, алерген, окислюється на повітрі",
     "description_en": "Aromatic compound, allergen, oxidizes in air",
     "cas_number": "5989-27-5", "ewg_score": 4,
     "eu_regulation_annex": "III",
     "source_of_risk_assessment": "SCCS"},

    {"name": "Linalool", "inci_name": "Linalool",
     "risk_level": "medium", "category": "fragrance",
     "description": "Ароматичне з'єднання, алерген при окисленні",
     "description_en": "Aromatic compound, allergen when oxidized",
     "cas_number": "78-70-6", "ewg_score": 4,
     "eu_regulation_annex": "III"},

    {"name": "Citronellol", "inci_name": "Citronellol",
     "risk_level": "medium", "category": "fragrance",
     "description": "Ароматичне з'єднання, алерген",
     "description_en": "Aromatic compound, allergen",
     "cas_number": "106-22-9", "ewg_score": 4,
     "eu_regulation_annex": "III"},

    {"name": "Geraniol", "inci_name": "Geraniol",
     "risk_level": "medium", "category": "fragrance",
     "description": "Ароматичне з'єднання, алерген",
     "description_en": "Aromatic compound, allergen",
     "cas_number": "106-24-1", "ewg_score": 4,
     "eu_regulation_annex": "III"},

    # ══════════════════════════════════════════════════════════
    # РОЗЧИННИКИ ТА СПИРТИ
    # ══════════════════════════════════════════════════════════
    {"name": "Alcohol Denat", "inci_name": "Alcohol Denat.",
     "risk_level": "medium", "category": "solvent",
     "description": "Денатурований спирт. Висушує шкіру, може порушувати бар'єр.",
     "description_en": "Denatured alcohol. Dries skin, may disrupt barrier.",
     "cas_number": "64-17-5", "ewg_score": 6,
     "source_of_risk_assessment": "EWG"},

    {"name": "Propylene Glycol", "inci_name": "Propylene Glycol",
     "risk_level": "medium", "category": "solvent",
     "description": "Розчинник та зволожувач. Може подразнювати чутливу шкіру.",
     "description_en": "Solvent and humectant. May irritate sensitive skin.",
     "cas_number": "57-55-6", "ewg_score": 4,
     "source_of_risk_assessment": "EWG"},

    {"name": "Butylene Glycol", "inci_name": "Butylene Glycol",
     "risk_level": "low", "category": "solvent",
     "description": "Розчинник, м'якіший ніж пропіленгліколь",
     "description_en": "Solvent, milder than propylene glycol",
     "cas_number": "107-88-0", "ewg_score": 1},

    # ══════════════════════════════════════════════════════════
    # ЕМОЛЄНТИ ТА СИЛІКОНИ
    # ══════════════════════════════════════════════════════════
    {"name": "Dimethicone", "inci_name": "Dimethicone",
     "risk_level": "low", "category": "emollient",
     "description": "Силікон, створює захисну плівку, некомедогенний",
     "description_en": "Silicone, creates protective film, non-comedogenic",
     "cas_number": "9006-65-9", "ewg_score": 3,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Mineral Oil", "inci_name": "Paraffinum Liquidum",
     "risk_level": "low", "category": "emollient",
     "description": "Мінеральна олія, окклюзійний агент",
     "description_en": "Mineral oil, occlusive agent",
     "cas_number": "8042-47-5", "ewg_score": 2,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Squalane", "inci_name": "Squalane",
     "risk_level": "safe", "category": "emollient",
     "description": "Сквалан, біоідентичний емолєнт, відмінна переносимість",
     "description_en": "Squalane, bio-identical emollient, excellent tolerance",
     "cas_number": "111-01-3", "ewg_score": 1},

    {"name": "Caprylic/Capric Triglyceride", "inci_name": "Caprylic/Capric Triglyceride",
     "risk_level": "safe", "category": "emollient",
     "description": "Тригліцерид кокосової олії, м'який емолєнт",
     "description_en": "Coconut-derived triglyceride, gentle emollient",
     "cas_number": "65381-09-1", "ewg_score": 1},

    {"name": "Isopropyl Myristate", "inci_name": "Isopropyl Myristate",
     "risk_level": "low", "category": "emollient",
     "description": "Емолєнт та пенетрант, може бути комедогенним",
     "description_en": "Emollient and penetrant, may be comedogenic",
     "cas_number": "110-27-0", "ewg_score": 2},

    # ══════════════════════════════════════════════════════════
    # УФ-ФІЛЬТРИ
    # ══════════════════════════════════════════════════════════
    {"name": "Titanium Dioxide", "inci_name": "Titanium Dioxide",
     "risk_level": "low", "category": "UV filter",
     "description": "Мінеральний УФ-фільтр, фізичний захист від сонця",
     "description_en": "Mineral UV filter, physical sun protection",
     "cas_number": "13463-67-7", "ewg_score": 2,
     "eu_max_concentration": "25%", "eu_regulation_annex": "VI",
     "source_of_risk_assessment": "SCCS"},

    {"name": "Zinc Oxide", "inci_name": "Zinc Oxide",
     "risk_level": "safe", "category": "UV filter",
     "description": "Мінеральний УФ-фільтр, широкий спектр, безпечний",
     "description_en": "Mineral UV filter, broad spectrum, safe",
     "cas_number": "1314-13-2", "ewg_score": 1,
     "eu_max_concentration": "25%", "eu_regulation_annex": "VI",
     "source_of_risk_assessment": "SCCS"},

    {"name": "Oxybenzone", "inci_name": "Benzophenone-3",
     "risk_level": "high", "category": "UV filter",
     "description": "Хімічний УФ-фільтр, ендокринний дисраптор, шкідливий для коралів",
     "description_en": "Chemical UV filter, endocrine disruptor, harmful to coral",
     "cas_number": "131-57-7", "ewg_score": 8,
     "eu_max_concentration": "6%", "eu_regulation_annex": "VI",
     "source_of_risk_assessment": "SCCS"},

    # ══════════════════════════════════════════════════════════
    # АКТИВНІ КОМПОНЕНТИ
    # ══════════════════════════════════════════════════════════
    {"name": "Niacinamide", "inci_name": "Niacinamide",
     "risk_level": "safe", "category": "active",
     "description": "Вітамін B3, зменшує пори, вирівнює тон шкіри, зміцнює бар'єр",
     "description_en": "Vitamin B3, minimizes pores, evens skin tone, strengthens barrier",
     "cas_number": "98-92-0", "ewg_score": 1,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Retinol", "inci_name": "Retinol",
     "risk_level": "medium", "category": "active",
     "description": "Вітамін А, антивіковий, стимулює оновлення клітин, може подразнювати",
     "description_en": "Vitamin A, anti-aging, stimulates cell renewal, can irritate",
     "cas_number": "68-26-8", "ewg_score": 7,
     "source_of_risk_assessment": "SCCS"},

    {"name": "Ascorbic Acid", "inci_name": "Ascorbic Acid",
     "risk_level": "safe", "category": "active",
     "description": "Вітамін C, антиоксидант, освітлює шкіру, стимулює колаген",
     "description_en": "Vitamin C, antioxidant, brightens skin, stimulates collagen",
     "cas_number": "50-81-7", "ewg_score": 1,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Tocopherol", "inci_name": "Tocopherol",
     "risk_level": "safe", "category": "active",
     "description": "Вітамін E, антиоксидант, захищає від вільних радикалів",
     "description_en": "Vitamin E, antioxidant, protects against free radicals",
     "cas_number": "59-02-9", "ewg_score": 1,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Salicylic Acid", "inci_name": "Salicylic Acid",
     "risk_level": "low", "category": "active",
     "description": "BHA, відлущувач, проникає в пори, для проблемної шкіри",
     "description_en": "BHA, exfoliant, penetrates pores, for acne-prone skin",
     "cas_number": "69-72-7", "ewg_score": 4,
     "eu_max_concentration": "2% (0.5% в rinse-off для дітей до 3р)", "eu_regulation_annex": "III",
     "source_of_risk_assessment": "SCCS"},

    {"name": "Glycolic Acid", "inci_name": "Glycolic Acid",
     "risk_level": "low", "category": "active",
     "description": "AHA, відлущувач, вирівнює текстуру шкіри",
     "description_en": "AHA, exfoliant, smooths skin texture",
     "cas_number": "79-14-1", "ewg_score": 4,
     "source_of_risk_assessment": "SCCS"},

    {"name": "Lactic Acid", "inci_name": "Lactic Acid",
     "risk_level": "low", "category": "active",
     "description": "AHA, м'який відлущувач, зволожує",
     "description_en": "AHA, gentle exfoliant, moisturizing",
     "cas_number": "50-21-5", "ewg_score": 3},

    {"name": "Allantoin", "inci_name": "Allantoin",
     "risk_level": "safe", "category": "active",
     "description": "Заспокоює, пом'якшує, стимулює загоєння",
     "description_en": "Soothes, softens, stimulates healing",
     "cas_number": "97-59-6", "ewg_score": 1,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Panthenol", "inci_name": "Panthenol",
     "risk_level": "safe", "category": "active",
     "description": "Провітамін B5, зволожує, заспокоює, відновлює",
     "description_en": "Provitamin B5, moisturizes, soothes, repairs",
     "cas_number": "81-13-0", "ewg_score": 1,
     "source_of_risk_assessment": "CosIng"},

    {"name": "Bisabolol", "inci_name": "Alpha-Bisabolol",
     "risk_level": "safe", "category": "active",
     "description": "Протизапальний, заспокійливий компонент з ромашки",
     "description_en": "Anti-inflammatory, soothing component from chamomile",
     "cas_number": "515-69-5", "ewg_score": 1},

    {"name": "Centella Asiatica Extract", "inci_name": "Centella Asiatica Extract",
     "risk_level": "safe", "category": "plant extract",
     "description": "Екстракт центели, загоює, зміцнює бар'єр шкіри",
     "description_en": "Centella extract, heals, strengthens skin barrier",
     "cas_number": "84696-21-9", "ewg_score": 1},

    # ══════════════════════════════════════════════════════════
    # РОСЛИННІ ОЛІЇ ТА ЕКСТРАКТИ
    # ══════════════════════════════════════════════════════════
    {"name": "Aloe Barbadensis Leaf Juice", "inci_name": "Aloe Barbadensis Leaf Juice",
     "risk_level": "safe", "category": "plant extract",
     "description": "Сік алое вера, зволожує та заспокоює подразнену шкіру",
     "description_en": "Aloe vera juice, moisturizes and soothes irritated skin",
     "cas_number": "85507-69-3", "ewg_score": 1},

    {"name": "Shea Butter", "inci_name": "Butyrospermum Parkii Butter",
     "risk_level": "safe", "category": "emollient",
     "description": "Масло ши, живить та пом'якшує шкіру",
     "description_en": "Shea butter, nourishes and softens skin",
     "cas_number": "194043-92-0", "ewg_score": 1},

    {"name": "Jojoba Oil", "inci_name": "Simmondsia Chinensis Seed Oil",
     "risk_level": "safe", "category": "emollient",
     "description": "Олія жожоба, за складом близька до шкірного себуму",
     "description_en": "Jojoba oil, composition similar to skin sebum",
     "cas_number": "61789-91-1", "ewg_score": 1},

    {"name": "Argan Oil", "inci_name": "Argania Spinosa Kernel Oil",
     "risk_level": "safe", "category": "emollient",
     "description": "Арганова олія, живить, відновлює, антиоксидант",
     "description_en": "Argan oil, nourishing, restorative, antioxidant",
     "cas_number": "223747-87-1", "ewg_score": 1},

    {"name": "Coconut Oil", "inci_name": "Cocos Nucifera Oil",
     "risk_level": "safe", "category": "emollient",
     "description": "Кокосова олія, зволожує, може бути комедогенною",
     "description_en": "Coconut oil, moisturizing, may be comedogenic",
     "cas_number": "8001-31-8", "ewg_score": 1},

    # ══════════════════════════════════════════════════════════
    # ЕМУЛЬГАТОРИ
    # ══════════════════════════════════════════════════════════
    {"name": "Cetearyl Alcohol", "inci_name": "Cetearyl Alcohol",
     "risk_level": "low", "category": "emulsifier",
     "description": "Жирний спирт, емульгатор та загущувач, не висушує шкіру",
     "description_en": "Fatty alcohol, emulsifier and thickener, does not dry skin",
     "cas_number": "67762-27-0", "ewg_score": 1},

    {"name": "Glyceryl Stearate", "inci_name": "Glyceryl Stearate",
     "risk_level": "low", "category": "emulsifier",
     "description": "Емульгатор з гліцерину та стеаринової кислоти",
     "description_en": "Emulsifier from glycerin and stearic acid",
     "cas_number": "31566-31-1", "ewg_score": 1},

    {"name": "Cetyl Alcohol", "inci_name": "Cetyl Alcohol",
     "risk_level": "low", "category": "emulsifier",
     "description": "Жирний спирт, загущувач та пом'якшувач",
     "description_en": "Fatty alcohol, thickener and emollient",
     "cas_number": "36653-82-4", "ewg_score": 1},

    {"name": "Stearic Acid", "inci_name": "Stearic Acid",
     "risk_level": "low", "category": "emulsifier",
     "description": "Стеаринова кислота, емульгатор та загущувач",
     "description_en": "Stearic acid, emulsifier and thickener",
     "cas_number": "57-11-4", "ewg_score": 1},

    # ══════════════════════════════════════════════════════════
    # ЗАГУЩУВАЧІ ТА ПОЛІМЕРИ
    # ══════════════════════════════════════════════════════════
    {"name": "Carbomer", "inci_name": "Carbomer",
     "risk_level": "low", "category": "thickener",
     "description": "Полімер, загущувач та стабілізатор гелів",
     "description_en": "Polymer, thickener and gel stabilizer",
     "cas_number": "9003-01-4", "ewg_score": 1},

    {"name": "Xanthan Gum", "inci_name": "Xanthan Gum",
     "risk_level": "safe", "category": "thickener",
     "description": "Натуральний загущувач, отримують ферментацією",
     "description_en": "Natural thickener, produced by fermentation",
     "cas_number": "11138-66-2", "ewg_score": 1},

    {"name": "Hydroxyethylcellulose", "inci_name": "Hydroxyethylcellulose",
     "risk_level": "low", "category": "thickener",
     "description": "Целюлозний загущувач",
     "description_en": "Cellulose-based thickener",
     "cas_number": "9004-62-0", "ewg_score": 1},

    # ══════════════════════════════════════════════════════════
    # ХЕЛАТУЮЧІ АГЕНТИ ТА pH-РЕГУЛЯТОРИ
    # ══════════════════════════════════════════════════════════
    {"name": "Disodium EDTA", "inci_name": "Disodium EDTA",
     "risk_level": "low", "category": "chelating agent",
     "description": "Хелатуючий агент, зв'язує іони металів",
     "description_en": "Chelating agent, binds metal ions",
     "cas_number": "139-33-3", "ewg_score": 1},

    {"name": "Citric Acid", "inci_name": "Citric Acid",
     "risk_level": "safe", "category": "pH adjuster",
     "description": "Лимонна кислота, регулятор pH",
     "description_en": "Citric acid, pH adjuster",
     "cas_number": "77-92-9", "ewg_score": 1},

    {"name": "Sodium Hydroxide", "inci_name": "Sodium Hydroxide",
     "risk_level": "low", "category": "pH adjuster",
     "description": "Натрій гідроксид, регулятор pH (у малих концентраціях безпечний)",
     "description_en": "Sodium hydroxide, pH adjuster (safe at low concentrations)",
     "cas_number": "1310-73-2", "ewg_score": 2},

    # ══════════════════════════════════════════════════════════
    # БАРВНИКИ (COLORANTS)
    # ══════════════════════════════════════════════════════════
    {"name": "CI 77891", "inci_name": "CI 77891",
     "risk_level": "low", "category": "colorant",
     "description": "Діоксид титану (як барвник)",
     "description_en": "Titanium dioxide (as colorant)",
     "cas_number": "13463-67-7", "ewg_score": 2,
     "eu_regulation_annex": "IV"},

    {"name": "CI 77491", "inci_name": "CI 77491",
     "risk_level": "low", "category": "colorant",
     "description": "Оксид заліза (червоний)",
     "description_en": "Iron oxide (red)",
     "cas_number": "1309-37-1", "ewg_score": 1,
     "eu_regulation_annex": "IV"},

    {"name": "CI 77492", "inci_name": "CI 77492",
     "risk_level": "low", "category": "colorant",
     "description": "Оксид заліза (жовтий)",
     "description_en": "Iron oxide (yellow)",
     "cas_number": "51274-00-1", "ewg_score": 1,
     "eu_regulation_annex": "IV"},

    {"name": "CI 77499", "inci_name": "CI 77499",
     "risk_level": "low", "category": "colorant",
     "description": "Оксид заліза (чорний)",
     "description_en": "Iron oxide (black)",
     "cas_number": "12227-89-3", "ewg_score": 1,
     "eu_regulation_annex": "IV"},
]


# ═══════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ SEED
# ═══════════════════════════════════════════════════════════════════

def seed_database():
    """Наповнення бази даних інгредієнтами з розширеними полями."""
    from app import app
    from models import db, User, Ingredient, Scan

    with app.app_context():
        db.create_all()

        print("=" * 60)
        print("НАПОВНЕННЯ БАЗИ ДАНИХ (v2 — розширені поля)")
        print("=" * 60)

        added = 0
        updated = 0

        for data in INGREDIENTS:
            existing = Ingredient.query.filter_by(name=data['name']).first()

            if not existing:
                ing = Ingredient(
                    name=data['name'],
                    inci_name=data.get('inci_name'),
                    risk_level=data.get('risk_level', 'unknown'),
                    category=data.get('category'),
                    description=data.get('description', ''),
                    description_en=data.get('description_en', ''),
                    cas_number=data.get('cas_number'),
                    ewg_score=data.get('ewg_score'),
                    eu_max_concentration=data.get('eu_max_concentration'),
                    eu_regulation_annex=data.get('eu_regulation_annex'),
                    is_banned_eu=data.get('is_banned_eu', False),
                    source_of_risk_assessment=data.get('source_of_risk_assessment', 'manual'),
                    verified=True,
                    verified_at=datetime.utcnow(),
                    verified_by='seed_script',
                    created_at=datetime.utcnow(),
                )
                db.session.add(ing)
                added += 1
            else:
                # Оновлення існуючого — заповнюємо нові поля
                existing.inci_name = data.get('inci_name') or existing.inci_name
                existing.risk_level = data.get('risk_level', existing.risk_level)
                existing.category = data.get('category') or existing.category
                existing.description = data.get('description') or existing.description
                existing.description_en = data.get('description_en') or existing.description_en
                existing.cas_number = data.get('cas_number') or existing.cas_number
                existing.ewg_score = data.get('ewg_score') or existing.ewg_score
                existing.eu_max_concentration = data.get('eu_max_concentration') or existing.eu_max_concentration
                existing.eu_regulation_annex = data.get('eu_regulation_annex') or existing.eu_regulation_annex
                if data.get('is_banned_eu'):
                    existing.is_banned_eu = True
                existing.source_of_risk_assessment = (
                    data.get('source_of_risk_assessment') or existing.source_of_risk_assessment
                )
                if not existing.verified:
                    existing.verified = True
                    existing.verified_at = datetime.utcnow()
                    existing.verified_by = 'seed_script'
                updated += 1

            if (added + updated) % 20 == 0:
                print(f"  Оброблено: {added + updated}...")

        db.session.commit()
        print(f"\nДодано: {added}, Оновлено: {updated}")

        # Тестові користувачі
        print("\nСтворення тестових користувачів...")
        admin = User.query.filter_by(email="admin@cosmetics.com").first()
        if not admin:
            admin = User(email="admin@cosmetics.com", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            print("  Створено: admin@cosmetics.com / admin123")

        user = User.query.filter_by(email="user@example.com").first()
        if not user:
            user = User(email="user@example.com", role="user")
            user.set_password("user123")
            db.session.add(user)
            print("  Створено: user@example.com / user123")

        db.session.commit()

        # Статистика
        from sqlalchemy import func

        total = Ingredient.query.count()
        verified = Ingredient.query.filter_by(verified=True).count()
        with_cas = Ingredient.query.filter(Ingredient.cas_number.isnot(None)).count()
        with_ewg = Ingredient.query.filter(Ingredient.ewg_score.isnot(None)).count()
        banned = Ingredient.query.filter_by(is_banned_eu=True).count()

        print(f"\n{'=' * 60}")
        print(f"СТАТИСТИКА БАЗИ:")
        print(f"  Усього інгредієнтів:        {total}")
        print(f"  Верифікованих:              {verified}")
        print(f"  З CAS-номером:             {with_cas}")
        print(f"  З EWG-скором:              {with_ewg}")
        print(f"  Заборонених в ЄС:          {banned}")
        print(f"  Користувачів:              {User.query.count()}")
        print(f"  Сканувань:                 {Scan.query.count()}")

        print(f"\nСТАТИСТИКА ЗА РИЗИКОМ:")
        risk_stats = db.session.query(
            Ingredient.risk_level, func.count(Ingredient.id)
        ).group_by(Ingredient.risk_level).all()
        icons = {'safe': '🟢', 'low': '🔵', 'medium': '🟡', 'high': '🔴', 'unknown': '⚪'}
        for risk, count in sorted(risk_stats, key=lambda x: list(icons.keys()).index(x[0]) if x[0] in icons else 99):
            print(f"  {icons.get(risk, '⚪')} {risk}: {count}")

        print(f"\nСТАТИСТИКА ЗА КАТЕГОРІЯМИ:")
        cat_stats = db.session.query(
            Ingredient.category, func.count(Ingredient.id)
        ).group_by(Ingredient.category).order_by(func.count(Ingredient.id).desc()).all()
        for cat, count in cat_stats[:10]:
            print(f"  • {cat}: {count}")

        print(f"\n{'=' * 60}")
        print("БАЗУ ДАНИХ ОНОВЛЕНО!")
        print(f"{'=' * 60}")
        return True


if __name__ == "__main__":
    seed_database()
