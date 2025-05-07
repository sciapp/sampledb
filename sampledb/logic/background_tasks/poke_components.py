import typing

import flask

from . import core
from ... import logic


def post_poke_components_task(component_ids: typing.Optional[typing.Sequence[int]] = None) -> None:
    if not component_ids:
        component_ids = []
    data = {'component_ids': component_ids}
    if flask.current_app.config["ENABLE_BACKGROUND_TASKS"]:
        core.post_background_task(
            type='poke_components',
            data=data,
            auto_delete=True
        )
    else:
        handle_poke_components_task({}, None)


def handle_poke_components_task(
    data: typing.Dict[str, typing.Any],
    task_id: typing.Optional[int]
) -> typing.Tuple[bool, typing.Optional[dict[str, typing.Any]]]:
    component_ids = data.get('component_ids', None)
    if component_ids is not None:
        components = []
        for component_id in component_ids:
            try:
                component = logic.components.get_component(component_id)
            except logic.errors.ComponentDoesNotExistError:
                pass
            else:
                components.append(component)
    else:
        components = logic.components.get_components()

    for component in components:
        if component.export_token_available:
            try:
                logic.federation.update.update_poke_component(component)
            except Exception:
                pass
    return True, {}
