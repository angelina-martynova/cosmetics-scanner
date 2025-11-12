class IngredientChecker:
    def __init__(self):
        self.ingredients = self.load_ingredients()
        self.common_fixes = {
            "methytisctvazuivare": "methylisothiazolinone",
            "tetrasodiurs edta":   "tetrasodium edta",
            "sodim laureth sulfate": "sodium laureth sulfate",
            "peg~4": "peg-4",
            "fragranc": "fragrance",
        }

    def load_ingredients(self):
        # загрузка ингредиентов из файла или БД
        return []

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
            if ingredient.id in seen_ids:
                continue

            if self.check_match(ingredient.name, cleaned_text):
                found_ingredients.append(ingredient.to_dict())
                seen_ids.add(ingredient.id)
                continue

            for alias in ingredient.aliases or []:
                if self.check_match(alias, cleaned_text):
                    found_ingredients.append(ingredient.to_dict())
                    seen_ids.add(ingredient.id)
                    break

        return found_ingredients
