
import base64
import datetime
import io
import json
import typing

import flask
import flask_login
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfdoc import PDFInfo
from reportlab.lib.pagesizes import A4 as pagesize
from reportlab.lib.units import mm
from PIL import Image
import qrcode
import qrcode.image.pil

from .. import logic
from ..logic import object_log
from ..logic.objects import get_object
from ..logic.actions import get_action, ActionType
from ..logic.object_log import ObjectLogEntryType
from ..logic.users import get_user

SECTIONS = {
    'activity_log',
    'locations',
    'publications',
    'files',
    'comments'
}

PAGE_WIDTH, PAGE_HEIGHT = pagesize
LEFT_MARGIN = 25.4 * mm
RIGHT_MARGIN = 25.4 * mm
TOP_MARGIN = 31.7 * mm
BOTTOM_MARGIN = 31.7 * mm


def _set_up_page(canvas, object_id, qrcode_uri, logo_uri=None, logo_aspect_ratio=1, logo_alignment='right'):
    canvas.saveState()
    canvas.drawImage(qrcode_uri, PAGE_WIDTH - 27.5 * mm, PAGE_HEIGHT - 27.5 * mm, 20 * mm, 20 * mm)
    if logo_uri:
        if logo_aspect_ratio > 1:
            logo_width = 19 * mm * logo_aspect_ratio
            logo_height = 19 * mm
        else:
            logo_width = 19 * mm
            logo_height = 19 * mm / logo_aspect_ratio
        # right margin due to QR code
        right_margin = 27.5 * mm
        max_width = PAGE_WIDTH - right_margin - LEFT_MARGIN
        if logo_width > max_width:
            logo_height *= max_width / logo_width
            logo_width = max_width
        max_height = 19 * mm
        if logo_height > max_height:
            logo_width *= max_height / logo_height
            logo_height = max_height
        logo_alignment = logo_alignment.lower()
        if logo_alignment == 'left':
            x = LEFT_MARGIN
        elif logo_alignment == 'center':
            x = (LEFT_MARGIN + PAGE_WIDTH - right_margin - logo_width) / 2
        else:
            x = PAGE_WIDTH - right_margin - logo_width
        y = PAGE_HEIGHT - 26.5 * mm
        canvas.drawImage(logo_uri, x, y, logo_width, logo_height)
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(PAGE_WIDTH - 17.5 * mm, PAGE_HEIGHT - 29 * mm, "#{}".format(object_id))
    canvas.drawCentredString(PAGE_WIDTH - 17.5 * mm, PAGE_HEIGHT - 33 * mm, "Exported on")
    canvas.drawCentredString(PAGE_WIDTH - 17.5 * mm, PAGE_HEIGHT - 37 * mm, datetime.datetime.utcnow().date().strftime('%Y-%m-%d'))
    page_num = canvas.getPageNumber()
    canvas.setFont('Helvetica', 11)
    canvas.drawCentredString(PAGE_WIDTH / 2, 15 * mm, "{}".format(page_num))
    canvas.restoreState()


def _get_num_fitting_characters(canvas, line, max_width, font_name, font_size):
    line_width = canvas.stringWidth(line, font_name, font_size)
    if line_width <= max_width:
        return len(line)
    # number of characters guaranteed to fit
    lower_boundary = 1
    # maximum possible number of fitting characters
    upper_boundary = len(line) - 1
    approx_num_fitting_characters = len(line)
    while lower_boundary < upper_boundary:
        # approximate fitting characters based on average width
        approx_num_fitting_characters = int(approx_num_fitting_characters / line_width * max_width)
        # enforce upper and lower boundaries for search
        approx_num_fitting_characters = max(lower_boundary + 1, approx_num_fitting_characters)
        approx_num_fitting_characters = min(upper_boundary, approx_num_fitting_characters)
        line_width = canvas.stringWidth(line[:approx_num_fitting_characters], font_name, font_size)
        if line_width < max_width:
            lower_boundary = approx_num_fitting_characters
        elif line_width > max_width:
            upper_boundary = approx_num_fitting_characters - 1
        else:
            lower_boundary = approx_num_fitting_characters
            break
    if ' ' in line[:lower_boundary]:
        return line[:lower_boundary].rfind(' ')
    return lower_boundary


