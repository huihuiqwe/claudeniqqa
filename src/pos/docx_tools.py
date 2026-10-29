"""Обёртка над python-docx: оформление записки по ГОСТ 7.32 (Times New Roman 14,
полуторный интервал, абзацный отступ 1,25 см), таблицы, рисунки, формулы."""
from __future__ import annotations

import re

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor

FONT = "Times New Roman"
TOKEN = re.compile(r"(_\[[^\]]*\]|\^\[[^\]]*\]|\*\*[^*]+\*\*)")


def num(x: float, nd: int = 0) -> str:
    """Число в русской записи: неразрывный пробел между разрядами, десятичная запятая."""
    s = f"{x:,.{nd}f}"
    if s.startswith("-"):
        s = "−" + s[1:]
    return s.replace(",", " ").replace(".", ",")


def plural(n: int, one: str, few: str, many: str) -> str:
    """Согласование существительного с числительным: 1 свая, 2 сваи, 5 свай."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _set_font(run, size=None, bold=None, italic=None):
    run.font.name = FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONT)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def add_runs(par, text: str, size=None, bold=None, italic=None):
    """Текст с разметкой: _[нижний индекс], ^[верхний индекс], **полужирный**."""
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith("_["):
            run = par.add_run(part[2:-1])
            run.font.subscript = True
            _set_font(run, size, bold, italic)
        elif part.startswith("^["):
            run = par.add_run(part[2:-1])
            run.font.superscript = True
            _set_font(run, size, bold, italic)
        elif part.startswith("**"):
            run = par.add_run(part[2:-2])
            _set_font(run, size, True, italic)
        else:
            run = par.add_run(part)
            _set_font(run, size, bold, italic)
    return par


def _field(par, instr: str, placeholder: str = ""):
    run = par.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    run._r.append(fld)
    run = par.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    run._r.append(it)
    run = par.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "separate")
    run._r.append(fld)
    run = par.add_run(placeholder)
    _set_font(run)
    run = par.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "end")
    run._r.append(fld)


class Doc:
    TEXT_W = 16.5        # см, ширина текста на листе А4 (30 + 15 мм поля)
    TEXT_W_LAND = 24.7   # см, ширина текста на альбомном листе

    def __init__(self):
        self.d = Document()
        self.n_tab = 0
        self.n_fig = 0
        self.n_frm = 0
        self.appendix = ""
        self._setup()

    # ----------------------------------------------------------- оформление
    def _setup(self):
        sec = self.d.sections[0]
        sec.page_width, sec.page_height = Mm(210), Mm(297)
        self._margins(sec)
        st = self.d.styles["Normal"]
        st.font.name = FONT
        st.font.size = Pt(14)
        rpr = st.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.insert(0, rf)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(attr), FONT)
        pf = st.paragraph_format
        pf.line_spacing = 1.5
        pf.space_after = Pt(0)
        pf.space_before = Pt(0)
        pf.first_line_indent = Cm(1.25)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for name, size in (("Heading 1", 14), ("Heading 2", 14)):
            h = self.d.styles[name]
            h.font.name = FONT
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.italic = False
            h.font.color.rgb = RGBColor(0, 0, 0)
            hr = h.element.get_or_add_rPr()
            hf = hr.find(qn("w:rFonts"))
            if hf is None:
                hf = OxmlElement("w:rFonts")
                hr.insert(0, hf)
            for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                hf.set(qn(attr), FONT)
            for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
                if hf.get(qn(attr)) is not None:
                    del hf.attrib[qn(attr)]
            hp = h.paragraph_format
            hp.first_line_indent = Cm(1.25)
            hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            hp.space_before = Pt(12)
            hp.space_after = Pt(6)
            hp.line_spacing = 1.5
            hp.keep_with_next = True
        for name, left in (("toc 1", 0.0), ("toc 2", 0.5)):
            try:
                ts = self.d.styles[name]
            except KeyError:
                ts = self.d.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            ts.base_style = st
            tf = ts.paragraph_format
            tf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            tf.first_line_indent = Cm(0)
            tf.left_indent = Cm(left)
            tf.line_spacing = 1.5
        # нумерация страниц в нижнем колонтитуле
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fp.paragraph_format.first_line_indent = Cm(0)
        _field(fp, "PAGE", "1")
        sec.different_first_page_header_footer = True
        # обновление полей (оглавления) при открытии в Word
        settings = self.d.settings.element
        upd = OxmlElement("w:updateFields")
        upd.set(qn("w:val"), "true")
        settings.append(upd)

    @staticmethod
    def _margins(sec):
        sec.left_margin, sec.right_margin = Mm(30), Mm(15)
        sec.top_margin, sec.bottom_margin = Mm(20), Mm(20)

    # ----------------------------------------------------------- текст
    def p(self, text: str = "", indent=True, align="justify", size=None, bold=None, italic=None,
          space_after=0, spacing=None, keep_next=False):
        par = self.d.add_paragraph()
        pf = par.paragraph_format
        pf.first_line_indent = Cm(1.25) if indent else Cm(0)
        pf.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                        "left": WD_ALIGN_PARAGRAPH.LEFT, "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        if space_after:
            pf.space_after = Pt(space_after)
        if spacing is not None:
            pf.line_spacing = spacing
        if keep_next:
            pf.keep_with_next = True
        add_runs(par, text, size, bold, italic)
        return par

    def h1(self, text: str, new_page=False):
        par = self.d.add_paragraph(style="Heading 1")
        par.paragraph_format.page_break_before = new_page
        add_runs(par, text)
        return par

    def h2(self, text: str):
        par = self.d.add_paragraph(style="Heading 2")
        add_runs(par, text)
        return par

    def h_center(self, text: str, new_page=True):
        """Заголовок структурного элемента (СОДЕРЖАНИЕ, ВВЕДЕНИЕ…): по центру, в оглавлении."""
        par = self.d.add_paragraph(style="Heading 1")
        par.paragraph_format.page_break_before = new_page
        par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.first_line_indent = Cm(0)
        add_runs(par, text)
        return par

    def bullets(self, items, size=None):
        for it in items:
            self.p("– " + it, size=size)

    def numbered(self, items, size=None):
        for i, it in enumerate(items, 1):
            self.p(f"{i}) {it}", size=size)

    def page_break(self):
        par = self.d.add_paragraph()
        par.paragraph_format.first_line_indent = Cm(0)
        par.add_run().add_break(WD_BREAK.PAGE)

    def formula(self, text: str, where: list[str] | None = None, number=True, then: list[str] | None = None):
        par = self.d.add_paragraph()
        pf = par.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.space_before = Pt(3)
        pf.space_after = Pt(3)
        w = self.TEXT_W if not self.appendix else self.TEXT_W_LAND
        pf.tab_stops.add_tab_stop(Cm(w / 2), WD_TAB_ALIGNMENT.CENTER)
        pf.tab_stops.add_tab_stop(Cm(w), WD_TAB_ALIGNMENT.RIGHT)
        add_runs(par, "\t" + text)
        if number:
            self.n_frm += 1
            add_runs(par, f"\t({self.n_frm})")
        if where:
            first = True
            for line in where:
                q = self.p(("где " if first else "") + line, indent=not first)
                if first:
                    q.paragraph_format.first_line_indent = Cm(0)
                first = False
        for line in then or []:
            self.p(line, indent=False, align="center")
        return self.n_frm

    # ----------------------------------------------------------- таблицы
    def tnext(self) -> str:
        return f"{self.appendix}{'.' if self.appendix else ''}{self.n_tab + 1}"

    def fnext(self) -> str:
        return f"{self.appendix}{'.' if self.appendix else ''}{self.n_fig + 1}"

    def table(self, caption: str, header, rows, widths, size=11, header_rows=1, align=None,
              bold_rows=(), merge=None):
        self.n_tab += 1
        label = f"{self.appendix}{'.' if self.appendix else ''}{self.n_tab}"
        cap = self.p(f"Таблица {label} – {caption}", indent=False, align="left", keep_next=True)
        cap.paragraph_format.space_before = Pt(6)
        all_rows = ([header] if header and not isinstance(header[0], (list, tuple)) else list(header or [])) + list(rows)
        n_head = header_rows if header else 0
        ncols = len(widths)
        t = self.d.add_table(rows=len(all_rows), cols=ncols)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for ci, col in enumerate(t.columns):
            col.width = Cm(widths[ci])
        tblPr = t._tbl.tblPr
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "fixed")
        tblPr.append(lay)
        for ri, row in enumerate(all_rows):
            tr = t.rows[ri]
            if ri < n_head:
                trPr = tr._tr.get_or_add_trPr()
                th = OxmlElement("w:tblHeader")
                th.set(qn("w:val"), "true")
                trPr.append(th)
            for ci in range(ncols):
                cell = tr.cells[ci]
                cell.width = Cm(widths[ci])
                val = row[ci] if ci < len(row) else ""
                par = cell.paragraphs[0]
                pf = par.paragraph_format
                pf.first_line_indent = Cm(0)
                pf.line_spacing = 1.0
                if ri < n_head:
                    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    a = (align or ["l"] * ncols)[ci]
                    pf.alignment = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER,
                                    "r": WD_ALIGN_PARAGRAPH.RIGHT, "j": WD_ALIGN_PARAGRAPH.JUSTIFY}[a]
                bold = ri < n_head or ri in bold_rows
                lines = str(val).split("\n")
                for li, line in enumerate(lines):
                    if li:
                        par = cell.add_paragraph()
                        par.paragraph_format.first_line_indent = Cm(0)
                        par.paragraph_format.line_spacing = 1.0
                        par.paragraph_format.alignment = pf.alignment
                    add_runs(par, line, size, bold=bold or None)
        if merge:
            for (r0, c0, r1, c1) in merge:
                a = t.cell(r0, c0)
                b = t.cell(r1, c1)
                txt = a.text
                m = a.merge(b)
                # после объединения остаётся текст всех ячеек — оставляем первый
                for par in m.paragraphs[1:]:
                    par._element.getparent().remove(par._element)
                if not m.paragraphs[0].text:
                    add_runs(m.paragraphs[0], txt, size, bold=True)
        after = self.d.add_paragraph()
        after.paragraph_format.first_line_indent = Cm(0)
        after.paragraph_format.line_spacing = 1.0
        return label

    # ----------------------------------------------------------- рисунки
    def figure(self, path: str, caption: str, width_cm: float):
        self.n_fig += 1
        label = f"{self.appendix}{'.' if self.appendix else ''}{self.n_fig}"
        par = self.d.add_paragraph()
        par.paragraph_format.first_line_indent = Cm(0)
        par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = True
        par.add_run().add_picture(path, width=Cm(width_cm))
        cap = self.p(f"Рисунок {label} – {caption}", indent=False, align="center", space_after=6)
        cap.paragraph_format.line_spacing = 1.0
        return label

    # ----------------------------------------------------------- разделы
    def landscape(self):
        sec = self.d.add_section(WD_SECTION.NEW_PAGE)
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = Mm(297), Mm(210)
        sec.left_margin, sec.right_margin = Mm(20), Mm(15)
        sec.top_margin, sec.bottom_margin = Mm(20), Mm(15)
        sec.different_first_page_header_footer = False
        return sec

    def portrait(self):
        sec = self.d.add_section(WD_SECTION.NEW_PAGE)
        sec.orientation = WD_ORIENT.PORTRAIT
        sec.page_width, sec.page_height = Mm(210), Mm(297)
        self._margins(sec)
        sec.different_first_page_header_footer = False
        return sec

    def toc(self):
        par = self.d.add_paragraph()
        par.paragraph_format.first_line_indent = Cm(0)
        _field(par, 'TOC \\o "1-2" \\h \\z \\u',
               "Оглавление формируется автоматически: в Word — правый щелчок → «Обновить поле».")

    def save(self, path: str):
        self.d.save(path)
