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
PAGE_SIZES = {
    'DIN A4 (Portrait)': (210, 297),
    'DIN A4 (Landscape)': (297, 210),
    'Letter (Portrait)': (8.5 * 25.4, 11 * 25.4),
    'Letter (Landscape)': (11 * 25.4, 8.5 * 25.4)
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


def _generate_font_uris() -> typing.Dict[str, str]:
    font_uris = {}
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "urw-base35-fonts"))
    for font_file_name in ["NimbusSans-Regular.otf", "NimbusSans-Bold.otf"]:
        with open(os.path.join(font_path, font_file_name), "rb") as font_file:
            font_uri = 'data:font/otf;base64,' + base64.b64encode(font_file.read()).decode('utf-8')
            font_uris[font_file_name] = font_uri
    return font_uris


FONT_URIS = _generate_font_uris()


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

    paper_width, paper_height = PAGE_SIZES[paper_format]

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
            box_height = 12.24
            label_margin = [horizontal_label_margin / 2 + 0.3, horizontal_label_margin + 0.3]
            page_margin = [9.55, 5, 5, 4.9]
            padding_top = 0.45
            padding_right = 0.3
        else:
            box_height = 7.7
            label_margin = [horizontal_label_margin / 2 + 0.544, horizontal_label_margin + 0.3]
            page_margin = [9.9, 5, 5, 5]
            padding_top = 1.0
            padding_right = 0.0

        if fill_single_page:
            if include_qrcode_in_long_labels:
                num_labels = page_amounts[paper_format][1]
            else:
                num_labels = page_amounts[paper_format][0]
        else:
            num_labels = quantity

        object_amount = len(username_list)
        html = flask.render_template(
            "labels/minimal_height_labels.html",
            username_list=username_list,
            object_name_list=object_name_list,
            creation_date_list=creation_date_list,
            hazard_list=hazard_list,
            qrcode_width=qrcode_width,
            ghs_width=ghs_width,
            object_id_list=sample_code_list,
            qr_code_uri_list=qr_code_uri_list,
            object_amount=object_amount,
            include_qrcode=include_qrcode_in_long_labels,
            box_height=box_height,
            paper_width=paper_width,
            paper_height=paper_height,
            num_labels=num_labels,
            GHS_IMAGE_URIS=GHS_IMAGE_URIS,
            min_label_width=min_label_width,
            text_extra_width_list=text_extra_width_list,
            FONT_URIS=FONT_URIS,
            label_margin=label_margin,
            page_margin=page_margin,
            padding_top=padding_top,
            padding_right=padding_right,
        )

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
        sixth_box_qrcode_box_width = 19.75
        sixth_box_ghs_box_width = 19.25
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
                    third_box_ghs_box_height_list.append(16.75 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9)
                    fourth_box_ghs_box_height_list.append(16.75 + int((ghs_amount_list[tmp_index] - 1) / 3) * 9)

                if ghs_amount_list[tmp_index] == 2 or ghs_amount_list[tmp_index] == 1:
                    third_box_ghs_box_height_list[tmp_index] += 0.3
                    fourth_box_ghs_box_height_list[tmp_index] += 0.3

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
                    fifth_inner_box_height_list[tmp_index] += 0.75
                    sixth_inner_box_height_list[tmp_index] += 0.75
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
        html = flask.render_template(
            "labels/mixed_format_labels.html",
            sample_code_list=sample_code_list,
            username_list=username_list,
            object_name_list=object_name_list,
            creation_date_list=creation_date_list,
            qr_code_uri_list=qr_code_uri_list,
            hazard_list=hazard_list,
            paper_width=paper_width,
            paper_height=paper_height,
            set_amount=set_amount,
            horizontal_label_margin=horizontal_label_margin,
            vertical_label_margin=vertical_label_margin,
            GHS_IMAGE_URIS=GHS_IMAGE_URIS,
            first_box_min_width_list=first_box_min_width_list,
            second_box_min_width_list=second_box_min_width_list,
            third_box_width=third_box_width,
            forth_box_width=forth_box_width,
            fifth_box_width=fifth_box_width,
            sixth_box_width=sixth_box_width,
            outer_box_width=outer_box_width,
            ghs_width=ghs_width,
            fifth_box_qrcode_box_width_list=fifth_box_qrcode_box_width_list,
            fifth_box_ghs_box_width_list=fifth_box_ghs_box_width_list,
            sixth_box_qrcode_box_width=sixth_box_qrcode_box_width,
            sixth_box_ghs_box_width=sixth_box_ghs_box_width,
            has_ghs_list=has_ghs_list,
            fifth_inner_box_height_list=fifth_inner_box_height_list,
            sixth_inner_box_height_list=sixth_inner_box_height_list,
            third_box_qrcode_box_height_list=third_box_qrcode_box_height_list,
            third_box_ghs_box_height_list=third_box_ghs_box_height_list,
            fourth_box_qrcode_box_height_list=fourth_box_qrcode_box_height_list,
            fourth_box_ghs_box_height_list=fourth_box_ghs_box_height_list,
            object_amount=object_amount,
            group_box_height_list=group_box_height_list,
            ghs_amount_list=ghs_amount_list,
            FONT_URIS=FONT_URIS,
            qrcode_width=qrcode_width,
            text_extra_width_list=text_extra_width_list,
            text_extra_width_list_qr=text_extra_width_list_qr,
            body_height=body_height,
        )

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

        box_height = max(math.floor(qr_code_width) + 1.225, 6)
        page_margin = [0.0, 0.0]

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

        if label_dimension is not None:
            paper_format = PAGE_SIZE_KEYS[label_dimension["paper_format"]]
            paper_width, paper_height = PAGE_SIZES[paper_format]
            qr_code_width = label_dimension["qr_code_width"]
            box_width = label_dimension["label_width"]
            box_height = label_dimension["label_height"]
            horizontal_label_margin = label_dimension["margin_horizontal"]
            vertical_label_margin = label_dimension["margin_vertical"]
            labels_in_row = label_dimension["labels_in_row"]
            labels_in_col = label_dimension["labels_in_col"]
            page_margin = [paper_height - (labels_in_col * (box_height + vertical_label_margin)),
                           paper_width - (labels_in_row * (box_width + horizontal_label_margin))]

        qrcode_width = qr_code_width + 0.5
        qr_code_top = (box_height - qr_code_width) / 2
        quantity_digits = math.floor(math.log10(quantity)) + 1
        if label_dimension:
            html = flask.render_template(
                "labels/custom_dimension_qrcode_labels.html",
                box_width=box_width,
                qr_code_uri=qr_code_uri,
                object_id=object_id,
                box_height=box_height,
                paper_width=paper_width,
                paper_height=paper_height,
                object_name=object_name,
                vertical_label_margin=vertical_label_margin,
                horizontal_label_margin=horizontal_label_margin,
                qrcode_width=qrcode_width,
                num_labels=quantity,
                show_id=show_id_on_label,
                add_label_nr=add_label_number,
                add_maximum_label_nr=add_maximum_label_number,
                qr_code_top=qr_code_top,
                FONT_URIS=FONT_URIS,
                quantity_digits=quantity_digits,
                page_margin=page_margin,
            )
        else:
            html = flask.render_template(
                "labels/qrcode_labels.html",
                qr_code_uri=qr_code_uri,
                object_id=object_id,
                paper_width=paper_width,
                paper_height=paper_height,
                object_name=object_name,
                qrcode_width=qrcode_width,
                num_labels=quantity,
                show_id=show_id_on_label,
                add_label_nr=add_label_number,
                add_maximum_label_nr=add_maximum_label_number,
                qr_code_top=qr_code_top,
                FONT_URIS=FONT_URIS,
                quantity_digits=quantity_digits,
            )

    else:
        box_width = max(label_width, min_label_width) - 0.4
        ghs_width = qr_code_width / 2
        ghs_box_width = box_width
        boxqrcode_height = 18.0

        if centered:
            if ghs_classes_side_by_side:
                ghs_box_width = ghs_box_width / 2
        else:
            if ghs_classes_side_by_side:
                ghs_box_width = ghs_width * 2
            else:
                ghs_box_width = ghs_width * 2 - 0.5
                boxqrcode_height = 19.25

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

            if centered:
                if ghs_classes_side_by_side:  # centered and ghs_classes_side_by_side
                    if len(hazard_list[tmp_index]) == 0:
                        ghs_box_width = 0
                else:  # centered and not ghs_classes_side_by_side
                    if len(hazard_list[tmp_index]) == 0:
                        boxqrcode_height += 0.1
            ghs_amount_list.append(len(hazard_list[tmp_index]))
            tmp_index += 1

        object_amount = len(username_list)

        if quantity == 1 and fill_single_page:
            num_labels = 100  # excess labels are clipped once the first page is full
            outer_box_width = paper_width - 7.5
        else:
            num_labels = quantity
            outer_box_width = paper_width - 10

        body_height = 0 if fill_single_page else 1

        html = flask.render_template(
            "labels/fixed_width_labels.html",
            box_width=box_width,
            object_amount=object_amount,
            min_label_height=min_label_height,
            qr_code_uri_list=qr_code_uri_list,
            paper_width=paper_width,
            paper_height=paper_height,
            hazard_list=hazard_list,
            GHS_IMAGE_URIS=GHS_IMAGE_URIS,
            ghs_width=ghs_width,
            sample_code_list=sample_code_list,
            username_list=username_list,
            object_name_list=object_name_list,
            creation_date_list=creation_date_list,
            ghs_amount_list=ghs_amount_list,
            ghs_classes_side_by_side=ghs_classes_side_by_side,
            centered=centered,
            ghs_box_width=ghs_box_width,
            num_labels=num_labels,
            outer_box_width=outer_box_width,
            FONT_URIS=FONT_URIS,
            boxqrcode_height=boxqrcode_height,
            body_height=body_height,
            qrcode_width=15
        )

    return typing.cast(bytes, HTML(
        string=html, base_url="img"
    ).write_pdf(presentational_hints=True))
