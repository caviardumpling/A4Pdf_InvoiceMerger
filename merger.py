from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf._page import PageObject


Mode = Literal["A4_2UP_PORTRAIT", "A4_4UP_LANDSCAPE"]


@dataclass(frozen=True)
class MergeProgress:
    current: int
    total: int
    source_path: str
    source_page_index: int


def _a4_size_pt() -> tuple[float, float]:
    return 595.275590551, 841.88976378


def _rects_a4_2up_portrait_top_origin(margin: float) -> tuple[tuple[float, float, float, float], ...]:
    w, h = _a4_size_pt()
    gutter = margin
    top = (margin, margin, w - margin, (h / 2) - (gutter / 2))
    bottom = (margin, (h / 2) + (gutter / 2), w - margin, h - margin)
    return top, bottom


def _rects_a4_4up_landscape_top_origin(margin: float) -> tuple[tuple[float, float, float, float], ...]:
    w, h = _a4_size_pt()
    w, h = h, w
    gutter = margin
    mid_x = w / 2
    mid_y = h / 2

    x0 = margin
    x1 = w - margin
    y0 = margin
    y1 = h - margin

    x_left_1 = mid_x - (gutter / 2)
    x_right_0 = mid_x + (gutter / 2)
    y_top_1 = mid_y - (gutter / 2)
    y_bottom_0 = mid_y + (gutter / 2)

    tl = (x0, y0, x_left_1, y_top_1)
    tr = (x_right_0, y0, x1, y_top_1)
    bl = (x0, y_bottom_0, x_left_1, y1)
    br = (x_right_0, y_bottom_0, x1, y1)
    return tl, tr, bl, br


def _rects_a4_2up_portrait(margin: float) -> tuple[tuple[float, float, float, float], ...]:
    w, h = _a4_size_pt()
    gutter = margin
    bottom = (margin, margin, w - margin, (h / 2) - (gutter / 2))
    top = (margin, (h / 2) + (gutter / 2), w - margin, h - margin)
    return bottom, top


def _rects_a4_4up_landscape(margin: float) -> tuple[tuple[float, float, float, float], ...]:
    w, h = _a4_size_pt()
    w, h = h, w
    gutter = margin
    mid_x = w / 2
    mid_y = h / 2

    x0 = margin
    x1 = w - margin
    y0 = margin
    y1 = h - margin

    x_left_1 = mid_x - (gutter / 2)
    x_right_0 = mid_x + (gutter / 2)
    y_bottom_1 = mid_y - (gutter / 2)
    y_top_0 = mid_y + (gutter / 2)

    bl = (x0, y0, x_left_1, y_bottom_1)
    br = (x_right_0, y0, x1, y_bottom_1)
    tl = (x0, y_top_0, x_left_1, y1)
    tr = (x_right_0, y_top_0, x1, y1)
    return bl, br, tl, tr


def _collect_pages(
    input_paths: Iterable[str | Path],
) -> tuple[list[tuple[str, PdfReader]], list[tuple[int, int]]]:
    readers: list[tuple[str, PdfReader]] = []
    page_refs: list[tuple[int, int]] = []

    for p in input_paths:
        path = str(Path(p))
        f = open(path, "rb")
        reader = PdfReader(f)
        readers.append((path, reader))
        reader_index = len(readers) - 1
        for page_index in range(len(reader.pages)):
            page_refs.append((reader_index, page_index))

    return readers, page_refs


def _place_page(
    out_page: PageObject,
    src_page: PageObject,
    rect: tuple[float, float, float, float],
) -> None:
    x0, y0, x1, y1 = rect
    dst_w = x1 - x0
    dst_h = y1 - y0

    src_w = float(src_page.mediabox.width)
    src_h = float(src_page.mediabox.height)
    if src_w <= 0 or src_h <= 0:
        return

    scale = min(dst_w / src_w, dst_h / src_h)
    tx = x0 + (dst_w - (src_w * scale)) / 2
    ty = y0 + (dst_h - (src_h * scale)) / 2

    transform = Transformation().scale(scale, scale).translate(tx, ty)
    out_page.merge_transformed_page(src_page, transform, expand=False)


def merge_invoices_to_a4(
    input_paths: list[str | Path],
    output_path: str | Path,
    mode: Mode,
    margin_pt: float = 18.0,
    render_compat: bool = True,
    render_dpi: int = 220,
    progress_callback: Callable[[MergeProgress], None] | None = None,
) -> None:
    if render_compat:
        _merge_invoices_to_a4_rendered(
            input_paths=input_paths,
            output_path=output_path,
            mode=mode,
            margin_pt=margin_pt,
            render_dpi=render_dpi,
            progress_callback=progress_callback,
        )
        return

    _merge_invoices_to_a4_vector(
        input_paths=input_paths,
        output_path=output_path,
        mode=mode,
        margin_pt=margin_pt,
        progress_callback=progress_callback,
    )


