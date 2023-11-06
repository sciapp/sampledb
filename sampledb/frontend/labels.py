"""
Module for generation sample/object labels as PDF files.
"""
import io
import base64
import os
import typing
from math import log10, ceil

from PIL import Image
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.units import mm

import qrcode
import qrcode.image.pil


DEFAULT_PAPER_FORMAT = 'DIN A4 (Portrait)'
PAGE_SIZES = {
    'DIN A4 (Portrait)': A4,
    'DIN A4 (Landscape)': (A4[1], A4[0]),
    'Letter (Portrait)': LETTER,
    'Letter (Landscape)': (LETTER[1], LETTER[0])
}

HORIZONTAL_LABEL_MARGIN = 10
VERTICAL_LABEL_MARGIN = 10


def _generate_ghs_image_uris() -> typing.List[str]:
    ghs_image_uris = []
    GHS_IMAGE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'static', 'sampledb', 'img')
    for i in range(0, 10):
        ghs_image = Image.open(os.path.join(GHS_IMAGE_DIR, f'ghs0{i}.png')).convert('RGBA')
        ghs_background_image = Image.new('RGBA', ghs_image.size, (255, 255, 255, 255))
        ghs_image = Image.alpha_composite(ghs_background_image, ghs_image)
        image_stream = io.BytesIO()
        ghs_image.save(image_stream, format='png')
        image_stream.seek(0)
        ghs_image_uri = 'data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8')
        ghs_image_uris.append(ghs_image_uri)
    return ghs_image_uris


GHS_IMAGE_URIS = _generate_ghs_image_uris()


def _draw_centered_wrapped_text(
        canvas: Canvas,
        text: str,
        left_offset: float,
        width: float,
        top_cursor: float,
        font_name: str,
        font_size: float,
        line_height: float
) -> float:
    lines = []
    while text:
        text = text.lstrip()
        line = text
        while canvas.stringWidth(line, font_name, font_size) > width:
            if ' ' in line:
                line = line.rsplit(' ', 1)[0]
            else:
                line = line[:-1]
        lines.append(line.strip())
        text = text[len(line):]

    canvas.setFont(font_name, font_size)
    for line in lines:
        if line:
            canvas.drawCentredString(left_offset + width / 2, top_cursor, line)
            top_cursor -= line_height * font_size
    return top_cursor


