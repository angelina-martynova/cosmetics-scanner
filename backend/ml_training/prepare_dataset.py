# prepare_dataset.py
"""Создаёт train.csv для обучения классификатора ингредиентов.
Использует все названия из seed_ingredients.py как позитивные,
и расширенный список негативных примеров (адреса, маркетинг, бытовые фразы).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from seed_ingredients import INGREDIENTS

import random
import csv

# 1. Позитивные примеры – все названия из seed (и их варианты, если есть inci_name)
positive = []
for ing in INGREDIENTS:
    positive.append(ing["name"])
    if ing.get("inci_name") and ing["inci_name"] != ing["name"]:
        positive.append(ing["inci_name"])

# 2. Негативные примеры – строки, которые НЕ должны быть ингредиентами
negative = [
    # английский мусор (адреса, предупреждения, маркетинг)
    "ISNTREE Clinically proven",
    "Non-irritating An emulsion containing Jeju green tea extract",
    "How to use At the last stage of skincare",
    "Apply proper amount onto the face",
    "until absorbed",
    "London WC2H 9JQ",
    "BE / UK",
    "Keep out of reach of children",
    "Cautions for use",
    "If skin irritations occur, seek immediate medical attention",
    "Do not apply on wounded area",
    "3F, Kesson Building, 20, Eonju-ro 133-gil",
    "Seoul, Republic of Korea",
    "Expiration date: see bottom",
    "Made in Korea",
    "www.isntree.com",
    "Tel: +82-2-123-4567",
    "For external use only",
    "Cautions for storage and handling",
    "Keep out of direct sunlight",
    "The manufacturing number and expiration date Marked separately",
    "Manufacturing distributor ISNTREE Inc",
    "Manufacturer CRTECH CORP",
    "Distributed by ABC Corp.",
    "Apt #2, Suite 101, Post Code 02000",
    "Rinse with warm water",
    "Avoid contact with eyes",
    "In case of contact, flush with water",
    "Shelf life: 12 months after opening",
    "Ingredients Water, Propanediol, Caprylic/Capric Triglyceride",
    "Product of Korea",
    "Cosmetics Scanner v2.0",
    "Skipley - сканер безпеки",

    # украинский / русский мусор
    "Виробник: ТОВ Косметик",
    "Україна, Київ, вул. Хрещатик 1",
    "Росія, Москва, вул. Тверская",
    "ГОСТ 12345-67",
    "Термін придатності: 24 міс.",
    "Зберігати при температурі від +5°С до +25°С",
    "Не застосовувати на пошкодженій шкірі",
    "Склад наведено на упаковці",
    "Призначено для зовнішнього застосування",
    "Упаковка: флакон 200 мл",
    "Штрихкод: 4820000000000",
    "Дата виробництва: 01.01.2025",
    "Партія № 12345",
    "Засіб гігієнічний миючий",
    "Крем-мило рідке",
    "Туба",
    "мл",
    "г",
    "Засіб для зняття макіяжу",
    "Очищуючий гель для вмивання",
    "Тонік для обличчя",
    "Пілінг-скатка",
    "Маска для волосся",
    "Бальзам після гоління",
    "Дезодорант-антиперспірант",
    "Сонцезахисний крем SPF 50",
    "Дитяча присипка",
    "Продукт протестовано дерматологами",
    "Гіпоалергенно",
    "Не містить парабенів",
    "pH збалансований",
    "Підходить для веганів",
    "Країна виробник: Польща",
    "Імпортер: ТОВ Бьюти-Трейд",

    # ещё несколько общих фраз и мусора
    "Для всіх типів шкіри",
    "Догляд за обличчям",
    "Натуральний склад",
    "Без барвників",
    "Клінічно доведено",
    "Рекомендовано лікарями",
    "Перед використанням збовтати",
    "Тільки для зовнішнього застосування",
    "Не їстівне",
    "Змити теплою водою",
    "У разі потрапляння в очі промити водою",
    "Берегти від дітей",
    "Не використовувати після закінчення терміну придатності",
    "Дата виготовлення та номер партії на упаковці",
    "Виготовлено відповідно до ТУ У 24.5-12345678-001:2020",
    "Сертифікат відповідності",
    "100% органічний продукт",
    "Не тестовано на тваринах",
    "Веганський продукт",
    "Біорозкладна упаковка",
    "Зроблено з любов'ю",
    "Дякуємо за покупку!",
    "Ваш надійний вибір",
    "Краса та здоров'я",
    "Ексклюзивна формула",
    "Активні компоненти:",
    "Спосіб застосування:",
    "Склад:",
    "Інгредієнти:",
    "Ingredients:",
    "INCI:",
    "Composition:",
    "Aqua (Water), Glycerin, Sodium Laureth Sulfate",  # полный список
    "/",  # один слеш иногда попадается
    ".",
    ",",
    "-",
    " ",
    "",
]

# 3. Балансируем классы: дублируем позитивные, чтобы их стало примерно столько же, сколько негативных
if len(negative) > len(positive):
    multiplier = len(negative) // len(positive) + 1
    positive = positive * multiplier
positive = positive[:len(negative)]   # обрезаем до одинакового количества

# 4. Перемешиваем и сохраняем
data = []
for text in positive:
    data.append((text, 1))
for text in negative:
    data.append((text, 0))
random.shuffle(data)

with open("train.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["text", "label"])
    writer.writerows(data)

print(f"train.csv создан: {len(data)} примеров (1: {sum(l for _,l in data)}, 0: {len(data)-sum(l for _,l in data)})")