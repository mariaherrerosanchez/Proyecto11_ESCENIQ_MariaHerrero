"""Pruebas locales del parser y el plan de sincronización, sin acceso a GitHub."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("sync_issues.py")
SPEC = importlib.util.spec_from_file_location("sync_issues", SCRIPT)
sync_issues = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = sync_issues
SPEC.loader.exec_module(sync_issues)


class SyncIssuesTests(unittest.TestCase):
    def test_parser_reads_twenty_complete_stories(self):
        stories = sync_issues.parse_stories()
        self.assertEqual([story.identifier for story in stories], [f"{value:03d}" for value in range(1, 21)])
        self.assertEqual({story.epic.split(" ")[0] for story in stories}, {"E1", "E2", "E3", "E4", "E5"})
        self.assertEqual([story.priority for story in stories].count("P0"), 8)
        self.assertIn("#### Fuera de alcance", stories[0].body)
        self.assertIn("- [ ]", stories[19].body)

    def test_plan_is_idempotent_and_detects_description_changes(self):
        stories = sync_issues.parse_stories()
        expected_body = stories[0].body
        remote = {"001": {"number": 10, "title": "US-001 — título existente", "body": expected_body, "url": "https://example/10"}}
        plan = sync_issues.plan_sync(stories, remote)
        self.assertEqual(plan[0][0], "SIN CAMBIOS")
        remote["001"]["body"] = "descripción anterior"
        self.assertEqual(sync_issues.plan_sync(stories, remote)[0][0], "ACTUALIZAR")
        self.assertEqual(plan[1][0], "CREAR")

    def test_existing_issues_matches_identifier_not_title_text(self):
        payload = json.dumps([{"number": 3, "title": "US-003 — título renombrado", "body": "", "url": "u"}])
        issues = sync_issues.existing_issues(lambda *args: payload)
        self.assertEqual(issues["003"]["number"], 3)


if __name__ == "__main__":
    unittest.main()
