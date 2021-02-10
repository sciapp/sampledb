import sampledb


def test_simple_params():
    schema = {
        "title": "Example Schema",
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            }
        }
    }
    data = {
        "name": {
            "_type": "text",
            "text": "Example Name"
        }
    }
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, 0) == []

    schema["notebookTemplates"] = [
        {
            "params": {}
        }
    ]
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, 0) == [
        {
            "params": {}
        }
    ]
    schema["notebookTemplates"][0]["params"]["id"] = "object_id"
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, 0) == [
        {
            "params": {
                "id": 0
            }
        }
    ]

    schema["notebookTemplates"][0]["params"]["name"] = ["name"]
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, 0) == [
        {
            "params": {
                "id": 0,
                "name": {
                    "_type": "text",
                    "text": "Example Name"
                }
            }
        }
    ]

    schema["notebookTemplates"][0]["params"]["name"] = ["name", "text"]
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, 0) == [
        {
            "params": {
                "id": 0,
                "name": "Example Name"
            }
        }
    ]


def test_params_with_reference():
    user = sampledb.models.User(
        name="User",
        email="example@example.org",
        type=sampledb.models.UserType.PERSON
    )
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name="Example Action",
        description="",
        schema={
            "title": "Example Schema",
            "type": "object",
            "properties": {
                "name": {
                    "title": "Name",
                    "type": "text"
                }
            },
            "required": ["name"]
        }
    )
    object = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            "name": {
                "_type": "text",
                "text": "Example Sample"
            }
        },
        user_id=user.id
    )

    schema = {
        "title": "Example Schema",
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "sample": {
                "title": "Reference",
                "type": "sample"
            }
        }
    }
    data = {
        "name": {
            "_type": "text",
            "text": "Example Name"
        },
        "sample": {
            "_type": "sample",
            "object_id": object.id
        }
    }
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, user.id) == []

    schema["notebookTemplates"] = [
        {
            "params": {
                "object_id": "object_id",
                "sample_id": ["sample", "object_id"],
                "sample_name": ["sample", "object", "name", "text"]
            }
        }
    ]
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, user.id) == [
        {
            "params": {
                "object_id": 0,
                "sample_id": object.id,
                "sample_name": "Example Sample"
            }
        }
    ]

    schema["properties"]["sample"]["type"] = "measurement"
    data["sample"]["_type"] = "measurement"
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, user.id) == [
        {
            "params": {
                "object_id": 0,
                "sample_id": object.id,
                "sample_name": "Example Sample"
            }
        }
    ]

    schema["properties"]["sample"]["type"] = "object_reference"
    data["sample"]["_type"] = "object_reference"
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, user.id) == [
        {
            "params": {
                "object_id": 0,
                "sample_id": object.id,
                "sample_name": "Example Sample"
            }
        }
    ]

    sampledb.logic.object_permissions.set_user_object_permissions(object.id, user.id, sampledb.models.permissions.Permissions.NONE)
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, user.id) == [
        {
            "params": {
                "object_id": 0,
                "sample_id": object.id,
                "sample_name": None
            }
        }
    ]

    sampledb.logic.object_permissions.set_user_object_permissions(object.id, user.id, sampledb.models.permissions.Permissions.READ)
    data["sample"]["object_id"] = object.id + 1
    assert sampledb.logic.notebook_templates.get_notebook_templates(0, data, schema, user.id) == [
        {
            "params": {
                "object_id": 0,
                "sample_id": object.id + 1,
                "sample_name": None
            }
        }
    ]
