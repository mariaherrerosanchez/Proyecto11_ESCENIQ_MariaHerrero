"""Utilidades sin dependencias para preparar datasets YOLO sin fugas."""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Sequence

from esceniq.vision.brand_classes import BrandClassValidationError, validate_yolo_names, yolo_names

SPLITS = ("train", "val", "test")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MANIFEST_FIELDS = (
    "image_path", "label_path", "class_ids", "source", "group_id", "split", "license",
)
# Las etiquetas se suelen serializar con precisión decimal finita. Esta tolerancia
# admite únicamente un exceso de redondeo de hasta ocho decimales, no cajas reales
# fuera de la imagen.
YOLO_BOUNDARY_TOLERANCE = 1e-8


class DatasetValidationError(ValueError):
    """Indica un manifiesto, etiqueta o estructura de dataset inválidos."""


@dataclass(frozen=True)
class DatasetRecord:
    """Metadatos relativos y portables de una imagen destinada al dataset."""

    image_path: str
    label_path: str
    class_ids: tuple[int, ...]
    source: str
    group_id: str
    split: str = ""
    license: str = ""


@dataclass(frozen=True)
class SplitConfig:
    """Proporciones y semilla de una división reproducible por grupo."""

    train: float = 0.70
    val: float = 0.15
    test: float = 0.15
    seed: int = 42

    def validate(self) -> None:
        if any(value <= 0 for value in (self.train, self.val, self.test)):
            raise DatasetValidationError("Las proporciones de train, val y test deben ser positivas.")
        if abs(self.train + self.val + self.test - 1.0) > 1e-9:
            raise DatasetValidationError("Las proporciones de train, val y test deben sumar 1.")


def _relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise DatasetValidationError(f"La ruta debe ser relativa y no escapar del dataset: {value!r}")
    return path.as_posix()


def validate_manifest(records: Sequence[DatasetRecord]) -> None:
    """Comprueba trazabilidad, rutas portables, clases y ausencia de conflictos."""
    image_paths: set[str] = set()
    label_paths: set[str] = set()
    for record in records:
        image_path, label_path = _relative_path(record.image_path), _relative_path(record.label_path)
        if Path(image_path).suffix.lower() not in IMAGE_SUFFIXES or Path(label_path).suffix.lower() != ".txt":
            raise DatasetValidationError("Las rutas deben referirse a una imagen y a una etiqueta .txt.")
        if image_path in image_paths or label_path in label_paths:
            raise DatasetValidationError("Hay rutas de imagen o etiqueta duplicadas; se evitará sobrescritura.")
        if not record.source or not record.group_id:
            raise DatasetValidationError("Cada registro requiere fuente y grupo de procedencia.")
        if record.split and record.split not in SPLITS:
            raise DatasetValidationError(f"Conjunto desconocido: {record.split}")
        if any(class_id not in yolo_names() for class_id in record.class_ids):
            raise DatasetValidationError("El manifiesto contiene un ID de clase fuera del catálogo oficial.")
        image_paths.add(image_path)
        label_paths.add(label_path)
    validate_group_assignments(records)


def validate_group_assignments(records: Sequence[DatasetRecord]) -> None:
    """Impide que un mismo vídeo, clip o fuente se reparta entre conjuntos."""
    groups: dict[str, set[str]] = defaultdict(set)
    for record in records:
        if record.split:
            groups[record.group_id].add(record.split)
    leaked_groups = sorted(group_id for group_id, splits in groups.items() if len(splits) > 1)
    if leaked_groups:
        raise DatasetValidationError(f"Hay grupos repartidos entre conjuntos: {leaked_groups}")


def validate_manifest_paths(records: Sequence[DatasetRecord], dataset_root: Path) -> None:
    """Verifica que las rutas relativas del manifiesto existen bajo el dataset."""
    validate_manifest(records)
    for record in records:
        for relative_path in (record.image_path, record.label_path):
            path = dataset_root / Path(_relative_path(relative_path))
            if not path.is_file():
                raise DatasetValidationError(f"No existe el archivo indicado por el manifiesto: {relative_path}")


def split_records_by_group(
    records: Sequence[DatasetRecord],
    config: SplitConfig = SplitConfig(),
    demo_groups: Iterable[str] = (),
) -> tuple[list[DatasetRecord], list[str]]:
    """Asigna grupos completos con semilla; los grupos de demo quedan fuera."""
    validate_manifest(records)
    config.validate()
    excluded = set(demo_groups)
    if group_overlap := {record.group_id for record in records} & excluded:
        raise DatasetValidationError(f"Los grupos de demostración no pueden entrar en el dataset: {sorted(group_overlap)}")

    grouped: dict[str, list[DatasetRecord]] = defaultdict(list)
    for record in records:
        grouped[record.group_id].append(record)
    group_ids = sorted(grouped)
    random.Random(config.seed).shuffle(group_ids)
    targets = {"train": config.train * len(records), "val": config.val * len(records), "test": config.test * len(records)}
    counts = {split: 0 for split in SPLITS}
    assignments: dict[str, str] = {}
    for group_id in group_ids:
        group_size = len(grouped[group_id])
        split = min(SPLITS, key=lambda name: (counts[name] - targets[name], SPLITS.index(name)))
        assignments[group_id] = split
        counts[split] += group_size

    split_records = [
        DatasetRecord(**{**record.__dict__, "split": assignments[record.group_id]}) for record in records
    ]
    return split_records, class_distribution_warnings(split_records)


