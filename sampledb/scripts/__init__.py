# coding: utf-8
"""

"""

from . import create_instrument
from . import update_instrument
from . import list_instruments
from . import update_instrument_responsible_users
from . import create_action
from . import update_action
from . import list_actions
from . import export_action_schema
from . import send_announcement
from . import sudo_file_source_get_existing_files
from . import sudo_file_source_copy_file
from . import run


script_functions = {
    'create_instrument': create_instrument.main,
    'update_instrument': update_instrument.main,
    'list_instruments': list_instruments.main,
    'update_instrument_responsible_users': update_instrument_responsible_users.main,
    'create_action': create_action.main,
    'update_action': update_action.main,
    'list_actions': list_actions.main,
    'export_action_schema': export_action_schema.main,
    'send_announcement': send_announcement.main,
    'sudo_file_source_copy_file': sudo_file_source_copy_file.main,
    'sudo_file_source_get_existing_files': sudo_file_source_get_existing_files.main,
    'run': run.main
}
