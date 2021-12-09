# coding: utf-8
"""

"""

from . import build_translations
from . import create_instrument
from . import disable_two_factor_authentication
from . import update_instrument
from . import list_instruments
from . import update_instrument_responsible_users
from . import create_action
from . import update_action
from . import list_actions
from . import export_action_schema
from . import create_other_user
from . import move_local_files_to_database
from . import send_announcement
from . import set_administrator
from . import set_up_demo
from . import set_user_readonly
from . import set_user_hidden
from . import run

script_modules = {
    module.__name__.split('.')[-1]: module
    for module in (
        build_translations,
        create_instrument,
        disable_two_factor_authentication,
        update_instrument,
        list_instruments,
        update_instrument_responsible_users,
        create_action,
        update_action,
        list_actions,
        export_action_schema,
        create_other_user,
        move_local_files_to_database,
        send_announcement,
        set_administrator,
        set_up_demo,
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