def _draw_label(
        canvas: Canvas,
        sample_name: str,
        sample_creator: str,
        sample_creation_date: str,
        sample_id: int,
        ghs_classes: typing.List[int],
        qrcode_uri: str,
        left_offset: float,
        top_offset: float,
        width: float,
        minimum_height: float,
        qrcode_width: float,
        ghs_classes_side_by_side: bool = False,
        centered: bool = True
) -> float:
    font_name = "Helvetica"
    font_size = 8
    right_offset = left_offset + width
    top_cursor: float = top_offset - 3 * mm

    top_cursor = _draw_centered_wrapped_text(canvas, sample_name, left_offset + 0.5 * mm, width - 1 * mm, top_cursor, font_name + '-Bold', font_size, 1.2)
    canvas.line(left_offset, top_cursor + font_size / 2 * 1.2, right_offset, top_cursor + font_size / 2 * 1.2)
    top_cursor -= font_size / 2 * 1.2
    top_cursor = _draw_centered_wrapped_text(canvas, sample_creator, left_offset + 0.5 * mm, width - 1 * mm, top_cursor, font_name, font_size, 1.2)
    top_cursor = _draw_centered_wrapped_text(canvas, sample_creation_date, left_offset + 0.5 * mm, width - 1 * mm, top_cursor, font_name, font_size, 1.2)
    full_left_offset = left_offset
    full_right_offset = right_offset
    full_width = width

    width = qrcode_width
    if ghs_classes_side_by_side and ghs_classes:
        width += 20 * mm
    if centered:
        left_offset = left_offset / 2 + right_offset / 2 - width / 2
    right_offset = left_offset + width

    top_cursor_before_qrcode = top_cursor - font_size / 2 * 1.2
    canvas.drawImage(qrcode_uri, left_offset + (not ghs_classes_side_by_side) * (width / 2 - qrcode_width / 2), top_cursor - qrcode_width * 0.9, qrcode_width, qrcode_width)
    canvas.line(full_left_offset, top_cursor + font_size / 2 * 1.2, full_right_offset, top_cursor + font_size / 2 * 1.2)
    top_cursor -= font_size / 2 * 1.2
    top_cursor -= qrcode_width

    canvas.setFont("Helvetica", 6)
    if ghs_classes_side_by_side:
        canvas.drawCentredString(left_offset + qrcode_width / 2, top_cursor + font_size * 1.2, f"#{sample_id}")
    else:
        canvas.drawCentredString(left_offset / 2 + right_offset / 2, top_cursor + font_size * 1.2, f"#{sample_id}")
    if not ghs_classes_side_by_side:
        if ghs_classes:
            canvas.line(full_left_offset, top_cursor + font_size / 2 * 1.2, full_right_offset, top_cursor + font_size / 2 * 1.2)
            top_cursor -= font_size / 2 * 1.2
        else:
            top_cursor += font_size / 2 * 1.2
    top_cursor_after_qrcode = top_cursor

    if ghs_classes_side_by_side:
        top_cursor = top_cursor_before_qrcode
        left_offset += 20 * mm

    ghs_start_position = 0
    if len(ghs_classes) > 2:
        ghs_start_position = 2
        top_cursor -= 4.5 * mm
    if len(ghs_classes) == 1:
        top_cursor -= 9 * mm
        canvas.drawImage(GHS_IMAGE_URIS[ghs_classes[0]], left_offset + ((right_offset - left_offset) / 2 - 9 * mm / 2), top_cursor + 5, 9 * mm, 9 * mm, (255, 255, 255, 255, 255, 255))
    else:
        for i, ghs_class in enumerate(ghs_classes, start=ghs_start_position):
            if i % 3 == 0:
                top_cursor -= 9 * mm
            canvas.drawImage(GHS_IMAGE_URIS[ghs_class], left_offset + ((right_offset - left_offset) / 2 - 19 * mm / 2) + 0.5 * mm + (i % 3 == 1) * 9 * mm + (i % 3 == 2) * 4.5 * mm, top_cursor + 5 - (i % 3 == 2) * 4.5 * mm, 9 * mm, 9 * mm, (255, 255, 255, 255, 255, 255))
        if (len(ghs_classes) - 1) % 3 == 0:
            top_cursor -= 4.5 * mm

    if ghs_classes_side_by_side:
        left_offset -= 20 * mm
        top_cursor = min(top_cursor_after_qrcode + font_size / 2 * 1.2, top_cursor)

    height = top_offset - top_cursor
    if height < minimum_height:
        top_cursor -= minimum_height - height
        height = minimum_height

    if ghs_classes and ghs_classes_side_by_side:
        canvas.line(left_offset + width / 2, top_cursor_before_qrcode + font_size * 1.2, left_offset + width / 2, top_cursor)
    if not centered and full_width != width:
        canvas.line(left_offset + width, top_cursor_before_qrcode + font_size * 1.2, left_offset + width, top_cursor)
    left_offset = full_left_offset
    right_offset = full_right_offset
    width = full_width

    canvas.rect(left_offset, top_cursor, width, height, 1)
    return top_cursor


def _draw_long_label(
        canvas: Canvas,
        sample_name: str,
        sample_creator: str,
        sample_creation_date: str,
        sample_id: int,
        ghs_classes: typing.List[int],
        qrcode_uri: str,
        left_offset: float,
        bottom_offset: float,
        minimum_width: float = 0,
        include_qrcode: bool = False,
        qrcode_size: float = 15 * mm
) -> float:
    font_name = "Helvetica"
    font_size = 8
    canvas.setFont(font_name, font_size)
    num_lines = 2
    if include_qrcode:
        upper_line_text1 = sample_name
        upper_line_text2 = f" • #{sample_id}"
        middle_line_text = sample_creator
        lower_line_text = sample_creation_date
        num_lines = 3
    else:
        upper_line_text1 = sample_name
        upper_line_text2 = f" • #{sample_id}"
        middle_line_text = sample_creator + " • " + sample_creation_date
        lower_line_text = ''

    min_height = 9 * mm
    if include_qrcode:
        min_height = max(min_height, qrcode_size - 2 * mm)
    padding = max(1 * mm, (min_height - num_lines * font_size) / 2)
    height = max(min_height, 2 * padding + num_lines * font_size)
    left_cursor = left_offset + 1 * mm
    canvas.setFont(font_name + '-Bold', font_size)
    canvas.drawString(left_cursor, bottom_offset + padding + (num_lines - 1) * font_size * 1.2, upper_line_text1)
    canvas.setFont(font_name, font_size)
    canvas.drawString(left_cursor + canvas.stringWidth(upper_line_text1, font_name + '-Bold', font_size), bottom_offset + padding + (num_lines - 1) * font_size * 1.2, upper_line_text2)
    canvas.drawString(left_cursor, bottom_offset + padding + (num_lines - 2) * font_size * 1.2, middle_line_text)
    if num_lines == 3:
        canvas.drawString(left_cursor, bottom_offset + padding, lower_line_text)
    text_width = max(
        canvas.stringWidth(upper_line_text1, font_name + '-Bold', font_size) + canvas.stringWidth(upper_line_text2, font_name, font_size),
        canvas.stringWidth(middle_line_text, font_name, font_size),
        canvas.stringWidth(lower_line_text, font_name, font_size)
    )
    left_cursor += 1 * mm + text_width
    for ghs_class in ghs_classes:
        canvas.drawImage(GHS_IMAGE_URIS[ghs_class], left_cursor, bottom_offset + height / 2 - 4.5 * mm, 9 * mm, 9 * mm, (255, 255, 255, 255, 255, 255))
        left_cursor += 9 * mm
    if height != 9 * mm:
        left_cursor += 1 * mm
    if include_qrcode:
        canvas.drawImage(qrcode_uri, left_cursor - 1 * mm, bottom_offset + height / 2 - qrcode_size / 2, qrcode_size, qrcode_size)
        left_cursor += qrcode_size - 2 * mm
    width = left_cursor - left_offset
    if width < minimum_width:
        width = minimum_width
    canvas.rect(left_offset, bottom_offset, width, height, 1)
    return bottom_offset