def _draw_left_aligned_wrapped_text(canvas: Canvas, text, left_offset, max_width, top_cursor, font_name, font_size, line_height, justify=False):
    canvas.setFont(font_name, font_size)
    lines = []
    while text:
        text = text.lstrip()
        line = text[:_get_num_fitting_characters(canvas, text, max_width, font_name, font_size)]
        lines.append(line.strip())
        text = text[len(line):]

    for index, line in enumerate(lines):
        if line:
            if justify and len(line) > 1 and index < len(lines) - 1:
                char_space = (max_width - canvas.stringWidth(line, font_name, font_size)) / (len(line) - 1)
            else:
                char_space = 0
            canvas.drawString(left_offset, top_cursor, line, charSpace=char_space)
            top_cursor -= line_height * font_size
            if top_cursor <= BOTTOM_MARGIN:
                canvas.showPage()
                canvas.set_up_page()
                canvas.setFont(font_name, font_size)
                top_cursor = PAGE_HEIGHT - TOP_MARGIN
    return top_cursor


def _append_text(canvas, text, justify=False):
    canvas.top_cursor = _draw_left_aligned_wrapped_text(canvas, text, canvas.left_cursor, PAGE_WIDTH - RIGHT_MARGIN - canvas.left_cursor, canvas.top_cursor, "Helvetica", 11, 1.2, justify)


def _handle_object(data, schema, path, canvas):
    if 'propertyOrder' not in schema:
        for property_name, property_data in data.items():
            property_schema = schema['properties'][property_name]
            _handle_any(property_data, property_schema, path + [property_name], canvas)
    else:
        for property_name in schema['propertyOrder']:
            property_data = data.get(property_name, None)
            property_schema = schema['properties'][property_name]
            _handle_any(property_data, property_schema, path + [property_name], canvas)
        for property_name, property_data in data.items():
            if property_name in schema['propertyOrder']:
                continue
            property_schema = schema['properties'][property_name]
            _handle_any(property_data, property_schema, path + [property_name], canvas)


def _handle_any(data, schema, path, canvas):
    if data is None and schema is None:
        return
    if data is None:
        _handle_none(data, schema, path, canvas)
    elif schema['type'] == 'object':
        _handle_object(data, schema, path, canvas)
    elif schema['type'] == 'array':
        _handle_array(data, schema, path, canvas)
    elif schema['type'] == 'text':
        _handle_text(data, schema, path, canvas)
    elif schema['type'] == 'bool':
        _handle_bool(data, schema, path, canvas)
    elif schema['type'] == 'quantity':
        _handle_quantity(data, schema, path, canvas)
    elif schema['type'] == 'sample':
        _handle_sample(data, schema, path, canvas)
    elif schema['type'] == 'measurement':
        _handle_measurement(data, schema, path, canvas)
    elif schema['type'] == 'tags':
        _handle_tags(data, schema, path, canvas)
    elif schema['type'] == 'datetime':
        _handle_datetime(data, schema, path, canvas)
    elif schema['type'] == 'hazards':
        _handle_hazards(data, schema, path, canvas)
    else:
        _handle_unknown(data, schema, path, canvas)


def _handle_none(data, schema, path, canvas):
    text = '• {}: —'.format(schema['title'])
    _append_text(canvas, text)


def _handle_unknown(data, schema, path, canvas):
    text = '• {}: {}'.format(schema['title'], json.dumps(data))
    _append_text(canvas, text)


def _handle_hazards(data, schema, path, canvas):
    if data['hazards']:
        hazards = [
            {
                1: 'Explosive',
                2: 'Flammable',
                3: 'Oxidizing',
                4: 'Compressed Gas',
                5: 'Corrosive',
                6: 'Toxic',
                7: 'Harmful',
                8: 'Health Hazard',
                9: 'Environmental Hazard'
            }.get(hazard, 'Unknown') for hazard in data['hazards']
        ]
        text = '• {}: {}'.format(schema['title'], ', '.join(hazards))
    else:
        text = '• {}: —'.format(schema['title'])
    _append_text(canvas, text)


