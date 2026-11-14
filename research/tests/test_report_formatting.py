import unittest

from research.report_formatting import compose_model_sections


class ModelReportSectionsTests(unittest.TestCase):
    def test_model_rows_stay_in_model_table_before_direction_section(self):
        model_rows = ["| logistic | 0.55 | 79/712 | ... |", "| random_forest | 0.55 | 60/712 | ... |"]
        direction_rows = ["| logistic | TEST | CALL | 56/386 | ... |"]
        sections = compose_model_sections(model_rows, direction_rows)

        model_heading = sections.index("## Model comparison")
        model_header = next(i for i, row in enumerate(sections) if row.startswith("| Model | Threshold |"))
        first_model = sections.index(model_rows[0])
        second_model = sections.index(model_rows[1])
        direction_heading = sections.index("## Direction and WAIT-filter diagnostics")
        direction_header = next(i for i, row in enumerate(sections) if row.startswith("| Model | Split |"))
        first_direction = sections.index(direction_rows[0])

        self.assertLess(model_heading, model_header)
        self.assertLess(model_header, first_model)
        self.assertLess(first_model, second_model)
        self.assertLess(second_model, direction_heading)
        self.assertLess(direction_heading, direction_header)
        self.assertLess(direction_header, first_direction)


if __name__ == "__main__":
    unittest.main()
