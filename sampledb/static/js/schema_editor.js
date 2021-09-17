$(function() {
  $('[data-toggle="tooltip"]:not(.disabled)').tooltip();
  var schema_editor = $('#schema-editor');
  var schema_editor_templates = $('#schema-editor-templates');
  var input_schema = $('#input-schema');
  input_schema.hide();
  $('.pygments').hide();

  var schema = JSON.parse(input_schema.text());
  delete schema['displayProperties'];
  if ('propertyOrder' in schema && schema['propertyOrder'].includes('tags')) {
    schema['propertyOrder'].splice(schema['propertyOrder'].indexOf('tags'), 1);
    schema['propertyOrder'].push('tags');
  }
  if ('propertyOrder' in schema && schema['propertyOrder'].includes('hazards')) {
    schema['propertyOrder'].splice(schema['propertyOrder'].indexOf('hazards'), 1);
    schema['propertyOrder'].push('hazards');
  }
  window.schema_editor_path_mapping = {};
  window.schema_editor_errors = {};
  window.schema_editor_missing_type_support = false;

  input_schema.text(JSON.stringify(schema, null, 4));

  schema_editor.html("");

  $('form').on('submit', function() {
    return (JSON.stringify(window.schema_editor_errors) === '{}');
  });


  function buildRootObjectNode(schema) {
    var node = schema_editor_templates.find('.schema-editor-root-object')[0].cloneNode(true);
    node = $(node);
    node.find('[data-toggle="tooltip"]:not(.disabled)').tooltip();

    if ('batch' in schema) {
      window.schema_editor_missing_type_support = true;
    }
    if ('batch_name_format' in schema) {
      window.schema_editor_missing_type_support = true;
    }
    if ('displayProperties' in schema) {
      window.schema_editor_missing_type_support = true;
    }

    var title_label = node.find('.schema-editor-root-object-title-label');
    var title_input = node.find('.schema-editor-root-object-title-input');
    if ('title' in schema) {
      if (typeof schema['title'] === 'string') {
        title_input.val(schema['title']);
      } else {
        title_input.val(schema['title']['en']);
      }
    } else {
      title_input.val("");
    }
    title_input.attr('id', 'schema-editor-root-object-title-input');
    title_label.attr('for', title_input.attr('id'));
    title_input.on('change', function() {
      var title_input = $(this);
      var title_group = title_input.parent();
      var title_help = title_group.find('.help-block');
      var title = title_input.val();
      if (title === "") {
        title_help.text(window.schema_editor_translations['enter_title']);
        title_group.addClass("has-error");
      } else {
        title_help.text("");
        title_group.removeClass("has-error");
        var schema = JSON.parse(input_schema.text());
        schema['title'] = title;
        input_schema.text(JSON.stringify(schema, null, 4));
      }
    });

    var hazards_label = node.find('.schema-editor-root-object-hazards-label');
    var hazards_input = node.find('.schema-editor-root-object-hazards-input');
    hazards_input.attr('id', 'schema-editor-root-object-hazards-input');
    hazards_label.attr('for', hazards_input.attr('id'));
    if ('properties' in schema) {
      hazards_input.prop('checked', 'hazards' in schema['properties']);
    } else {
      hazards_input.prop('checked', false);
    }
    hazards_input.bootstrapToggle();
    hazards_input.on('change', function() {
      var schema = JSON.parse(input_schema.text());
      if ('properties' in schema && 'hazards' in schema['properties']) {
        delete schema['properties']['hazards'];
      }
      while ('propertyOrder' in schema && schema['propertyOrder'].includes('hazards')) {
        var index = schema['propertyOrder'].indexOf('hazards');
        schema['propertyOrder'].splice(index, 1);
      }
      while ('required' in schema && schema['required'].includes('hazards')) {
        var index = schema['required'].indexOf('hazards');
        schema['required'].splice(index, 1);
      }
      if ($(this).prop('checked')) {
        if (!('properties' in schema)) {
          schema['properties'] = {}
        }
        schema['properties']['hazards'] = {
          "type": "hazards",
          "title": "GHS Hazards"
        };
        if (!('required' in schema)) {
          schema['required'] = []
        }
        schema['required'].push('hazards');
        if (!('propertyOrder' in schema)) {
          schema['propertyOrder'] = []
        }
        schema['propertyOrder'].push('hazards');
      }
      input_schema.text(JSON.stringify(schema, null, 4));
    });

    var tags_label = node.find('.schema-editor-root-object-tags-label');
    var tags_input = node.find('.schema-editor-root-object-tags-input');
    tags_input.attr('id', 'schema-editor-root-object-tags-input');
    tags_label.attr('for', tags_input.attr('id'));
    if ('properties' in schema) {
      tags_input.prop('checked', 'tags' in schema['properties']);
    } else {
      tags_input.prop('checked', false);
    }
    tags_input.bootstrapToggle();
    tags_input.on('change', function() {
      var schema = JSON.parse(input_schema.text());
      if ('properties' in schema && 'tags' in schema['properties']) {
        delete schema['properties']['tags'];
      }
      while ('propertyOrder' in schema && schema['propertyOrder'].includes('tags')) {
        var index = schema['propertyOrder'].indexOf('tags');
        schema['propertyOrder'].splice(index, 1);
      }
      while ('required' in schema && schema['required'].includes('tags')) {
        var index = schema['required'].indexOf('tags');
        schema['required'].splice(index, 1);
      }
      if ($(this).prop('checked')) {
        if (!('properties' in schema)) {
          schema['properties'] = {}
        }
        schema['properties']['tags'] = {
          "type": "tags",
          "title": "Tags"
        };
        if (!('required' in schema)) {
          schema['required'] = []
        }
        schema['required'].push('tags');
        if (!('propertyOrder' in schema)) {
          schema['propertyOrder'] = []
        }
        schema['propertyOrder'].push('tags');
        // make sure hazards are always the final property
        if (schema['propertyOrder'].includes('hazards')) {
          while ('propertyOrder' in schema && schema['propertyOrder'].includes('hazards')) {
            var index = schema['propertyOrder'].indexOf('hazards');
            schema['propertyOrder'].splice(index, 1);
          }
          schema['propertyOrder'].push('hazards');
        }
      }
      input_schema.text(JSON.stringify(schema, null, 4));
    });

    var properties_node = node.find('.schema-editor-root-object-properties');
    var properties_in_order = [];
    if ('propertyOrder' in schema) {
      for (var i in schema['propertyOrder']) {
        var name = schema['propertyOrder'][i];
        if (!properties_in_order.includes(name)) {
          properties_in_order.push(name);
        }
      }
    } else {
      schema['propertyOrder'] = [];
    }
    for (var name in schema['properties']) {
      if (!properties_in_order.includes(name)) {
        properties_in_order.push(name);
        schema['propertyOrder'].push(name);
      }
    }
    for (var i in properties_in_order) {
      var name = properties_in_order[i];
      if (schema['properties'].hasOwnProperty(name)) {
        var path = [name];
        var is_required = ('required' in schema && schema['required'].includes(name));
        var property_node = buildPropertyNode(schema['properties'][name], path, is_required);
        if (property_node !== null) {
          properties_node[0].appendChild(property_node[0]);
        }
      }
    }

    var create_property_button = node.find('.schema-editor-create-property-button');
    create_property_button.on('click', function() {
      var schema = JSON.parse(input_schema.text());
      var num_new_properties = 1;
      var name = 'new_property_' + num_new_properties;
      while (name in schema['properties'] || [name] in window.schema_editor_path_mapping) {
        num_new_properties += 1;
        name = 'new_property_' + num_new_properties;
      }
      schema['properties'][name] = {
        "title": "",
        "type": "text"
      };
      schema['propertyOrder'].push(name);
      if (schema['propertyOrder'].includes('tags')) {
        schema['propertyOrder'].splice(schema['propertyOrder'].indexOf('tags'), 1);
        schema['propertyOrder'].push('tags');
      }
      if (schema['propertyOrder'].includes('hazards')) {
        schema['propertyOrder'].splice(schema['propertyOrder'].indexOf('hazards'), 1);
        schema['propertyOrder'].push('hazards');
      }
      var path = [name];
      var is_required = ('required' in schema && schema['required'].includes(name));
      var property_node = buildPropertyNode(schema['properties'][name], path, is_required);
      if (property_node !== null) {
        properties_node[0].appendChild(property_node[0]);
      }
      input_schema.text(JSON.stringify(schema, null, 4));
      var name_input = property_node.find('.schema-editor-generic-property-name-input');
      name_input.val("");
      name_input.trigger('change');
    });

    return node;
  }

  function globallyValidateSchema() {
    var schema = JSON.parse(input_schema.text());

    var help_block = $('#schema-editor .schema-editor-global-help');
    var help_parent = help_block.parent();
    help_block.text("");
    help_parent.removeClass("has-error");
    var has_error = false;
    if (!('properties' in schema)) {
      help_block.text(window.schema_editor_translations['objects_need_one_property']);
      help_parent.addClass("has-error");
      has_error = true;
    } else if (!('name' in schema['properties'])) {
      help_block.html(window.schema_editor_translations['object_must_have_name_text']);
      help_parent.addClass("has-error");
      has_error = true;
    } else if (!('type' in schema['properties']['name']) || schema['properties']['name']['type'] !== "text" || ('multiline' in schema['properties']['name'] && schema['properties']['name']['multiline']) || ('markdown' in schema['properties']['name'] && schema['properties']['name']['markdown']) || 'choices' in schema['properties']['name']) {
      help_block.html(window.schema_editor_translations['object_name_must_be_text']);
      help_parent.addClass("has-error");
      has_error = true;
    } else if (!('required' in schema) || !schema['required'].includes('name')) {
      help_block.html(window.schema_editor_translations['object_name_must_be_required']);
      help_parent.addClass("has-error");
      has_error = true;
    }

    var property_elements = $('#schema-editor .schema-editor-property');
    for (var i = 0; i < property_elements.length; i += 1) {
      var move_property_up_button = $(property_elements[i]).find('.schema-editor-move-property-up-button');
      var move_property_down_button = $(property_elements[i]).find('.schema-editor-move-property-down-button');
      if (i === 0) {
        move_property_up_button.prop('disabled', true);
        move_property_up_button.addClass('disabled');
      } else {
        move_property_up_button.prop('disabled', false);
        move_property_up_button.removeClass('disabled');
      }
      if (i === property_elements.length-1) {
        move_property_down_button.prop('disabled', true);
        move_property_down_button.addClass('disabled');
      } else {
        move_property_down_button.prop('disabled', false);
        move_property_down_button.removeClass('disabled');
      }
    }

    window.schema_editor_errors["global"] = true;
    if (!has_error) {
      delete window.schema_editor_errors["global"];
    }
    $('button[name="action_submit"]').prop('disabled', (JSON.stringify(window.schema_editor_errors) !== '{}'));
  }

  function buildPropertyNode(schema, path, is_required) {
    var type;
    if (schema['type'] === 'text') {
      if ('choices' in schema) {
        type = "choice";
      } else if ('markdown' in schema && schema['markdown']) {
        type = "markdown";
      } else if ('multiline' in schema && schema['multiline']) {
        type = "multiline";
      } else {
        type = "text";
      }
    } else if (schema['type'] === 'sample') {
      type = "sample";
    } else if (schema['type'] === 'measurement') {
      type = "measurement";
    } else if (schema['type'] === 'object_reference') {
      type = "object_reference";
    } else if (schema['type'] === 'bool') {
      type = "bool";
    } else if (schema['type'] === 'quantity') {
      type = "quantity";
    } else if (schema['type'] === 'datetime') {
      type = "datetime";
    } else if (schema['type'] === 'tags') {
      return null;
    } else if (schema['type'] === 'hazards') {
      return null;
    } else if (schema['type'] === 'user') {
      type = "user";
    } else if (schema['type'] === 'plotly_chart') {
      type = "plotly_chart";
    } else {
      window.schema_editor_missing_type_support = true;
      return null;
    }

    var node = schema_editor_templates.find('.schema-editor-generic-property')[0].cloneNode(true);
    node = $(node);
    node.find('[data-toggle="tooltip"]:not(.disabled)').tooltip();
    node.find('.schema-editor-' + type + '-property-settings').css('display', 'flex');

    function updateProperty() {
      var path = this;
      var real_path = window.schema_editor_path_mapping[path.join('__')].slice();
      var type = $('#schema-editor-object__' + path.join('__') + '-type-input').val();
      if (type === "text") {
        updateTextProperty(path, real_path);
      } else if (type === "choice") {
        updateChoiceProperty(path, real_path);
      } else if (type === "multiline") {
        updateMultilineProperty(path, real_path);
      } else if (type === "markdown") {
        updateMarkdownProperty(path, real_path);
      } else if (type === "bool") {
        updateBoolProperty(path, real_path);
      } else if (type === "sample") {
        updateSampleProperty(path, real_path);
      } else if (type === "user") {
        updateUserProperty(path, real_path);
      } else if (type === "measurement") {
        updateMeasurementProperty(path, real_path);
      } else if (type === "object_reference") {
        updateObjectReferenceProperty(path, real_path);
      } else if (type === "quantity") {
        updateQuantityProperty(path, real_path);
      } else if (type === "datetime") {
        updateDatetimeProperty(path, real_path);
      } else if (type === "plotly_chart") {
        updatePlotlyChartProperty(path, real_path);
      }
      globallyValidateSchema();
    }

    var delete_property_button = node.find('.schema-editor-delete-property-button');
    delete_property_button.on('click', function() {
      var path = this;
      var real_path = window.schema_editor_path_mapping[path.join('__')].slice();
      var schema = JSON.parse(input_schema.text());
      var name = real_path[real_path.length-1];
      if ('properties' in schema && name in schema['properties']) {
        delete schema['properties'][name];
      }
      while ('propertyOrder' in schema && schema['propertyOrder'].includes(name)) {
        var index = schema['propertyOrder'].indexOf(name);
        schema['propertyOrder'].splice(index, 1);
      }
      while ('required' in schema && schema['required'].includes(name)) {
        var index = schema['required'].indexOf(name);
        schema['required'].splice(index, 1);
      }
      input_schema.text(JSON.stringify(schema, null, 4));

      var name_input = $('#schema-editor #schema-editor-object__' + path.join('__') + '-name-input');
      name_input.closest('.schema-editor-property').remove();

      delete window.schema_editor_errors[path.join('__') + '__generic'];
      delete window.schema_editor_errors[path.join('__') + '__specific'];
      $('button[name="action_submit"]').prop('disabled', (JSON.stringify(window.schema_editor_errors) !== '{}'));
      globallyValidateSchema();
    }.bind(path));
    var move_property_up_button = node.find('.schema-editor-move-property-up-button');
    move_property_up_button.on('click', function() {
      var path = this;
      var real_path = window.schema_editor_path_mapping[path.join('__')].slice();
      var schema = JSON.parse(input_schema.text());
      var name = real_path[real_path.length-1];
      if ('propertyOrder' in schema && schema['propertyOrder'].includes(name)) {
        var index = schema['propertyOrder'].indexOf(name);
        if (index > 0) {
          schema['propertyOrder'].splice(index, 1);
          schema['propertyOrder'].splice(index-1, 0, name);
        }
      input_schema.text(JSON.stringify(schema, null, 4));
      globallyValidateSchema();
      var name_input = $('#schema-editor #schema-editor-object__' + path.join('__') + '-name-input');
      var element = name_input.closest('.schema-editor-property');
      element.insertBefore(element.prev('.schema-editor-property'));
      element.find('[data-toggle="tooltip"]').tooltip('hide');
      globallyValidateSchema();
      }
    }.bind(path));
    var move_property_down_button = node.find('.schema-editor-move-property-down-button');
    move_property_down_button.on('click', function() {
      var path = this;
      var real_path = window.schema_editor_path_mapping[path.join('__')].slice();
      var schema = JSON.parse(input_schema.text());
      var name = real_path[real_path.length-1];
      if ('propertyOrder' in schema && schema['propertyOrder'].includes(name)) {
        var index = schema['propertyOrder'].indexOf(name);
        var num_properties = schema['propertyOrder'].length;
        if (schema['propertyOrder'].includes('tags')) {
          num_properties -= 1;
        }
        if (schema['propertyOrder'].includes('hazards')) {
          num_properties -= 1;
        }
        if (index < num_properties - 1) {
          schema['propertyOrder'].splice(index, 1);
          schema['propertyOrder'].splice(index+1, 0, name);
        }
      input_schema.text(JSON.stringify(schema, null, 4));
      globallyValidateSchema();
      var name_input = $('#schema-editor #schema-editor-object__' + path.join('__') + '-name-input');
      var element = name_input.closest('.schema-editor-property');
      element.insertAfter(element.next('.schema-editor-property'));
      element.find('[data-toggle="tooltip"]').tooltip('hide');
      globallyValidateSchema();
      }
    }.bind(path));

    var name_label = node.find('.schema-editor-generic-property-name-label');
    var name_input = node.find('.schema-editor-generic-property-name-input');
    window.schema_editor_path_mapping[path.join('__')] = path;
    name_input.attr('id', 'schema-editor-object__' + path.join('__') + '-name-input');
    name_label.attr('for', name_input.attr('id'));
    name_input.val(path[path.length-1]);
    name_input.on('change', updateProperty.bind(path));


    var title_label = node.find('.schema-editor-generic-property-title-label');
    var title_input = node.find('.schema-editor-generic-property-title-input');
    title_input.attr('id', 'schema-editor-object__' + path.join('__') + '-title-input');
    title_label.attr('for', title_input.attr('id'));
    if ('title' in schema) {
      if (typeof schema['title'] === 'string') {
        title_input.val(schema['title']);
      } else {
        title_input.val(schema['title']['en']);
      }
    } else {
      title_input.val("");
    }
    title_input.on('change', updateProperty.bind(path));


    var type_label = node.find('.schema-editor-generic-property-type-label');
    var type_input = node.find('.schema-editor-generic-property-type-input');
    type_input.attr('id', 'schema-editor-object__' + path.join('__') + '-type-input');
    type_label.attr('for', type_input.attr('id'));
    type_input.val(type);
    type_input.selectpicker();

    type_input.on('change', function() {
      var type = $(this).val();
      var node = $(this).closest('.schema-editor-generic-property');
      node.find('.schema-editor-property-settings').css('display', 'none');
      $(node.find('.schema-editor-property-settings')[0]).css('display', 'flex');
      node.find('.schema-editor-' + type + '-property-settings').css('display', 'flex');
    });
    type_input.on('change', updateProperty.bind(path));

    function setOptionalValueInPropertySchema(path, type, name, property_schema) {
      var has_value = $('#schema-editor-object__' + path.join('__') + '-' + type + '-' + name + '-checkbox').prop('checked');
      var value = $('#schema-editor-object__' + path.join('__') + '-' + type + '-' + name + '-input').val();

      if (has_value) {
        property_schema[name] = value;
      }
    }

    function setMinAndMaxLengthInPropertySchema(path, type, property_schema, has_error) {
      var has_minlength = $('#schema-editor-object__' + path.join('__') + '-' + type + '-minlength-checkbox').prop('checked');
      var minlength_input = $('#schema-editor-object__' + path.join('__') + '-' + type + '-minlength-input');
      var minlength = minlength_input.val();
      var minlength_group = minlength_input.parent();
      var minlength_help = minlength_group.find('.help-block');

      if (has_minlength) {
        if (isNaN(minlength)) {
          minlength_help.text(window.schema_editor_translations['enter_number']);
          minlength_group.addClass("has-error");
          has_error = true;
        } else {
          minlength = Number.parseInt(minlength);
          if (minlength >= 0) {
            property_schema['minLength'] = minlength;
            minlength_help.text("");
            minlength_group.removeClass("has-error");
          } else {
            minlength_help.text(window.schema_editor_translations['enter_nonnegative_number']);
            minlength_group.addClass("has-error");
            has_error = true;
          }
        }
      } else {
        delete property_schema["minLength"];
        minlength_help.text("");
        minlength_group.removeClass("has-error");
      }

      var has_maxlength = $('#schema-editor-object__' + path.join('__') + '-' + type + '-maxlength-checkbox').prop('checked');
      var maxlength_input = $('#schema-editor-object__' + path.join('__') + '-' + type + '-maxlength-input');
      var maxlength = maxlength_input.val();
      var maxlength_group = maxlength_input.parent();
      var maxlength_help = maxlength_group.find('.help-block');

      if (has_maxlength) {
        if (isNaN(maxlength)) {
          maxlength_help.text(window.schema_editor_translations['enter_number']);
          maxlength_group.addClass("has-error");
          has_error = true;
        } else {
          maxlength = Number.parseInt(maxlength);
          if (maxlength >= 0) {
            property_schema['maxLength'] = maxlength;
            maxlength_help.text("");
            maxlength_group.removeClass("has-error");
          } else {
            maxlength_help.text(window.schema_editor_translations['enter_nonnegative_number']);
            maxlength_group.addClass("has-error");
            has_error = true;
          }
        }
      } else {
        delete property_schema["maxLength"];
        maxlength_help.text("");
        maxlength_group.removeClass("has-error");
      }
      if ('minLength' in property_schema && 'maxLength' in property_schema && property_schema['minLength'] > property_schema['maxLength']) {
        minlength_help.text(window.schema_editor_translations['enter_at_most_max_length']);
        minlength_group.addClass("has-error");
        maxlength_help.text(window.schema_editor_translations['enter_at_least_min_length']);
        maxlength_group.addClass("has-error");
        has_error = true;
      }
      return has_error;
    }

    function updateGenericProperty(path, real_path) {
      var has_error = false;
      var schema = JSON.parse(input_schema.text());
      var name_input = $('#schema-editor-object__' + path.join('__') + '-name-input');
      var name = name_input.val();
      var name_group = name_input.parent();
      var name_help = name_group.find('.help-block');
      if (name !== real_path[real_path.length - 1] && name in schema['properties']) {
        name = real_path[real_path.length - 1];
        name_help.text(window.schema_editor_translations['name_must_be_unique']);
        name_group.addClass("has-error");
        has_error = true;
      } else if (name === "hazards" || name === "tags") {
        name = real_path[real_path.length - 1];
        name_help.text(window.schema_editor_translations['name_must_not_be_hazards_or_tags']);
        name_group.addClass("has-error");
        has_error = true;
      } else if (!RegExp('^[A-Za-z].*$').test(name)) {
        name = real_path[real_path.length - 1];
        name_help.text(window.schema_editor_translations['name_must_begin_with_character']);
        name_group.addClass("has-error");
        has_error = true;
      } else if (!RegExp('^.*[A-Za-z0-9]$').test(name)) {
        name = real_path[real_path.length - 1];
        name_help.text(window.schema_editor_translations['name_must_end_with_character_or_number']);
        name_group.addClass("has-error");
        has_error = true;
      } else if (RegExp('^[A-Za-z0-9_]*$').test(name) && !RegExp('^[A-Za-z0-9]*__[A-Za-z0-9_]*$').test(name)) {
        name_help.text("");
        name_group.removeClass("has-error");
      } else {
        name = real_path[real_path.length - 1];
        name_help.text(window.schema_editor_translations['name_must_contain_valid_chars']);
        name_group.addClass("has-error");
        has_error = true;
      }
      var title_input = $('#schema-editor-object__' + path.join('__') + '-title-input');
      var title_group = title_input.parent();
      var title_help = title_group.find('.help-block');
      var title = title_input.val();
      if (title === "") {
        title_help.text(window.schema_editor_translations['title_must_not_be_empty']);
        title_group.addClass("has-error");
        has_error = true;
      } else if (RegExp('^\\s*$').test(title)) {
        title_help.text(window.schema_editor_translations['title_must_not_be_whitespace']);
        title_group.addClass("has-error");
        has_error = true;
      } else {
        title_help.text("");
        title_group.removeClass("has-error");
      }
      var required = $('#schema-editor-object__' + path.join('__') + '-required-input').prop('checked');
      var has_note = $('#schema-editor-object__' + path.join('__') + '-note-checkbox').prop('checked');
      var note = $('#schema-editor-object__' + path.join('__') + '-note-input').val();
      if (name !== real_path[real_path.length-1]) {
        delete schema['properties'][real_path[real_path.length-1]];
        if ('required' in schema) {
          for (var i = 0; i < schema['required'].length; i++) {
            if (schema['required'][i] === real_path[real_path.length - 1]) {
              schema['required'].splice(i, 1);
            }
          }
        }
        if ('propertyOrder' in schema) {
          var found_in_order = false;
          for (var i = 0; i < schema['propertyOrder'].length; i++) {
            if (schema['propertyOrder'][i] === real_path[real_path.length - 1]) {
              schema['propertyOrder'][i] = name;
              found_in_order = true;
              break;
            }
          }
          if (!found_in_order) {
            schema['propertyOrder'].push(name);
          }
          if (schema['propertyOrder'].includes('tags')) {
            schema['propertyOrder'].splice(schema['propertyOrder'].indexOf('tags'), 1);
            schema['propertyOrder'].push('tags')
          }
          if (schema['propertyOrder'].includes('hazards')) {
            schema['propertyOrder'].splice(schema['propertyOrder'].indexOf('hazards'), 1);
            schema['propertyOrder'].push('hazards')
          }
        }
        real_path[real_path.length-1] = name;
        window.schema_editor_path_mapping[path.join('__')] = real_path;
      }
      property_schema = {
        "title": title
      };
      if (has_note) {
        property_schema["note"] = note;
      }
      if (required) {
        if (!('required' in schema)) {
          schema['required'] = [];
        }
        if (!schema['required'].includes(real_path[real_path.length-1])) {
          schema['required'].push(real_path[real_path.length-1]);
        }
      } else if ('required' in schema){
        for(var i = 0; i < schema['required'].length; i++){
           if ( schema['required'][i] === real_path[real_path.length-1]) {
             schema['required'].splice(i, 1);
           }
        }
      }
      schema['properties'][real_path[real_path.length-1]] = property_schema;

      input_schema.text(JSON.stringify(schema, null, 4));

      window.schema_editor_errors[path.join('__') + '__generic'] = true;
      if (!has_error) {
        delete window.schema_editor_errors[path.join('__') + '__generic'];
      }
      $('button[name="action_submit"]').prop('disabled', (JSON.stringify(window.schema_editor_errors) !== '{}'));
    }

    function updateSpecificProperty(path, real_path, schema, property_schema, has_error) {
      schema['properties'][real_path[real_path.length-1]] = property_schema;

      input_schema.text(JSON.stringify(schema, null, 4));

      window.schema_editor_errors[path.join('__') + '__specific'] = true;
      if (!has_error) {
        delete window.schema_editor_errors[path.join('__') + '__specific'];
      }
      $('button[name="action_submit"]').prop('disabled', (JSON.stringify(window.schema_editor_errors) !== '{}'));
    }

    function updateTextProperty(path, real_path) {
      updateGenericProperty(path, real_path);
      var has_error = false;
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "text";

      setOptionalValueInPropertySchema(path, 'text', 'default', property_schema);
      setOptionalValueInPropertySchema(path, 'text', 'placeholder', property_schema);
      setOptionalValueInPropertySchema(path, 'text', 'pattern', property_schema);
      has_error = setMinAndMaxLengthInPropertySchema(path, 'text', property_schema, has_error);

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updateChoiceProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "text";

      setOptionalValueInPropertySchema(path, 'choice', 'default', property_schema);

      var choices_input = $('#schema-editor-object__' + path.join('__') + '-choice-choices-input');
      var choices_group = choices_input.parent();
      var choices_help = choices_group.find('.help-block');
      var choices = choices_input.val();
      choices = choices.match(/[^\r\n]+/g);
      if (choices === null) {
        choices = [];
      }
      var non_empty_choices = [];
      for (var i = 0; i < choices.length; i++) {
        var choice = choices[i].trim();
        if (choice.length) {
          non_empty_choices.push(choice);
        }
      }
      choices = non_empty_choices;
      if (choices.length === 0) {
        choices_help.text(window.schema_editor_translations['choices_must_not_be_empty']);
        choices_group.addClass("has-error");
        has_error = true;
      } else {
        choices_help.text("");
        choices_group.removeClass("has-error");
      }
      property_schema['choices'] = choices;

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updateMultilineProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "text";
      property_schema["multiline"] = true;

      setOptionalValueInPropertySchema(path, 'multiline', 'default', property_schema);
      setOptionalValueInPropertySchema(path, 'multiline', 'placeholder', property_schema);
      has_error = setMinAndMaxLengthInPropertySchema(path, 'multiline', property_schema, has_error);

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updateMarkdownProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "text";
      property_schema["markdown"] = true;

      setOptionalValueInPropertySchema(path, 'markdown', 'default', property_schema);
      setOptionalValueInPropertySchema(path, 'markdown', 'placeholder', property_schema);
      has_error = setMinAndMaxLengthInPropertySchema(path, 'markdown', property_schema, has_error);

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updateBoolProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "bool";

      var has_default = $('#schema-editor-object__' + path.join('__') + '-bool-default-checkbox').prop('checked');
      var default_value = $('#schema-editor-object__' + path.join('__') + '-bool-default-input').prop('checked');

      if (has_default) {
        property_schema['default'] = default_value;
      }

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updatePlotlyChartProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "plotly_chart";

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updateSampleProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "sample";

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updateMeasurementProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "measurement";

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updateUserProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "user";

      var has_default = $('#schema-editor-object__' + path.join('__') + '-user-default-checkbox').prop('checked');
      if (has_default) {
        property_schema["default"] = "self";
      } else {
        delete property_schema.default;
      }

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updateObjectReferenceProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "object_reference";

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updateDatetimeProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "datetime";

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    function updateQuantityProperty(path, real_path) {
      var has_error = false;
      updateGenericProperty(path, real_path);
      var schema = JSON.parse(input_schema.text());
      var property_schema = schema['properties'][real_path[real_path.length-1]];
      property_schema["type"] = "quantity";

      var units_input = $('#schema-editor-object__' + path.join('__') + '-quantity-units-input');
      var units = units_input.val();
      var units_group = units_input.parent();
      var units_help = units_group.find('.help-block');
      // TODO: validate units
      if (units.length > 0) {
        property_schema['units'] = units;
        units_help.text("");
        units_group.removeClass("has-error");
      } else {
        units_help.text(window.schema_editor_translations['enter_units']);
        units_group.addClass("has-error");
        has_error = true;
      }

      var has_default = $('#schema-editor-object__' + path.join('__') + '-quantity-default-checkbox').prop('checked');
      var default_input = $('#schema-editor-object__' + path.join('__') + '-quantity-default-input');
      var default_value = default_input.val();
      var default_group = default_input.parent();
      var default_help = default_group.find('.help-block');

      if (has_default) {
        if (isNaN(default_value) || default_value === null || default_value === "") {
          default_help.text(window.schema_editor_translations['enter_default_magnitude']);
          default_group.addClass("has-error");
          has_error = true;
        } else {
          default_value = Number.parseFloat(default_value);
          property_schema['default'] = default_value;
          default_help.text("");
          default_group.removeClass("has-error");
        }
      } else {
        default_help.text("");
        default_group.removeClass("has-error");
      }

      var has_placeholder = $('#schema-editor-object__' + path.join('__') + '-quantity-placeholder-checkbox').prop('checked');
      var placeholder_value = $('#schema-editor-object__' + path.join('__') + '-quantity-placeholder-input').val();

      if (has_placeholder) {
        property_schema['placeholder'] = placeholder_value;
      }

      updateSpecificProperty(path, real_path, schema, property_schema, has_error);
    }

    var required_label = node.find('.schema-editor-generic-property-required-label');
    var required_input = node.find('.schema-editor-generic-property-required-input');
    required_input.attr('id', 'schema-editor-object__' + path.join('__') + '-required-input');
    required_label.attr('for', required_input.attr('id'));
    required_input.prop('checked', is_required);
    required_input.bootstrapToggle();
    required_input.on('change', updateProperty.bind(path));

    function setupValueFromSchema(path, type, name, schema, is_type) {
      var value_label = node.find('.schema-editor-' + type + '-property-' + name.toLowerCase() + '-label');
      var value_input = node.find('.schema-editor-' + type + '-property-' + name.toLowerCase() + '-input');
      var value_checkbox = node.find('.schema-editor-' + type + '-property-' + name.toLowerCase() + '-checkbox');
      value_checkbox.attr('id', 'schema-editor-object__' + path.join('__') + '-' + type + '-' + name.toLowerCase() + '-checkbox');
      value_input.attr('id', 'schema-editor-object__' + path.join('__') + '-' + type + '-' + name.toLowerCase() + '-input');
      value_label.attr('for', value_input.attr('id'));
      if (is_type && name in schema) {
        if (typeof schema[name] === 'object') {
          // translations for text properties not supported in graphical editor
          window.schema_editor_missing_type_support = true;
          if ('en' in schema[name]) {
            value_input.val(schema[name]['en']);
            value_checkbox.prop('checked', true);
            value_input.prop('disabled', false);
          } else {
            value_input.val('');
            value_checkbox.prop('checked', false);
            value_input.prop('disabled', true);
          }
        } else {
          value_input.val(schema[name]);
          value_checkbox.prop('checked', true);
          value_input.prop('disabled', false);
        }
      } else {
        value_input.val("");
        value_checkbox.prop('checked', false);
        value_input.prop('disabled', true);
      }
      value_checkbox.on('change', function() {
        var value_input = $(this).parent().parent().find('.schema-editor-' + type + '-property-' + name.toLowerCase() + '-input');
        if ($(this).prop('checked')) {
          value_input.prop('disabled', false);
        } else {
          value_input.prop('disabled', true);
        }
      });
      value_checkbox.on('change', updateProperty.bind(path));
      value_input.on('change', updateProperty.bind(path));
    }

    setupValueFromSchema(path, 'generic', 'note', schema, type === 'text');
    setupValueFromSchema(path, 'text', 'default', schema, type === 'text');
    setupValueFromSchema(path, 'text', 'placeholder', schema, type === 'text');
    setupValueFromSchema(path, 'text', 'pattern', schema, type === 'text');
    setupValueFromSchema(path, 'text', 'minLength', schema, type === 'text');
    setupValueFromSchema(path, 'text', 'maxLength', schema, type === 'text');

    setupValueFromSchema(path, 'choice', 'default', schema, type === 'choice');

    var choices_label = node.find('.schema-editor-choice-property-choices-label');
    var choices_input = node.find('.schema-editor-choice-property-choices-input');
    choices_input.attr('id', 'schema-editor-object__' + path.join('__') + '-choice-choices-input');
    choices_label.attr('for', choices_input.attr('id'));
    if (type === 'choice' && 'choices' in schema) {
      var choices_text = "";
      for (var i in schema['choices']) {
        if (typeof schema['choices'][i] === 'object') {
          // translations for text properties not supported in graphical editor
          window.schema_editor_missing_type_support = true;
          if ('en' in schema['choices'][i]) {
            choices_text += schema['choices'][i]['en'] + "\n";
          }
        } else {
          choices_text += schema['choices'][i] + "\n";
        }
      }
      choices_input.val(choices_text);
    } else {
      choices_input.val("");
    }
    choices_input.on('change', updateProperty.bind(path));

    setupValueFromSchema(path, 'multiline', 'default', schema, type === 'multiline');
    setupValueFromSchema(path, 'multiline', 'placeholder', schema, type === 'multiline');
    setupValueFromSchema(path, 'multiline', 'minLength', schema, type === 'multiline');
    setupValueFromSchema(path, 'multiline', 'maxLength', schema, type === 'multiline');

    setupValueFromSchema(path, 'markdown', 'default', schema, type === 'markdown');
    setupValueFromSchema(path, 'markdown', 'placeholder', schema, type === 'markdown');
    setupValueFromSchema(path, 'markdown', 'minLength', schema, type === 'markdown');
    setupValueFromSchema(path, 'markdown', 'maxLength', schema, type === 'markdown');

    var default_label = node.find('.schema-editor-bool-property-default-label');
    var default_input = node.find('.schema-editor-bool-property-default-input');
    var default_checkbox = node.find('.schema-editor-bool-property-default-checkbox');
    default_checkbox.attr('id', 'schema-editor-object__' + path.join('__') + '-bool-default-checkbox');
    default_input.attr('id', 'schema-editor-object__' + path.join('__') + '-bool-default-input');
    default_label.attr('for', default_input.attr('id'));
    default_input.bootstrapToggle();
    if (type === 'bool' && 'default' in schema) {
      default_input.prop('checked', schema['default']);
      if (schema['default']) {
        default_input.bootstrapToggle('on');
      } else {
        default_input.bootstrapToggle('off');
      }
      default_checkbox.prop('checked', true);
      default_input.prop('disabled', false);
      default_input.closest('.toggle').removeClass('disabled');
    } else {
      default_input.prop('checked', false);
      default_checkbox.prop('checked', false);
      default_input.prop('disabled', true);
      default_input.closest('.toggle').addClass('disabled');
    }
    default_checkbox.on('change', function() {
      var default_input = $(this).parent().parent().find('.schema-editor-bool-property-default-input');
      if ($(this).prop('checked')) {
        default_input.prop('disabled', false);
        default_input.closest('.toggle').removeClass('disabled');
      } else {
        default_input.prop('disabled', true);
        default_input.closest('.toggle').addClass('disabled');
      }
    });
    default_checkbox.on('change', updateProperty.bind(path));
    default_input.on('change', updateProperty.bind(path));

    setupValueFromSchema(path, 'quantity', 'default', schema, type === 'quantity');
    setupValueFromSchema(path, 'quantity', 'placeholder', schema, type === 'quantity');

    var units_label = node.find('.schema-editor-quantity-property-units-label');
    var units_input = node.find('.schema-editor-quantity-property-units-input');
    units_input.attr('id', 'schema-editor-object__' + path.join('__') + '-quantity-units-input');
    units_label.attr('for', units_input.attr('id'));
    if (type === 'quantity' && 'units' in schema) {
      units_input.val(schema['units']);
    } else {
      units_input.val("");
    }
    units_input.on('change', updateProperty.bind(path));
    if (window.schema_editor_error_message !== null && window.schema_editor_error_message === ("invalid units (at " + path[0] + ")")) {
      var units_group = units_input.parent();
      units_group.addClass("has-error");
      units_group.find('.help-block').text(window.schema_editor_translations['enter_valid_units']);
      window.schema_editor_errors[path.join('__') + '__specific'] = true;
    }

    var default_checkbox = node.find('.schema-editor-user-property-default-checkbox');
    default_checkbox.attr('id', 'schema-editor-object__' + path.join('__') + '-user-default-checkbox');
    if (type === 'user' && 'default' in schema) {
      default_checkbox.prop('checked', true);
    } else {
      default_checkbox.prop('checked', false);
    }
    default_checkbox.on('change', updateProperty.bind(path));

    return node;
  }

  var root_object_node = buildRootObjectNode(schema);
  schema_editor[0].appendChild(root_object_node[0]);
  input_schema.text(JSON.stringify(schema, null, 4));
  globallyValidateSchema();
  if (window.schema_editor_missing_type_support) {
    $('#schemaEditorWarningModal').modal('show');
  }
});
