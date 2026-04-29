# init_db.py (повна ініціалізація)
"""
Єдиний скрипт повної ініціалізації бази даних Cosmetics Scanner.

Послідовність:
  1. Створення всіх таблиць (users, ingredients, ingredient_aliases,
     scans, scan_ingredients)
  2. Створення тестових користувачів
  3. Наповнення таблиці ingredients (seed з розширеними полями)
  4. Міграція хардкоджених словників → ingredient_aliases
  5. Фінальна статистика та перевірка

Запуск:
  python init_db.py              — повна ініціалізація
  python init_db.py --seed-only  — тільки seed (без створення таблиць)
  python init_db.py --migrate    — тільки міграція аліасів
  python init_db.py --stats      — тільки статистика

Безпечно для повторного запуску.
"""

import sys
import os
import argparse
from datetime import datetime

print("=" * 60)
print("ІНІЦІАЛІЗАЦІЯ БАЗИ ДАНИХ COSMETICS SCANNER")
print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)


def parse_args():
    parser = argparse.ArgumentParser(description='Ініціалізація БД Cosmetics Scanner')
    parser.add_argument('--seed-only', action='store_true', help='Тільки seed інгредієнтів')
    parser.add_argument('--migrate', action='store_true', help='Тільки міграція аліасів')
    parser.add_argument('--stats', action='store_true', help='Тільки статистика')
    parser.add_argument('--skip-seed', action='store_true', help='Пропустити seed')
    parser.add_argument('--skip-migrate', action='store_true', help='Пропустити міграцію аліасів')
    return parser.parse_args()


def step_create_tables(app, db):
    """Крок 1: Створення таблиць."""
    print("\n" + "─" * 50)
    print("КРОК 1: Створення таблиць")
    print("─" * 50)

    with app.app_context():
        db.create_all()
        print("✓ Таблиці створено/перевірено:")
        print("  • users")
        print("  • ingredients (розширена: inci_name, cas_number, ewg_score, ...)")
        print("  • ingredient_aliases (НОВА)")
        print("  • scans")
        print("  • scan_ingredients (НОВА)")

        # Перевірка підключення
        try:
            from sqlalchemy import text, inspect

            # Спробуємо визначити тип БД
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"\n  Таблиць у БД: {len(tables)}")
            for t in sorted(tables):
                columns = inspector.get_columns(t)
                print(f"    {t}: {len(columns)} колонок")

        except Exception as e:
            print(f"\n  ⚠ Не вдалося отримати інформацію про БД: {e}")

        # Створення необхідних директорій
        for d in ['uploads', 'static', 'data_cache']:
            os.makedirs(d, exist_ok=True)
        print("\n✓ Директорії перевірено: uploads, static, data_cache")


def step_create_users(app, db):
    """Крок 2: Створення тестових користувачів."""
    print("\n" + "─" * 50)
    print("КРОК 2: Тестові користувачі")
    print("─" * 50)

    from models import User

    with app.app_context():
        test_users = [
            {"email": "admin@cosmetics.com", "password": "admin123", "role": "admin"},
            {"email": "user@example.com", "password": "user123", "role": "user"},
        ]

        created = 0
        for data in test_users:
            existing = User.query.filter_by(email=data['email']).first()
            if not existing:
                user = User(email=data['email'], role=data['role'])
                user.set_password(data['password'])
                db.session.add(user)
                created += 1
                print(f"  ✚ Створено: {data['email']} ({data['role']})")
            else:
                print(f"  ✓ Вже існує: {data['email']} ({existing.role})")

        if created:
            db.session.commit()
        print(f"\n✓ Користувачів: {User.query.count()}")


def step_seed_ingredients(app, db):
    """Крок 3: Наповнення таблиці ingredients."""
    print("\n" + "─" * 50)
    print("КРОК 3: Seed інгредієнтів")
    print("─" * 50)

    try:
        from seed_ingredients import seed_database
        seed_database()
    except ImportError as e:
        print(f"  ⚠ Не вдалося імпортувати seed_ingredients: {e}")
        print("  Пропускаю крок seed...")
    except Exception as e:
        print(f"  ⚠ Помилка при seed: {e}")
        import traceback
        traceback.print_exc()


