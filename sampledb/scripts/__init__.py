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

script_modules = {
    module.__name__.split('.')[-1]: module
    for module in (
        create_instrument,
        update_instrument,
        list_instruments,
        update_instrument_responsible_users,
        create_action,
        update_action,
        list_actions,
        export_action_schema,
        create_other_user,
        send_announcement,
        set_administrator,
        set_user_readonly,
        set_user_hidden,
        run
    )
}

script_documentation = {
    script_name: script_module.__doc__
    for script_name, script_module
    in script_modules.items()
}

script_functions = {
    script_name: script_module.main
    for script_name, script_module
    in script_modules.items()
}
