"""Genera un editor HTML local para revisar anotaciones Eggo sin alterar sus fuentes."""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


class GalleryValidationError(ValueError):
    """Indica que las anotaciones locales no son aptas para la galería."""


@dataclass(frozen=True)
class GalleryItem:
    """Una imagen de revisión, su estado y sus cajas normalizadas."""

    filename: str
    image_path: Path
    status: str
    status_label: str
    observations: str
    boxes: tuple[tuple[float, float, float, float], ...]
    excluded: bool = False


STATUS_LABELS = {
    "corrected_pending_human_review": "Corregida pendiente de revisión",
    "retained_provisional_pending_human_review": "Retenida provisionalmente",
    "policy_review": "Pendiente de decisión de política",
    "pilot": "Piloto",
    "excluded_from_main_training": "Excluida del entrenamiento",
}
REQUIRED_MANIFEST_FIELDS = {
    "filename",
    "status",
    "box_count_after",
    "observations",
}


def validate_xywh_box(box: tuple[float, float, float, float]) -> None:
    """Valida una caja visual normalizada ``left, top, width, height``."""
    left, top, width, height = box
    if not all(isinstance(value, (int, float)) and 0 <= value <= 1 for value in box):
        raise GalleryValidationError("La caja contiene coordenadas normalizadas inválidas.")
    if width <= 0 or height <= 0 or left + width > 1 or top + height > 1:
        raise GalleryValidationError("La caja YOLO está fuera de la imagen o no tiene tamaño positivo.")


def yolo_to_xywh(class_id: int, center_x: float, center_y: float, width: float, height: float) -> tuple[float, float, float, float]:
    """Convierte una fila YOLO de Eggo a rectángulo normalizado para el SVG."""
    if class_id != 0:
        raise GalleryValidationError(f"Se esperaba clase 0 (eggo), se recibió {class_id}.")
    box = (center_x - width / 2, center_y - height / 2, width, height)
    validate_xywh_box(box)
    return box


def xywh_to_yolo(box: tuple[float, float, float, float]) -> tuple[int, float, float, float, float]:
    """Convierte una caja visual normalizada al formato YOLO de clase 0."""
    validate_xywh_box(box)
    left, top, width, height = box
    return (0, left + width / 2, top + height / 2, width, height)


def pixels_to_yolo(
    box: tuple[float, float, float, float], image_width: float, image_height: float
) -> tuple[int, float, float, float, float]:
    """Convierte una caja en píxeles a YOLO normalizado para una imagen concreta."""
    if image_width <= 0 or image_height <= 0:
        raise GalleryValidationError("Las dimensiones de imagen deben ser positivas.")
    left, top, width, height = box
    return xywh_to_yolo((left / image_width, top / image_height, width / image_width, height / image_height))


def yolo_to_pixels(
    yolo_box: tuple[int, float, float, float, float], image_width: float, image_height: float
) -> tuple[float, float, float, float]:
    """Convierte una caja YOLO a píxeles; conserva su posición en cualquier resolución."""
    if image_width <= 0 or image_height <= 0:
        raise GalleryValidationError("Las dimensiones de imagen deben ser positivas.")
    class_id, center_x, center_y, width, height = yolo_box
    left, top, normalized_width, normalized_height = yolo_to_xywh(class_id, center_x, center_y, width, height)
    return (left * image_width, top * image_height, normalized_width * image_width, normalized_height * image_height)