def step_migrate_aliases(app, db):
    """Крок 4: Міграція хардкоджених словників → ingredient_aliases."""
    print("\n" + "─" * 50)
    print("КРОК 4: Міграція аліасів")
    print("─" * 50)

    try:
        from migrate_aliases import migrate
        migrate()
    except ImportError as e:
        print(f"  ⚠ Не вдалося імпортувати migrate_aliases: {e}")
        print("  Пропускаю крок міграції...")
    except Exception as e:
        print(f"  ⚠ Помилка при міграції: {e}")
        import traceback
        traceback.print_exc()


def step_statistics(app, db):
    """Крок 5: Фінальна статистика."""
    print("\n" + "─" * 50)
    print("КРОК 5: Статистика бази даних")
    print("─" * 50)

    from models import User, Ingredient, IngredientAlias, Scan, ScanIngredient

    with app.app_context():
        total_ingredients = Ingredient.query.count()
        verified = Ingredient.query.filter_by(verified=True).count()
        unverified = Ingredient.query.filter_by(verified=False).count()
        with_cas = Ingredient.query.filter(Ingredient.cas_number.isnot(None)).count()
        with_ewg = Ingredient.query.filter(Ingredient.ewg_score.isnot(None)).count()
        banned = Ingredient.query.filter_by(is_banned_eu=True).count()
        total_aliases = IngredientAlias.query.count()
        total_scans = Scan.query.count()
        total_scan_ings = ScanIngredient.query.count()
        total_users = User.query.count()

        print(f"""
  ЗАГАЛЬНА СТАТИСТИКА:
  ┌──────────────────────────────┬──────────┐
  │ Показник                     │ Значення │
  ├──────────────────────────────┼──────────┤
  │ Користувачів                 │ {total_users:>8} │
  │ Інгредієнтів (всього)        │ {total_ingredients:>8} │
  │   ├ верифікованих            │ {verified:>8} │
  │   └ неверифікованих          │ {unverified:>8} │
  │ З CAS-номером                │ {with_cas:>8} │
  │ З EWG-скором                 │ {with_ewg:>8} │
  │ Заборонених в ЄС             │ {banned:>8} │
  │ Аліасів                      │ {total_aliases:>8} │
  │ Сканувань                    │ {total_scans:>8} │
  │ Зв'язків скан↔інгредієнт     │ {total_scan_ings:>8} │
  └──────────────────────────────┴──────────┘""")

        # Статистика за рівнем ризику
        from sqlalchemy import func
        risk_stats = (db.session.query(Ingredient.risk_level, func.count(Ingredient.id))
                      .group_by(Ingredient.risk_level).all())

        icons = {'safe': '🟢', 'low': '🔵', 'medium': '🟡', 'high': '🔴', 'unknown': '⚪'}
        order = ['safe', 'low', 'medium', 'high', 'unknown']
        risk_dict = dict(risk_stats)

        print("\n  ЗА РІВНЕМ РИЗИКУ:")
        for risk in order:
            count = risk_dict.get(risk, 0)
            if count > 0:
                bar = '█' * min(count, 40)
                print(f"    {icons.get(risk, '⚪')} {risk:>8}: {count:>4}  {bar}")

        # Статистика за категоріями
        cat_stats = (db.session.query(Ingredient.category, func.count(Ingredient.id))
                     .group_by(Ingredient.category)
                     .order_by(func.count(Ingredient.id).desc())
                     .all())

        print("\n  ЗА КАТЕГОРІЯМИ (топ-10):")
        for cat, count in cat_stats[:10]:
            print(f"    • {cat or 'без категорії':30s} {count:>4}")

        # Статистика аліасів за типом
        if total_aliases > 0:
            alias_stats = (db.session.query(IngredientAlias.alias_type, func.count(IngredientAlias.id))
                           .group_by(IngredientAlias.alias_type)
                           .order_by(func.count(IngredientAlias.id).desc())
                           .all())
            print("\n  АЛІАСИ ЗА ТИПОМ:")
            for atype, count in alias_stats:
                print(f"    • {atype or 'unknown':20s} {count:>4}")

        # Перевірка цілісності
        print("\n  ПЕРЕВІРКА ЦІЛІСНОСТІ:")
        orphan_aliases = (IngredientAlias.query
                          .filter(~IngredientAlias.ingredient_id.in_(
                              db.session.query(Ingredient.id)))
                          .count())
        print(f"    {'✓' if orphan_aliases == 0 else '⚠'} Аліаси без інгредієнта: {orphan_aliases}")

        dup_names = (db.session.query(Ingredient.name, func.count(Ingredient.id))
                     .group_by(Ingredient.name)
                     .having(func.count(Ingredient.id) > 1)
                     .all())
        print(f"    {'✓' if len(dup_names) == 0 else '⚠'} Дублікати назв: {len(dup_names)}")

        if dup_names:
            for name, count in dup_names:
                print(f"      ⚠ '{name}' — {count} записів")


