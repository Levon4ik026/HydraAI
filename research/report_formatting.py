"""Small, dependency-free Markdown section builder for research reports."""

def compose_model_sections(model_rows, direction_rows):
    """Keep model summary rows inside their own table, before direction diagnostics."""
    return [
        "",
        "## Model comparison",
        "",
        "Each model is fitted only on TRAIN decisive outcomes. Its threshold is selected only on VALIDATION from the fixed grid 0.50–0.75, requiring at least 40 accepted validation trades. The selected threshold is then frozen for TEST. Rejected model signals are WAIT.",
        "| Model | Threshold | VAL accepted | VAL W/L/D | VAL WR | VAL net | TEST accepted | TEST W/L/D | TEST WR | TEST Wilson 95% CI | TEST net | TEST ROI | TEST PF | TEST maxDD | TEST max loss streak |",
        "|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        *model_rows,
        "",
        "## Direction and WAIT-filter diagnostics",
        "",
        "| Model | Split | Direction | Accepted / base signals | WAIT count (%) | W/L/D | Decisive WR | Wilson 95% CI | Wins / all | Net | ROI | PF | Max DD | Max loss streak |",
        "|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        *direction_rows,
    ]