def _draw_qr_code_label(
        canvas: Canvas,
        sample_id: int,
        current_label_number: typing.Optional[int],
        max_label_number: int,
        qrcode_uri: str,
        left_offset: float,
        bottom_offset: float,
        row_last: bool,
        column_first: bool,
        minimum_width: float = 0,
        qrcode_size: float = 15 * mm,
        show_id_on_label: bool = True,
        add_maximum_label_number: bool = False
) -> float:
    font_name = "Helvetica"
    font_size = 8
    canvas.setFont(font_name, font_size)
    if show_id_on_label:
        label_text = f"#{sample_id} "
    else:
        label_text = ""

    if current_label_number is not None:
        num_digits = ceil(log10(max_label_number))
        label_text += f"{current_label_number:0{num_digits}}"
        if add_maximum_label_number:
            label_text += f"_{max_label_number}"

    min_height = qrcode_size + 2 * mm
    height = min_height
    left_cursor = left_offset + 1 * mm
    canvas.drawImage(qrcode_uri, left_cursor, bottom_offset + height / 2 - qrcode_size / 2, qrcode_size, qrcode_size)

    left_cursor += qrcode_size + 1 * mm
    canvas.setFont(font_name + '-Bold', font_size)
    canvas.drawString(left_cursor, bottom_offset + (height + 3 - font_size) / 2, label_text)
    if show_id_on_label or current_label_number is not None:
        text_width = canvas.stringWidth(label_text, font_name, font_size)
        left_cursor += text_width + 1 * mm

    width: float = left_cursor - left_offset
    if width < minimum_width:
        width = minimum_width

    canvas.setLineWidth(0.1 * mm)
    canvas.setDash([0.5 * mm, 0.5 * mm], 0)
    canvas.line(left_offset, bottom_offset, left_offset, bottom_offset + height)
    canvas.line(left_offset, bottom_offset, left_offset + width, bottom_offset)
    if row_last:
        canvas.line(left_offset + width, bottom_offset, left_offset + width, bottom_offset + height)
    if column_first:
        canvas.line(left_offset, bottom_offset + height, left_offset + width, bottom_offset + height)
    return bottom_offset


