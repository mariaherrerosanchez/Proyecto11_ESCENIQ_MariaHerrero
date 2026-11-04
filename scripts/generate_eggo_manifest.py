"""Genera manifiestos de procedencia y transición para las imágenes Eggo sin anotación."""
from __future__ import annotations

import argparse
import csv
import hashlib
import struct
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from esceniq.dataset.preparation import DatasetRecord, write_manifest  # noqa: E402

BRAND = "eggo"
CLASS_ID = 0
SOURCE_TYPE = "google_images_capture"
LICENSE = "unverified"
GROUP_ID = "provisional-unresolved-source"
SOURCE_MANIFEST_FIELDS = (
    "image_id", "filename", "source_path", "brand", "class_id", "source_type",
    "source_url", "license", "width", "height", "sha256", "group_id", "split",
    "annotation_status", "review_status", "notes",
)

SMALL_IMAGES = {
    "2026-10-23_10h25_42.png", "2026-10-23_10h26_08.png", "2026-10-23_10h26_28.png",
    "2026-10-23_10h27_08.png", "2026-10-23_10h32_21.png", "2026-10-23_10h34_39.png",
    "2026-10-23_10h38_08.png", "2026-10-23_10h38_55.png",
}
UNUSUAL_ASPECT_IMAGES = {
    "2026-10-23_10h26_08.png", "2026-10-23_10h32_53.png", "2026-10-23_10h35_52.png",
    "2026-10-23_10h42_07.png",
}
VISUAL_REVIEW_IMAGES = {
    "2026-10-23_10h30_25.png", "2026-10-23_10h31_31.png", "2026-10-23_10h32_21.png",
    "2026-10-23_10h33_16.png", "2026-10-23_10h36_55.png", "2026-10-23_10h43_50.png",
    "2026-10-23_10h45_12.png", "2026-10-23_10h45_37.png", "2026-10-23_10h46_44.png",
    "2026-10-23_10h47_28.png",
}


def png_dimensions(path: Path) -> tuple[int, int]:
    """Lee las dimensiones IHDR de un PNG sin modificarlo ni requerir dependencias externas."""
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"No es un PNG con cabecera IHDR válida: {path.name}")
    width, height = struct.unpack(">II", header[16:24])
    if not width or not height:
        raise ValueError(f"PNG con dimensiones inválidas: {path.name}")
    return width, height


def sha256(path: Path) -> str:
    """Calcula la huella de contenido leyendo el archivo en bloques."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_notes(filename: str) -> tuple[str, str]:
    """Devuelve estado y avisos derivados de la auditoría existente, sin excluir imágenes."""
    notes: list[str] = []
    if filename in SMALL_IMAGES:
        notes.append("lado mínimo inferior a 400 px; revisar tamaño efectivo de la caja")
    if filename in UNUSUAL_ASPECT_IMAGES:
        notes.append("relación de aspecto fuera de la banda operativa 0,75-1,90")
    if filename in VISUAL_REVIEW_IMAGES:
        notes.append("revisión visual prioritaria: escena/anuncio o desenfoque")
    return ("needs_review" if notes else "pending", "; ".join(notes))


def build_rows(source_root: Path) -> list[dict[str, str | int]]:
    """Construye un registro estable por PNG, ordenado por nombre de archivo."""
    rows: list[dict[str, str | int]] = []
    for image_path in sorted(source_root.glob("*.png")):
        width, height = png_dimensions(image_path)
        digest = sha256(image_path)
        review_status, notes = audit_notes(image_path.name)
        rows.append({
            "image_id": f"eggo-{digest[:16]}",
            "filename": image_path.name,
            "source_path": f"originales/{image_path.name}",
            "brand": BRAND,
            "class_id": CLASS_ID,
            "source_type": SOURCE_TYPE,
            "source_url": "unknown",
            "license": LICENSE,
            "width": width,
            "height": height,
            "sha256": digest,
            "group_id": GROUP_ID,
            "split": "",
            "annotation_status": "pending",
            "review_status": review_status,
            "notes": notes,
        })
    return rows


def write_source_manifest(rows: list[dict[str, str | int]], destination: Path) -> None:
    """Escribe el inventario ampliado UTF-8 sin rutas absolutas del equipo."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=SOURCE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def dataset_records(rows: list[dict[str, str | int]]) -> list[DatasetRecord]:
    """Proyecta el inventario al contrato sin modificar de DatasetRecord."""
    return [
        DatasetRecord(
            image_path=str(row["source_path"]),
            label_path=f"labels/{Path(str(row['filename'])).stem}.txt",
            class_ids=(CLASS_ID,),
            source=SOURCE_TYPE,
            group_id=str(row["group_id"]),
            split="",
            license=LICENSE,
        )
        for row in rows
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path, help="Directorio local de PNG originales, no se modifica.")
    parser.add_argument("--source-manifest", type=Path, default=PROJECT_ROOT / "datasets/esceniq/manifests/eggo_source_manifest.csv")
    parser.add_argument("--dataset-records", type=Path, default=PROJECT_ROOT / "datasets/esceniq/manifests/eggo_dataset_records_pending.csv")
    arguments = parser.parse_args()

    rows = build_rows(arguments.source_root)
    if not rows:
        raise SystemExit("No se encontraron PNG para registrar.")
    ids = [str(row["image_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("Los image_id derivados de SHA-256 no son únicos.")
    write_source_manifest(rows, arguments.source_manifest)
    write_manifest(dataset_records(rows), arguments.dataset_records)
    print(f"Registros generados: {len(rows)}")


if __name__ == "__main__":
    main()
