import typing

import flask

from . import core
from ... import logic


def post_poke_components_task() -> None:
    if flask.current_app.config["ENABLE_BACKGROUND_TASKS"]:
        core.post_background_task(
            type='poke_components',
            data={},
            auto_delete=True
        )
    else:
        handle_poke_components_task({}, None)


def handle_poke_components_task(
    data: typing.Dict[str, typing.Any],
    task_id: typing.Optional[int]
) -> typing.Tuple[bool, typing.Optional[dict[str, typing.Any]]]:
    for component in logic.components.get_components():
        if component.export_token_available:
            try:
                logic.federation.update.update_poke_component(component)
            except Exception:
                pass
    return True, {}
