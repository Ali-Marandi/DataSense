from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

from core.data.model import ColumnProfile, DatasetProfile

_SUPPORTED_CSV_SUFFIXES: Final[frozenset[str]] = frozenset({".csv", ".tsv", ".txt"})


class DatasetLoadError(ValueError):
    """User-safe error raised when a local tabular file cannot be loaded."""


class DataService:
    """Local-only dataset loading and aggregate profiling service.

    The service deliberately returns raw DataFrames only to the local composition layer.
    It never emits cell values, filenames, or paths to telemetry/evidence services.
    """

    def load_csv(
        self,
        path: str | Path,
        *,
        encoding: str = "utf-8",
        delimiter: str | None = None,
    ) -> pd.DataFrame:
        source = Path(path).expanduser()
        if not source.exists():
            raise DatasetLoadError(f"Dataset not found: {source.name}")
        if not source.is_file():
            raise DatasetLoadError("Select a file, not a folder.")
        if source.suffix.lower() not in _SUPPORTED_CSV_SUFFIXES:
            raise DatasetLoadError("Supported starter formats are CSV, TSV and delimited text.")

        read_options: dict[str, object] = {"encoding": encoding}
        if delimiter is not None:
            if len(delimiter) != 1:
                raise DatasetLoadError("Delimiter must be one character.")
            read_options["sep"] = delimiter
        elif source.suffix.lower() == ".tsv":
            read_options["sep"] = "\t"

        try:
            frame = pd.read_csv(source, **read_options)
        except UnicodeDecodeError as exc:
            raise DatasetLoadError("The file encoding is not supported. Try UTF-8 or choose an encoding explicitly.") from exc
        except pd.errors.EmptyDataError as exc:
            raise DatasetLoadError("The selected file contains no tabular data.") from exc
        except pd.errors.ParserError as exc:
            raise DatasetLoadError("The file could not be parsed. Check the delimiter and quoting.") from exc
        except OSError as exc:
            raise DatasetLoadError("DataSense could not read the selected local file.") from exc

        return self._validate_frame(frame)

    def sample_dataset(self) -> pd.DataFrame:
        frame = pd.DataFrame(
            {
                "order_id": ["SO-1001", "SO-1002", "SO-1003", "SO-1004"],
                "region": ["North", "North", "West", "West"],
                "revenue": [1200.0, 850.0, 1630.0, 940.0],
                "delivery_days": [2, 5, 3, 4],
            }
        )
        return self._validate_frame(frame)

    def profile(self, frame: pd.DataFrame) -> DatasetProfile:
        validated = self._validate_frame(frame)
        summaries = tuple(
            ColumnProfile(
                name=str(column),
                dtype=str(validated[column].dtype),
                missing=int(validated[column].isna().sum()),
                unique=int(validated[column].nunique(dropna=True)),
            )
            for column in validated.columns
        )
        return DatasetProfile(
            rows=len(validated),
            columns=validated.shape[1],
            missing_cells=int(validated.isna().sum().sum()),
            duplicate_rows=int(validated.duplicated().sum()),
            memory_mb=float(validated.memory_usage(deep=True).sum() / (1024 * 1024)),
            column_summaries=summaries,
        )

    @staticmethod
    def _validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("DataService expects a pandas DataFrame.")
        if frame.empty:
            raise DatasetLoadError("The selected dataset contains no rows.")
        if frame.columns.empty:
            raise DatasetLoadError("The selected dataset contains no columns.")
        if frame.columns.has_duplicates:
            raise DatasetLoadError("Dataset column names must be unique before analysis.")
        return frame.copy(deep=True)