def create_labels(
        object_id: int,
        object_name: str,
        object_url: str,
        creation_user: str,
        creation_date: str,
        ghs_classes: typing.List[int],
        paper_format: str = DEFAULT_PAPER_FORMAT,
        create_mixed_labels: bool = True,
        create_long_labels: bool = False,
        create_only_qr_codes: bool = False,
        include_qrcode_in_long_labels: bool = False,
        label_width: float = 18,
        label_minimum_height: float = 0,
        label_minimum_width: float = 0,
        qrcode_width: float = 18,
        label_quantity: int = 1,
        ghs_classes_side_by_side: bool = False,
        centered: bool = True,
        only_id_qr_code: bool = False,
        add_label_number: bool = False,
        add_maximum_label_number: bool = False,
        show_id_on_label: bool = True
) -> bytes:
    object_specification = {
        object_id: {
            "object_name": object_name,
            "object_url": object_url,
            "creation_user": creation_user,
            "creation_date": creation_date,
            "ghs_classes": ghs_classes
        }
    }
    return create_multiple_labels(
        object_specifications=object_specification,
        paper_format=paper_format,
        create_mixed_labels=create_mixed_labels,
        create_long_labels=create_long_labels,
        create_only_qr_codes=create_only_qr_codes,
        include_qrcode_in_long_labels=include_qrcode_in_long_labels,
        label_width=label_width,
        min_label_height=label_minimum_height,
        min_label_width=label_minimum_width,
        qr_code_width=qrcode_width,
        quantity=label_quantity,
        ghs_classes_side_by_side=ghs_classes_side_by_side,
        centered=centered,
        fill_single_page=not create_only_qr_codes,
        only_id_qr_code=only_id_qr_code,
        add_label_number=add_label_number,
        add_maximum_label_number=add_maximum_label_number,
        show_id_on_label=show_id_on_label
    )


