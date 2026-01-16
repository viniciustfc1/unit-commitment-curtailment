"""Utility: convert an .xlsx file to .csv placed in repository root.

Usage:
	from scripts.xlsx_to_csv import xlsx_to_csv
	xlsx_to_csv('path/to/file.xlsx')

Or run as script:
	python scripts/xlsx_to_csv.py path/to/file.xlsx
"""
from __future__ import annotations

import os
import sys
from typing import Optional, Union

import pandas as pd


def xlsx_to_csv(xlsx_path: str, csv_path: Optional[str] = None, sheet_name: Union[str, int, None] = 0) -> str:
	"""Convert an Excel file to CSV and return the path to the created CSV.

	- `xlsx_path`: path to the input .xlsx file.
	- `csv_path`: optional path for the output .csv file. If not provided,
	  the file is created in the repository root with the same base name.
	- `sheet_name`: sheet to read (name or index). Defaults to first sheet (0).

	The function uses `utf-8-sig` encoding for better Excel compatibility.
	Raises FileNotFoundError, ValueError, or pandas errors on failure.
	"""

	if not os.path.isfile(xlsx_path):
		raise FileNotFoundError(f"Input file not found: {xlsx_path}")

	lower = xlsx_path.lower()
	if not (lower.endswith(".xls") or lower.endswith(".xlsx") or lower.endswith(".xlsm")):
		raise ValueError("Input file does not appear to be an Excel file (.xls, .xlsx, .xlsm)")

	# If csv_path not provided, place the CSV in repository root (two levels up from scripts/)
	if csv_path is None:
		repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
		base = os.path.splitext(os.path.basename(xlsx_path))[0]
		csv_path = os.path.join(repo_root, f"{base}.csv")

	# Read the Excel sheet (let pandas raise useful errors for corrupt files)
	df = pd.read_excel(xlsx_path, sheet_name=sheet_name)

	# Write CSV with UTF-8 BOM for Excel compatibility and without the index
	df.to_csv(csv_path, index=False, encoding="utf-8-sig")

	return csv_path

def convert_simples_in_scripts() -> str:
	"""Convenience wrapper to convert the known Excel file inside `scripts/`.

	Looks for `scripts/Simples Geração Solar Normalizado.xlsx` and converts it
	to a CSV placed at the repository root. Returns the CSV path.
	Raises FileNotFoundError if the XLSX is not present.
	"""

	repo_scripts = os.path.dirname(__file__)
	candidate = os.path.join(repo_scripts, "Simples Geração Solar Normalizado.xlsx")
	if not os.path.isfile(candidate):
		raise FileNotFoundError(f"Expected Excel not found: {candidate}")

	return xlsx_to_csv(candidate)


if __name__ == "__main__":
	convert_simples_in_scripts()
