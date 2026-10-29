"""Обновление оглавления и экспорт в PDF через LibreOffice (UNO)."""
from __future__ import annotations

import os
import subprocess
import tempfile
import time

import uno
from com.sun.star.beans import PropertyValue


def _prop(name, value):
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


def export(docx_path: str, pdf_path: str | None = None, docx_out: str | None = None) -> None:
    pipe = f"posbuild{os.getpid()}"
    profile = tempfile.mkdtemp(prefix="lo_profile_")
    proc = subprocess.Popen(
        ["soffice", "--headless", "--invisible", "--norestore", "--nologo",
         f"-env:UserInstallation=file://{profile}", f"--accept=pipe,name={pipe};urp;"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        ctx = None
        for _ in range(120):
            try:
                ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
                break
            except Exception:
                time.sleep(0.5)
        if ctx is None:
            raise RuntimeError("LibreOffice не запустился")
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        url = uno.systemPathToFileUrl(os.path.abspath(docx_path))
        doc = desktop.loadComponentFromURL(url, "_blank", 0, (_prop("Hidden", True),))
        indexes = doc.getDocumentIndexes()
        for _ in range(2):   # второй проход — после того как оглавление сдвинуло страницы
            for i in range(indexes.getCount()):
                indexes.getByIndex(i).update()
        if pdf_path:
            doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(pdf_path)),
                           (_prop("FilterName", "writer_pdf_Export"),))
        if docx_out:
            doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(docx_out)),
                           (_prop("FilterName", "MS Word 2007 XML"),))
        doc.close(True)
        try:
            desktop.terminate()
        except Exception:
            pass
    finally:
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