def step_verify_checker(app, db):
    """Крок 6 (бонус): Перевірка роботи чекера."""
    print("\n" + "─" * 50)
    print("КРОК 6: Тестовий запуск чекера")
    print("─" * 50)

    with app.app_context():
        try:
            from checker import IngredientChecker

            checker = IngredientChecker(use_cache=False, auto_save_unknown=False)

            test_cases = [
                ("Aqua", "exact"),
                ("гліцерин", "alias (translation)"),
                ("glycerln", "alias (ocr_fix)"),
                ("SLS", "alias (abbreviation)"),
                ("Sodium Laureth Sulfate", "exact"),
                ("Formaldehyde", "exact (banned EU)"),
                ("Unknown Ingredient XYZ", "heuristic"),
            ]

            print(f"\n  Тестовий пошук ({len(test_cases)} запитів):")
            for query, expected in test_cases:
                result = checker.search_ingredient(query)
                match_type = result.get('match_type', '?')
                risk = result.get('risk_level', '?')
                name = result.get('name', '?')
                score = result.get('match_score', '')
                score_str = f" ({score:.0f}%)" if score else ""

                icons_risk = {'safe': '🟢', 'low': '🔵', 'medium': '🟡', 'high': '🔴', 'unknown': '⚪'}
                icon = icons_risk.get(risk, '⚪')

                print(f"    {icon} '{query}' → '{name}' "
                      f"[{match_type}{score_str}] (ризик: {risk})")

            print("\n  ✓ Чекер працює коректно")

        except Exception as e:
            print(f"  ⚠ Помилка тестового запуску: {e}")


# ═══════════════════════════════════════════════════════════════════
# ГОЛОВНИЙ БЛОК
# ═══════════════════════════════════════════════════════════════════

def main():
    args = parse_args()

    try:
        from app import app
        from models import db

    except ImportError as e:
        print(f"\n✗ Помилка імпорту: {e}")
        print("\nПереконайтеся, що:")
        print("  1. Ви знаходитесь у папці backend")
        print("  2. Файли app.py та models.py існують")
        print("  3. Встановлені залежності: pip install -r requirements.txt")
        sys.exit(1)

    # Тільки статистика
    if args.stats:
        step_statistics(app, db)
        return

    # Тільки seed
    if args.seed_only:
        step_seed_ingredients(app, db)
        step_statistics(app, db)
        return

    # Тільки міграція аліасів
    if args.migrate:
        step_migrate_aliases(app, db)
        step_statistics(app, db)
        return

    # Повна ініціалізація
    try:
        step_create_tables(app, db)
        step_create_users(app, db)

        if not args.skip_seed:
            step_seed_ingredients(app, db)
        else:
            print("\n  ⏭ Seed пропущено (--skip-seed)")

        if not args.skip_migrate:
            step_migrate_aliases(app, db)
        else:
            print("\n  ⏭ Міграція аліасів пропущена (--skip-migrate)")

        step_statistics(app, db)
        step_verify_checker(app, db)

    except Exception as e:
        print(f"\n✗ Критична помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Фінальне повідомлення
    print("\n" + "=" * 60)
    print("✓ БАЗА ДАНИХ COSMETICS SCANNER ГОТОВА!")
    print("=" * 60)
    print(f"""
  ТЕСТОВІ ОБЛІКОВІ ЗАПИСИ:
    Адмін:      admin@cosmetics.com / admin123
    Користувач: user@example.com    / user123

  ЗАПУСК:
    python app.py

  НОВІ АДМІН-ЕНДПОІНТИ:
    GET  /api/admin/unverified      — неверифіковані інгредієнти
    POST /api/admin/verify/<id>     — верифікувати інгредієнт
    GET  /api/admin/aliases         — список аліасів
    POST /api/admin/aliases         — додати аліас
    GET  /api/ingredients/<id>      — деталі + аліаси
    GET  /api/db-check              — статистика БД

  Відкрийте: http://localhost:5000
""")


if __name__ == "__main__":
    main()