def class_distribution_warnings(records: Sequence[DatasetRecord]) -> list[str]:
    """Advierte cuando una clase no puede estar representada en todos los conjuntos."""
    seen: dict[int, set[str]] = defaultdict(set)
    for record in records:
        for class_id in record.class_ids:
            if record.split:
                seen[class_id].add(record.split)
    return [
        f"La clase {class_id} solo aparece en {', '.join(sorted(seen[class_id])) or 'ningún conjunto'}; "
        "no puede validarse en los tres conjuntos."
        for class_id in yolo_names() if seen[class_id] != set(SPLITS)
    ]


def write_manifest(records: Sequence[DatasetRecord], path: Path) -> None:
    """Escribe un CSV UTF-8 con rutas relativas, sin rutas personales."""
    validate_manifest(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for record in records:
            row = record.__dict__.copy()
            row["class_ids"] = " ".join(str(value) for value in record.class_ids)
            writer.writerow(row)


def read_manifest(path: Path) -> list[DatasetRecord]:
    """Lee un manifiesto CSV y conserva las clases presentes por imagen."""
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != MANIFEST_FIELDS:
            raise DatasetValidationError("Las columnas del manifiesto no coinciden con el formato esperado.")
        records = [DatasetRecord(
            image_path=row["image_path"], label_path=row["label_path"],
            class_ids=tuple(int(value) for value in row["class_ids"].split() if value),
            source=row["source"], group_id=row["group_id"], split=row["split"], license=row["license"],
        ) for row in reader]
    validate_manifest(records)
    return records


def validate_yolo_label(label_path: Path) -> tuple[int, ...]:
    """Valida un TXT YOLO; un archivo vacío es una imagen negativa válida.

    Además de los valores normalizados, comprueba los bordes derivados de la caja.
    Se permite una tolerancia máxima de ``1e-8`` para errores de serialización
    decimal, pero no para anotaciones que realmente excedan la imagen.
    """
    class_ids: list[int] = []
    for line_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise DatasetValidationError(f"{label_path}:{line_number} debe contener cinco valores YOLO.")
        try:
            class_id = int(fields[0])
            x_center, y_center, width, height = (float(value) for value in fields[1:])
        except ValueError as error:
            raise DatasetValidationError(f"{label_path}:{line_number} contiene valores no numéricos.") from error
        if class_id not in yolo_names():
            raise DatasetValidationError(f"{label_path}:{line_number} usa una clase desconocida.")
        if not all(0 <= value <= 1 for value in (x_center, y_center, width, height)) or width <= 0 or height <= 0:
            raise DatasetValidationError(f"{label_path}:{line_number} tiene coordenadas YOLO inválidas.")
        left, right = x_center - width / 2, x_center + width / 2
        top, bottom = y_center - height / 2, y_center + height / 2
        if left < -YOLO_BOUNDARY_TOLERANCE or right > 1 + YOLO_BOUNDARY_TOLERANCE:
            raise DatasetValidationError(f"{label_path}:{line_number} excede los límites horizontales de la imagen.")
        if top < -YOLO_BOUNDARY_TOLERANCE or bottom > 1 + YOLO_BOUNDARY_TOLERANCE:
            raise DatasetValidationError(f"{label_path}:{line_number} excede los límites verticales de la imagen.")
        class_ids.append(class_id)
    return tuple(class_ids)


def validate_dataset_files(root: Path) -> None:
    """Comprueba pares imagen/etiqueta y etiquetas de los tres conjuntos."""
    for split in SPLITS:
        images_dir, labels_dir = root / "images" / split, root / "labels" / split
        if not images_dir.is_dir() or not labels_dir.is_dir():
            raise DatasetValidationError(f"Falta la estructura de imágenes o etiquetas para {split}.")
        image_stems = {path.stem for path in images_dir.glob("*") if path.suffix.lower() in IMAGE_SUFFIXES}
        label_stems = {path.stem for path in labels_dir.glob("*.txt")}
        missing_labels, missing_images = image_stems - label_stems, label_stems - image_stems
        if missing_labels or missing_images:
            raise DatasetValidationError(
                f"{split}: imágenes sin etiqueta={sorted(missing_labels)}, etiquetas sin imagen={sorted(missing_images)}"
            )
        for label_path in labels_dir.glob("*.txt"):
            validate_yolo_label(label_path)


def render_data_yaml(dataset_root: Path = Path("datasets/esceniq")) -> str:
    """Genera el data.yaml portable que referencia el catálogo oficial de US-001."""
    root = dataset_root.as_posix()
    lines = [f"path: {root}", "train: images/train", "val: images/val", "test: images/test", "names:"]
    lines.extend(f"  {class_id}: {class_name}" for class_id, class_name in yolo_names().items())
    return "\n".join(lines) + "\n"


def validate_data_yaml_text(content: str) -> None:
    """Valida la configuración generada sin requerir PyYAML."""
    expected_names = "\n".join(f"  {key}: {value}" for key, value in yolo_names().items())
    if not all(f"{field}:" in content for field in ("path", "train", "val", "test")) or f"names:\n{expected_names}" not in content:
        raise DatasetValidationError("data.yaml no contiene rutas y clases oficiales completas.")
    try:
        validate_yolo_names({int(key): value for key, value in (line.strip().split(": ") for line in content.splitlines() if line.startswith("  "))})
    except (ValueError, BrandClassValidationError) as error:
        raise DatasetValidationError("data.yaml contiene clases incompatibles con US-001.") from error
