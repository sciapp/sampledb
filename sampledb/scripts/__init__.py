# coding: utf-8
"""

"""

import importlib.util
import os
import string
import typing
import types


def _find_script_modules() -> typing.Dict[str, types.ModuleType]:
    """
    Find, import and return all .py files located in the scripts directory.
    """
    scripts_path = os.path.abspath(os.path.dirname(__file__))
    script_modules = {}
    for file_name in os.listdir(scripts_path):
        module_name, file_extension = os.path.splitext(file_name)
        # only import Python files
        if file_extension != '.py':
            continue
        # prevent importing files with invalid module names
        if not all(c in string.ascii_letters + string.digits + '_' for c in module_name) or module_name.startswith('__'):
            continue
        module_path = os.path.join(scripts_path, file_name)
        spec = importlib.util.spec_from_file_location(f'sampledb.scripts.{module_name}', module_path)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        script_modules[module_name] = module
    return script_modules


script_modules = _find_script_modules()
globals().update(script_modules)

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
