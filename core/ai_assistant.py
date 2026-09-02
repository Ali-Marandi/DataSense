"""Privacy-aware AI assistant facade.

The assistant never sends raw DataFrame rows implicitly. Remote model access is opt-in via
``generate_response(..., allow_remote=True)`` and receives only metadata context.
"""
from __future__ import annotations

import os
from typing import Any


class AIAssistant:
    def __init__(self, data_manager, *, model: str | None = None) -> None:
        self.data_manager = data_manager
        self.model = model or os.getenv("DATASENSE_AI_MODEL", "gpt-4.1-mini")

    def context(self) -> dict[str, Any]:
        """Return metadata-only context suitable for prompting an external model."""
        df = self.data_manager.df
        if df is None:
            return {"loaded": False, "columns": [], "summary": "No dataset loaded."}
        return {
            "loaded": True,
            "columns": [str(c) for c in df.columns],
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "summary": self.data_manager.get_summary(),
            "numeric_columns": self.data_manager.numeric_columns,
            "datetime_columns": self.data_manager.datetime_columns,
        }

    def generate_response(self, prompt: str, *, allow_remote: bool = False) -> str:
        if self.data_manager.df is None:
            return "Please load a dataset before asking for analysis."
        text = (prompt or "").strip()
        if not text:
            return "Enter a question or analysis request."
        if not allow_remote:
            return self._local_response(text)
        return self._remote_response(text)

    def _local_response(self, prompt: str) -> str:
        ctx = self.context()
        lowered = prompt.lower()
        if any(token in lowered for token in ("chart", "plot", "visual")):
            return f"Available columns: {', '.join(ctx['columns'])}. Specify X, Y and chart type; no dataset rows are exposed to the assistant."
        if any(token in lowered for token in ("summary", "analysis", "profile")):
            return f"{ctx['summary']} Numeric columns: {', '.join(ctx['numeric_columns']) or 'none'}."
        if any(token in lowered for token in ("predict", "forecast", "model")):
            return "Use the ML workspace to select a target, features and an explicit validation strategy. The assistant does not train or export a model implicitly."
        return "The local assistant can explain the dataset structure, available columns, analysis workflows and validation choices without transmitting row-level data."

    def _remote_response(self, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            return "Remote AI is unavailable because the OpenAI client is not installed."
        if not os.getenv("OPENAI_API_KEY"):
            return "Remote AI is disabled because OPENAI_API_KEY is not configured."
        try:
            client = OpenAI()
            response = client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": "You are a cautious analytics assistant. Use only metadata supplied below. Do not claim causal conclusions or inspect raw rows. Clearly distinguish descriptive, inferential, and predictive statements.",
                    },
                    {
                        "role": "user",
                        "content": f"Dataset metadata:\n{self.context()}\n\nQuestion:\n{prompt}",
                    },
                ],
            )
            return response.output_text
        except Exception as exc:
            return f"Remote AI request failed safely: {exc}"

    def interpret_results(self, analysis_type, results):
        if analysis_type == "AutoML":
            return f"Model result received: {results}. Treat this as predictive evidence, not causal evidence."
        if analysis_type == "Statistical Summary":
            return f"Statistical summary received: {results}. Check assumptions and confidence intervals before drawing conclusions."
        return "Interpretation is limited to the supplied result metadata."
