"""Catálogo inmutable de las clases de marca oficiales de ESCENIQ."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


class BrandClassValidationError(ValueError):
    """Indica una definición de clases incompatible con el catálogo oficial."""


class UnknownBrandClassError(LookupError):
    """Indica un identificador YOLO o un nombre de marca no reconocido."""


@dataclass(frozen=True)
class BrandClass:
    """Una clase YOLO y la marca comercial que representa."""

    yolo_id: int
    class_name: str
    brand_name: str
    visual_variants: tuple[str, ...]


BRAND_CLASSES: tuple[BrandClass, ...] = (
    BrandClass(0, "eggo", "Eggo", ("logotipo", "envases")),
    BrandClass(1, "coca_cola", "Coca-Cola", ("Coca-Cola", "Coke", "New Coke")),
    BrandClass(2, "pepsi", "Pepsi", ("Pepsi", "Pepsi Perfect")),
    BrandClass(3, "fedex", "FedEx", ("diferentes soportes del logotipo",)),
    BrandClass(4, "wilson", "Wilson", ("logotipo completo", "W aislada inequívoca")),
)
OFFICIAL_YOLO_NAMES = {0: "eggo", 1: "coca_cola", 2: "pepsi", 3: "fedex", 4: "wilson"}
OFFICIAL_BRAND_NAMES = ("Eggo", "Coca-Cola", "Pepsi", "FedEx", "Wilson")


def validate_brand_catalog(catalog: Sequence[BrandClass] = BRAND_CLASSES) -> None:
    """Valida identificadores, nombres y el orden continuo de un catálogo."""
    identifiers = [brand.yolo_id for brand in catalog]
    class_names = [brand.class_name for brand in catalog]
    official_names = [brand.brand_name.casefold() for brand in catalog]
    if len(catalog) != 5:
        raise BrandClassValidationError("El catálogo debe contener exactamente cinco clases.")
    if identifiers != list(range(5)):
        raise BrandClassValidationError("Los identificadores YOLO deben ser consecutivos de 0 a 4.")
    if len(set(identifiers)) != len(identifiers):
        raise BrandClassValidationError("Hay identificadores YOLO duplicados.")
    if len(set(class_names)) != len(class_names) or len(set(official_names)) != len(official_names):
        raise BrandClassValidationError("Hay nombres de clase o de marca duplicados.")
    if any(not brand.class_name or not brand.brand_name for brand in catalog):
        raise BrandClassValidationError("Las clases y marcas deben tener nombres no vacíos.")
    if {brand.yolo_id: brand.class_name for brand in catalog} != OFFICIAL_YOLO_NAMES:
        raise BrandClassValidationError("El catálogo contiene una clase YOLO desconocida o inconsistente.")
    if tuple(brand.brand_name for brand in catalog) != OFFICIAL_BRAND_NAMES:
        raise BrandClassValidationError("El catálogo contiene una marca oficial desconocida o inconsistente.")


def brand_class_for_yolo_id(yolo_id: int) -> BrandClass:
    """Obtiene la definición oficial asociada a un identificador YOLO."""
    if isinstance(yolo_id, bool) or not isinstance(yolo_id, int) or yolo_id not in range(len(BRAND_CLASSES)):
        raise UnknownBrandClassError(f"Identificador YOLO desconocido: {yolo_id!r}")
    return BRAND_CLASSES[yolo_id]


def brand_name_for_yolo_id(yolo_id: int) -> str:
    """Obtiene el nombre oficial de la marca asociada a un identificador YOLO."""
    return brand_class_for_yolo_id(yolo_id).brand_name


def yolo_id_for_brand_name(brand_name: str) -> int:
    """Obtiene el identificador de una marca oficial; las variantes no son nombres válidos."""
    if not isinstance(brand_name, str):
        raise UnknownBrandClassError(f"Marca desconocida: {brand_name!r}")
    normalized_name = brand_name.casefold()
    for brand in BRAND_CLASSES:
        if brand.brand_name.casefold() == normalized_name:
            return brand.yolo_id
    raise UnknownBrandClassError(f"Marca desconocida: {brand_name!r}")


def yolo_names() -> dict[int, str]:
    """Devuelve el mapa ``names`` listo para reutilizar en un dataset YOLO."""
    return {brand.yolo_id: brand.class_name for brand in BRAND_CLASSES}


def validate_yolo_names(names: Mapping[int, str]) -> None:
    """Comprueba que un mapa de clases de dataset coincide con el oficial."""
    if dict(names) != yolo_names():
        raise BrandClassValidationError(
            "El mapa de clases YOLO no coincide con el catálogo oficial de ESCENIQ."
        )


def render_yolo_names_yaml() -> str:
    """Genera el bloque YAML de ``names`` sin requerir una dependencia YAML."""
    lines = ["names:"]
    lines.extend(f"  {yolo_id}: {class_name}" for yolo_id, class_name in yolo_names().items())
    return "\n".join(lines) + "\n"


validate_brand_catalog()
