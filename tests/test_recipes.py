import json

import pandas as pd
import pytest

from core.data_manager import DataManager
from core.recipes import AnalysisRecipe, RecipeStep, execute_recipe


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


def test_execute_recipe_uses_allowlist_and_history() -> None:
    manager = DataManager()
    manager.df = pd.DataFrame({"x": [1, 1, 2], "y": [10.0, None, 20.0]})
    manager.history = []
    manager.set_frame(manager.df.copy(), "Loaded")
    messages = execute_recipe(manager, AnalysisRecipe(name="clean", steps=[RecipeStep("drop_duplicates")]))
    assert messages
    assert len(manager.df) == 2


def test_execute_recipe_blocks_unknown_operation() -> None:
    manager = DataManager()
    with pytest.raises(ValueError, match="not allowed"):
        execute_recipe(manager, AnalysisRecipe(name="unsafe", steps=[RecipeStep("run_shell", {})]))
