import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "rwe_validator.py"
SPEC = importlib.util.spec_from_file_location("rwe_validator", MODULE_PATH)
assert SPEC and SPEC.loader
rwe_validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rwe_validator
SPEC.loader.exec_module(rwe_validator)


class ValidatorTest(unittest.TestCase):
    def setUp(self):
        rules_path = Path(__file__).parents[1] / "config" / "validation-rules.json"
        self.config = json.loads(rules_path.read_text(encoding="utf-8"))
        self.fields = [rule["name"] for rule in self.config["columns"]]

    def test_valid_row_has_no_findings(self):
        rows = [{
            "patient_id": "P1",
            "sex_code": "F",
            "age": "70",
            "index_date": "2026-01-01",
            "followup_date": "2026-02-01",
            "diagnosis_code": "G30.1",
            "score": "25",
        }]
        self.assertEqual(rwe_validator.validate_rows(self.fields, rows, self.config), [])

    def test_invalid_values_and_duplicate_are_detected(self):
        row = {
            "patient_id": "P1",
            "sex_code": "X",
            "age": "140",
            "index_date": "2026-03-01",
            "followup_date": "2026-02-01",
            "diagnosis_code": "UNKNOWN",
            "score": "40",
        }
        findings = rwe_validator.validate_rows(self.fields, [row, row.copy()], self.config)
        rule_ids = {finding.rule_id for finding in findings}
        self.assertIn("column.sex_code.allowed_values", rule_ids)
        self.assertIn("column.age.max", rule_ids)
        self.assertIn("date_order.followup_not_before_index", rule_ids)
        self.assertIn("unique.patient_visit_unique", rule_ids)

    def test_cli_writes_reports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_path = root / "data.csv"
            rules_path = Path(__file__).parents[1] / "config" / "validation-rules.json"
            json_path = root / "report.json"
            md_path = root / "report.md"
            csv_path.write_text(
                "patient_id,sex_code,age,index_date,followup_date,diagnosis_code,score\n"
                "P1,F,70,2026-01-01,2026-02-01,G30.1,25\n",
                encoding="utf-8",
            )
            exit_code = rwe_validator.main([
                "--input", str(csv_path),
                "--rules", str(rules_path),
                "--output-json", str(json_path),
                "--output-md", str(md_path),
            ])
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(json_path.read_text())["status"], "pass")
            self.assertIn("승인 가능", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
