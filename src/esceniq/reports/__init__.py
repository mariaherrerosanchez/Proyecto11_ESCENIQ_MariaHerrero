"""Generación local de informes de resultados."""

from .csv_export import CSV_HEADERS, build_results_csv, build_stored_results_csv

__all__ = ("CSV_HEADERS", "build_results_csv", "build_stored_results_csv")
