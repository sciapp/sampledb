"""
Module for generation sample/object labels as PDF files.
"""
import collections
import io
import base64
import math
import os
import typing

from PIL import Image
from reportlab.lib.pagesizes import A4, LETTER
from weasyprint import HTML

import qrcode
import qrcode.image.pil

import flask

DEFAULT_PAPER_FORMAT = 'DIN A4 (Portrait)'
PAGE_SIZES = {
    'DIN A4 (Portrait)': A4,
    'DIN A4 (Landscape)': (A4[1], A4[0]),
    'Letter (Portrait)': LETTER,
    'Letter (Landscape)': (LETTER[1], LETTER[0])
}

PAGE_SIZE_KEYS = ['DIN A4 (Portrait)', 'DIN A4 (Landscape)', 'Letter (Portrait)', 'Letter (Landscape)']

HORIZONTAL_LABEL_MARGIN = 10
VERTICAL_LABEL_MARGIN = 10


def _generate_ghs_image_uris() -> typing.List[str]:
    ghs_image_uris = []
    GHS_IMAGE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'static', 'sampledb', 'img')
    for i in range(0, 10):
        ghs_image = Image.open(os.path.join(GHS_IMAGE_DIR, f'ghs0{i}.png')).convert('RGBA')
        image_stream = io.BytesIO()
        ghs_image.save(image_stream, format='png')
        image_stream.seek(0)
        ghs_image_uri = 'data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8')
        ghs_image_uris.append(ghs_image_uri)
    return ghs_image_uris