def _merge_invoices_to_a4_vector(
    input_paths: list[str | Path],
    output_path: str | Path,
    mode: Mode,
    margin_pt: float,
    progress_callback: Callable[[MergeProgress], None] | None,
) -> None:
    if not input_paths:
        raise ValueError("未选择任何PDF文件")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    readers, page_refs = _collect_pages(input_paths)
    try:
        if mode == "A4_2UP_PORTRAIT":
            page_w, page_h = _a4_size_pt()
            slots = 2
            rects = _rects_a4_2up_portrait(margin_pt)
        elif mode == "A4_4UP_LANDSCAPE":
            w, h = _a4_size_pt()
            page_w, page_h = h, w
            slots = 4
            rects = _rects_a4_4up_landscape(margin_pt)
        else:
            raise ValueError(f"未知模式: {mode}")

        writer = PdfWriter()
        total = len(page_refs)
        if total == 0:
            raise ValueError("没有可合并的页面")

        for start in range(0, total, slots):
            out_page = PageObject.create_blank_page(width=page_w, height=page_h)
            for slot_index in range(slots):
                idx = start + slot_index
                if idx >= total:
                    break
                reader_i, page_i = page_refs[idx]
                source_path, reader = readers[reader_i]
                src_page = reader.pages[page_i]
                _place_page(out_page, src_page, rects[slot_index])
                if progress_callback:
                    progress_callback(
                        MergeProgress(
                            current=idx + 1,
                            total=total,
                            source_path=source_path,
                            source_page_index=page_i,
                        )
                    )
            writer.add_page(out_page)

        with open(output_path, "wb") as f_out:
            writer.write(f_out)
    finally:
        for _, reader in readers:
            try:
                reader.stream.close()  # type: ignore[attr-defined]
            except Exception:
                pass


def _merge_invoices_to_a4_rendered(
    input_paths: list[str | Path],
    output_path: str | Path,
    mode: Mode,
    margin_pt: float,
    render_dpi: int,
    progress_callback: Callable[[MergeProgress], None] | None,
) -> None:
    if not input_paths:
        raise ValueError("未选择任何PDF文件")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import io

    import pypdfium2 as pdfium
    from fpdf import FPDF

    if mode == "A4_2UP_PORTRAIT":
        page_w, page_h = _a4_size_pt()
        slots = 2
        rects = _rects_a4_2up_portrait_top_origin(margin_pt)
    elif mode == "A4_4UP_LANDSCAPE":
        w, h = _a4_size_pt()
        page_w, page_h = h, w
        slots = 4
        rects = _rects_a4_4up_landscape_top_origin(margin_pt)
    else:
        raise ValueError(f"未知模式: {mode}")

    docs: list[tuple[str, pdfium.PdfDocument]] = []
    page_refs: list[tuple[int, int]] = []
    for p in input_paths:
        path = str(Path(p))
        doc = pdfium.PdfDocument(path)
        docs.append((path, doc))
        doc_i = len(docs) - 1
        for page_i in range(len(doc)):
            page_refs.append((doc_i, page_i))

    total = len(page_refs)
    if total == 0:
        raise ValueError("没有可合并的页面")

    pdf = FPDF(unit="pt", format=(page_w, page_h))
    try:
        for start in range(0, total, slots):
            pdf.add_page()
            for slot_index in range(slots):
                idx = start + slot_index
                if idx >= total:
                    break
                doc_i, page_i = page_refs[idx]
                source_path, doc = docs[doc_i]
                page = doc.get_page(page_i)
                try:
                    src_w = float(page.get_width())
                    src_h = float(page.get_height())

                    x0, y0, x1, y1 = rects[slot_index]
                    dst_w = x1 - x0
                    dst_h = y1 - y0
                    if dst_w <= 0 or dst_h <= 0 or src_w <= 0 or src_h <= 0:
                        continue

                    fit_scale = min(dst_w / src_w, dst_h / src_h)
                    target_scale = (render_dpi / 72.0) * fit_scale
                    target_scale = max(0.5, min(6.0, target_scale))

                    bitmap = page.render(scale=target_scale)
                    img = bitmap.to_pil()

                    buf = io.BytesIO()
                    img.save(buf, format="PNG", optimize=True)
                    buf.seek(0)

                    img_w = float(img.width)
                    img_h = float(img.height)
                    if img_w <= 0 or img_h <= 0:
                        continue
                    place_scale = min(dst_w / img_w, dst_h / img_h)
                    place_w = img_w * place_scale
                    place_h = img_h * place_scale
                    place_x = x0 + (dst_w - place_w) / 2
                    place_y = y0 + (dst_h - place_h) / 2

                    pdf.image(buf, x=place_x, y=place_y, w=place_w, h=place_h)

                    if progress_callback:
                        progress_callback(
                            MergeProgress(
                                current=idx + 1,
                                total=total,
                                source_path=source_path,
                                source_page_index=page_i,
                            )
                        )
                finally:
                    page.close()

        pdf.output(str(output_path))
    finally:
        for _, d in docs:
            try:
                d.close()
            except Exception:
                pass

