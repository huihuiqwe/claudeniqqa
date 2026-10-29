"""Сборка пояснительной записки ПОС: расчёт → рисунки → DOCX → PDF.

Запуск из каталога src:
    python3 build.py            # DOCX и PDF в корне репозитория
    python3 build.py --no-pdf   # только DOCX (без LibreOffice)
"""
from __future__ import annotations

import argparse
import os

from pos import calc, content, figures

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "POS_148-037sp-1.2_Norilsk"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--out", default=ROOT)
    args = ap.parse_args()

    r = calc.compute()
    figs = figures.make_all(r, os.path.join(args.out, "figures"))
    raw = os.path.join(args.out, f"{NAME}.raw.docx")
    content.build(r, figs, raw)
    docx = os.path.join(args.out, f"{NAME}.docx")
    if args.no_pdf:
        os.replace(raw, docx)
        print(docx)
        return
    from pos import lo_export
    pdf = os.path.join(args.out, f"{NAME}.pdf")
    # LibreOffice обновляет оглавление (номера страниц) и сохраняет PDF и итоговый DOCX
    lo_export.export(raw, pdf_path=pdf, docx_out=docx)
    os.remove(raw)
    print(docx)
    print(pdf)


if __name__ == "__main__":
    main()