def parse_yolo_label(path: Path) -> tuple[tuple[float, float, float, float], ...]:
    """Lee un TXT YOLO y devuelve rectángulos ``x, y, width, height`` normalizados."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise GalleryValidationError(f"No se pudo leer la etiqueta: {path}") from error
    boxes: list[tuple[float, float, float, float]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise GalleryValidationError(f"{path.name}:{line_number} debe tener cinco valores YOLO.")
        try:
            class_id = int(fields[0])
            center_x, center_y, width, height = (float(value) for value in fields[1:])
        except ValueError as error:
            raise GalleryValidationError(f"{path.name}:{line_number} contiene valores no numéricos.") from error
        try:
            boxes.append(yolo_to_xywh(class_id, center_x, center_y, width, height))
        except GalleryValidationError as error:
            raise GalleryValidationError(f"{path.name}:{line_number} {error}") from error
    return tuple(boxes)


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            return list(csv.DictReader(source))
    except OSError as error:
        raise GalleryValidationError(f"No se pudo leer el manifiesto: {path}") from error


def image_url(image_path: Path, output_dir: Path) -> str:
    """Devuelve una URL relativa para que el HTML local no divulgue rutas absolutas."""
    relative = Path(os.path.relpath(image_path, output_dir)).as_posix()
    return quote(relative, safe="/-_.~")


def _require_image(originals_dir: Path, filename: str) -> Path:
    image_path = originals_dir / filename
    if Path(filename).name != filename or Path(filename).suffix.casefold() != ".png" or not image_path.is_file():
        raise GalleryValidationError(f"No existe el original PNG esperado: {filename}")
    return image_path


def load_gallery_items(dataset_root: Path) -> tuple[list[GalleryItem], list[GalleryItem]]:
    """Carga las 44 candidatas y las exclusiones sin modificar ninguna fuente."""
    dataset_root = Path(dataset_root)
    originals_dir = dataset_root / "originales"
    revision_dir = dataset_root / "revision_corregida"
    labels_dir = revision_dir / "labels"
    pilot_labels_dir = dataset_root / "piloto" / "labels"
    revision_manifest = revision_dir / "revision_manifest.csv"
    excluded_manifest = revision_dir / "excluded_from_main_training.csv"
    for path in (originals_dir, labels_dir, pilot_labels_dir):
        if not path.is_dir():
            raise GalleryValidationError(f"Falta el directorio requerido: {path}")
    rows = read_csv(revision_manifest)
    if not rows or not REQUIRED_MANIFEST_FIELDS.issubset(rows[0]):
        raise GalleryValidationError("El manifiesto de revisión no contiene las columnas esperadas.")

    candidates: list[GalleryItem] = []
    excluded: list[GalleryItem] = []
    seen_names: set[str] = set()
    for row in rows:
        filename, status = row["filename"], row["status"]
        if filename in seen_names:
            raise GalleryValidationError(f"El manifiesto repite la imagen: {filename}")
        seen_names.add(filename)
        image_path = _require_image(originals_dir, filename)
        if status == "excluded_from_main_training":
            excluded.append(
                GalleryItem(
                    filename=filename,
                    image_path=image_path,
                    status=status,
                    status_label=STATUS_LABELS[status],
                    observations=row.get("observations", ""),
                    boxes=(),
                    excluded=True,
                )
            )
            continue
        if status not in STATUS_LABELS:
            raise GalleryValidationError(f"Estado de revisión desconocido en {filename}: {status}")
        label_path = labels_dir / f"{Path(filename).stem}.txt"
        boxes = parse_yolo_label(label_path)
        expected_count = int(row["box_count_after"])
        if len(boxes) != expected_count:
            raise GalleryValidationError(f"{filename}: manifiesto={expected_count} cajas, etiqueta={len(boxes)}.")
        candidates.append(
            GalleryItem(filename, image_path, status, STATUS_LABELS[status], row.get("observations", ""), boxes)
        )

    excluded_rows = read_csv(excluded_manifest)
    excluded_names = {row.get("filename", "") for row in excluded_rows}
    if excluded_names != {item.filename for item in excluded}:
        raise GalleryValidationError("Las exclusiones no coinciden entre los dos manifiestos de revisión.")

    for label_path in sorted(pilot_labels_dir.glob("*.txt")):
        filename = f"{label_path.stem}.png"
        if filename in seen_names:
            raise GalleryValidationError(f"El piloto se solapa con el lote corregido: {filename}")
        candidates.append(
            GalleryItem(
                filename=filename,
                image_path=_require_image(originals_dir, filename),
                status="pilot",
                status_label=STATUS_LABELS["pilot"],
                observations="Anotación piloto provisional; requiere revisión humana.",
                boxes=parse_yolo_label(label_path),
            )
        )

    candidates.sort(key=lambda item: item.filename)
    excluded.sort(key=lambda item: item.filename)
    if len(candidates) != 44 or len(excluded) != 6:
        raise GalleryValidationError(
            f"Se esperaban 44 candidatas y 6 excluidas; se encontraron {len(candidates)} y {len(excluded)}."
        )
    return candidates, excluded


def _boxes_svg(boxes: tuple[tuple[float, float, float, float], ...]) -> str:
    rectangles = []
    for index, (left, top, width, height) in enumerate(boxes, start=1):
        label_width, label_height = 0.09, 0.065
        label_top = min(max(0, top), 1 - label_height)
        rectangles.append(
            f'<rect x="{left:.6f}" y="{top:.6f}" width="{width:.6f}" height="{height:.6f}" '
            'fill="rgba(200,255,0,.06)" stroke="#c8ff00" stroke-width="3" '
            'stroke-linejoin="round" vector-effect="non-scaling-stroke" />'
            f'<rect x="{left:.6f}" y="{label_top:.6f}" width="{label_width:.6f}" height="{label_height:.6f}" '
            'fill="#071c20" stroke="#c8ff00" stroke-width="2" vector-effect="non-scaling-stroke" />'
            f'<text x="{left + label_width / 2:.6f}" y="{label_top + label_height / 2:.6f}" font-size="0.040" '
            'fill="#f8ffe8" text-anchor="middle" dominant-baseline="middle">'
            f"{index}</text>"
        )
    return "".join(rectangles)


def _card(item: GalleryItem, output_dir: Path, review_index: int | None = None) -> str:
    escaped_name = html.escape(item.filename)
    escaped_status = html.escape(item.status_label)
    escaped_notes = html.escape(item.observations or "Sin observaciones adicionales.")
    url = image_url(item.image_path, output_dir)
    if review_index is None:
        image_content = (
            f'<div class="image-static"><img src="{url}" alt="{escaped_name}" loading="lazy">'
            '<svg class="overlay" viewBox="0 0 1 1" preserveAspectRatio="none"></svg></div>'
        )
        decision = ""
    else:
        image_content = f"""
        <button class="image-button" type="button" data-review-index="{review_index}" onclick="openModal(Number(this.dataset.reviewIndex))">
          <img src="{url}" alt="{escaped_name}" loading="lazy">
          <svg class="overlay" viewBox="0 0 1 1" preserveAspectRatio="none">{_boxes_svg(item.boxes)}</svg>
        </button>"""
        decision = f'<span class="decision pending" data-decision-index="{review_index}">Sin decisión</span>'
    return f"""
    <article class="card" data-status="{html.escape(item.status)}" {f'data-review-index="{review_index}"' if review_index is not None else ''}>
      {image_content}
      <div class="card-body">
        <strong>{escaped_name}</strong>
        <span class="badge {html.escape(item.status)}">{escaped_status}</span>
        <span class="box-count">{len(item.boxes)} cajas</span>
        {decision}
        <p>{escaped_notes}</p>
      </div>
    </article>"""


def render_html(candidates: list[GalleryItem], excluded: list[GalleryItem], output_dir: Path) -> str:
    """Renderiza un editor autónomo; sus cambios viven solo en el navegador."""
    candidate_cards = "\n".join(_card(item, output_dir, index) for index, item in enumerate(candidates))
    excluded_cards = "\n".join(_card(item, output_dir) for item in excluded)
    box_count = sum(len(item.boxes) for item in candidates)
    filters = [("all", "Todas"), *[(key, label) for key, label in STATUS_LABELS.items() if key != "excluded_from_main_training"]]
    filter_buttons = "".join(
        f'<button type="button" data-filter="{key}" onclick="filterCards(this)">{html.escape(label)}</button>'
        for key, label in filters
    )
    review_items = [
        {
            "filename": item.filename,
            "imageUrl": image_url(item.image_path, output_dir),
            "status": item.status,
            "statusLabel": item.status_label,
            "sourceObservation": item.observations,
            "boxes": item.boxes,
            "decision": "pending",
            "notes": "",
            "dirty": False,
        }
        for item in candidates
    ]
    review_json = json.dumps(review_items, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ESCENIQ · Revisión visual Eggo</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, Segoe UI, sans-serif; background:#091923; color:#e9f7f8; }}
body {{ margin:0; padding:24px; background:#091923; }}
main {{ max-width:1600px; margin:auto; }} h1 {{ margin:0; }}
.subtitle,.notice {{ color:#b7ced1; }} .summary {{ display:flex; flex-wrap:wrap; gap:12px; margin:20px 0; }}
.summary span,.badge,.box-count {{ border-radius:999px; padding:6px 10px; background:#17333e; font-size:.9rem; }}
.filters {{ display:flex; flex-wrap:wrap; gap:8px; margin:18px 0; }} button {{ font:inherit; }}
.filters button {{ border:1px solid #2f6672; background:#102a34; color:#e9f7f8; padding:8px 12px; border-radius:6px; cursor:pointer; }}
.filters button.active {{ background:#16b9c5; color:#052128; font-weight:700; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:18px; }}
.card {{ background:#102731; border:1px solid #27505a; border-radius:10px; overflow:hidden; }}
.image-button,.image-static {{ display:block; position:relative; width:100%; border:0; padding:0; background:#000; overflow:hidden; }}
.image-button {{ cursor:zoom-in; }} .image-button img,.image-static img {{ width:100%; height:auto; display:block; }}
.overlay {{ position:absolute; inset:0; width:100%; height:100%; pointer-events:none; }}
.overlay text {{ font-weight:bold; }}
.card-body {{ padding:12px; display:grid; gap:8px; }} .card-body p {{ margin:0; color:#bfd0d2; font-size:.9rem; }}
.decision {{ border-radius:999px; padding:5px 9px; font-size:.85rem; width:max-content; }} .decision.pending {{ background:#3e4752; }} .decision.approved {{ background:#246d45; }} .decision.corrected {{ background:#4d477c; }} .decision.excluded {{ background:#70313b; }}
.pilot {{ background:#3d315b; }} .policy_review {{ background:#704817; }} .corrected_pending_human_review {{ background:#16515a; }}
.retained_provisional_pending_human_review {{ background:#3f4a28; }} .excluded_from_main_training {{ background:#572b35; }}
.excluded {{ margin-top:42px; border-top:1px solid #5b3740; padding-top:20px; }}
#review-tools {{ display:flex; flex-wrap:wrap; gap:8px; margin:14px 0; }} .action-button {{ border:1px solid #4b808a; background:#17333e; color:white; padding:8px 12px; border-radius:6px; cursor:pointer; }} .dirty-summary {{ color:#f3df83; align-self:center; }}
#modal {{ position:fixed; inset:0; background:rgba(0,0,0,.88); display:none; z-index:10; padding:18px; overflow:auto; }}
#modal.open {{ display:flex; flex-direction:column; align-items:center; }} #modal button {{ background:#17333e; color:white; border:1px solid #4b808a; padding:8px 12px; border-radius:6px; cursor:pointer; }}
#modal-header {{ width:min(95vw,1400px); display:flex; justify-content:space-between; align-items:center; gap:12px; }} #modal h2 {{ margin:12px; font-size:1rem; }}
#editor-controls {{ width:min(95vw,1400px); display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:8px 0; }} #editor-controls .decision-button.active {{ outline:3px solid #c8ff00; }}
#editor-status {{ width:min(95vw,1400px); margin:4px 0 10px; color:#dceced; }} #editor-notes {{ width:min(95vw,1400px); min-height:52px; background:#0b2028; color:#eefeff; border:1px solid #4b808a; border-radius:6px; padding:8px; box-sizing:border-box; }}
#modal-view {{ position:relative; display:inline-block; max-width:95vw; max-height:68vh; background:#000; }} #modal-image {{ max-width:95vw; max-height:68vh; display:block; object-fit:contain; }} #editor-svg {{ position:absolute; inset:0; width:100%; height:100%; }}
#editor-svg .editor-box {{ cursor:move; fill:rgba(200,255,0,.06); stroke:#c8ff00; stroke-width:3; stroke-linejoin:round; vector-effect:non-scaling-stroke; }} #editor-svg .editor-box.selected {{ stroke:#ffea00; }}
#editor-svg .editor-label {{ fill:#071c20; stroke:#c8ff00; stroke-width:2; vector-effect:non-scaling-stroke; pointer-events:none; }} #editor-svg .editor-number {{ fill:#f8ffe8; font-weight:bold; pointer-events:none; }}
#editor-svg .resize-handle {{ fill:#ffea00; stroke:#071c20; stroke-width:2; vector-effect:non-scaling-stroke; cursor:nwse-resize; }}
@media (max-width:600px) {{ body {{ padding:12px; }} }}
</style>
</head>
<body><main>
<h1>ESCENIQ · Revisión visual de Eggo</h1>
<p class="subtitle">Editor local en memoria: no modifica PNG, TXT ni manifiestos. Exporta un JSON solo cuando lo solicites.</p>
<div class="summary"><span>{len(candidates)} candidatas</span><span>{box_count} cajas YOLO</span><span>{len(excluded)} excluidas fuera del entrenamiento</span></div>
<p class="notice">Haz clic en una candidata para ampliar, seleccionar y corregir sus cajas. Ninguna decisión comienza aprobada.</p>
<div id="review-tools"><button class="action-button" type="button" onclick="exportReview()">Exportar JSON de revisión</button><button class="action-button" type="button" onclick="document.getElementById('import-file').click()">Importar JSON</button><input id="import-file" type="file" accept="application/json" hidden onchange="importReview(event)"><span id="dirty-summary" class="dirty-summary">Sin cambios pendientes de exportar.</span></div>
<div class="filters">{filter_buttons}</div>
<section id="candidates" class="grid">{candidate_cards}</section>
<section class="excluded"><h2>Excluidas provisionalmente del entrenamiento</h2><p class="notice">Se muestran separadas para trazabilidad; no forman parte de las 44 candidatas y no incluyen cajas activas.</p><div class="grid">{excluded_cards}</div></section>
</main>
<div id="modal" role="dialog" aria-modal="true" aria-label="Editor de anotación Eggo">
  <div id="modal-header"><h2 id="modal-title"></h2><button type="button" onclick="closeModal()">Cerrar</button></div>
  <div id="editor-controls">
    <button type="button" class="action-button" onclick="startAddBox()">Añadir caja</button>
    <button type="button" class="action-button" onclick="deleteSelectedBox()">Eliminar caja seleccionada</button>
    <button type="button" class="action-button decision-button" data-decision="approved" onclick="setDecision('approved')">Aprobar</button>
    <button type="button" class="action-button decision-button" data-decision="corrected" onclick="setDecision('corrected')">Corregir</button>
    <button type="button" class="action-button decision-button" data-decision="excluded" onclick="setDecision('excluded')">Excluir</button>
    <button type="button" class="action-button decision-button" data-decision="pending" onclick="setDecision('pending')">Sin decisión</button>
  </div>
  <p id="editor-status"></p>
  <div id="modal-view"><img id="modal-image" alt=""><svg id="editor-svg" viewBox="0 0 1 1" preserveAspectRatio="none"></svg></div>
  <label for="editor-notes">Notas de revisión (se exportan solo en el JSON):</label><textarea id="editor-notes" placeholder="Observaciones opcionales"></textarea>
</div>
<script>
const reviewItems = {review_json};
const decisions = new Set(['pending', 'approved', 'corrected', 'excluded']);
const editor = {{ index:null, selected:null, mode:'select', drag:null }};
const minimumSize = .01;
function filterCards(button) {{
  const filter = button.dataset.filter;
  document.querySelectorAll('.filters button').forEach(item => item.classList.toggle('active', item === button));
  document.querySelectorAll('#candidates .card').forEach(card => {{ card.hidden = filter !== 'all' && card.dataset.status !== filter; }});
}}
function clamp(value, low, high) {{ return Math.min(high, Math.max(low, value)); }}
function isValidBox(box) {{ return Array.isArray(box) && box.length === 4 && box.every(value => Number.isFinite(value)) && box[0] >= 0 && box[1] >= 0 && box[2] > 0 && box[3] > 0 && box[0] + box[2] <= 1 && box[1] + box[3] <= 1; }}
function xywhToYolo(box) {{ if (!isValidBox(box)) throw new Error('Caja normalizada inválida.'); return [0, box[0] + box[2] / 2, box[1] + box[3] / 2, box[2], box[3]]; }}
function yoloToXywh(row) {{ if (!Array.isArray(row) || row.length !== 5 || row[0] !== 0 || !row.slice(1).every(value => Number.isFinite(value))) throw new Error('Fila YOLO inválida.'); const box = [row[1] - row[3] / 2, row[2] - row[4] / 2, row[3], row[4]]; if (!isValidBox(box)) throw new Error('Caja YOLO fuera de la imagen.'); return box; }}
function labelSvg(box, index) {{ const labelWidth=.09, labelHeight=.065, labelTop=Math.min(Math.max(0,box[1]),1-labelHeight); return `<rect class="editor-label" x="${{box[0]}}" y="${{labelTop}}" width="${{labelWidth}}" height="${{labelHeight}}"></rect><text class="editor-number" x="${{box[0]+labelWidth/2}}" y="${{labelTop+labelHeight/2}}" text-anchor="middle" dominant-baseline="middle" font-size=".040">${{index+1}}</text>`; }}
function readOnlyBoxesSvg(boxes) {{ return boxes.map((box,index)=>{{ const labelWidth=.09,labelHeight=.065,labelTop=Math.min(Math.max(0,box[1]),1-labelHeight); return `<rect x="${{box[0]}}" y="${{box[1]}}" width="${{box[2]}}" height="${{box[3]}}" fill="rgba(200,255,0,.06)" stroke="#c8ff00" stroke-width="3" vector-effect="non-scaling-stroke"></rect><rect x="${{box[0]}}" y="${{labelTop}}" width="${{labelWidth}}" height="${{labelHeight}}" fill="#071c20" stroke="#c8ff00" stroke-width="2" vector-effect="non-scaling-stroke"></rect><text x="${{box[0]+labelWidth/2}}" y="${{labelTop+labelHeight/2}}" font-size=".040" fill="#f8ffe8" text-anchor="middle" dominant-baseline="middle">${{index+1}}</text>`; }}).join(''); }}
function handlesSvg(box) {{ const [left,top,width,height] = box, right=left+width, bottom=top+height, middleX=left+width/2, middleY=top+height/2; return [['nw',left,top],['n',middleX,top],['ne',right,top],['e',right,middleY],['se',right,bottom],['s',middleX,bottom],['sw',left,bottom],['w',left,middleY]].map(handle => `<circle class="resize-handle" data-handle="${{handle[0]}}" cx="${{handle[1]}}" cy="${{handle[2]}}" r=".014"></circle>`).join(''); }}
function renderEditor() {{ const item=reviewItems[editor.index], svg=document.getElementById('editor-svg'); svg.innerHTML=item.boxes.map((box,index) => `<rect class="editor-box ${{index===editor.selected?'selected':''}}" data-box-index="${{index}}" x="${{box[0]}}" y="${{box[1]}}" width="${{box[2]}}" height="${{box[3]}}"></rect>${{labelSvg(box,index)}}${{index===editor.selected?handlesSvg(box):''}}`).join(''); document.getElementById('editor-status').textContent = editor.mode === 'draw' ? 'Haz clic y arrastra sobre la imagen para dibujar una nueva caja.' : `${{item.boxes.length}} cajas. Selecciona una caja para moverla o redimensionarla.`; document.querySelectorAll('.decision-button').forEach(button => button.classList.toggle('active', button.dataset.decision===item.decision)); }}
function updateCard(index) {{ const item=reviewItems[index], card=document.querySelector(`.card[data-review-index="${{index}}"]`); if (!card) return; card.querySelector('.box-count').textContent=`${{item.boxes.length}} cajas`; card.querySelector('.overlay').innerHTML=readOnlyBoxesSvg(item.boxes); const badge=card.querySelector('.decision'); badge.textContent={{pending:'Sin decisión',approved:'Aprobada',corrected:'Corregida',excluded:'Excluida'}}[item.decision]; badge.className=`decision ${{item.decision}}`; }}
function updateDirtySummary() {{ const count=reviewItems.filter(item=>item.dirty).length; document.getElementById('dirty-summary').textContent=count ? `${{count}} imágenes con modificaciones pendientes de exportar.` : 'Sin cambios pendientes de exportar.'; }}
function markDirty() {{ reviewItems[editor.index].dirty=true; updateCard(editor.index); updateDirtySummary(); }}
function openModal(index) {{ editor.index=index; editor.selected=null; editor.mode='select'; const item=reviewItems[index]; document.getElementById('modal-title').textContent=item.filename; const image=document.getElementById('modal-image'); image.src=item.imageUrl; image.alt=item.filename; document.getElementById('editor-notes').value=item.notes; document.getElementById('modal').classList.add('open'); renderEditor(); }}
function closeModal() {{ document.getElementById('modal').classList.remove('open'); editor.drag=null; }}
function setDecision(decision) {{ if (!decisions.has(decision)) return; reviewItems[editor.index].decision=decision; markDirty(); renderEditor(); }}
function startAddBox() {{ editor.selected=null; editor.mode='draw'; renderEditor(); }}
function deleteSelectedBox() {{ if (editor.selected===null) return; reviewItems[editor.index].boxes.splice(editor.selected,1); editor.selected=null; markDirty(); renderEditor(); }}
function pointFromEvent(event) {{ const rect=document.getElementById('editor-svg').getBoundingClientRect(); return [clamp((event.clientX-rect.left)/rect.width,0,1),clamp((event.clientY-rect.top)/rect.height,0,1)]; }}
function resizedBox(box, handle, x, y) {{ let [left,top,width,height]=box, right=left+width, bottom=top+height; if(handle.includes('w')) left=clamp(x,0,right-minimumSize); if(handle.includes('e')) right=clamp(x,left+minimumSize,1); if(handle.includes('n')) top=clamp(y,0,bottom-minimumSize); if(handle.includes('s')) bottom=clamp(y,top+minimumSize,1); return [left,top,right-left,bottom-top]; }}
function onEditorPointerDown(event) {{ const target=event.target, [x,y]=pointFromEvent(event), handle=target.dataset.handle, boxIndex=target.dataset.boxIndex; if(handle && editor.selected!==null) {{ editor.drag={{type:'resize',handle,start:reviewItems[editor.index].boxes[editor.selected].slice()}}; }} else if(boxIndex!==undefined) {{ editor.selected=Number(boxIndex); editor.mode='select'; editor.drag={{type:'move',start:reviewItems[editor.index].boxes[editor.selected].slice(),origin:[x,y]}}; renderEditor(); }} else if(editor.mode==='draw') {{ editor.drag={{type:'draw',origin:[x,y]}}; }} else {{ editor.selected=null; renderEditor(); return; }} document.getElementById('editor-svg').setPointerCapture(event.pointerId); event.preventDefault(); }}
function onEditorPointerMove(event) {{ if(!editor.drag) return; const [x,y]=pointFromEvent(event), item=reviewItems[editor.index]; if(editor.drag.type==='move') {{ const [left,top,width,height]=editor.drag.start; item.boxes[editor.selected]=[clamp(left+x-editor.drag.origin[0],0,1-width),clamp(top+y-editor.drag.origin[1],0,1-height),width,height]; }} else if(editor.drag.type==='resize') {{ item.boxes[editor.selected]=resizedBox(editor.drag.start,editor.drag.handle,x,y); }} else {{ const [startX,startY]=editor.drag.origin; item.boxes=item.boxes.filter((_,index)=>index!==editor.previewIndex); editor.previewIndex=item.boxes.length; item.boxes.push([Math.min(startX,x),Math.min(startY,y),Math.abs(x-startX),Math.abs(y-startY)]); }} renderEditor(); }}
function onEditorPointerUp(event) {{ if(!editor.drag) return; const item=reviewItems[editor.index]; if(editor.drag.type==='draw') {{ const box=item.boxes[editor.previewIndex]; if(!box || box[2]<minimumSize || box[3]<minimumSize) item.boxes.splice(editor.previewIndex,1); else {{ editor.selected=editor.previewIndex; markDirty(); }} delete editor.previewIndex; editor.mode='select'; }} else markDirty(); editor.drag=null; renderEditor(); }}
function exportReview() {{ try {{ const payload={{schema_version:1,dataset:'Eggo',class_id:0,annotations:reviewItems.map(item=>({{filename:item.filename,decision:item.decision,notes:item.notes,boxes_yolo:item.boxes.map(xywhToYolo)}}))}}; const link=document.createElement('a'); link.href=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{{type:'application/json'}})); link.download='eggo_review_corrections.json'; link.click(); URL.revokeObjectURL(link.href); reviewItems.forEach(item=>item.dirty=false); updateDirtySummary(); }} catch(error) {{ alert(`No se pudo exportar: ${{error.message}}`); }} }}
function importReview(event) {{ const file=event.target.files[0]; if(!file) return; const reader=new FileReader(); reader.onload=() => {{ try {{ const payload=JSON.parse(reader.result); if(payload.schema_version!==1 || !Array.isArray(payload.annotations)) throw new Error('Formato de revisión no reconocido.'); const seen=new Set(); payload.annotations.forEach(row=>{{ if(!row || typeof row.filename!=='string' || seen.has(row.filename) || !decisions.has(row.decision) || !Array.isArray(row.boxes_yolo)) throw new Error('Registro de revisión inválido.'); const item=reviewItems.find(candidate=>candidate.filename===row.filename); if(!item) throw new Error(`Imagen no candidata: ${{row.filename}}`); seen.add(row.filename); item.boxes=row.boxes_yolo.map(yoloToXywh); item.decision=row.decision; item.notes=typeof row.notes==='string'?row.notes:''; item.dirty=true; }}); updateDirtySummary(); if(editor.index!==null) openModal(editor.index); document.querySelectorAll('.card[data-review-index]').forEach(card=>updateCard(Number(card.dataset.reviewIndex))); alert('Revisión importada en memoria. Exporta un JSON cuando quieras guardar esta nueva versión.'); }} catch(error) {{ alert(`No se pudo importar: ${{error.message}}`); }} finally {{ event.target.value=''; }} }}; reader.readAsText(file,'utf-8'); }}
document.getElementById('editor-notes').addEventListener('input', event => {{ if(editor.index===null) return; reviewItems[editor.index].notes=event.target.value; markDirty(); }});
document.getElementById('editor-svg').addEventListener('pointerdown',onEditorPointerDown); document.getElementById('editor-svg').addEventListener('pointermove',onEditorPointerMove); document.getElementById('editor-svg').addEventListener('pointerup',onEditorPointerUp); document.getElementById('editor-svg').addEventListener('pointercancel',onEditorPointerUp);
document.querySelector('[data-filter="all"]').classList.add('active'); updateDirtySummary();
</script>
</body></html>"""


