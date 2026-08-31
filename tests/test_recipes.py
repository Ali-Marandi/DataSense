import json

from core.recipes import AnalysisRecipe, RecipeStep


def test_recipe_roundtrip_is_stable() -> None:
    recipe = AnalysisRecipe(
        name="Retail quality",
        description="Repeatable preparation workflow",
        steps=[
            RecipeStep("drop_missing", {"columns": ["revenue"]}),
            RecipeStep("scale_columns", {"columns": ["units"], "method": "minmax"}),
        ],
    )
    restored = AnalysisRecipe.from_json(recipe.to_json())
    assert restored.fingerprint == recipe.fingerprint
    assert restored.steps[0].operation == "drop_missing"


def test_recipe_json_is_object() -> None:
    recipe = AnalysisRecipe(name="Smoke", steps=[RecipeStep("profile")])
    payload = json.loads(recipe.to_json())
    assert payload["schema"] == "datasense.analysis-recipe/v1"
    assert payload["fingerprint"] == recipe.fingerprint
