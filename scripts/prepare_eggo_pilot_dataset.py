"""Prepara un dataset piloto YOLO de Eggo desde una revisión humana exportada."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from esceniq.dataset.preparation import (  # noqa: E402
    DatasetRecord,
    DatasetValidationError,
    validate_dataset_files,
    validate_manifest_paths,
    write_manifest,
)

SPLITS = ("train", "val", "test")
EXPECTED_IMAGE_COUNT = 44
EXPECTED_BOX_COUNT = 83
SEED = 42
SPLIT_COUNTS = {"train": 31, "val": 7, "test": 6}
SOURCE = "google_images_capture"
LICENSE = "unverified"
JSON_DIFFERENCES = (
    {
        "filename": "2026-10-23_10h32_21.png",
        "provisional_txt_boxes": 2,
        "reviewed_json_boxes": 3,
    },
    {
        "filename": "2026-10-23_10h41_44.png",
        "provisional_txt_boxes": 3,
        "reviewed_json_boxes": 2,
    },
)


class PilotDatasetError(ValueError):
    """Indica que la revisión exportada no puede convertirse en un dataset piloto."""


@dataclass(frozen=True)
class ReviewedImage:
    """Una imagen aprobada y sus cajas YOLO definitivas."""

    filename: str
    boxes: tuple[tuple[int, float, float, float, float], ...]


def sha256(path: Path) -> str:
    """Calcula una huella estable del original, leyendo en bloques."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_box(box: Any, filename: str, box_number: int) -> tuple[int, float, float, float, float]:
    """Valida una caja del JSON y devuelve sus valores tipados."""
    if not isinstance(box, list) or len(box) != 5:
        raise PilotDatasetError(f"{filename}: caja {box_number} no tiene cinco valores.")
    class_id, center_x, center_y, width, height = box
    if class_id != 0 or not all(isinstance(value, (int, float)) for value in (center_x, center_y, width, height)):
        raise PilotDatasetError(f"{filename}: caja {box_number} no es una anotación YOLO de clase 0.")
    numeric = (float(center_x), float(center_y), float(width), float(height))
    if not all(0 <= value <= 1 for value in numeric) or numeric[2] <= 0 or numeric[3] <= 0:
        raise PilotDatasetError(f"{filename}: caja {box_number} contiene coordenadas YOLO inválidas.")
    if numeric[0] - numeric[2] / 2 < 0 or numeric[0] + numeric[2] / 2 > 1:
        raise PilotDatasetError(f"{filename}: caja {box_number} excede los límites horizontales.")
    if numeric[1] - numeric[3] / 2 < 0 or numeric[1] + numeric[3] / 2 > 1:
        raise PilotDatasetError(f"{filename}: caja {box_number} excede los límites verticales.")
    return (0, *numeric)