def validate_output_directory(dataset_root: Path, output_dir: Path) -> None:
    """Evita escribir fuera de la carpeta local explícitamente indicada por la usuaria."""
    root = dataset_root.resolve()
    destination = output_dir.resolve()
    if destination == root or root not in destination.parents:
        raise GalleryValidationError("El directorio de salida debe estar dentro de la raíz local del dataset Eggo.")
    protected = {root / name for name in ("originales", "piloto", "revision_corregida", "anotaciones_provisionales")}
    if destination in protected:
        raise GalleryValidationError("El directorio de salida no puede reemplazar fuentes ni anotaciones existentes.")


def write_review_template(path: Path, candidates: list[GalleryItem]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=("filename", "decision", "notes"))
        writer.writeheader()
        writer.writerows({"filename": item.filename, "decision": "", "notes": ""} for item in candidates)


def generate_gallery(dataset_root: Path, output_dir: Path) -> tuple[int, int]:
    """Genera HTML y plantilla CSV; devuelve número de candidatas y cajas dibujadas."""
    validate_output_directory(dataset_root, output_dir)
    candidates, excluded = load_gallery_items(dataset_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "eggo_review_gallery.html").write_text(render_html(candidates, excluded, output_dir), encoding="utf-8")
    write_review_template(output_dir / "eggo_review_template.csv", candidates)
    return len(candidates), sum(len(item.boxes) for item in candidates)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True, help="Raíz local con originales, piloto y revision_corregida.")
    parser.add_argument("--output-dir", type=Path, help="Carpeta local para el HTML y CSV; debe estar dentro de dataset-root.")
    args = parser.parse_args()
    output_dir = args.output_dir or args.dataset_root / "revision_visual_html"
    try:
        candidate_count, box_count = generate_gallery(args.dataset_root, output_dir)
    except GalleryValidationError as error:
        raise SystemExit(f"Error de validación: {error}") from error
    print(f"Galería generada: {output_dir / 'eggo_review_gallery.html'}")
    print(f"Candidatas: {candidate_count}; cajas representadas: {box_count}; excluidas: 6")


if __name__ == "__main__":
    main()
