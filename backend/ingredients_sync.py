"""
Модуль для синхронизации данных из внешних источников
"""

import requests
import json
import sqlite3
from datetime import datetime, timedelta
import time
from app import app, db, Ingredient
from bs4 import BeautifulSoup


class IngredientsSync:
    """Класс для синхронизации данных об ингредиентах"""
    
    def __init__(self):
        self.cache_file = 'data_cache/external_cache.db'
        self.init_database()
    
    def init_database(self):
        """Инициализация базы для кэша"""
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS external_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                data TEXT,
                source TEXT,
                risk_level TEXT,
                category TEXT,
                last_synced TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                status TEXT,
                items_synced INTEGER,
                error_message TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def sync_from_cosing(self, max_items=100):
        """Синхронизация из CosIng (ЕС)"""
        print(f"🔄 Синхронизация с CosIng (макс: {max_items} записей)")
        
        try:
            # В реальном проекте здесь будет работа с CosIng API
            # Для демо используем статические данные
            
            demo_ingredients = [
                {
                    "name": "Butylparaben",
                    "risk_level": "medium",
                    "category": "preservative",
                    "description": "Консервант, разрешенный в ЕС с ограничениями",
                    "source": "cosing"
                },
                {
                    "name": "Propylparaben",
                    "risk_level": "medium",
                    "category": "preservative",
                    "description": "Консервант, аналогичный метилпарабену",
                    "source": "cosing"
                },
                {
                    "name": "Phenoxyethanol",
                    "risk_level": "low",
                    "category": "preservative",
                    "description": "Широко используемый консервант",
                    "source": "cosing"
                }
            ]
            
            synced_count = 0
            for ingredient_data in demo_ingredients:
                if synced_count >= max_items:
                    break
                
                self.save_to_cache(ingredient_data)
                synced_count += 1
            
            self.log_sync('cosing', 'success', synced_count)
            print(f"✅ Синхронизировано {synced_count} ингредиентов из CosIng")
            
            return synced_count
            
        except Exception as e:
            self.log_sync('cosing', 'error', 0, str(e))
            print(f"❌ Ошибка синхронизации с CosIng: {e}")
            return 0
    
    def sync_from_openfoodfacts(self, max_items=50):
        """Синхронизация из Open Food Facts"""
        print(f"🔄 Синхронизация с Open Food Facts")
        
        try:
            # Пример запроса популярных ингредиентов
            url = "https://world.openfoodfacts.org/ingredients.json"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                ingredients = data.get('tags', [])[:max_items]
                
                synced_count = 0
                for ingredient in ingredients:
                    ingredient_data = {
                        "name": ingredient.get('name', ''),
                        "risk_level": "low",  # Пищевые ингредиенты обычно безопасны
                        "category": "food_ingredient",
                        "description": f"Пищевой ингредиент: {ingredient.get('products', 0)} продуктов",
                        "source": "openfoodfacts"
                    }
                    
                    self.save_to_cache(ingredient_data)
                    synced_count += 1
                
                self.log_sync('openfoodfacts', 'success', synced_count)
                print(f"✅ Синхронизировано {synced_count} ингредиентов из Open Food Facts")
                
                return synced_count
            
            return 0
            
        except Exception as e:
            self.log_sync('openfoodfacts', 'error', 0, str(e))
            print(f"❌ Ошибка синхронизации с Open Food Facts: {e}")
            return 0
    
    def save_to_cache(self, ingredient_data):
        """Сохранение ингредиента в кэш"""
        try:
            conn = sqlite3.connect(self.cache_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO external_ingredients 
                (name, data, source, risk_level, category, last_synced)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                ingredient_data['name'],
                json.dumps(ingredient_data),
                ingredient_data.get('source', 'unknown'),
                ingredient_data.get('risk_level', 'unknown'),
                ingredient_data.get('category', 'unknown'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка сохранения в кэш: {e}")
    
    def log_sync(self, source, status, items_synced, error_message=None):
        """Логирование синхронизации"""
        try:
            conn = sqlite3.connect(self.cache_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sync_log (source, status, items_synced, error_message)
                VALUES (?, ?, ?, ?)
            ''', (source, status, items_synced, error_message))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка логирования: {e}")
    
    def get_sync_stats(self):
        """Получение статистики синхронизации"""
        try:
            conn = sqlite3.connect(self.cache_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    source,
                    COUNT(*) as total,
                    MAX(last_synced) as last_sync,
                    SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) as high_risk
                FROM external_ingredients 
                GROUP BY source
            ''')
            
            sources_stats = cursor.fetchall()
            
            cursor.execute('''
                SELECT source, status, COUNT(*) as count
                FROM sync_log 
                GROUP BY source, status
                ORDER BY synced_at DESC
            ''')
            
            sync_logs = cursor.fetchall()
            
            conn.close()
            
            return {
                "sources": [
                    {
                        "source": source,
                        "total": total,
                        "last_sync": last_sync,
                        "high_risk": high_risk
                    }
                    for source, total, last_sync, high_risk in sources_stats
                ],
                "sync_logs": [
                    {
                        "source": source,
                        "status": status,
                        "count": count
                    }
                    for source, status, count in sync_logs
                ]
            }
            
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return {"sources": [], "sync_logs": []}
    
    def search_in_cache(self, query, limit=20):
        """Поиск в кэшированных данных"""
        try:
            conn = sqlite3.connect(self.cache_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT name, data, source, risk_level, category
                FROM external_ingredients 
                WHERE name LIKE ?
                ORDER BY last_synced DESC
                LIMIT ?
            ''', (f'%{query}%', limit))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    "name": name,
                    **json.loads(data),
                    "source": source,
                    "risk_level": risk_level,
                    "category": category
                }
                for name, data, source, risk_level, category in results
            ]
            
        except Exception as e:
            print(f"❌ Ошибка поиска в кэше: {e}")
            return []


def run_sync_job():
    """Запуск задачи синхронизации"""
    print("=" * 60)
    print("🔄 ЗАПУСК СИНХРОНИЗАЦИИ ВНЕШНИХ ИСТОЧНИКОВ")
    print("=" * 60)
    
    sync = IngredientsSync()
    
    # Синхронизация из разных источников
    cosing_count = sync.sync_from_cosing(max_items=50)
    openfoodfacts_count = sync.sync_from_openfoodfacts(max_items=30)
    
    # Статистика
    stats = sync.get_sync_stats()
    
    print(f"\n📊 РЕЗУЛЬТАТЫ СИНХРОНИЗАЦИИ:")
    print(f"   CosIng: {cosing_count} ингредиентов")
    print(f"   Open Food Facts: {openfoodfacts_count} ингредиентов")
    print(f"   Всего в кэше: {sum(s['total'] for s in stats['sources'])} ингредиентов")
    
    print("\n✅ Синхронизация завершена")
    return stats


if __name__ == "__main__":
    run_sync_job()