def load_approved_review(path: Path) -> list[ReviewedImage]:
    """Carga exactamente las imágenes aprobadas desde el JSON del editor."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PilotDatasetError(f"No se pudo leer el JSON de revisión: {path}") from error
    if payload.get("schema_version") != 1 or payload.get("dataset") != "Eggo" or payload.get("class_id") != 0:
        raise PilotDatasetError("El JSON no corresponde al esquema de revisión Eggo esperado.")
    rows = payload.get("annotations")
    if not isinstance(rows, list):
        raise PilotDatasetError("El JSON no contiene una lista de anotaciones.")

    reviewed: list[ReviewedImage] = []
    names: set[str] = set()
    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise PilotDatasetError(f"El registro {row_number} no es un objeto.")
        filename, decision = row.get("filename"), row.get("decision")
        if not isinstance(filename, str) or Path(filename).name != filename or Path(filename).suffix.lower() != ".png":
            raise PilotDatasetError(f"El registro {row_number} contiene un nombre PNG inválido.")
        if filename in names:
            raise PilotDatasetError(f"El JSON repite la imagen: {filename}")
        names.add(filename)
        if decision != "approved":
            raise PilotDatasetError(f"{filename}: solo se pueden preparar imágenes aprobadas, no {decision!r}.")
        boxes = row.get("boxes_yolo")
        if not isinstance(boxes, list) or not boxes:
            raise PilotDatasetError(f"{filename}: una imagen aprobada debe incluir al menos una caja.")
        reviewed.append(ReviewedImage(filename, tuple(validate_box(box, filename, index) for index, box in enumerate(boxes, 1))))

    if len(reviewed) != EXPECTED_IMAGE_COUNT:
        raise PilotDatasetError(f"Se esperaban {EXPECTED_IMAGE_COUNT} imágenes aprobadas; se recibieron {len(reviewed)}.")
    if sum(len(image.boxes) for image in reviewed) != EXPECTED_BOX_COUNT:
        raise PilotDatasetError(f"Se esperaban {EXPECTED_BOX_COUNT} cajas aprobadas.")
    return sorted(reviewed, key=lambda image: image.filename)


def split_reviewed_images(images: Iterable[ReviewedImage], seed: int = SEED) -> dict[str, list[ReviewedImage]]:
    """Crea la división piloto determinista por imagen, no por fuente real."""
    shuffled = list(images)
    random.Random(seed).shuffle(shuffled)
    expected = sum(SPLIT_COUNTS.values())
    if len(shuffled) != expected:
        raise PilotDatasetError(f"La partición piloto requiere {expected} imágenes; se recibieron {len(shuffled)}.")
    train_end = SPLIT_COUNTS["train"]
    val_end = train_end + SPLIT_COUNTS["val"]
    return {
        "train": sorted(shuffled[:train_end], key=lambda image: image.filename),
        "val": sorted(shuffled[train_end:val_end], key=lambda image: image.filename),
        "test": sorted(shuffled[val_end:], key=lambda image: image.filename),
    }


def yolo_text(boxes: Iterable[tuple[int, float, float, float, float]]) -> str:
    """Representa cajas futuras a ocho decimales sin desbordar sus bordes.

    Al redondear, el centro se vuelve a limitar según el ancho o alto ya
    redondeado. Así una caja válida en el borde no se convierte en inválida por
    una diferencia de coma flotante durante la serialización.
    """

    def rounded_box(box: tuple[int, float, float, float, float]) -> tuple[int, float, float, float, float]:
        class_id, center_x, center_y, width, height = box
        rounded_width, rounded_height = round(width, 8), round(height, 8)
        rounded_center_x, rounded_center_y = round(center_x, 8), round(center_y, 8)
        center_x = min(max(rounded_center_x, rounded_width / 2), 1 - rounded_width / 2)
        center_y = min(max(rounded_center_y, rounded_height / 2), 1 - rounded_height / 2)
        return class_id, center_x, center_y, rounded_width, rounded_height

    return "".join(
        f"{class_id} {center_x:.8f} {center_y:.8f} {width:.8f} {height:.8f}\n"
        for class_id, center_x, center_y, width, height in map(rounded_box, boxes)
    )


def render_data_yaml(dataset_root: Path) -> str:
    """Devuelve un YAML con raíz absoluta para que Ultralytics no dependa del CWD."""
    root = dataset_root.resolve().as_posix()
    return f"path: {root}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: eggo\n"


def validate_pilot_data_yaml(content: str, dataset_root: Path) -> None:
    """Valida el contrato mínimo del YAML monoclase sin tocar el YAML oficial."""
    expected = render_data_yaml(dataset_root)
    if content != expected:
        raise PilotDatasetError("El data.yaml del piloto debe tener raíz absoluta y solo 0: eggo.")


def ensure_empty_output_directory(output_root: Path) -> None:
    """Evita mezclar una nueva preparación con resultados previos."""
    if output_root.exists():
        raise PilotDatasetError(f"La salida ya existe; debe ser una carpeta nueva: {output_root}")


def write_report(
    path: Path,
    json_source: Path,
    partitions: dict[str, list[ReviewedImage]],
    content_hashes: dict[str, str],
) -> None:
    """Escribe trazabilidad y limitaciones sin rutas locales personales."""
    report = {
        "dataset": "eggo-pilot-yolo-v1",
        "annotation_source": json_source.name,
        "annotation_source_sha256": sha256(json_source),
        "class_map": {"0": "eggo"},
        "seed": SEED,
        "counts": {
            "images": sum(len(images) for images in partitions.values()),
            "boxes": sum(len(image.boxes) for images in partitions.values() for image in images),
            "splits": {split: len(images) for split, images in partitions.items()},
        },
        "split_method": "Deterministic per-image shuffle with seed 42; this is not a source-independent split.",
        "provenance_limitation": (
            "Source URLs, campaigns and clip identities are unknown. Exact duplicates and dHash-near pairs "
            "were absent in the prior audit, but independence between train, validation and test cannot be guaranteed."
        ),
        "demo_video_policy": "No ESCENIQ demonstration video is included in this image-only dataset.",
        "provisional_txt_differences": JSON_DIFFERENCES,
        "records": [
            {
                "filename": image.filename,
                "sha256": content_hashes[image.filename],
                "split": split,
                "box_count": len(image.boxes),
                "group_id": f"provisional-image-{content_hashes[image.filename][:16]}",
            }
            for split, images in partitions.items()
            for image in images
        ],
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_dataset(originals_dir: Path, review_json: Path, output_root: Path) -> dict[str, int]:
    """Copia originales y genera etiquetas derivadas, manifiesto y YAML para el piloto."""
    reviewed = load_approved_review(review_json)
    ensure_empty_output_directory(output_root)
    if not originals_dir.is_dir():
        raise PilotDatasetError(f"No existe el directorio de originales: {originals_dir}")

    hashes: dict[str, str] = {}
    for image in reviewed:
        source = originals_dir / image.filename
        if not source.is_file():
            raise PilotDatasetError(f"No existe el original referenciado: {image.filename}")
        hashes[image.filename] = sha256(source)
    if duplicate_hashes := [digest for digest, count in Counter(hashes.values()).items() if count > 1]:
        raise PilotDatasetError(f"Hay duplicados exactos en las candidatas: {duplicate_hashes}")

    partitions = split_reviewed_images(reviewed)
    output_root.mkdir(parents=True)
    records: list[DatasetRecord] = []
    for split in SPLITS:
        for directory in (output_root / "images" / split, output_root / "labels" / split):
            directory.mkdir(parents=True)
        for image in partitions[split]:
            source = originals_dir / image.filename
            image_destination = output_root / "images" / split / image.filename
            label_destination = output_root / "labels" / split / f"{Path(image.filename).stem}.txt"
            shutil.copy2(source, image_destination)
            label_destination.write_text(yolo_text(image.boxes), encoding="utf-8")
            digest = hashes[image.filename]
            records.append(
                DatasetRecord(
                    image_path=f"images/{split}/{image.filename}",
                    label_path=f"labels/{split}/{Path(image.filename).stem}.txt",
                    class_ids=(0,),
                    source=SOURCE,
                    group_id=f"provisional-image-{digest[:16]}",
                    split=split,
                    license=LICENSE,
                )
            )

    data_yaml = render_data_yaml(output_root)
    (output_root / "data.yaml").write_text(data_yaml, encoding="utf-8")
    manifests = output_root / "manifests"
    manifests.mkdir()
    write_manifest(records, manifests / "dataset_records.csv")
    write_report(manifests / "preparation_report.json", review_json, partitions, hashes)

    validate_pilot_data_yaml(data_yaml, output_root)
    validate_dataset_files(output_root)
    validate_manifest_paths(records, output_root)
    counts = {split: len(partitions[split]) for split in SPLITS}
    if counts != SPLIT_COUNTS:
        raise PilotDatasetError(f"Distribución incorrecta: {counts}")
    return {"images": len(records), "boxes": sum(len(image.boxes) for image in reviewed), **counts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--originals-dir", type=Path, required=True, help="Carpeta de PNG originales, solo lectura.")
    parser.add_argument("--review-json", type=Path, required=True, help="JSON definitivo exportado por la revisión humana.")
    parser.add_argument("--output-root", type=Path, required=True, help="Carpeta nueva y vacía para el dataset piloto.")
    arguments = parser.parse_args()
    try:
        result = prepare_dataset(arguments.originals_dir, arguments.review_json, arguments.output_root)
    except (PilotDatasetError, DatasetValidationError) as error:
        raise SystemExit(f"Error de preparación: {error}") from error
    print(
        "Dataset piloto preparado: "
        f"{result['images']} imágenes, {result['boxes']} cajas; "
        f"train={result['train']}, val={result['val']}, test={result['test']}."
    )


if __name__ == "__main__":
    main()