def create_multiple_labels(
        object_specifications: typing.Dict[int, typing.Dict[str, typing.Any]],
        quantity: int = 1,
        label_width: float = 18,
        min_label_width: float = 0,
        min_label_height: float = 0,
        qr_code_width: float = 18,
        paper_format: str = DEFAULT_PAPER_FORMAT,
        create_mixed_labels: bool = False,
        create_long_labels: bool = False,
        create_only_qr_codes: bool = False,
        include_qrcode_in_long_labels: bool = False,
        ghs_classes_side_by_side: bool = False,
        centered: bool = True,
        fill_single_page: bool = False,
        only_id_qr_code: bool = False,
        add_label_number: bool = False,
        add_maximum_label_number: bool = False,
        show_id_on_label: bool = True,
) -> bytes:
    page_size = PAGE_SIZES.get(paper_format, PAGE_SIZES[DEFAULT_PAPER_FORMAT])
    page_width, page_height = page_size
    pdf_stream = io.BytesIO()
    canvas = Canvas(pdf_stream, pagesize=page_size)
    top_cursor = 0

    label_width = label_width * mm
    min_label_height = min_label_height * mm
    label_minimum_width = min_label_width * mm
    qr_code_width = qr_code_width * mm

    vertical_padding = 3 * mm if not create_only_qr_codes else qr_code_width + 2 * mm
    horizontal_padding = 3 * mm if not create_only_qr_codes else 0
    horizontal_margin = HORIZONTAL_LABEL_MARGIN * mm
    vertical_margin = VERTICAL_LABEL_MARGIN * mm
    if create_only_qr_codes:
        extra_space = 2
        if show_id_on_label:
            object_id = list(object_specifications.keys())[0]
            extra_space = 3
            max_length_text = f"#{object_id} "
        else:
            max_length_text = ""

        if add_label_number:
            extra_space = 3
            max_length_text += f"{quantity}"
            if add_maximum_label_number:
                max_length_text += f"_{quantity}"

        text_width = canvas.stringWidth(max_length_text, "Helvetica-Bold", 8)
        label_width = text_width + qr_code_width + extra_space * mm

    top_cursor = page_height - vertical_margin - vertical_padding
    max_label_height = None

    num_labels_per_row = int((page_width - 2 * horizontal_margin + horizontal_padding) / (label_width + horizontal_padding))
    if create_only_qr_codes:
        horizontal_margin = (page_width - num_labels_per_row * label_width) / 2
    if num_labels_per_row <= 0:
        num_labels_per_row = 1
        horizontal_centering_offset = 0
    if create_long_labels or create_mixed_labels:
        num_labels_per_row = 1

    horizontal_centering_offset = (page_width - 2 * horizontal_margin + horizontal_padding - num_labels_per_row * (label_width + horizontal_padding)) / 2
    label_counter = 0
    object_ids = sorted(list(object_specifications.keys()))
    object_id = -1
    num_labels_per_row = int((page_width - 2 * horizontal_margin + horizontal_padding) / (label_width + horizontal_padding))

    if create_mixed_labels or create_long_labels:
        num_labels_per_row = 1

    first_row = True

    while label_counter < quantity * len(object_ids) or fill_single_page:
        if ((label_counter % quantity) == 0 and (not fill_single_page or label_counter == 0)) or add_label_number:
            object_id = object_ids[min(int(label_counter / quantity), len(object_ids) - 1)]
            object_specification = object_specifications[object_id]
            if create_only_qr_codes:
                if only_id_qr_code:
                    if add_label_number:
                        qr_data = f"{object_id}_{label_counter + 1}_{quantity}"
                    else:
                        qr_data = str(object_id)
                else:
                    qr_data = object_specification["object_url"]
                qr = qrcode.QRCode(
                    box_size=qr_code_width,
                    border=0
                )
                qr.add_data(qr_data)
                image = qr.make_image(fill_color="black", back_color="white")
            else:
                image = qrcode.make(object_specification["object_url"])
            image_stream = io.BytesIO()
            image.save(image_stream, format='png')
            image_stream.seek(0)
            qr_code_uri = 'data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8')
        assert object_id != -1

        ghs_classes = [
            ghs_class if 0 < ghs_class < 10 else 0
            for ghs_class in object_specification['ghs_classes']
        ]

        left_cursor = horizontal_margin + horizontal_centering_offset + (label_counter % num_labels_per_row) * (label_width + horizontal_padding)

        if create_long_labels:
            bottom_cursor = _draw_long_label(canvas, object_specification["object_name"], object_specification["creation_user"], object_specification["creation_date"], object_id, ghs_classes, qr_code_uri, horizontal_margin, top_cursor - vertical_margin - (3.5 * mm if include_qrcode_in_long_labels else 0 * mm), minimum_width=label_minimum_width, include_qrcode=include_qrcode_in_long_labels)
        elif create_mixed_labels:
            bottom_cursor = min(
                _draw_long_label(canvas, object_specification["object_name"], object_specification["creation_user"], object_specification["creation_date"], object_id, ghs_classes, qr_code_uri, 10 * mm, top_cursor - 9 * mm),
                _draw_long_label(canvas, object_specification["object_name"], object_specification["creation_user"], object_specification["creation_date"], object_id, ghs_classes, qr_code_uri, 10 * mm, top_cursor - 27 * mm, include_qrcode=True),
                _draw_label(canvas, object_specification["object_name"], object_specification["creation_user"], object_specification["creation_date"], object_id, ghs_classes, qr_code_uri, 10 * mm, top_cursor - 32 * mm, 18 * mm, 52 * mm, 18 * mm),
                _draw_label(canvas, object_specification["object_name"], object_specification["creation_user"], object_specification["creation_date"], object_id, ghs_classes, qr_code_uri, 33 * mm, top_cursor - 32 * mm, 20 * mm, 52 * mm, 20 * mm),
                _draw_label(canvas, object_specification["object_name"], object_specification["creation_user"], object_specification["creation_date"], object_id, ghs_classes, qr_code_uri, 58 * mm, top_cursor - 32 * mm, 40 * mm, 35 * mm, 20 * mm, ghs_classes_side_by_side=True),
                _draw_label(canvas, object_specification["object_name"], object_specification["creation_user"], object_specification["creation_date"], object_id, ghs_classes, qr_code_uri, 103 * mm, top_cursor - 32 * mm, 75 * mm, 35 * mm, 20 * mm, ghs_classes_side_by_side=True, centered=False),
            )
        elif create_only_qr_codes:
            bottom_cursor = _draw_qr_code_label(
                canvas=canvas,
                sample_id=object_id,
                current_label_number=label_counter + 1 if add_label_number else None,
                max_label_number=quantity,
                qrcode_uri=qr_code_uri,
                left_offset=left_cursor,
                bottom_offset=top_cursor,
                row_last=(label_counter + 1) % num_labels_per_row == 0 or label_counter + 1 == quantity,
                column_first=first_row,
                minimum_width=label_minimum_width,
                qrcode_size=qr_code_width,
                show_id_on_label=show_id_on_label,
                add_maximum_label_number=add_maximum_label_number
            )
        else:
            bottom_cursor = _draw_label(canvas, object_specification['object_name'], object_specification['creation_user'], object_specification['creation_date'], object_id, ghs_classes, qr_code_uri, left_cursor, top_cursor, label_width, min_label_height, qr_code_width, ghs_classes_side_by_side=ghs_classes_side_by_side, centered=centered)

        label_counter += 1

        if max_label_height is None:
            max_label_height = top_cursor - bottom_cursor

        if (label_counter % num_labels_per_row) == 0:
            top_cursor = bottom_cursor - vertical_padding
            first_row = False

        if top_cursor - max_label_height <= vertical_margin:
            top_cursor = page_height - vertical_margin - vertical_padding
            canvas.showPage()
            first_row = True
            if fill_single_page:
                break

    canvas.save()
    pdf_stream.seek(0)
    return pdf_stream.read()