def _handle_array(data, schema, path, canvas):
    _append_text(canvas, '• {}:'.format(schema['title']))

    previous_left_cursor = canvas.left_cursor
    for index, data in enumerate(data):
        canvas.left_cursor = previous_left_cursor + 2.5 * mm
        _append_text(canvas, '{}. {}:'.format(index + 1, schema['items']['title']))
        canvas.left_cursor = previous_left_cursor + 6 * mm
        _handle_any(data, schema['items'], path + [index], canvas)
    canvas.left_cursor = previous_left_cursor


def _handle_quantity(data, schema, path, canvas):
    if data['units'] == '1':
        text = '• {}: {}'.format(schema['title'], data['magnitude_in_base_units'])
    else:
        quantity = logic.datatypes.Quantity.from_json(data)
        text = '• {}: {:g} {}'.format(schema['title'], quantity.magnitude, logic.units.prettify_units(quantity.units))
    _append_text(canvas, text)


def _handle_sample(data, schema, path, canvas):
    text = '• {}: #{}'.format(schema['title'], data['object_id'])
    _append_text(canvas, text)


def _handle_measurement(data, schema, path, canvas):
    text = '• {}: #{}'.format(schema['title'], data['object_id'])
    _append_text(canvas, text)


def _handle_datetime(data, schema, path, canvas):
    text = '• {}: {}'.format(schema['title'], data['utc_datetime'])
    _append_text(canvas, text)


def _handle_tags(data, schema, path, canvas):
    text = '• {}: {}'.format(schema['title'], ', '.join(data['tags']))
    _append_text(canvas, text)


def _handle_text(data, schema, path, canvas):
    prefix = '• {}: '.format(schema['title'])
    text = prefix + data.get('text', '-')
    previously_used_left_cursor = canvas.left_cursor
    indent = canvas.stringWidth(prefix, 'Helvetica', 11)
    for paragraph in text.splitlines(keepends=False):
        if paragraph.strip():
            _append_text(canvas, paragraph, justify=True)
        else:
            canvas.top_cursor -= 1.2 * 11
        canvas.left_cursor = previously_used_left_cursor + indent
    canvas.left_cursor = previously_used_left_cursor


def _handle_bool(data, schema, path, canvas):
    text = '• {}: {}'.format(schema['title'], 'Yes' if data.get('value', True) else 'No')
    _append_text(canvas, text)


def _write_metadata(object, canvas):
    action = get_action(object.action_id)
    object_type = {
        ActionType.SAMPLE_CREATION: "Sample",
        ActionType.MEASUREMENT: "Measurement",
        ActionType.SIMULATION: "Simulation"
    }.get(action.type, "Object")
    title = '{} #{}: {}'.format(object_type, object.id, object.data.get('name', {}).get('text', ''))

    canvas.bookmarkPage('object_{}'.format(object.id))
    canvas.addOutlineEntry(title, 'object_{}'.format(object.id), level=0)
    canvas.bookmarkPage('object_{}_info'.format(object.id))
    canvas.addOutlineEntry("Information", 'object_{}_info'.format(object.id), level=1)
    canvas.set_up_page()
    canvas.top_cursor = PAGE_HEIGHT - TOP_MARGIN
    canvas.top_cursor = _draw_left_aligned_wrapped_text(canvas, title, canvas.left_cursor, PAGE_WIDTH - RIGHT_MARGIN - canvas.left_cursor, canvas.top_cursor, "Helvetica-Bold", 18, 1.2)
    canvas.top_cursor -= 6 * mm
    canvas.top_cursor = _draw_left_aligned_wrapped_text(canvas, "Information", canvas.left_cursor, PAGE_WIDTH - RIGHT_MARGIN - canvas.left_cursor, canvas.top_cursor, "Helvetica-Bold", 14, 1.2)
    canvas.top_cursor -= 4 * mm
    _handle_object(object.data, object.schema, [], canvas)
    canvas.showPage()


