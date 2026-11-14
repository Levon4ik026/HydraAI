import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reversal_day_cluster_bootstrap import write_report


class ReversalDayBootstrapReportTests(unittest.TestCase):
    def test_report_uses_real_newlines(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.md"
            write_report(path, ["# Header", "", "| A |"])
            self.assertEqual(path.read_text(encoding="utf-8"), "# Header\n\n| A |")
            self.assertNotIn(r"\n", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
