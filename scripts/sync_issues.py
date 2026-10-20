#!/usr/bin/env python3
"""Sincroniza las US de FUNCTIONAL_SPEC; la vista previa es el modo por defecto."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REPO = "mariaherrerosanchez/Proyecto11_ESCENIQ_MariaHerrero"
OWNER, PROJECT = "mariaherrerosanchez", "3"
SPEC = Path(__file__).resolve().parents[1] / "specs" / "FUNCTIONAL_SPEC.md"
EPIC_RE = re.compile(r"^### Épica (E\d)\s*[—-]\s*(.+?)(?:\s*\(P\d(?:/P\d)?\))?\s*$")
STORY_RE = re.compile(r"^### US-(\d{3})\s*[—-]\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^\*\*(Prioridad|Épica):\*\*\s*(.+?)\s*$")
ISSUE_RE = re.compile(r"^US-(\d{3})\b")


@dataclass(frozen=True)
class Story:
    identifier: str
    title: str
    priority: str
    epic: str
    body: str

    @property
    def issue_title(self) -> str:
        return f"US-{self.identifier} — {self.title}"


def gh(*args: str) -> str:
    process = subprocess.run(["gh", *args], text=True, capture_output=True)
    if process.returncode:
        detail = process.stderr.strip() or process.stdout.strip() or "sin detalle"
        raise RuntimeError(f"gh {' '.join(args)}: {detail}")
    return process.stdout


def validate_stories(stories: list[Story]) -> None:
    expected = [f"{value:03d}" for value in range(1, 21)]
    if [story.identifier for story in stories] != expected:
        raise ValueError("Se esperaban US-001 a US-020, en orden y sin duplicados.")
    for story in stories:
        if story.priority not in {"P0", "P1", "P2", "P3"}:
            raise ValueError(f"US-{story.identifier}: prioridad inválida.")
        if not re.match(r"^E[1-5]\b", story.epic):
            raise ValueError(f"US-{story.identifier}: épica inválida.")
        if "#### Criterios de aceptación" not in story.body or "- [ ]" not in story.body:
            raise ValueError(f"US-{story.identifier}: faltan criterios verificables.")


def parse_stories(spec_path: Path = SPEC) -> list[Story]:
    """Conserva todos los apartados Markdown de cada historia en el cuerpo publicado."""
    current_epic = ""
    blocks: list[tuple[str, str, list[str]]] = []
    active: tuple[str, str, list[str]] | None = None
    for line in spec_path.read_text(encoding="utf-8").splitlines():
        if match := EPIC_RE.match(line):
            current_epic = f"{match.group(1)} — {match.group(2)}"
        elif match := STORY_RE.match(line):
            if active:
                blocks.append(active)
            active = (match.group(1), match.group(2), [])
        elif active:
            active[2].append(line)
    if active:
        blocks.append(active)

    stories = []
    for identifier, title, lines in blocks:
        fields = {match.group(1): match.group(2) for line in lines if (match := FIELD_RE.match(line))}
        priority, epic = fields.get("Prioridad"), fields.get("Épica", current_epic)
        if not priority or not epic:
            raise ValueError(f"US-{identifier} debe incluir Prioridad y Épica.")
        stories.append(Story(identifier, title, priority, epic, "\n".join(lines).strip() + "\n"))
    validate_stories(stories)
    return stories


def existing_issues(runner: Callable[..., str] = gh) -> dict[str, dict[str, object]]:
    raw = runner("issue", "list", "--repo", REPO, "--state", "all", "--limit", "500", "--json", "number,title,body,url")
    by_id: dict[str, dict[str, object]] = {}
    for issue in json.loads(raw):
        if match := ISSUE_RE.match(str(issue["title"])):
            identifier = match.group(1)
            if identifier in by_id:
                raise RuntimeError(f"Hay más de una issue existente para US-{identifier}.")
            by_id[identifier] = issue
    return by_id


def plan_sync(stories: list[Story], issues: dict[str, dict[str, object]]) -> list[tuple[str, Story, dict[str, object] | None]]:
    plan = []
    for story in stories:
        issue = issues.get(story.identifier)
        action = "CREAR" if issue is None else "SIN CAMBIOS" if issue.get("body", "") == story.body else "ACTUALIZAR"
        plan.append((action, story, issue))
    return plan


def with_body_file(body: str, callback: Callable[[Path], None]) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md", delete=False) as file:
        file.write(body)
        path = Path(file.name)
    try:
        callback(path)
    finally:
        path.unlink(missing_ok=True)


def apply_plan(plan: list[tuple[str, Story, dict[str, object] | None]], runner: Callable[..., str] = gh) -> None:
    """Existing issues keep their title, labels and Project association; only body changes."""
    for action, story, issue in plan:
        if action == "SIN CAMBIOS":
            print(f"SIN CAMBIOS US-{story.identifier}: #{issue['number']}")
        elif action == "ACTUALIZAR":
            number = str(issue["number"])
            with_body_file(story.body, lambda path: runner("issue", "edit", number, "--repo", REPO, "--body-file", str(path)))
            print(f"ACTUALIZADA US-{story.identifier}: #{number} (solo descripción)")
        else:
            created: list[str] = []
            with_body_file(story.body, lambda path: created.append(runner(
                "issue", "create", "--repo", REPO, "--title", story.issue_title, "--body-file", str(path),
                "--label", story.priority, "--label", story.epic.split(" ")[0],
            ).strip()))
            runner("project", "item-add", PROJECT, "--owner", OWNER, "--url", created[0])
            print(f"CREADA US-{story.identifier}: {created[0]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Crear o actualizar GitHub; por defecto solo vista previa")
    args = parser.parse_args()
    try:
        plan = plan_sync(parse_stories(), existing_issues())
        print("APLICACIÓN: se modificarán recursos remotos." if args.apply else "VISTA PREVIA: no se modificará GitHub.")
        for action, story, issue in plan:
            target = f"#{issue['number']}" if issue else story.issue_title
            print(f"{action}: US-{story.identifier} — {target}")
        if args.apply:
            apply_plan(plan)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
