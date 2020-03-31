"""
Module for generation sample/object labels as PDF files.
"""
import io
import base64
import os
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


def _generate_ghs_image_uris():
    ghs_image_uris = []
    GHS_IMAGE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'static', 'img')
    for i in range(0, 10):
        ghs_image = Image.open(os.path.join(GHS_IMAGE_DIR, 'ghs0{}.png'.format(i))).convert('RGBA')
        ghs_background_image = Image.new('RGBA', ghs_image.size, (255, 255, 255, 255))
        ghs_image = Image.alpha_composite(ghs_background_image, ghs_image)
        image_stream = io.BytesIO()
        ghs_image.save(image_stream, format='png')
        image_stream.seek(0)
        ghs_image_uri = 'data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8')
        ghs_image_uris.append(ghs_image_uri)
    return ghs_image_uris


GHS_IMAGE_URIS = _generate_ghs_image_uris()


def _draw_centered_wrapped_text(canvas, text, left_offset, width, top_cursor, font_name, font_size, line_height):
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


def _draw_label(canvas, sample_name, sample_creator, sample_creation_date, sample_id, ghs_classes, qrcode_uri, left_offset, top_offset, width, minimum_height, qrcode_width, ghs_classes_side_by_side=False, centered=True):
    font_name = "Helvetica"
    font_size = 8
    right_offset = left_offset + width
    top_cursor = top_offset - 3 * mm

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
        canvas.drawCentredString(left_offset + qrcode_width / 2, top_cursor + font_size * 1.2, "#{}".format(sample_id))
    else:
        canvas.drawCentredString(left_offset / 2 + right_offset / 2, top_cursor + font_size * 1.2, "#{}".format(sample_id))
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


def _draw_long_label(canvas: Canvas, sample_name, sample_creator, sample_creation_date, sample_id, ghs_classes, qrcode_uri, left_offset, bottom_offset, minimum_width=0, include_qrcode=False, qrcode_size=15 * mm):
    font_name = "Helvetica"
    font_size = 8
    canvas.setFont(font_name, font_size)
    num_lines = 2
    if include_qrcode:
        upper_line_text1 = sample_name
        upper_line_text2 = " • #{}".format(sample_id)
        middle_line_text = sample_creator
        lower_line_text = sample_creation_date
        num_lines = 3
    else:
        upper_line_text1 = sample_name
        upper_line_text2 = " • #{}".format(sample_id)
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


def create_labels(
        object_id, object_name, object_url, creation_user, creation_date, ghs_classes, paper_format=DEFAULT_PAPER_FORMAT,
        create_mixed_labels=True, create_long_labels=False, include_qrcode_in_long_labels=False,
        label_width=18, label_minimum_height=0, label_minimum_width=0, qrcode_width=18, ghs_classes_side_by_side=False,
        centered=True
):

    page_size = PAGE_SIZES.get(paper_format, PAGE_SIZES[DEFAULT_PAPER_FORMAT])
    page_width, page_height = page_size
    image = qrcode.make(object_url, image_factory=qrcode.image.pil.PilImage)
    image_stream = io.BytesIO()
    image.save(image_stream, format='png')
    image_stream.seek(0)
    qrcode_uri = 'data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8')

    # 0 for unknown GHS classes with question mark icon
    ghs_classes = [
        ghs_class if 0 < ghs_class < 10 else 0
        for ghs_class in ghs_classes
    ]

    pdf_stream = io.BytesIO()
    canvas = Canvas(pdf_stream, pagesize=page_size)

    label_width = label_width * mm
    label_minimum_height = label_minimum_height * mm
    qrcode_width = qrcode_width * mm
    label_minimum_width = label_minimum_width * mm

    vertical_padding = 3 * mm
    horizontal_padding = 3 * mm
    horizontal_margin = HORIZONTAL_LABEL_MARGIN * mm
    vertical_margin = VERTICAL_LABEL_MARGIN * mm
    top_cursor = page_height - vertical_margin
    max_label_height = None
    while max_label_height is None or top_cursor - max_label_height > vertical_margin:
        if create_mixed_labels:
            bottom_cursor = min(
                _draw_long_label(canvas, object_name, creation_user, creation_date, object_id, ghs_classes, qrcode_uri, 10 * mm, top_cursor - 9 * mm),
                _draw_long_label(canvas, object_name, creation_user, creation_date, object_id, ghs_classes, qrcode_uri, 10 * mm, top_cursor - 27 * mm, include_qrcode=True),
                _draw_label(canvas, object_name, creation_user, creation_date, object_id, ghs_classes, qrcode_uri, 10 * mm, top_cursor - 32 * mm, 18 * mm, 52 * mm, 18 * mm),
                _draw_label(canvas, object_name, creation_user, creation_date, object_id, ghs_classes, qrcode_uri, 33 * mm, top_cursor - 32 * mm, 20 * mm, 52 * mm, 20 * mm),
                _draw_label(canvas, object_name, creation_user, creation_date, object_id, ghs_classes, qrcode_uri, 58 * mm, top_cursor - 32 * mm, 40 * mm, 35 * mm, 20 * mm, ghs_classes_side_by_side=True),
                _draw_label(canvas, object_name, creation_user, creation_date, object_id, ghs_classes, qrcode_uri, 103 * mm, top_cursor - 32 * mm, 75 * mm, 35 * mm, 20 * mm, ghs_classes_side_by_side=True, centered=False)
            )
        elif create_long_labels:
            bottom_cursor = _draw_long_label(canvas, object_name, creation_user, creation_date, object_id, ghs_classes, qrcode_uri, horizontal_margin, top_cursor - vertical_margin - (3.5 * mm if include_qrcode_in_long_labels else 0 * mm), minimum_width=label_minimum_width, include_qrcode=include_qrcode_in_long_labels)
        else:
            num_labels_per_row = int((page_width - 2 * horizontal_margin + horizontal_padding) / (label_width + horizontal_padding))
            horizontal_centering_offset = (page_width - 2 * horizontal_margin + horizontal_padding - num_labels_per_row * (label_width + horizontal_padding)) / 2
            if num_labels_per_row <= 0:
                # Better a cropped label than no label at all
                num_labels_per_row = 1
                horizontal_centering_offset = 0
            for i in range(num_labels_per_row):
                left_cursor = horizontal_margin + horizontal_centering_offset + i * (label_width + horizontal_padding)
                bottom_cursor = _draw_label(canvas, object_name, creation_user, creation_date, object_id, ghs_classes, qrcode_uri, left_cursor, top_cursor, label_width, label_minimum_height, qrcode_width, ghs_classes_side_by_side=ghs_classes_side_by_side, centered=centered)
        if max_label_height is None:
            max_label_height = top_cursor - bottom_cursor
        top_cursor = bottom_cursor - vertical_padding

    canvas.showPage()
    canvas.save()
    pdf_stream.seek(0)
    return pdf_stream.read()