def _write_activity_log(object, canvas):
    object_log_entries = object_log.get_object_log_entries(object_id=object.id, user_id=flask_login.current_user.id)

    canvas.bookmarkPage('object_{}_activity_log'.format(object.id))
    canvas.addOutlineEntry("Activity Log", 'object_{}_activity_log'.format(object.id), level=1)
    canvas.set_up_page()
    canvas.top_cursor = PAGE_HEIGHT - TOP_MARGIN
    canvas.top_cursor = _draw_left_aligned_wrapped_text(canvas, "Activity Log", canvas.left_cursor, PAGE_WIDTH - RIGHT_MARGIN - canvas.left_cursor, canvas.top_cursor, "Helvetica-Bold", 14, 1.2)
    canvas.top_cursor -= 4 * mm
    for object_log_entry in reversed(object_log_entries):
        text = '• {} — {}'.format(object_log_entry.utc_datetime.strftime('%Y-%m-%d %H:%M'), get_user(object_log_entry.user_id).name)
        if object_log_entry.type == ObjectLogEntryType.CREATE_BATCH:
            text += ' created this object as part of a batch'
        elif object_log_entry.type == ObjectLogEntryType.CREATE_OBJECT:
            text += ' created this object'
        elif object_log_entry.type == ObjectLogEntryType.EDIT_OBJECT:
            text += ' edited this object'
        elif object_log_entry.type == ObjectLogEntryType.POST_COMMENT:
            text += ' posted a comment'
        elif object_log_entry.type == ObjectLogEntryType.RESTORE_OBJECT_VERSION:
            text += ' restored a previous version of this object'
        elif object_log_entry.type == ObjectLogEntryType.UPLOAD_FILE:
            text += ' posted a file'
        elif object_log_entry.type == ObjectLogEntryType.USE_OBJECT_IN_MEASUREMENT:
            text += ' used this object in measurement #{}'.format(object_log_entry.data['measurement_id'])
        elif object_log_entry.type == ObjectLogEntryType.USE_OBJECT_IN_SAMPLE_CREATION:
            text += ' used this object to create sample #{}'.format(object_log_entry.data['sample_id'])
        elif object_log_entry.type == ObjectLogEntryType.ASSIGN_LOCATION:
            object_location_assignment_id = object_log_entry.data['object_location_assignment_id']
            object_location_assignment = logic.locations.get_object_location_assignment(object_location_assignment_id)
            if object_location_assignment.location_id is not None and object_location_assignment.responsible_user_id is not None:
                text += ' assigned this object to location #{} and user #{}'.format(object_location_assignment.location_id, object_location_assignment.responsible_user_id)
            elif object_location_assignment.location_id is not None:
                text += ' assigned this object to location #{}'.format(object_location_assignment.location_id)
            elif object_location_assignment.responsible_user_id is not None:
                text += ' assigned this object to user #{}'.format(object_location_assignment.responsible_user_id)
        elif object_log_entry.type == ObjectLogEntryType.LINK_PUBLICATION:
            text += ' linked publication {} to this object.'.format(object_log_entry.data['doi'])
        else:
            text += ' performed an unknown action'
        _append_text(canvas, text)
    canvas.showPage()


