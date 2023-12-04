import datetime
import typing

import flask

from . import core
from ... import logic
from ...models import BackgroundTask, BackgroundTaskStatus, DataverseExport, DataverseExportStatus
from ... import db


def post_dataverse_export_task(
    object_id: int,
    user_id: int,
    server_url: str,
    api_token: str,
    dataverse: str,
    property_whitelist: typing.Optional[typing.Sequence[typing.List[typing.Union[str, int]]]],
    file_id_whitelist: typing.Sequence[int] = (),
    tag_whitelist: typing.Sequence[str] = ()
) -> typing.Tuple[typing.Union[BackgroundTaskStatus, typing.Tuple[bool, dict[str, typing.Any]]], typing.Optional[BackgroundTask]]:
    data = {
        'object_id': object_id,
        'user_id': user_id,
        'server_url': server_url,
        'api_token': api_token,
        'dataverse': dataverse,
        'property_whitelist': property_whitelist,
        'file_id_whitelist': file_id_whitelist,
        'tag_whitelist': tag_whitelist
    }
    if flask.current_app.config["ENABLE_BACKGROUND_TASKS"]:
        dataverse_export = DataverseExport(object_id, None, user_id, DataverseExportStatus.TASK_CREATED)
        db.session.add(dataverse_export)
        db.session.commit()
        return core.post_background_task(
            type='dataverse_export',
            data=data,
            auto_delete=False
        )
    else:
        return (handle_dataverse_export_task(data, None), None)  # type: ignore


def handle_dataverse_export_task(
    data: typing.Dict[str, typing.Any],
    task_id: typing.Optional[int]
) -> typing.Tuple[bool, typing.Optional[dict[str, typing.Any]]]:
    object_id: int = data['object_id']
    user_id: int = data['user_id']
    server_url: str = data['server_url']
    api_token: str = data['api_token']
    dataverse: str = data['dataverse']
    property_whitelist: typing.Optional[typing.Sequence[typing.List[typing.Union[str, int]]]] = data['property_whitelist']
    file_id_whitelist: typing.Sequence[int] = data['file_id_whitelist']
    tag_whitelist: typing.Sequence[str] = data['tag_whitelist']

    del data['api_token']
    if task_id:
        BackgroundTask.query.filter_by(id=task_id).update({"data": data})
        db.session.commit()

    credentials_are_valid = True
    validation_error = ""

    if not logic.dataverse_export.is_api_token_valid(server_url, api_token):
        credentials_are_valid = False
        validation_error = "API Token is not valid."
    else:
        if not logic.dataverse_export.dataverse_has_required_metadata_blocks(server_url, api_token, dataverse):
            credentials_are_valid = False
            validation_error = "The Dataverse does not have the required metadata blocks."

    if not credentials_are_valid:
        if task_id:
            expiration_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
            task_result = {
                "error_message": validation_error,
                "expiration_date": expiration_date
            }
            BackgroundTask.query.filter_by(id=task_id).update({"result": task_result})

            db.session.delete(
                DataverseExport.query.filter_by(object_id=object_id).first()
            )
            db.session.commit()
            return False, None
        else:
            return False, {
                "status": BackgroundTaskStatus.FAILED,
                "error_message": validation_error
            }
    else:
        try:
            success, url_or_error = logic.dataverse_export.upload_object(
                object_id=object_id,
                user_id=user_id,
                server_url=server_url,
                api_token=api_token,
                dataverse=dataverse,
                property_whitelist=property_whitelist,
                file_id_whitelist=file_id_whitelist,
                tag_whitelist=tag_whitelist
            )
        except logic.errors.DataverseNotReachableError:
            success = False
            url_or_error = '%(service_name)s cannot reach the %(dataverse_name)s API at this time. Please try again later.'

        result_key = "url" if success else "error_message"
        if task_id:
            # background tasks enabled
            if not success:
                db.session.delete(
                    DataverseExport.query.filter_by(object_id=object_id).first()
                )

            expiration_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
            BackgroundTask.query.filter_by(id=task_id).update({
                "result": {
                    f"{result_key}": url_or_error
                },
                "expiration_date": expiration_date
            })
            db.session.commit()
            return success, None
        else:
            # background tasks disabled
            return success, {
                f"{result_key}": url_or_error
            }