GHS_IMAGE_URIS = _generate_ghs_image_uris()


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
        show_id_on_label: bool = True,
        label_dimension: typing.Optional[dict[str, typing.Any]] = None
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
        include_qrcode_in_long_labels=include_qrcode_in_long_labels,
        paper_format=paper_format,
        quantity=label_quantity,
        label_width=label_width,
        min_label_width=label_minimum_width,
        qr_code_width=qrcode_width,
        min_label_height=label_minimum_height,
        ghs_classes_side_by_side=ghs_classes_side_by_side,
        centered=centered,
        create_mixed_labels=create_mixed_labels,
        create_long_labels=create_long_labels,
        create_only_qr_codes=create_only_qr_codes,
        only_id_qr_code=only_id_qr_code,
        add_label_number=add_label_number,
        add_maximum_label_number=add_maximum_label_number,
        show_id_on_label=show_id_on_label,
        label_dimension=label_dimension,
        fill_single_page=not create_only_qr_codes
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
        label_dimension: typing.Optional[dict[str, typing.Any]] = None
) -> bytes:
    vertical_label_margin = VERTICAL_LABEL_MARGIN / 4
    horizontal_label_margin = HORIZONTAL_LABEL_MARGIN / 4

    paper_formats: typing.Dict[str, typing.List[float]] = {
        "DIN A4 (Portrait)": [297.0, 210.0],
        "DIN A4 (Landscape)": [210.0, 297.0],
        "Letter (Portrait)": [279.4, 215.9],
        "Letter (Landscape)": [215.9, 279.4]
    }

    paper_height = paper_formats[paper_format][0]
    paper_width = paper_formats[paper_format][1]

    tmp_object_specifications_dict = collections.OrderedDict(sorted(object_specifications.items()))
    object_specifications = tmp_object_specifications_dict

    username_list = []
    object_name_list = []
    creation_date_list = []
    object_url_list = []
    hazard_list = []
    sample_code_list = []
    qr_code_uri_list = []
    ghs_amount_list = []
    ghs_width = 9.0
    qrcode_width = 12.0

    if create_long_labels:
        box_width_list = []
        tmp_index = 0
        for object_id in object_specifications:
            username_list.append(object_specifications[object_id]["creation_user"])
            object_name_list.append(object_specifications[object_id]["object_name"])
            creation_date_list.append(object_specifications[object_id]["creation_date"])
            object_url_list.append(object_specifications[object_id]["object_url"])
            hazard_list.append(object_specifications[object_id]["ghs_classes"])
            sample_code_list.append(object_id)

            url = object_url_list[tmp_index]
            image = qrcode.make(url, border=1)
            image_stream = io.BytesIO()
            image.save(image_stream, format='png')
            image_stream.seek(0)
            qr_code_uri_list.append('data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8'))

            if include_qrcode_in_long_labels:
                label_width = 2 + qrcode_width + ghs_width * len(hazard_list[tmp_index]) + (
                    max(3 + len(object_name_list[tmp_index]) + len(str(sample_code_list[tmp_index])),
                        len(username_list[tmp_index]), len(creation_date_list[tmp_index]))) * 2
                if len(hazard_list[tmp_index]) == 0:
                    label_width += 2
            else:
                label_width = ghs_width * len(hazard_list[tmp_index]) + (
                    max(3 + len(object_name_list[tmp_index]) + len(str(sample_code_list[tmp_index])),
                        len(username_list[tmp_index]) + 3 + len(creation_date_list[tmp_index]))) * 2

            box_width_list.append(max(label_width, min_label_width))

            tmp_index += 1

        if include_qrcode_in_long_labels:
            box_height = 4 * 3.0
        else:
            box_height = 3 * 3.0

        if quantity == 1 and fill_single_page:
            label_amount = (2 + int((paper_height - 15) / (box_height + (2 * vertical_label_margin))))
        else:
            label_amount = quantity

        object_amount = len(username_list)
        html = flask.render_template("labels/LongLabel.html", username_list=username_list,
                                     object_name_list=object_name_list, creation_date_list=creation_date_list,
                                     object_url_list=object_url_list, hazard_list=hazard_list,
                                     object_id_list=sample_code_list, qr_code_uri_list=qr_code_uri_list,
                                     object_amount=object_amount, box_width_list=box_width_list,
                                     include_qrcode=include_qrcode_in_long_labels, box_height=box_height,
                                     paper_width=paper_width, paper_height=paper_height, label_amount=label_amount,
                                     GHS_IMAGE_URIS=GHS_IMAGE_URIS, vertical_label_margin=vertical_label_margin,
                                     horizontal_label_margin=horizontal_label_margin, qrcode_width=qrcode_width,
                                     ghs_width=ghs_width)

    elif create_mixed_labels:
        has_ghs_list = []

        first_box_width_list = []
        second_box_width_list = []
        third_box_width_list = []
        third_box_height_list = []
        third_box_qrcode_box_height_list = []
        third_box_ghs_box_height_list = []
        forth_box_width_list = []
        forth_box_height_list = []
        fourth_box_qrcode_box_height_list = []
        fourth_box_ghs_box_height_list = []
        fifth_box_width_list = []
        fifth_box_height_list = []
        fifth_box_qrcode_box_width_list = []
        fifth_box_ghs_box_width_list = []
        fifth_inner_box_height_list = []
        sixth_box_width_list = []
        sixth_box_height_list = []
        sixth_inner_box_height_list = []

        outer_box_width = 200.0
        outer_box_height = 60.0
        sixth_box_qrcode_box_width = 20.0
        sixth_box_ghs_box_width = 20.0

        if quantity == 1 and fill_single_page:
            set_amount = math.floor((paper_height - 15) / (28.5 + outer_box_height))
        else:
            set_amount = quantity

        tmp_index = 0

        for object_id in object_specifications:
            username_list.append(object_specifications[object_id]["creation_user"])
            object_name_list.append(object_specifications[object_id]["object_name"])
            creation_date_list.append(object_specifications[object_id]["creation_date"])
            object_url_list.append(object_specifications[object_id]["object_url"])
            hazard_list.append(object_specifications[object_id]["ghs_classes"])
            sample_code_list.append(object_id)

            url = object_url_list[tmp_index]
            image = qrcode.make(url, border=1)
            image_stream = io.BytesIO()
            image.save(image_stream, format='png')
            image_stream.seek(0)
            qr_code_uri_list.append('data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8'))

            ghs_height = 17.0 + int((len(hazard_list[tmp_index]) - 1) / 3) * 9

            first_box_width_list.append(ghs_width * len(hazard_list[tmp_index]) + (
                max(3 + len(object_name_list[tmp_index]) + len(str(sample_code_list[tmp_index])),
                    len(username_list[tmp_index]) + 3 + len(creation_date_list[tmp_index]))) * 2)

            second_box_width_list.append(2 + qrcode_width + ghs_width * len(hazard_list[tmp_index]) + (
                max(3 + len(object_name_list[tmp_index]) + len(str(sample_code_list[tmp_index])),
                    len(username_list[tmp_index]), len(creation_date_list[tmp_index]))) * 2)
            if len(hazard_list[tmp_index]) == 0:
                second_box_width_list[tmp_index] += 2

            third_box_width_list.append(max(15.0, max(len(object_name_list[tmp_index]), len(username_list[tmp_index]),
                                                      len(creation_date_list[tmp_index]),
                                                      len(str(sample_code_list[tmp_index]))) * 2))
            third_box_height_list.append(max(60.0, 32 + math.ceil(ghs_height)))

            forth_box_width_list.append(max(18.0, max(len(object_name_list[tmp_index]), len(username_list[tmp_index]),
                                                      len(creation_date_list[tmp_index]),
                                                      len(str(sample_code_list[tmp_index]))) * 2))
            forth_box_height_list.append(max(60.0, 32 + math.ceil(ghs_height)))

            fifth_box_width_list.append(max(45.0, max(len(object_name_list[tmp_index]), len(username_list[tmp_index]),
                                                      len(creation_date_list[tmp_index]),
                                                      len(str(sample_code_list[tmp_index]))) * 2))
            fifth_box_height_list.append(max(50.0, 12.0 + math.ceil(ghs_height)))
            fifth_box_qrcode_box_width_list.append(fifth_box_width_list[tmp_index] / 2.0)
            fifth_box_ghs_box_width_list.append(fifth_box_width_list[tmp_index] / 2.0)

            sixth_box_width_list.append(
                max(80.0 - ((third_box_width_list[tmp_index] - 20) + (forth_box_width_list[tmp_index] - 20)),
                    max(len(object_name_list[tmp_index]), len(username_list[tmp_index]),
                        len(creation_date_list[tmp_index]),
                        len(str(sample_code_list[tmp_index]))) * 2))
            sixth_box_height_list.append(max(50.0, 12.0 + math.ceil(ghs_height)))

            ghs_amount_list.append(len(hazard_list[tmp_index]))

            if ghs_amount_list[tmp_index] > 0:
                has_ghs_list.append(True)
                third_box_qrcode_box_height_list.append(20.0)
                third_box_ghs_box_height_list.append(22.0 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9)

                fourth_box_qrcode_box_height_list.append(23.0)
                fourth_box_ghs_box_height_list.append(19.0 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9)

                fifth_inner_box_height_list.append(max(22.0, 17.0 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9))
                sixth_inner_box_height_list.append(max(22.0, 17.0 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9))

                outer_box_height = 60.0 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9
            else:
                has_ghs_list.append(False)
                third_box_qrcode_box_height_list.append(40.0)
                third_box_ghs_box_height_list.append(0.0)

                fourth_box_qrcode_box_height_list.append(40.0)
                fourth_box_ghs_box_height_list.append(0.0)

                fifth_inner_box_height_list.append(22.0)
                sixth_inner_box_height_list.append(22.0)

            tmp_index += 1

        object_amount = len(username_list)
        html = flask.render_template("labels/MixedFormats.html",
                                     sample_code_list=sample_code_list, username_list=username_list,
                                     object_name_list=object_name_list, creation_date_list=creation_date_list,
                                     qr_code_uri_list=qr_code_uri_list, hazard_list=hazard_list,
                                     paper_width=paper_width, paper_height=paper_height, set_amount=set_amount,
                                     horizontal_label_margin=horizontal_label_margin,
                                     vertical_label_margin=vertical_label_margin,
                                     GHS_IMAGE_URIS=GHS_IMAGE_URIS,
                                     third_box_height_list=third_box_height_list,
                                     forth_box_height_list=forth_box_height_list,
                                     fifth_box_height_list=fifth_box_height_list,
                                     sixth_box_height_list=sixth_box_height_list,
                                     first_box_width_list=first_box_width_list,
                                     second_box_width_list=second_box_width_list,
                                     third_box_width_list=third_box_width_list,
                                     forth_box_width_list=forth_box_width_list,
                                     fifth_box_width_list=fifth_box_width_list,
                                     sixth_box_width_list=sixth_box_width_list,
                                     outer_box_width=outer_box_width, outer_box_height=outer_box_height,
                                     ghs_width=ghs_width,
                                     fifth_box_qrcode_box_width_list=fifth_box_qrcode_box_width_list,
                                     fifth_box_ghs_box_width_list=fifth_box_ghs_box_width_list,
                                     sixth_box_qrcode_box_width=sixth_box_qrcode_box_width,
                                     sixth_box_ghs_box_width=sixth_box_ghs_box_width, has_ghs_list=has_ghs_list,
                                     fifth_inner_box_height_list=fifth_inner_box_height_list,
                                     sixth_inner_box_height_list=sixth_inner_box_height_list,
                                     third_box_qrcode_box_height_list=third_box_qrcode_box_height_list,
                                     third_box_ghs_box_height_list=third_box_ghs_box_height_list,
                                     fourth_box_qrcode_box_height_list=fourth_box_qrcode_box_height_list,
                                     fourth_box_ghs_box_height_list=fourth_box_ghs_box_height_list,
                                     object_amount=object_amount)

    elif create_only_qr_codes:
        object_id = list(object_specifications.keys())[0]
        object_name = object_specifications[object_id]["object_name"]
        object_url = object_specifications[object_id]["object_url"]
        qr_code_uri = []

        for quantity_index in range(1, quantity + 1):
            if only_id_qr_code:
                if add_label_number:
                    if add_maximum_label_number:
                        url = f"{object_id} {quantity_index}_{quantity}"
                    else:
                        url = f"{object_id} {quantity_index}"
                else:
                    url = f"{object_id}"
            else:
                url = f"{object_url}"
            image = qrcode.make(url, border=1)
            image_stream = io.BytesIO()
            image.save(image_stream, format='png')
            image_stream.seek(0)
            qr_code_uri.append('data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8'))

        qr_quantity = quantity
        qrcode_width = qr_code_width
        box_height = max(math.floor(qrcode_width + 0.5), 6)
        has_label_dimension = False
        horizontal_label_margin = 0
        vertical_label_margin = 0
        text_left = 1 + qr_code_width
        text_top = (qr_code_width - 3) / 4
        text_name_top = ((qr_code_width - 3) / 4) * 3
        labels_on_page = 0

        if not show_id_on_label and not add_label_number and not add_maximum_label_number:
            text_name_top = (qr_code_width - 3) / 2
        if qr_code_width <= 6 and not has_label_dimension:
            text_top = 0.125
            text_name_top = 3.125

        if show_id_on_label:
            if add_label_number:
                if add_maximum_label_number:
                    box_width = qr_code_width + max((len(str(object_id)) * 2.8) + (2 * len(str(qr_quantity))) + 6,
                                                    len(object_name) * 2.2)
                    if qr_quantity >= 10:
                        box_width += 2.8
                    if qr_quantity >= 100:
                        box_width += 2.8
                else:
                    box_width = qr_code_width + max(2.8 + (len(str(object_id)) * 2.8) + len(str(qr_quantity)),
                                                    len(object_name) * 2.2)
                    if qr_quantity >= 10:
                        box_width += 2.8
                    if qr_quantity >= 100:
                        box_width += 2.8
            else:
                box_width = qr_code_width + max(2.8 + (len(str(object_id)) * 2.8), len(object_name) * 2.2)
        elif add_label_number:
            if add_maximum_label_number:
                box_width = qr_code_width + max((2 * len(str(qr_quantity))) + 5.6, len(object_name) * 2.2)
                if qr_quantity >= 100:
                    box_width += 2.8
                if qr_quantity == 1000:
                    box_width += 2.8
            else:
                box_width = qr_code_width + max(len(str(qr_quantity)) + 2.8, len(object_name) * 2.2)
                if qr_quantity >= 100:
                    box_width += 2.8
        else:
            box_width = qr_code_width + len(object_name) * 2.2

        if label_dimension is not None:
            if label_dimension["paper_format"] == 0:
                paper_height = paper_formats["DIN A4 (Portrait)"][0]
                paper_width = paper_formats["DIN A4 (Portrait)"][1]
            elif label_dimension["paper_format"] == 1:
                paper_height = paper_formats["DIN A4 (Landscape)"][0]
                paper_width = paper_formats["DIN A4 (Landscape)"][1]
            elif label_dimension["paper_format"] == 2:
                paper_height = paper_formats["Letter (Portrait)"][0]
                paper_width = paper_formats["Letter (Portrait)"][1]
            elif label_dimension["paper_format"] == 3:
                paper_height = paper_formats["Letter (Landscape)"][0]
                paper_width = paper_formats["Letter (Landscape)"][1]
            qrcode_width = label_dimension["qr_code_width"]
            box_width = label_dimension["label_width"]
            box_height = label_dimension["label_height"]
            horizontal_label_margin = label_dimension["margin_horizontal"] / 2
            vertical_label_margin = label_dimension["margin_vertical"] / 2 - 0.25
            labels_in_row = label_dimension["labels_in_row"]
            labels_in_col = label_dimension["labels_in_col"]
            has_label_dimension = True
            text_name_top += 2
            labels_on_page = labels_in_row * labels_in_col
            if qrcode_width > 7:
                text_top = 0.125

        if qr_code_width <= 8 and not has_label_dimension:
            text_top -= 0.5
            text_name_top += 0.5
        qr_code_top = (box_height - qr_code_width) / 2
        outer_box_width = paper_width
        out_box_width = paper_width - 11.5
        out_box_height = paper_height - 4.5
        text_width = box_width - qr_code_width - 1.5
        html = flask.render_template("labels/QRCode.html", qr_code_uri=qr_code_uri, object_id=object_id,
                                     box_width=box_width, include_qrcode=include_qrcode_in_long_labels,
                                     box_height=box_height, paper_width=paper_width, object_name=object_name,
                                     paper_height=paper_height, vertical_label_margin=vertical_label_margin,
                                     horizontal_label_margin=horizontal_label_margin, qrcode_width=qrcode_width,
                                     qr_quantity=qr_quantity, show_id=show_id_on_label, add_label_nr=add_label_number,
                                     add_maximum_label_nr=add_maximum_label_number, outer_box_width=outer_box_width,
                                     text_left=text_left, text_top=text_top, text_name_top=text_name_top,
                                     out_box_width=out_box_width, out_box_height=out_box_height,
                                     has_label_dimension=has_label_dimension, text_width=text_width,
                                     qr_code_top=qr_code_top, labels_on_page=labels_on_page)

    else:
        box_width = max(label_width, min_label_width)
        qrcode_width = qr_code_width
        ghs_width = qrcode_width / 2
        qrcode_box_width = box_width
        ghs_box_width = box_width

        if centered:
            if ghs_classes_side_by_side:
                qrcode_box_width = qrcode_box_width / 2
                ghs_box_width = ghs_box_width / 2
        else:
            qrcode_box_width = qrcode_width
            ghs_box_width = ghs_width * 2

        row_amount = int(math.floor((paper_width - 10) / (box_width + 5)))

        tmp_index = 0
        for object_id in object_specifications:
            username_list.append(object_specifications[object_id]["creation_user"])
            object_name_list.append(object_specifications[object_id]["object_name"])
            creation_date_list.append(object_specifications[object_id]["creation_date"])
            object_url_list.append(object_specifications[object_id]["object_url"])
            hazard_list.append(object_specifications[object_id]["ghs_classes"])
            sample_code_list.append(object_id)

            url = object_url_list[tmp_index]
            image = qrcode.make(url, border=1)
            image_stream = io.BytesIO()
            image.save(image_stream, format='png')
            image_stream.seek(0)
            qr_code_uri_list.append('data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8'))

            ghs_height = 17.0 + int((len(hazard_list[tmp_index]) - 1) / 3) * 9
            ghs_amount_list.append(len(hazard_list[tmp_index]))

            if ghs_classes_side_by_side:
                box_height = max(min_label_height, 33, 15 + ghs_height)
            else:
                if len(hazard_list[tmp_index]) == 0:
                    box_height = 33
                else:
                    box_height = max(min_label_height, ghs_height + 33)
                if min_label_height > ghs_height + 33:
                    ghs_height += min_label_height - (ghs_height + 33)

            box_side_by_side_height = max(21, math.ceil(ghs_height), box_height - 12)
            column_amount = int(math.floor((paper_height - 15) / (box_height + 5)))

            if quantity == 1 and fill_single_page:
                page_amount = row_amount * column_amount
                outer_box_width = paper_width - 10
                outer_box_height = paper_height - 15
            else:
                page_amount = quantity
                outer_box_width = paper_width - 10
                outer_box_height = ((quantity // 4) + 1) * box_height + 5

            tmp_index += 1

        object_amount = len(username_list)

        if not fill_single_page:
            outer_box_height = (((quantity * object_amount) // 4) + 1) * box_height + 5

        html = flask.render_template("labels/FixedWidth.html", vertical_label_margin=vertical_label_margin,
                                     horizontal_label_margin=horizontal_label_margin, box_width=box_width,
                                     box_height=box_height, qr_code_uri_list=qr_code_uri_list,
                                     qrcode_width=qrcode_width, paper_width=paper_width, paper_height=paper_height,
                                     hazard_list=hazard_list, GHS_IMAGE_URIS=GHS_IMAGE_URIS, ghs_width=ghs_width,
                                     sample_code_list=sample_code_list, username_list=username_list,
                                     object_name_list=object_name_list, creation_date_list=creation_date_list,
                                     ghs_amount_list=ghs_amount_list, ghs_height=ghs_height,
                                     ghs_classes_side_by_side=ghs_classes_side_by_side, centered=centered,
                                     qrcode_box_width=qrcode_box_width, ghs_box_width=ghs_box_width,
                                     box_side_by_side_height=box_side_by_side_height, page_amount=page_amount,
                                     outer_box_width=outer_box_width, outer_box_height=outer_box_height,
                                     row_amount=row_amount, column_amount=column_amount, object_amount=object_amount)

    # return html.encode()

    return typing.cast(bytes, HTML(
        string=html, base_url="img"
    ).write_pdf(presentational_hints=True))
