.. _labels:

Label Paper Formats
===================

The configuration variable ``SAMPLEDB_LABEL_PAPER_FORMATS`` can be used to set available label paper formats for
self-adhesive labels, which can be used when generating QR Code labels. The value of this variable must consist of a list
of JSON objects. Each JSON object represents a label paper format and must contain the following keys:

 * ``format_name``: Name of the label paper format which is shown during selection (string or dictionary with language keys (e.g. ``{"en": "Example Format"}``))
 * ``labels_in_row``: Number of labels in a row (positive integer)
 * ``labels_in_col``: Number of labels in a column (positive integer)
 * ``qr_code_width``: Width of the QR code in mm (positive integer)
 * ``label_width``: Width of a single label in mm (positive float)
 * ``label_height``: Height of a single label in mm (positive float)
 * ``margin_horizontal``: Distance between two labels in horizontal direction in mm (positive float)
 * ``margin_vertical``: Distance between two labels in vertical direction in mm (positive float)
 * ``paper_format``: Paper format that should be used (integer between 0 and 3)
    * 0: DIN A4 Portrait
    * 1: DIN A4 Landscape
    * 2: Letter Portrait
    * 3: Letter Landscape

By default, no label paper formats are available. (``[]``)
