import io
import tempfile
import os
from typing import Any, Dict, List

import pandas as pd


def build_dataframe(
    responses: List[List[Dict[str, Any]]],
    personas: List[Dict[str, str]],
    questions: List[Dict[str, Any]],
) -> pd.DataFrame:
    """
    Build a wide-format DataFrame where each row is one respondent.
    Columns: demographic fields + one column per question.
    """
    rows = []
    for i, (persona, answers) in enumerate(zip(personas, responses)):
        row: Dict[str, Any] = {
            "respondent_id": i + 1,
            **persona,
        }
        for answer in answers:
            col_name = f"{answer['question_id']}: {answer['question_text']}"[:80]
            row[col_name] = answer["answer"]
        rows.append(row)
    return pd.DataFrame(rows)


def export_csv(df: pd.DataFrame) -> str:
    """Write DataFrame to a temp CSV file and return the file path."""
    fd, path = tempfile.mkstemp(suffix=".csv", prefix="survey_")
    os.close(fd)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def export_excel(df: pd.DataFrame) -> str:
    """Write DataFrame to a temp Excel file and return the file path."""
    fd, path = tempfile.mkstemp(suffix=".xlsx", prefix="survey_")
    os.close(fd)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Survey Results")
    return path