def _write_files(object, canvas):
    files = logic.files.get_files_for_object(object.id)
    if files:
        canvas.bookmarkPage('object_{}_files'.format(object.id))
        canvas.addOutlineEntry("Files", 'object_{}_files'.format(object.id), level=1)
        canvas.set_up_page()
        canvas.top_cursor = PAGE_HEIGHT - TOP_MARGIN
        canvas.top_cursor = _draw_left_aligned_wrapped_text(canvas, "Files", canvas.left_cursor, PAGE_WIDTH - RIGHT_MARGIN - canvas.left_cursor, canvas.top_cursor, "Helvetica-Bold", 14, 1.2)
        canvas.top_cursor -= 4 * mm
        for file in files:
            if file.is_hidden:
                text = '• {} — {}: (hidden)'.format(file.utc_datetime.strftime('%Y-%m-%d %H:%M'), file.uploader.name)
            else:
                text = '• {} — {}: {}'.format(file.utc_datetime.strftime('%Y-%m-%d %H:%M'), file.uploader.name, file.title)
            _append_text(canvas, text)
        canvas.showPage()
        for index, file in enumerate(files):
            if file.is_hidden:
                continue
            if file.storage != 'local':
                continue
            for file_extension in ('.png', '.jpg', '.jpeg'):
                if file.original_file_name.lower().endswith(file_extension):
                    try:
                        image = Image.open(file.open())
                    except Exception:
                        continue
                    title = "File #{}: {}".format(index + 1, file.title)
                    canvas.bookmarkPage('object_{}_files_{}'.format(object.id, index))
                    canvas.addOutlineEntry(title, 'object_{}_files_{}'.format(object.id, index), level=2)
                    canvas.set_up_page()
                    canvas.top_cursor = PAGE_HEIGHT - TOP_MARGIN
                    canvas.top_cursor = _draw_left_aligned_wrapped_text(canvas, title, canvas.left_cursor, PAGE_WIDTH - RIGHT_MARGIN - canvas.left_cursor, canvas.top_cursor, "Helvetica-Bold", 12, 1.2)
                    canvas.top_cursor -= 4 * mm
                    if file.description:
                        _append_text(canvas, file.description)
                    original_image_width, original_image_height = image.size
                    image_width = original_image_width / 300 * 25.4 * mm
                    image_height = original_image_height / 300 * 25.4 * mm
                    max_image_width = PAGE_WIDTH - RIGHT_MARGIN - canvas.left_cursor
                    max_image_height = canvas.top_cursor - BOTTOM_MARGIN
                    if max_image_height / original_image_height <= max_image_width / original_image_width:
                        if max_image_height < image_height:
                            image_width = max_image_height / original_image_height * original_image_width
                            image_height = max_image_height
                    else:
                        if max_image_width < image_width:
                            image_height = max_image_width / original_image_width * original_image_height
                            image_width = max_image_width
                    image_stream = io.BytesIO()
                    image.save(image_stream, format='png')
                    image_stream.seek(0)
                    image_uri = 'data:image/png;base64,' + base64.b64encode(image_stream.read()).decode('utf-8')
                    canvas.drawImage(image_uri, canvas.left_cursor, canvas.top_cursor - image_height, image_width, image_height)
                    canvas.showPage()
                    break


def _write_comments(object, canvas):
    comments = logic.comments.get_comments_for_object(object.id)
    if comments:
        canvas.bookmarkPage('object_{}_comments'.format(object.id))
        canvas.addOutlineEntry("Comments", 'object_{}_comments'.format(object.id), level=1)
        canvas.set_up_page()
        canvas.top_cursor = PAGE_HEIGHT - TOP_MARGIN
        canvas.top_cursor = _draw_left_aligned_wrapped_text(canvas, "Comments", canvas.left_cursor, PAGE_WIDTH - RIGHT_MARGIN - canvas.left_cursor, canvas.top_cursor, "Helvetica-Bold", 14, 1.2)
        canvas.top_cursor -= 4 * mm
        for comment in comments:
            text = '• {} — {}:'.format(comment.utc_datetime.strftime('%Y-%m-%d %H:%M'), comment.author.name)
            _append_text(canvas, text)
            previous_left_cursor = canvas.left_cursor
            canvas.left_cursor = previous_left_cursor + 5 * mm
            for paragraph in comment.content.splitlines(keepends=False):
                if paragraph.strip():
                    _append_text(canvas, paragraph, justify=True)
                else:
                    canvas.top_cursor -= 1.2 * 11
            canvas.left_cursor = previous_left_cursor
            canvas.top_cursor -= 4 * mm
        canvas.showPage()


def _write_locations(object, canvas):
    location_assignments = logic.locations.get_object_location_assignments(object.id)
    if location_assignments:
        canvas.bookmarkPage('object_{}_locations'.format(object.id))
        canvas.addOutlineEntry("Locations", 'object_{}_locations'.format(object.id), level=1)
        canvas.set_up_page()
        canvas.top_cursor = PAGE_HEIGHT - TOP_MARGIN
        canvas.top_cursor = _draw_left_aligned_wrapped_text(canvas, "Locations", canvas.left_cursor, PAGE_WIDTH - RIGHT_MARGIN - canvas.left_cursor, canvas.top_cursor, "Helvetica-Bold", 14, 1.2)
        canvas.top_cursor -= 4 * mm
        for location_assignment in location_assignments:
            text = '• {} — {}:'.format(location_assignment.utc_datetime.strftime('%Y-%m-%d %H:%M'), logic.users.get_user(location_assignment.user_id).name)
            _append_text(canvas, text)
            previous_left_cursor = canvas.left_cursor
            canvas.left_cursor = previous_left_cursor + 5 * mm
            if location_assignment.location_id is not None:
                text = 'Location: {} (#{})'.format(logic.locations.get_location(location_assignment.location_id).name, location_assignment.location_id)
                _append_text(canvas, text)
            if location_assignment.responsible_user_id is not None:
                text = 'Responsible User: {} (#{})'.format(logic.users.get_user(location_assignment.responsible_user_id).name, location_assignment.responsible_user_id)
                _append_text(canvas, text)
            if location_assignment.description:
                _append_text(canvas, 'Description:')
            canvas.left_cursor = previous_left_cursor + 10 * mm
            for paragraph in location_assignment.description.splitlines(keepends=False):
                if paragraph.strip():
                    _append_text(canvas, paragraph, justify=True)
                else:
                    canvas.top_cursor -= 1.2 * 11
            canvas.left_cursor = previous_left_cursor
            canvas.top_cursor -= 4 * mm
        canvas.showPage()


