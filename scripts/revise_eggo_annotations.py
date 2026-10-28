"""Generate a separate, provisional Eggo correction batch from local inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esceniq.dataset.preparation import validate_yolo_label


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_corrections(path: Path) -> tuple[dict[str, str], dict[str, list[tuple[float, float, float, float]]], dict[str, dict[str, str]]]:
    """Load source-derived data that must remain outside the repository."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    excluded = payload.get("excluded")
    revised_boxes = payload.get("revised_boxes")
    overrides = payload.get("review_overrides", {})
    if not isinstance(excluded, dict) or not isinstance(revised_boxes, dict) or not isinstance(overrides, dict):
        raise ValueError("El JSON debe incluir excluded, revised_boxes y review_overrides.")
    parsed_boxes: dict[str, list[tuple[float, float, float, float]]] = {}
    for filename, entries in revised_boxes.items():
        if not isinstance(filename, str) or not isinstance(entries, list):
            raise ValueError("Formato de revised_boxes inválido.")
        parsed_entries = []
        for entry in entries:
            if not isinstance(entry, list) or len(entry) != 4 or not all(isinstance(value, (int, float)) for value in entry):
                raise ValueError(f"Caja inválida en {filename}.")
            x1, y1, x2, y2 = entry
            if not 0 <= x1 < x2 <= 1 or not 0 <= y1 < y2 <= 1:
                raise ValueError(f"Caja fuera de rango en {filename}.")
            parsed_entries.append((x1, y1, x2, y2))
        parsed_boxes[filename] = parsed_entries
    if not all(isinstance(filename, str) and isinstance(reason, str) for filename, reason in excluded.items()):
        raise ValueError("Formato de excluded inválido.")
    if not all(isinstance(filename, str) and isinstance(value, dict) for filename, value in overrides.items()):
        raise ValueError("Formato de review_overrides inválido.")
    return excluded, parsed_boxes, overrides


def write_yolo(path: Path, boxes: list[tuple[float, float, float, float]]) -> None:
    lines = (f"0 {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}\n" for x1, y1, x2, y2 in boxes)
    path.write_text("".join(lines), encoding="utf-8")


def preview(image_path: Path, label_path: Path, output: Path) -> None:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    width, height = image.size
    draw = ImageDraw.Draw(image)
    for number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), 1):
        _, center_x, center_y, box_width, box_height = map(float, line.split())
        x1, y1 = round((center_x - box_width / 2) * width), round((center_y - box_height / 2) * height)
        x2, y2 = round((center_x + box_width / 2) * width), round((center_y + box_height / 2) * height)
        draw.rectangle((x1, y1, x2, y2), outline=(0, 255, 0), width=2)
        draw.text((x1 + 4, max(4, y1 + 4)), str(number), fill=(0, 255, 0), stroke_width=1, stroke_fill=(0, 0, 0))
    image.save(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--originals", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, required=True, help="JSON local no versionado con exclusiones y cajas.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    excluded, revised_boxes, overrides = load_corrections(args.corrections)
    source_labels = args.source / "labels"
    source_rows = list(csv.DictReader((args.source / "review_manifest.csv").open(encoding="utf-8-sig", newline="")))
    expected_names = {row["filename"] for row in source_rows}
    images = sorted((path for path in args.originals.glob("*.png") if path.name in expected_names), key=lambda path: path.name)
    if len(images) != 45 or {path.name for path in images} != expected_names:
        raise ValueError("Los 45 originales y el manifiesto fuente no coinciden")
    if not set(excluded).issubset(expected_names) or not set(revised_boxes).issubset(expected_names):
        raise ValueError("El JSON contiene archivos ajenos al lote fuente.")
    if args.output.exists():
        raise FileExistsError(f"No se sobrescribe salida existente: {args.output}")
    labels_dir, previews_dir = args.output / "labels", args.output / "previews"
    labels_dir.mkdir(parents=True)
    previews_dir.mkdir()
    before_hashes = {path.name: digest(path) for path in images}
    output_rows = []
    for image_path in images:
        name = image_path.name
        source_label = source_labels / f"{image_path.stem}.txt"
        old_count = len(source_label.read_text(encoding="utf-8").splitlines())
        with Image.open(image_path) as source:
            width, height = source.size
        if name in excluded:
            output_rows.append(dict(filename=name, width=width, height=height, status="excluded_from_main_training", box_count_before=old_count, box_count_after=0, changes="Sin etiqueta nueva; fuente intacta.", observations=excluded[name], original_sha256=before_hashes[name]))
            continue
        target_label = labels_dir / source_label.name
        if name in revised_boxes:
            write_yolo(target_label, revised_boxes[name])
            status, changes = "corrected_pending_human_review", "Límites sustituidos tras revisión visual; pendiente de aprobación."
        else:
            shutil.copy2(source_label, target_label)
            status, changes = "retained_provisional_pending_human_review", "Sin corrección solicitada; copia para revisión unificada."
        class_ids = validate_yolo_label(target_label)
        if set(class_ids) != {0}:
            raise ValueError(f"Clase no permitida: {name}")
        preview(image_path, target_label, previews_dir / f"{image_path.stem}_preview.png")
        override = overrides.get(name, {})
        output_rows.append(dict(filename=name, width=width, height=height, status=override.get("status", status), box_count_before=old_count, box_count_after=len(class_ids), changes=changes, observations=override.get("observation", "Límites y objeto requieren confirmación humana."), original_sha256=before_hashes[name]))
    if before_hashes != {path.name: digest(path) for path in images}:
        raise RuntimeError("Falló la integridad de originales")
    fields = list(output_rows[0])
    with (args.output / "revision_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    with (args.output / "excluded_from_main_training.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["filename", "status", "justification", "source_label_retained"])
        writer.writeheader()
        for name in sorted(excluded):
            writer.writerow(dict(filename=name, status="excluded_from_main_training", justification=excluded[name], source_label_retained="true"))
    active = [row for row in output_rows if row["status"] != "excluded_from_main_training"]
    (args.output / "README.md").write_text(
        "# Corrección provisional Eggo\n\n"
        f"- Originales de este lote: {len(images)}\n"
        f"- Cartones desplegados excluidos: {len(excluded)}\n"
        f"- Etiquetas activas de este lote: {len(active)}\n"
        "- Candidatas totales incluidas las 5 del piloto: 44\n"
        f"- Cajas fuente: {sum(int(row['box_count_before']) for row in output_rows)}\n"
        f"- Cajas activas corregidas: {sum(int(row['box_count_after']) for row in active)}\n\n"
        "Todas las etiquetas activas pasaron `validate_yolo_label()` y siguen pendientes de revisión humana.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
