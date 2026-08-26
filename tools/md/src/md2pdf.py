#!/usr/bin/env python3
"""Convert a Markdown file to a styled PDF, rendering Mermaid diagrams inline."""

import os
import re
import shutil
import subprocess
import sys
import tempfile

import click
import markdown
from pygments.formatters import HtmlFormatter
from weasyprint import HTML

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STYLE_CSS = os.path.join(SCRIPT_DIR, "style.css")

_MERMAID_RE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)


def _render_mermaid_blocks(source: str, tmp_dir: str) -> str:
    """Replace mermaid fenced blocks with absolute-path <img> HTML tags."""
    counter = 0

    def replace(match: re.Match) -> str:
        nonlocal counter
        counter += 1
        mmd_path = os.path.join(tmp_dir, f"diagram_{counter}.mmd")
        png_path = os.path.join(tmp_dir, f"diagram_{counter}.png")

        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(match.group(1))

        result = subprocess.run(
            ["mmdc", "-i", mmd_path, "-o", png_path, "--backgroundColor", "white"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(
                f"warning: mmdc failed for diagram {counter}:\n{result.stderr}",
                file=sys.stderr,
            )
            return match.group(0)

        # Raw HTML block — passed through by python-markdown
        return f'\n\n<figure><img src="file://{png_path}" alt="Diagram {counter}"></figure>\n\n'

    return _MERMAID_RE.sub(replace, source)


def _build_html(md_source: str, base_url: str) -> str:
    body = markdown.markdown(
        md_source,
        extensions=["fenced_code", "codehilite", "tables", "toc", "attr_list"],
        extension_configs={"codehilite": {"guess_lang": False}},
    )

    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        user_css = f.read()

    pygments_css = HtmlFormatter(style="friendly").get_style_defs(".codehilite")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <style>
{user_css}
{pygments_css}
  </style>
</head>
<body>
{body}
</body>
</html>"""


def convert(input_md: str, output_pdf: str) -> None:
    tmp_dir = tempfile.mkdtemp(prefix="md2pdf_")
    try:
        with open(input_md, "r", encoding="utf-8") as f:
            source = f.read()

        source = _render_mermaid_blocks(source, tmp_dir)

        base_url = "file://" + os.path.dirname(input_md) + "/"
        html = _build_html(source, base_url)

        HTML(string=html, base_url=base_url).write_pdf(output_pdf)
        print(f"PDF written: {output_pdf}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("input_md")
@click.argument("output_pdf", required=False)
def main(input_md: str, output_pdf: str | None) -> None:
    """Convert Markdown to PDF.

    INPUT_MD is the Markdown file to convert. OUTPUT_PDF is the optional
    destination path; it defaults to the input path with a .pdf suffix.
    """
    input_md = os.path.abspath(input_md)
    if not os.path.isfile(input_md):
        click.echo(f"error: file not found: {input_md}", err=True)
        sys.exit(1)

    if output_pdf:
        output_pdf = os.path.abspath(output_pdf)
    else:
        output_pdf = os.path.splitext(input_md)[0] + ".pdf"

    convert(input_md, output_pdf)


if __name__ == "__main__":
    main()
