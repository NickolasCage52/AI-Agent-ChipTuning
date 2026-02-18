from __future__ import annotations

import csv
import io
import os
import zipfile
from xml.sax.saxutils import escape


ROOT = os.path.dirname(__file__)
CSV_PATH = os.path.join(ROOT, "supplier_price.csv")
XLSX_PATH = os.path.join(ROOT, "supplier_price.xlsx")


def col_name(idx: int) -> str:
    # 0 -> A
    name = ""
    i = idx + 1
    while i:
        i, r = divmod(i - 1, 26)
        name = chr(ord("A") + r) + name
    return name


def cell(ref: str, value: str) -> str:
    # inline string cell
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def cell_num(ref: str, value: str) -> str:
    return f'<c r="{ref}"><v>{escape(value)}</v></c>'


def build_sheet(rows: list[list[str]]) -> str:
    sheet_rows = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx, v in enumerate(row):
            ref = f"{col_name(c_idx)}{r_idx}"
            vv = (v or "").strip()
            if c_idx in (4, 5, 6):  # price/stock/delivery_days as numbers when possible
                try:
                    float(vv.replace(",", "."))
                    cells.append(cell_num(ref, vv.replace(",", ".")))
                    continue
                except Exception:
                    pass
            cells.append(cell(ref, vv))
        sheet_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

    dim = f"A1:{col_name(max(0, len(rows[0]) - 1))}{len(rows)}" if rows else "A1:A1"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dim}"/>'
        "<sheetData>"
        + "".join(sheet_rows)
        + "</sheetData>"
        "</worksheet>"
    )


def main() -> None:
    with open(CSV_PATH, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(text), delimiter=";")
    rows = [list(r) for r in reader if r]
    if len(rows) < 21:
        raise SystemExit("CSV must have 20+ data rows for demo")

    sheet1 = build_sheet(rows)

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""

    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Price" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""

    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""

    os.makedirs(ROOT, exist_ok=True)
    with zipfile.ZipFile(XLSX_PATH, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet1)

    print(f"Generated: {XLSX_PATH}")


if __name__ == "__main__":
    main()

