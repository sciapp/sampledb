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
from . import create_other_user
from . import send_announcement
from . import set_administrator
from . import set_user_readonly
from . import set_user_hidden
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
    'create_other_user': create_other_user.main,
    'send_announcement': send_announcement.main,
    'set_administrator': set_administrator.main,
    'set_user_readonly': set_user_readonly.main,
    'set_user_hidden': set_user_hidden.main,
    'run': run.main
}