def _write_publications(object, canvas):
    publications = logic.publications.get_publications_for_object(object.id)
    if publications:
        canvas.bookmarkPage('object_{}_publications'.format(object.id))
        canvas.addOutlineEntry("Publications", 'object_{}_publications'.format(object.id), level=1)
        canvas.set_up_page()
        canvas.top_cursor = PAGE_HEIGHT - TOP_MARGIN
        canvas.top_cursor = _draw_left_aligned_wrapped_text(canvas, "Publications", canvas.left_cursor, PAGE_WIDTH - RIGHT_MARGIN - canvas.left_cursor, canvas.top_cursor, "Helvetica-Bold", 14, 1.2)
        canvas.top_cursor -= 4 * mm
        for publication in publications:
            text = f'• {publication.doi}: {publication.title or "—"}'
            if publication.object_name:
                text += f' ({publication.object_name})'
            _append_text(canvas, text)
        canvas.showPage()


def create_pdfexport(
        object_ids: typing.Sequence[int],
        sections: typing.Set[str] = SECTIONS
) -> bytes:
    """
    Create a PDF containing the exported information of one or more objects.

    :param object_ids: the ID of the objects
    :param sections: a list of sections to include in the generated PDF
    :return: the PDF data
    """
    pdf_stream = io.BytesIO()
    canvas = Canvas(pdf_stream, pagesize=pagesize)
    for object_id in object_ids:
        object = get_object(object_id)

        image = qrcode.make(flask.url_for('.object', object_id=object_id, _external=True), image_factory=qrcode.image.pil.PilImage)
        image_stream = io.BytesIO()
        image.save(image_stream)
        image_stream.seek(0)
        qrcode_uri = 'data:image/svg+xml;base64,' + base64.b64encode(image_stream.read()).decode('utf-8')

        service_name = flask.current_app.config['SERVICE_NAME']
        canvas.setTitle(service_name + ' Export')
        canvas.setAuthor(service_name)
        canvas.setCreator(service_name)
        # set PDF producer (not exposed by reportlab Canvas API)
        PDFInfo.producer = service_name
        canvas.showOutline()
        logo_uri = flask.current_app.config['internal'].get('PDFEXPORT_LOGO_URL', None)
        logo_aspect_ratio = flask.current_app.config['internal'].get('PDFEXPORT_LOGO_ASPECT_RATIO', 1)
        logo_alignment = flask.current_app.config['PDFEXPORT_LOGO_ALIGNMENT']
        canvas.set_up_page = lambda: _set_up_page(canvas, object_id, qrcode_uri, logo_uri, logo_aspect_ratio, logo_alignment)
        canvas.left_cursor = LEFT_MARGIN
        canvas.top_cursor = PAGE_HEIGHT - TOP_MARGIN
        _write_metadata(object, canvas)
        if 'activity_log' in sections:
            _write_activity_log(object, canvas)
        if 'locations' in sections:
            _write_locations(object, canvas)
        if 'publications' in sections:
            _write_publications(object, canvas)
        if 'files' in sections:
            _write_files(object, canvas)
        if 'comments' in sections:
            _write_comments(object, canvas)
    canvas.save()
    pdf_stream.seek(0)
    return pdf_stream.read()
