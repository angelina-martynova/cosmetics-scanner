import re

class IngredientChecker:
    def __init__(self):
        self.ingredients = self.load_ingredients()
        self.common_fixes = {
            "methytisctvazuivare": "methylisothiazolinone",
            "tetrasodiurs edta": "tetrasodium edta", 
            "sodim laureth sulfate": "sodium laureth sulfate",
            "peg~4": "peg-4",
            "fragranc": "fragrance",
            "paraben": "parabens",
            "sls": "sodium laureth sulfate",
            # Украинские исправления
            "натрію": "sodium",
            "сульфат": "sulfate",
            "парабен": "paraben",
        }

    def load_ingredients(self):
        # Базовый список ингредиентов (расширьте по необходимости)
        return [
            {
                "id": 1,
                "name": "Sodium Laureth Sulfate",
                "risk_level": "medium",
                "category": "surfactant", 
                "description": "Пінник, може викликати подразнення шкіри",
                "aliases": ["sodium laureth sulfate", "sles", "sls", "натрію лаурет сульфат"]
            },
            {
                "id": 2, 
                "name": "Methylparaben",
                "risk_level": "medium",
                "category": "preservative",
                "description": "Консервант з можливим гормональним впливом",
                "aliases": ["methylparaben", "methyl paraben", "метилпарабен"]
            },
            {
                "id": 3,
                "name": "Parfum", 
                "risk_level": "high",
                "category": "fragrance",
                "description": "Ароматизатор, може викликати алергії",
                "aliases": ["parfum", "fragrance", "aroma", "perfume", "парфум", "ароматизатор"]
            },
            {
                "id": 4,
                "name": "Formaldehyde",
                "risk_level": "high",
                "category": "preservative", 
                "description": "Канцероген, може викликати алергії",
                "aliases": ["formaldehyde", "formalin", "формальдегід"]
            }
        ]

    def clean_text(self, text):
        text = text.lower()
        text = re.sub(r'[^a-zA-Z0-9а-яА-ЯіІїЇєЄ\s,]', ' ', text)
        for wrong, correct in self.common_fixes.items():
            text = text.replace(wrong, correct)
        return text

    def check_match(self, ingredient_name, cleaned_text):
        return ingredient_name.lower() in cleaned_text

    def find_ingredients(self, text):
        cleaned_text = self.clean_text(text)
        found_ingredients = []
        seen_ids = set()
        
        for ingredient in self.ingredients:
            if ingredient["id"] in seen_ids:
                continue

            if self.check_match(ingredient["name"], cleaned_text):
                found_ingredients.append(ingredient)
                seen_ids.add(ingredient["id"])
                continue

            for alias in ingredient.get("aliases", []):
                if self.check_match(alias, cleaned_text):
                    found_ingredients.append(ingredient)
                    seen_ids.add(ingredient["id"])
                    break

        return found_ingredients