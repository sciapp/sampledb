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
from weasyprint import HTML

import qrcode
import qrcode.image.pil

import flask


DEFAULT_PAPER_FORMAT = 'DIN A4 (Portrait)'
inch = 72.0
mm = (inch / 2.54) * 0.1
PAGE_SIZES = {
    'DIN A4 (Portrait)': (210 * mm, 297 * mm),
    'DIN A4 (Landscape)': (297 * mm, 210 * mm),
    'Letter (Portrait)': (8.5 * inch, 11 * inch),
    'Letter (Landscape)': (11 * inch, 8.5 * inch)
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
        label_dimension: typing.Optional[dict[str, typing.Any]] = None,
        custom_qr_code_texts: typing.Optional[typing.Dict[str, str]] = None
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
        fill_single_page=not create_only_qr_codes,
        custom_qr_code_texts=custom_qr_code_texts
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
        label_dimension: typing.Optional[dict[str, typing.Any]] = None,
        custom_qr_code_texts: typing.Optional[typing.Dict[str, str]] = None
) -> bytes:
    vertical_label_margin = VERTICAL_LABEL_MARGIN / 4
    horizontal_label_margin = HORIZONTAL_LABEL_MARGIN / 4

    paper_formats: typing.Dict[str, typing.List[float]] = {
        "DIN A4 (Portrait)": [297.0, 210.0],
        "DIN A4 (Landscape)": [210.0, 297.0],
        "Letter (Portrait)": [279.4, 215.9],
        "Letter (Landscape)": [215.9, 279.4]
    }

    with open(os.path.join(os.path.dirname(__file__), "..", "static", "sampledb", "fonts", "NimbusSanL-Reg.otf"), "rb") as font_file:
        regular_font = 'data:font/otf;base64,' + base64.b64encode(font_file.read()).decode('utf-8')

    with open(os.path.join(os.path.dirname(__file__), "..", "static", "sampledb", "fonts", "NimbusSanL-Bol.otf"), "rb") as font_file:
        bold_font = 'data:font/otf;base64,' + base64.b64encode(font_file.read()).decode('utf-8')

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

    if create_long_labels:
        text_extra_width_list = []
        tmp_index = 0
        qrcode_width = 12.5
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

            text_extra_width_list.append(len(hazard_list[tmp_index]) * ghs_width)
            if include_qrcode_in_long_labels:
                text_extra_width_list[tmp_index] = text_extra_width_list[tmp_index] + qrcode_width + 1
            tmp_index += 1

        page_amounts: typing.Dict[str, typing.List[int]] = {
            "DIN A4 (Portrait)": [21, 16],
            "DIN A4 (Landscape)": [14, 11],
            "Letter (Portrait)": [19, 15],
            "Letter (Landscape)": [15, 11]
        }

        if include_qrcode_in_long_labels:
            box_height = 11.69
            label_margin = [horizontal_label_margin / 2 + 0.3, horizontal_label_margin + 0.3]
            page_margin = [9.55, 5, 5, 4.9]
        else:
            box_height = 7.7
            label_margin = [horizontal_label_margin / 2 + 0.544, horizontal_label_margin + 0.3]
            page_margin = [9.9, 5, 5, 5]

        if fill_single_page:
            if include_qrcode_in_long_labels:
                label_amount = page_amounts[paper_format][1]
            else:
                label_amount = page_amounts[paper_format][0]
        else:
            label_amount = quantity

        object_amount = len(username_list)
        html = flask.render_template("labels/LongLabel.html", username_list=username_list,
                                     object_name_list=object_name_list, creation_date_list=creation_date_list,
                                     hazard_list=hazard_list, qrcode_width=qrcode_width, ghs_width=ghs_width,
                                     object_id_list=sample_code_list, qr_code_uri_list=qr_code_uri_list,
                                     object_amount=object_amount,
                                     include_qrcode=include_qrcode_in_long_labels, box_height=box_height,
                                     paper_width=paper_width, paper_height=paper_height, label_amount=label_amount,
                                     GHS_IMAGE_URIS=GHS_IMAGE_URIS, horizontal_label_margin=horizontal_label_margin,
                                     min_label_width=min_label_width, text_extra_width_list=text_extra_width_list,
                                     regular_font=regular_font, bold_font=bold_font, label_margin=label_margin,
                                     page_margin=page_margin)

    elif create_mixed_labels:
        has_ghs_list = []

        first_box_min_width_list = []
        second_box_min_width_list = []
        third_box_qrcode_box_height_list = []
        third_box_ghs_box_height_list = []
        fourth_box_qrcode_box_height_list = []
        fourth_box_ghs_box_height_list = []
        fifth_box_height_list = []
        fifth_box_qrcode_box_width_list = []
        fifth_box_ghs_box_width_list = []
        fifth_inner_box_height_list = []
        sixth_box_height_list = []
        sixth_inner_box_height_list = []
        outer_box_height_list = []

        group_box_height_list = []
        text_extra_width_list = []
        text_extra_width_list_qr = []

        third_box_width = 17.5
        forth_box_width = 19.55
        fifth_box_width = 39.5
        sixth_box_width = 74.5
        outer_box_width = 200.0
        sixth_box_qrcode_box_width = 20.0
        sixth_box_ghs_box_width = 20.0
        qrcode_width = 12.5

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

            first_box_min_width_list.append(ghs_width * len(hazard_list[tmp_index]))

            second_box_min_width_list.append(2 + qrcode_width + ghs_width * len(hazard_list[tmp_index]))

            text_extra_width_list.append(len(hazard_list[tmp_index]) * ghs_width)
            text_extra_width_list_qr.append(len(hazard_list[tmp_index]) * ghs_width + qrcode_width)

            fifth_box_height_list.append(max(50.0, 12.0 + math.ceil(ghs_height)))

            if len(hazard_list[tmp_index]) > 0:
                fifth_box_qrcode_box_width_list.append(fifth_box_width / 2.0)
                fifth_box_ghs_box_width_list.append(fifth_box_width / 2.0)
            else:
                fifth_box_qrcode_box_width_list.append(fifth_box_width)
                fifth_box_ghs_box_width_list.append(0)

            sixth_box_height_list.append(max(50.0, 12.0 + math.ceil(ghs_height)))

            ghs_amount_list.append(len(hazard_list[tmp_index]))

            third_box_qrcode_box_height_list.append(18)
            fourth_box_qrcode_box_height_list.append(20.0)

            if ghs_amount_list[tmp_index] > 0:
                has_ghs_list.append(True)

                if ghs_amount_list[tmp_index] <= 2:
                    third_box_ghs_box_height_list.append(12.0 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9)
                    fourth_box_ghs_box_height_list.append(12.0 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9)
                else:
                    third_box_ghs_box_height_list.append(16.25 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9)
                    fourth_box_ghs_box_height_list.append(16.5 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9)

                fifth_inner_box_height_list.append(max(22.0, 16.25 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9))
                sixth_inner_box_height_list.append(max(22.0, 16.25 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9))

                outer_box_height_list.append(26.0 + 4 * math.floor(len(object_name_list[tmp_index]) * 2.3 / third_box_width) +
                                             int((ghs_amount_list[tmp_index] - 1) / 3) * 9)

                if ghs_amount_list[tmp_index] == 4:
                    third_box_ghs_box_height_list[tmp_index] -= ghs_width / 2.0
                    fourth_box_ghs_box_height_list[tmp_index] -= ghs_width / 2.0
                    fifth_inner_box_height_list[tmp_index] -= ghs_width / 2 - 0.5
                    sixth_inner_box_height_list[tmp_index] -= ghs_width / 2 - 0.5
                elif ghs_amount_list[tmp_index] == 7:
                    third_box_ghs_box_height_list[tmp_index] -= ghs_width / 2.0
                    fourth_box_ghs_box_height_list[tmp_index] -= ghs_width / 2.0
                    fifth_inner_box_height_list[tmp_index] -= ghs_width / 2.0
                    sixth_inner_box_height_list[tmp_index] -= ghs_width / 2.0

                if ghs_amount_list[tmp_index] > 3:
                    fifth_inner_box_height_list[tmp_index] += 0.5
                    sixth_inner_box_height_list[tmp_index] += 0.5
            else:
                has_ghs_list.append(False)
                third_box_ghs_box_height_list.append(0.0)
                fourth_box_ghs_box_height_list.append(0.0)

                fifth_inner_box_height_list.append(22.0)
                sixth_inner_box_height_list.append(22.0)
                outer_box_height_list.append(60)

            group_box_height_list.append(outer_box_height_list[tmp_index] + 25)

            tmp_index += 1

        if fill_single_page:
            amount_on_page: typing.Dict[str, int] = {
                "DIN A4 (Portrait)": 3,
                "DIN A4 (Landscape)": 2,
                "Letter (Portrait)": 2,
                "Letter (Landscape)": 2
            }
            set_amount = int(amount_on_page[paper_format])
            body_height = 0
        else:
            set_amount = quantity
            body_height = 1

        object_amount = len(username_list)
        html = flask.render_template("labels/MixedFormats.html",
                                     sample_code_list=sample_code_list, username_list=username_list,
                                     object_name_list=object_name_list, creation_date_list=creation_date_list,
                                     qr_code_uri_list=qr_code_uri_list, hazard_list=hazard_list,
                                     paper_width=paper_width, paper_height=paper_height, set_amount=set_amount,
                                     horizontal_label_margin=horizontal_label_margin,
                                     vertical_label_margin=vertical_label_margin,
                                     GHS_IMAGE_URIS=GHS_IMAGE_URIS,
                                     fifth_box_height_list=fifth_box_height_list,
                                     sixth_box_height_list=sixth_box_height_list,
                                     first_box_min_width_list=first_box_min_width_list,
                                     second_box_min_width_list=second_box_min_width_list,
                                     third_box_width=third_box_width,
                                     forth_box_width=forth_box_width,
                                     fifth_box_width=fifth_box_width,
                                     sixth_box_width=sixth_box_width,
                                     outer_box_width=outer_box_width, outer_box_height_list=outer_box_height_list,
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
                                     object_amount=object_amount, group_box_height_list=group_box_height_list,
                                     ghs_amount_list=ghs_amount_list,
                                     regular_font=regular_font, bold_font=bold_font,
                                     qrcode_width=qrcode_width, text_extra_width_list=text_extra_width_list,
                                     text_extra_width_list_qr=text_extra_width_list_qr, body_height=body_height)

    elif create_only_qr_codes:
        object_id = list(object_specifications.keys())[0]
        object_name = object_specifications[object_id]["object_name"]
        object_url = object_specifications[object_id]["object_url"]
        qr_code_uri = []

        for quantity_index in range(1, quantity + 1):
            if custom_qr_code_texts and f"{object_id}_{quantity_index}" in custom_qr_code_texts:
                url = custom_qr_code_texts[f"{object_id}_{quantity_index}"]
            elif only_id_qr_code and add_label_number:
                url = f"{object_id} {quantity_index}"
                if add_maximum_label_number:
                    url += f"_{quantity}"
            else:
                url = f"{object_id if only_id_qr_code else object_url}"
            image = qrcode.make(url, border=1)
            image_stream = io.BytesIO()
            image.save(image_stream, format='png')
            image_stream.seek(0)
            qr_code_uri.append('data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8'))

        box_height = max(math.floor(qr_code_width + 0.5), 6)
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
                    box_width = qr_code_width + max((len(str(object_id)) * 2.8) + (2 * len(str(quantity))) + 6,
                                                    len(object_name) * 2.2)
                    if quantity >= 10:
                        box_width += 2.8
                    if quantity >= 100:
                        box_width += 2.8
                else:
                    box_width = qr_code_width + max(2.8 + (len(str(object_id)) * 2.8) + len(str(quantity)),
                                                    len(object_name) * 2.2)
                    if quantity >= 10:
                        box_width += 2.8
                    if quantity >= 100:
                        box_width += 2.8
            else:
                box_width = qr_code_width + max(2.8 + (len(str(object_id)) * 2.8), len(object_name) * 2.2)
        elif add_label_number:
            if add_maximum_label_number:
                box_width = qr_code_width + max((2 * len(str(quantity))) + 5.6, len(object_name) * 2.2)
                if quantity >= 100:
                    box_width += 2.8
                if quantity == 1000:
                    box_width += 2.8
            else:
                box_width = qr_code_width + max(len(str(quantity)) + 2.8, len(object_name) * 2.2)
                if quantity >= 100:
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
            qr_code_width = label_dimension["qr_code_width"]
            box_width = label_dimension["label_width"]
            box_height = label_dimension["label_height"]
            horizontal_label_margin = label_dimension["margin_horizontal"] / 2
            vertical_label_margin = label_dimension["margin_vertical"] / 2 - 0.25
            labels_in_row = label_dimension["labels_in_row"]
            labels_in_col = label_dimension["labels_in_col"]
            has_label_dimension = True
            text_name_top += 2
            labels_on_page = labels_in_row * labels_in_col
            if qr_code_width > 7:
                text_top = 0.125

        if qr_code_width <= 8 and not has_label_dimension:
            text_top -= 0.5
            text_name_top += 0.5
        qr_code_top = (box_height - qr_code_width) / 2
        out_box_width = paper_width - 13.5
        out_box_height = paper_height - 4.5
        text_width = box_width - qr_code_width - 1.5
        if not show_id_on_label and not add_label_number:
            text_top = (qr_code_width - 2) / 2
        html = flask.render_template("labels/QRCode.html", qr_code_uri=qr_code_uri, object_id=object_id,
                                     box_width=box_width,
                                     box_height=box_height, paper_width=paper_width, paper_height=paper_height,
                                     object_name=object_name, vertical_label_margin=vertical_label_margin,
                                     horizontal_label_margin=horizontal_label_margin, qrcode_width=qr_code_width,
                                     qr_quantity=quantity, show_id=show_id_on_label, add_label_nr=add_label_number,
                                     add_maximum_label_nr=add_maximum_label_number,
                                     text_left=text_left, text_top=text_top, text_name_top=text_name_top,
                                     out_box_width=out_box_width, out_box_height=out_box_height,
                                     has_label_dimension=has_label_dimension, text_width=text_width,
                                     qr_code_top=qr_code_top, labels_on_page=labels_on_page,
                                     regular_font=regular_font, bold_font=bold_font)

    else:
        box_width = max(label_width, min_label_width)
        ghs_width = qr_code_width / 2
        qrcode_box_width = box_width
        ghs_box_width = box_width
        qrcode_width = 15

        if centered:
            if ghs_classes_side_by_side:
                qrcode_box_width = qrcode_box_width / 2
                ghs_box_width = ghs_box_width / 2
        else:
            qrcode_box_width = qr_code_width
            ghs_box_width = ghs_width * 2

        row_amount = int(math.floor((paper_width - 6.5) / (box_width + 5)))

        tmp_index = 0
        max_box_height = 0.0
        max_ghs_height = 0.0
        max_box_height_amount = 0.0

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

            box_side_by_side_height = max(21, math.ceil(max_ghs_height), box_height - 12)

            box_height_amount = box_height + 4 * math.floor(len(object_name_list[tmp_index]) * 2.3 / box_width)

            tmp_index += 1
            if box_height > max_box_height:
                max_box_height = box_height
            if ghs_height > max_ghs_height:
                max_ghs_height = ghs_height
            if box_height_amount > max_box_height_amount:
                max_box_height_amount = box_height_amount

        object_amount = len(username_list)

        column_amount = int(math.floor((paper_height - 15) / (max_box_height_amount + 5)))
        if quantity == 1 and fill_single_page:
            page_amount = row_amount * column_amount
            outer_box_width = paper_width - 10
            outer_box_height = paper_height - 15
        else:
            page_amount = quantity
            outer_box_width = paper_width - 10
            outer_box_height = ((quantity // 4) + 1) * max_box_height + 5

        if not fill_single_page:
            outer_box_height = (((quantity * object_amount) // 4) + 1) * max_box_height + 5

        has_ghs = [len(hazard_list[hazard_index]) > 0 for hazard_index in range(0, len(hazard_list))]

        html = flask.render_template("labels/FixedWidth.html",
                                     box_width=box_width, object_amount=object_amount,
                                     box_height=max_box_height, qr_code_uri_list=qr_code_uri_list,
                                     qrcode_width=qrcode_width, paper_width=paper_width, paper_height=paper_height,
                                     hazard_list=hazard_list, GHS_IMAGE_URIS=GHS_IMAGE_URIS, ghs_width=ghs_width,
                                     sample_code_list=sample_code_list, username_list=username_list,
                                     object_name_list=object_name_list, creation_date_list=creation_date_list,
                                     ghs_amount_list=ghs_amount_list, ghs_height=max_ghs_height, has_ghs=has_ghs,
                                     ghs_classes_side_by_side=ghs_classes_side_by_side, centered=centered,
                                     qrcode_box_width=qrcode_box_width, ghs_box_width=ghs_box_width,
                                     box_side_by_side_height=box_side_by_side_height, page_amount=page_amount,
                                     outer_box_width=outer_box_width, outer_box_height=outer_box_height,
                                     regular_font=regular_font, bold_font=bold_font)

    # return html.encode()

    return typing.cast(bytes, HTML(
        string=html, base_url="img"
    ).write_pdf(presentational_hints=True))
