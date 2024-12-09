'use strict';
/* eslint-env jquery */
/* globals CodeMirror */

/**
 * Enables the graphical schema editor and hides the JSON editor.
 */
function enableSchemaEditor () {
  window.schema_editor_enabled = true;
  $('[data-toggle="tooltip"]:not(.disabled)').tooltip();
  const schemaEditor = $('#schema-editor');
  const schemaEditorTemplates = $('#schema-editor-templates');
  const inputSchema = $('#input-schema');
  inputSchema.hide();
  window.code_mirror_editor.save();
  $('#input-schema ~ .CodeMirror').hide();
  schemaEditor.show();

  const schemaText = inputSchema.val();
  let schema = {};
  try {
    schema = JSON.parse(schemaText);
  } catch (error) {
    // Since invalid JSON schemas can only be created and repaired in the texteditor, use it instead
    const toggle = $('#toggle-schema-editor');
    toggle.bootstrapToggle('off');
    const wrapper = toggle.parent().parent();
    wrapper.tooltip('show');
    setTimeout(function () {
      wrapper.tooltip('hide');
    }, 2000);
    return disableSchemaEditor();
  }
  delete schema.displayProperties;
  if ('propertyOrder' in schema && schema.propertyOrder.includes('tags')) {
    schema.propertyOrder.splice(schema.propertyOrder.indexOf('tags'), 1);
    schema.propertyOrder.push('tags');
  }
  if ('propertyOrder' in schema && schema.propertyOrder.includes('hazards')) {
    schema.propertyOrder.splice(schema.propertyOrder.indexOf('hazards'), 1);
    schema.propertyOrder.push('hazards');
  }
  window.schema_editor_path_mapping = {};
  window.schema_editor_errors = {};
  window.schema_editor_missing_type_support = false;
  window.schema_editor_initial_updates = [];

  inputSchema.val(JSON.stringify(schema, null, 2));
  window.code_mirror_editor.setValue(inputSchema.val());

  schemaEditor.html('');

  $('#form-action').on('submit', function () {
    return (JSON.stringify(window.schema_editor_errors) === '{}');
  });

  function getElementForProperty (path, elementSuffix) {
    const elementID = 'schema-editor-object__' + path.join('__') + '-' + elementSuffix;
    // find object via document.getElementById instead of $() to avoid selector string mix-ups with invalid name
    const element = document.getElementById(elementID);
    // then create JQuery element from DOM element
    return $(element);
  }

  function buildRootObjectNode (schema) {
    let node = schemaEditorTemplates.find('.schema-editor-root-object')[0].cloneNode(true);
    node = $(node);
    node.find('[data-toggle="tooltip"]:not(.disabled)').tooltip();

    const advancedRootObjectFeatures = [
      'recipes', 'batch', 'batch_name_format', 'displayProperties',
      'notebookTemplates', 'show_more', 'workflow_view', 'workflow_views', 'workflow_show_more'
    ];

    for (const name of advancedRootObjectFeatures) {
      if (name in schema) {
        window.schema_editor_missing_type_support = true;
        break;
      }
    }

    const titleInputs = node.find('.schema-editor-root-object-title-input');
    titleInputs.val('');
    titleInputs.each(function (_, titleInput) {
      const langCode = $(titleInput).data('sampledbLangCode');
      const id = 'schema-editor-root-object-title-input-' + langCode;
      $(titleInput).attr('id', id);
      $(titleInput).parent().find('.schema-editor-root-object-title-label').attr('for', id);
    });
    if ('title' in schema) {
      if (typeof schema.title === 'string') {
        schema.title = { en: schema.title };
      }
      for (const langCode in schema.title) {
        const titleInput = titleInputs.filter('[data-sampledb-lang-code="' + langCode + '"]');
        if (titleInput.length > 0) {
          titleInput.val(schema.title[langCode]);
        } else {
          window.schema_editor_missing_type_support = true;
        }
      }
    }
    titleInputs.on('change', function () {
      const titleInput = $(this);
      const langCode = titleInput.data('sampledbLangCode');
      const titleGroup = titleInput.parent();
      const titleHelp = titleGroup.find('.help-block');
      const title = titleInput.val();
      let hasError = false;
      if (title === '' && langCode === 'en') {
        titleHelp.text(window.getTemplateValue('translations.enter_title'));
        titleGroup.addClass('has-error');
        hasError = true;
      } else if (/^\\s+$/.test(title)) {
        titleHelp.text(window.getTemplateValue('translations.title_must_not_be_whitespace'));
        titleGroup.addClass('has-error');
        hasError = true;
      } else if (title !== '') {
        titleHelp.text('');
        titleGroup.removeClass('has-error');
        const schema = JSON.parse(inputSchema.val());
        if (typeof schema.title === 'string') {
          schema.title = { en: schema.title };
        }
        schema.title[langCode] = title;
        inputSchema.val(JSON.stringify(schema, null, 2));
        window.code_mirror_editor.setValue(inputSchema.val());
      }
      window.schema_editor_errors['root_title__' + langCode] = true;
      if (!hasError) {
        delete window.schema_editor_errors['root_title__' + langCode];
      }
      globallyValidateSchema();
    }).change();

    const hazardsLabel = node.find('.schema-editor-root-object-hazards-label');
    const hazardsInput = node.find('.schema-editor-root-object-hazards-input');
    hazardsInput.attr('id', 'schema-editor-root-object-hazards-input');
    hazardsLabel.attr('for', hazardsInput.attr('id'));
    if ('properties' in schema) {
      hazardsInput.prop('checked', 'hazards' in schema.properties);
    } else {
      hazardsInput.prop('checked', false);
    }
    hazardsInput.bootstrapToggle();
    hazardsInput.on('change', function () {
      const schema = JSON.parse(inputSchema.val());
      if ('properties' in schema && 'hazards' in schema.properties) {
        delete schema.properties.hazards;
      }
      if ('propertyOrder' in schema) {
        while (schema.propertyOrder.includes('hazards')) {
          const index = schema.propertyOrder.indexOf('hazards');
          schema.propertyOrder.splice(index, 1);
        }
      }
      if ('required' in schema) {
        while (schema.required.includes('hazards')) {
          const index = schema.required.indexOf('hazards');
          schema.required.splice(index, 1);
        }
      }
      if ($(this).prop('checked')) {
        if (!('properties' in schema)) {
          schema.properties = {};
        }
        schema.properties.hazards = {
          type: 'hazards',
          title: window.getTemplateValue('hazards_translations')
        };
        if (!('required' in schema)) {
          schema.required = [];
        }
        schema.required.push('hazards');
        if (!('propertyOrder' in schema)) {
          schema.propertyOrder = [];
        }
        schema.propertyOrder.push('hazards');
      }
      inputSchema.val(JSON.stringify(schema, null, 2));
      window.code_mirror_editor.setValue(inputSchema.val());
    });

    const tagsLabel = node.find('.schema-editor-root-object-tags-label');
    const tagsInput = node.find('.schema-editor-root-object-tags-input');
    tagsInput.attr('id', 'schema-editor-root-object-tags-input');
    tagsLabel.attr('for', tagsInput.attr('id'));
    if ('properties' in schema) {
      tagsInput.prop('checked', 'tags' in schema.properties);
    } else {
      tagsInput.prop('checked', false);
    }
    tagsInput.bootstrapToggle();
    tagsInput.on('change', function () {
      const schema = JSON.parse(inputSchema.val());
      if ('properties' in schema && 'tags' in schema.properties) {
        delete schema.properties.tags;
      }
      if ('propertyOrder' in schema) {
        while (schema.propertyOrder.includes('tags')) {
          const index = schema.propertyOrder.indexOf('tags');
          schema.propertyOrder.splice(index, 1);
        }
      }
      if ('required' in schema) {
        while (schema.required.includes('tags')) {
          const index = schema.required.indexOf('tags');
          schema.required.splice(index, 1);
        }
      }
      if ($(this).prop('checked')) {
        if (!('properties' in schema)) {
          schema.properties = {};
        }
        schema.properties.tags = {
          type: 'tags',
          title: window.getTemplateValue('tags_translations')
        };
        if (!('required' in schema)) {
          schema.required = [];
        }
        schema.required.push('tags');
        if (!('propertyOrder' in schema)) {
          schema.propertyOrder = [];
        }
        schema.propertyOrder.push('tags');
        // make sure hazards are always the final property
        if (schema.propertyOrder.includes('hazards')) {
          while (schema.propertyOrder.includes('hazards')) {
            const index = schema.propertyOrder.indexOf('hazards');
            schema.propertyOrder.splice(index, 1);
          }
          schema.propertyOrder.push('hazards');
        }
      }
      inputSchema.val(JSON.stringify(schema, null, 2));
      window.code_mirror_editor.setValue(inputSchema.val());
    });

    const propertiesNode = node.find('.schema-editor-root-object-properties');
    const propertiesInOrder = [];
    if ('propertyOrder' in schema) {
      for (const name of schema.propertyOrder) {
        if (!propertiesInOrder.includes(name)) {
          propertiesInOrder.push(name);
        }
      }
    } else {
      schema.propertyOrder = [];
    }
    for (const name in schema.properties) {
      if (!propertiesInOrder.includes(name)) {
        propertiesInOrder.push(name);
        schema.propertyOrder.push(name);
      }
    }
    for (const name of propertiesInOrder) {
      if (Object.prototype.hasOwnProperty.call(schema.properties, name)) {
        const path = [name];
        const isRequired = ('required' in schema && schema.required.includes(name));
        const propertyNode = buildPropertyNode(schema.properties[name], path, isRequired);

        if (propertyNode !== null) {
          if ('template' in schema.properties[name]) {
            const currentTemplate = schema.properties[name].template;
            const templateInput = propertyNode.find('select.schema-editor-generic-property-template-id-input');
            templateInput.selectpicker('val', currentTemplate);
            propertiesNode[0].appendChild(propertyNode[0]);
          } else {
            propertiesNode[0].appendChild(propertyNode[0]);
          }
        }
      }
    }

    const createPropertyButton = node.find('.schema-editor-create-property-button');
    createPropertyButton.on('click', function () {
      const schema = JSON.parse(inputSchema.val());
      let numNewProperties = 1;
      let name = 'new_property_' + numNewProperties;
      while (name in schema.properties || [name] in window.schema_editor_path_mapping) {
        numNewProperties += 1;
        name = 'new_property_' + numNewProperties;
      }
      schema.properties[name] = {
        title: '',
        type: 'text'
      };
      schema.propertyOrder.push(name);
      if (schema.propertyOrder.includes('tags')) {
        schema.propertyOrder.splice(schema.propertyOrder.indexOf('tags'), 1);
        schema.propertyOrder.push('tags');
      }
      if (schema.propertyOrder.includes('hazards')) {
        schema.propertyOrder.splice(schema.propertyOrder.indexOf('hazards'), 1);
        schema.propertyOrder.push('hazards');
      }
      const path = [name];
      const isRequired = ('required' in schema && schema.required.includes(name));
      const propertyNode = buildPropertyNode(schema.properties[name], path, isRequired);
      if (propertyNode !== null) {
        propertiesNode[0].appendChild(propertyNode[0]);
      }
      inputSchema.val(JSON.stringify(schema, null, 2));
      window.code_mirror_editor.setValue(inputSchema.val());
      const nameInput = propertyNode.find('.schema-editor-generic-property-name-input');
      nameInput.val('');
      nameInput.trigger('change');
    });

    return node;
  }

  function globallyValidateSchema () {
    const schema = JSON.parse(inputSchema.val());
    const helpBlock = $('#schema-editor .schema-editor-global-help');
    const helpParent = helpBlock.parent();
    helpBlock.text('');
    helpParent.removeClass('has-error');
    let hasError = false;
    if (!('properties' in schema)) {
      helpBlock.text(window.getTemplateValue('translations.objects_need_one_property'));
      helpParent.addClass('has-error');
      hasError = true;
    } else if (!('name' in schema.properties)) {
      helpBlock.html(window.getTemplateValue('translations.object_must_have_name_text'));
      helpParent.addClass('has-error');
      hasError = true;
    } else if (!('type' in schema.properties.name) || schema.properties.name.type !== 'text' || ('multiline' in schema.properties.name && schema.properties.name.multiline) || ('markdown' in schema.properties.name && schema.properties.name.markdown) || 'choices' in schema.properties.name) {
      helpBlock.html(window.getTemplateValue('translations.object_name_must_be_text'));
      helpParent.addClass('has-error');
      hasError = true;
    } else if (!('required' in schema) || !schema.required.includes('name')) {
      helpBlock.html(window.getTemplateValue('translations.object_name_must_be_required'));
      helpParent.addClass('has-error');
      hasError = true;
    }

    const propertyElements = $('#schema-editor .schema-editor-property');
    for (let i = 0; i < propertyElements.length; i += 1) {
      const movePropertyUpButton = $(propertyElements[i]).find('.schema-editor-move-property-up-button');
      const movePropertyDownButton = $(propertyElements[i]).find('.schema-editor-move-property-down-button');
      if (i === 0) {
        movePropertyUpButton.prop('disabled', true);
        movePropertyUpButton.addClass('disabled');
      } else {
        movePropertyUpButton.prop('disabled', false);
        movePropertyUpButton.removeClass('disabled');
      }
      if (i === propertyElements.length - 1) {
        movePropertyDownButton.prop('disabled', true);
        movePropertyDownButton.addClass('disabled');
      } else {
        movePropertyDownButton.prop('disabled', false);
        movePropertyDownButton.removeClass('disabled');
      }
    }

    window.schema_editor_errors.global = true;
    if (!hasError) {
      delete window.schema_editor_errors.global;
    }
    $('button[name="action_submit"]').prop('disabled', (JSON.stringify(window.schema_editor_errors) !== '{}'));
  }

  function buildPropertyNode (schema, path, isRequired) {
    let type;
    if (schema.type === 'text') {
      if ('choices' in schema) {
        type = 'choice';
      } else if ('markdown' in schema && schema.markdown) {
        type = 'markdown';
      } else if ('multiline' in schema && schema.multiline) {
        type = 'multiline';
      } else {
        type = 'text';
      }
    } else if (schema.type === 'sample') {
      type = 'sample';
    } else if (schema.type === 'measurement') {
      type = 'measurement';
    } else if (schema.type === 'object_reference') {
      type = 'object_reference';
    } else if (schema.type === 'bool') {
      type = 'bool';
    } else if (schema.type === 'quantity') {
      type = 'quantity';
    } else if (schema.type === 'datetime') {
      type = 'datetime';
    } else if (schema.type === 'tags') {
      return null;
    } else if (schema.type === 'hazards') {
      return null;
    } else if (schema.type === 'user') {
      type = 'user';
    } else if (schema.type === 'plotly_chart') {
      type = 'plotly_chart';
    } else if (schema.type === 'object' && 'template' in schema) {
      type = 'template';
    } else if (schema.type === 'timeseries') {
      type = 'timeseries';
    } else if (schema.type === 'file') {
      type = 'file';
    } else {
      window.schema_editor_missing_type_support = true;
      return null;
    }

    let node = schemaEditorTemplates.find('.schema-editor-generic-property')[0].cloneNode(true);
    node = $(node);
    node.find('[data-toggle="tooltip"]:not(.disabled)').tooltip();
    node.find('.schema-editor-' + type + '-property-setting').css('display', 'block');

    function updateProperty (path) {
      const realPath = window.schema_editor_path_mapping[path.join('__')].slice();
      const type = getElementForProperty(path, 'type-input').selectpicker('val');
      if (type === 'text') {
        updateTextProperty(path, realPath);
      } else if (type === 'choice') {
        updateChoiceProperty(path, realPath);
      } else if (type === 'multiline') {
        updateMultilineProperty(path, realPath);
      } else if (type === 'markdown') {
        updateMarkdownProperty(path, realPath);
      } else if (type === 'bool') {
        updateBoolProperty(path, realPath);
      } else if (type === 'sample') {
        updateSampleProperty(path, realPath);
      } else if (type === 'user') {
        updateUserProperty(path, realPath);
      } else if (type === 'measurement') {
        updateMeasurementProperty(path, realPath);
      } else if (type === 'object_reference') {
        updateObjectReferenceProperty(path, realPath);
      } else if (type === 'quantity') {
        updateQuantityProperty(path, realPath);
      } else if (type === 'datetime') {
        updateDatetimeProperty(path, realPath);
      } else if (type === 'plotly_chart') {
        updatePlotlyChartProperty(path, realPath);
      } else if (type === 'template') {
        updateTemplateObjectProperty(path, realPath);
      } else if (type === 'timeseries') {
        updateTimeseriesProperty(path, realPath);
      } else if (type === 'file') {
        updateFileProperty(path, realPath);
      }
      globallyValidateSchema();
    }

    const deletePropertyButton = node.find('.schema-editor-delete-property-button');
    deletePropertyButton.on('click', function () {
      const path = this;
      const realPath = window.schema_editor_path_mapping[path.join('__')].slice();
      const schema = JSON.parse(inputSchema.val());
      const name = realPath[realPath.length - 1];
      if ('properties' in schema && name in schema.properties) {
        delete schema.properties[name];
      }
      if ('propertyOrder' in schema) {
        while (schema.propertyOrder.includes(name)) {
          const index = schema.propertyOrder.indexOf(name);
          schema.propertyOrder.splice(index, 1);
        }
      }
      if ('required' in schema) {
        while (schema.required.includes(name)) {
          const index = schema.required.indexOf(name);
          schema.required.splice(index, 1);
        }
      }
      inputSchema.val(JSON.stringify(schema, null, 2));
      window.code_mirror_editor.setValue(inputSchema.val());

      const nameInput = getElementForProperty(path, 'name-input');
      nameInput.closest('.schema-editor-property').remove();

      delete window.schema_editor_errors[path.join('__') + '__generic'];
      delete window.schema_editor_errors[path.join('__') + '__specific'];
      $('button[name="action_submit"]').prop('disabled', (JSON.stringify(window.schema_editor_errors) !== '{}'));
      globallyValidateSchema();
    }.bind(path));
    const movePropertyUpButton = node.find('.schema-editor-move-property-up-button');
    movePropertyUpButton.on('click', function () {
      const path = this;
      const realPath = window.schema_editor_path_mapping[path.join('__')].slice();
      const schema = JSON.parse(inputSchema.val());
      const name = realPath[realPath.length - 1];
      if ('propertyOrder' in schema && schema.propertyOrder.includes(name)) {
        const index = schema.propertyOrder.indexOf(name);
        if (index > 0) {
          schema.propertyOrder.splice(index, 1);
          schema.propertyOrder.splice(index - 1, 0, name);
        }
        inputSchema.val(JSON.stringify(schema, null, 2));
        window.code_mirror_editor.setValue(inputSchema.val());
        globallyValidateSchema();
        const nameInput = getElementForProperty(path, 'name-input');
        const element = nameInput.closest('.schema-editor-property');
        element.insertBefore(element.prev('.schema-editor-property'));
        element.find('[data-toggle="tooltip"]').tooltip('hide');
        globallyValidateSchema();
      }
    }.bind(path));
    const movePropertyDownButton = node.find('.schema-editor-move-property-down-button');
    movePropertyDownButton.on('click', function () {
      const path = this;
      const realPath = window.schema_editor_path_mapping[path.join('__')].slice();
      const schema = JSON.parse(inputSchema.val());
      const name = realPath[realPath.length - 1];
      if ('propertyOrder' in schema && schema.propertyOrder.includes(name)) {
        const index = schema.propertyOrder.indexOf(name);
        let numProperties = schema.propertyOrder.length;
        if (schema.propertyOrder.includes('tags')) {
          numProperties -= 1;
        }
        if (schema.propertyOrder.includes('hazards')) {
          numProperties -= 1;
        }
        if (index < numProperties - 1) {
          schema.propertyOrder.splice(index, 1);
          schema.propertyOrder.splice(index + 1, 0, name);
        }
        inputSchema.val(JSON.stringify(schema, null, 2));
        window.code_mirror_editor.setValue(inputSchema.val());
        globallyValidateSchema();
        const nameInput = getElementForProperty(path, 'name-input');
        const element = nameInput.closest('.schema-editor-property');
        element.insertAfter(element.next('.schema-editor-property'));
        element.find('[data-toggle="tooltip"]').tooltip('hide');
        globallyValidateSchema();
      }
    }.bind(path));

    const nameLabel = node.find('.schema-editor-generic-property-name-label');
    const nameInput = node.find('.schema-editor-generic-property-name-input');
    window.schema_editor_path_mapping[path.join('__')] = path;
    nameInput.attr('id', 'schema-editor-object__' + path.join('__') + '-name-input');
    nameLabel.attr('for', nameInput.attr('id'));
    nameInput.val(path[path.length - 1]);
    nameInput.on('change', function () { updateProperty(path); });

    const titleInputs = node.find('.schema-editor-generic-property-title-input');
    titleInputs.val('');
    window.schema_editor_lang_codes = [];
    titleInputs.each(function (_, titleInput) {
      const langCode = $(titleInput).data('sampledbLangCode');
      window.schema_editor_lang_codes.push(langCode);
      const id = 'schema-editor-object__' + path.join('__') + '-title-input-' + langCode;
      $(titleInput).attr('id', id);
      $(titleInput).parent().find('.schema-editor-generic-property-title-label').attr('for', id);
    });
    if ('title' in schema) {
      if (typeof schema.title === 'string') {
        schema.title = { en: schema.title };
      }
      for (const langCode in schema.title) {
        const titleInput = titleInputs.filter('[data-sampledb-lang-code="' + langCode + '"]');
        if (titleInput.length > 0) {
          titleInput.val(schema.title[langCode]);
        } else {
          window.schema_editor_missing_type_support = true;
        }
      }
    }
    titleInputs.on('change', function () { updateProperty(path); });

    const typeLabel = node.find('.schema-editor-generic-property-type-label');
    const typeInput = node.find('.schema-editor-generic-property-type-input');
    typeInput.attr('id', 'schema-editor-object__' + path.join('__') + '-type-input');
    typeLabel.attr('for', typeInput.attr('id'));
    typeInput.selectpicker('val', type);

    typeInput.on('change', function () {
      const type = $(this).val();
      const node = $(this).closest('.schema-editor-generic-property');
      node.find('.schema-editor-property-setting').css('display', 'none');
      node.find('.help-block').html('');
      node.find('.has-error').removeClass('has-error');
      node.find('.schema-editor-' + type + '-property-setting').css('display', 'block');
    });
    typeInput.on('change', function () { updateProperty(path); });

    function setOptionalValueInPropertySchema (path, type, name, propertySchema) {
      const hasValue = getElementForProperty(path, type + '-' + name + '-checkbox').prop('checked');
      const value = getElementForProperty(path, type + '-' + name + '-input').val();

      if (hasValue) {
        propertySchema[name] = value;
      }
    }

    function setMinAndMaxLengthInPropertySchema (path, type, propertySchema, hasError) {
      const hasMinLength = getElementForProperty(path, type + '-minlength-checkbox').prop('checked');
      const minLengthInput = getElementForProperty(path, type + '-minlength-input');
      let minLength = minLengthInput.val();
      const minLengthGroup = minLengthInput.parent();
      const minLengthHelp = minLengthGroup.find('.help-block');

      if (hasMinLength) {
        if (isNaN(minLength)) {
          minLengthHelp.text(window.getTemplateValue('translations.enter_number'));
          minLengthGroup.addClass('has-error');
          hasError = true;
        } else {
          minLength = Number.parseInt(minLength);
          if (minLength >= 0) {
            propertySchema.minLength = minLength;
            minLengthHelp.text('');
            minLengthGroup.removeClass('has-error');
          } else {
            minLengthHelp.text(window.getTemplateValue('translations.enter_nonnegative_number'));
            minLengthGroup.addClass('has-error');
            hasError = true;
          }
        }
      } else {
        delete propertySchema.minLength;
        minLengthHelp.text('');
        minLengthGroup.removeClass('has-error');
      }

      const hasMaxLength = getElementForProperty(path, type + '-maxlength-checkbox').prop('checked');
      const maxLengthInput = getElementForProperty(path, type + '-maxlength-input');
      let maxLength = maxLengthInput.val();
      const maxLengthGroup = maxLengthInput.parent();
      const maxLengthHelp = maxLengthGroup.find('.help-block');

      if (hasMaxLength) {
        if (isNaN(maxLength)) {
          maxLengthHelp.text(window.getTemplateValue('translations.enter_number'));
          maxLengthGroup.addClass('has-error');
          hasError = true;
        } else {
          maxLength = Number.parseInt(maxLength);
          if (maxLength >= 0) {
            propertySchema.maxLength = maxLength;
            maxLengthHelp.text('');
            maxLengthGroup.removeClass('has-error');
          } else {
            maxLengthHelp.text(window.getTemplateValue('translations.enter_nonnegative_number'));
            maxLengthGroup.addClass('has-error');
            hasError = true;
          }
        }
      } else {
        delete propertySchema.maxLength;
        maxLengthHelp.text('');
        maxLengthGroup.removeClass('has-error');
      }
      if ('minLength' in propertySchema && 'maxLength' in propertySchema && propertySchema.minLength > propertySchema.maxLength) {
        minLengthHelp.text(window.getTemplateValue('translations.enter_at_most_max_length'));
        minLengthGroup.addClass('has-error');
        maxLengthHelp.text(window.getTemplateValue('translations.enter_at_least_min_length'));
        maxLengthGroup.addClass('has-error');
        hasError = true;
      }
      return hasError;
    }

    function updateGenericProperty (path, realPath) {
      let hasError = false;
      const schema = JSON.parse(inputSchema.val());
      const nameInput = getElementForProperty(path, 'name-input');
      let name = nameInput.val();
      const nameGroup = nameInput.parent();
      const nameHelp = nameGroup.find('.help-block');
      if (name !== realPath[realPath.length - 1] && name in schema.properties) {
        name = realPath[realPath.length - 1];
        nameHelp.text(window.getTemplateValue('translations.name_must_be_unique'));
        nameGroup.addClass('has-error');
        hasError = true;
      } else if (name === 'hazards' || name === 'tags') {
        name = realPath[realPath.length - 1];
        nameHelp.text(window.getTemplateValue('translations.name_must_not_be_hazards_or_tags'));
        nameGroup.addClass('has-error');
        hasError = true;
      } else if (!/^[A-Za-z].*$/.test(name)) {
        name = realPath[realPath.length - 1];
        nameHelp.text(window.getTemplateValue('translations.name_must_begin_with_character'));
        nameGroup.addClass('has-error');
        hasError = true;
      } else if (!/^.*[A-Za-z0-9]$/.test(name)) {
        name = realPath[realPath.length - 1];
        nameHelp.text(window.getTemplateValue('translations.name_must_end_with_character_or_number'));
        nameGroup.addClass('has-error');
        hasError = true;
      } else if (/^[A-Za-z0-9_]*$/.test(name) && !/^[A-Za-z0-9]*__[A-Za-z0-9_]*$/.test(name)) {
        nameHelp.text('');
        nameGroup.removeClass('has-error');
      } else {
        name = realPath[realPath.length - 1];
        nameHelp.text(window.getTemplateValue('translations.name_must_contain_valid_chars'));
        nameGroup.addClass('has-error');
        hasError = true;
      }

      const translatedTitle = {};
      for (const langCode of window.schema_editor_lang_codes) {
        const titleInput = getElementForProperty(path, 'title-input-' + langCode);
        const titleGroup = titleInput.parent();
        const titleHelp = titleGroup.find('.help-block');
        const title = titleInput.val();
        if (title === '' && langCode === 'en') {
          titleHelp.text(window.getTemplateValue('translations.title_must_not_be_empty'));
          titleGroup.addClass('has-error');
          hasError = true;
        } else if (/^\\s+$/.test(title)) {
          titleHelp.text(window.getTemplateValue('translations.title_must_not_be_whitespace'));
          titleGroup.addClass('has-error');
          hasError = true;
        } else {
          titleHelp.text('');
          titleGroup.removeClass('has-error');
        }
        if (langCode === 'en' || title !== '') {
          translatedTitle[langCode] = title;
        }
      }
      const required = getElementForProperty(path, 'required-input').prop('checked');
      const hasNote = getElementForProperty(path, 'generic-note-checkbox').prop('checked');
      const translatedNote = {};
      for (const langCode of window.schema_editor_lang_codes) {
        const noteInput = getElementForProperty(path, 'generic-note-input-' + langCode);
        const noteGroup = noteInput.parent();
        const noteHelp = noteGroup.find('.help-block');
        const note = noteInput.val();
        if (hasNote && note === '' && langCode === 'en') {
          noteHelp.text(window.getTemplateValue('translations.note_must_not_be_empty'));
          noteGroup.addClass('has-error');
          hasError = true;
        } else if (hasNote && /^\\s+$/.test(note)) {
          noteHelp.text(window.getTemplateValue('translations.note_must_not_be_whitespace'));
          noteGroup.addClass('has-error');
          hasError = true;
        } else {
          noteHelp.text('');
          noteGroup.removeClass('has-error');
        }
        if (note || langCode === 'en') {
          translatedNote[langCode] = note;
        }
      }
      const hasTooltip = getElementForProperty(path, 'generic-tooltip-checkbox').prop('checked');
      const translatedTooltip = {};
      for (const langCode of window.schema_editor_lang_codes) {
        const tooltipInput = getElementForProperty(path, 'generic-tooltip-input-' + langCode);
        const tooltipGroup = tooltipInput.parent();
        const tooltipHelp = tooltipGroup.find('.help-block');
        const tooltip = tooltipInput.val();
        if (hasTooltip && tooltip === '' && langCode === 'en') {
          tooltipHelp.text(window.getTemplateValue('translations.tooltip_must_not_be_empty'));
          tooltipGroup.addClass('has-error');
          hasError = true;
        } else if (hasTooltip && /^\\s+$/.test(tooltip)) {
          tooltipHelp.text(window.getTemplateValue('translations.tooltip_must_not_be_whitespace'));
          tooltipGroup.addClass('has-error');
          hasError = true;
        } else {
          tooltipHelp.text('');
          tooltipGroup.removeClass('has-error');
        }
        if (tooltip || langCode === 'en') {
          translatedTooltip[langCode] = tooltip;
        }
      }
      if (name !== realPath[realPath.length - 1]) {
        delete schema.properties[realPath[realPath.length - 1]];
        if ('required' in schema) {
          for (let i = 0; i < schema.required.length; i++) {
            if (schema.required[i] === realPath[realPath.length - 1]) {
              schema.required.splice(i, 1);
            }
          }
        }
        if ('propertyOrder' in schema) {
          let foundInOrder = false;
          for (let i = 0; i < schema.propertyOrder.length; i++) {
            if (schema.propertyOrder[i] === realPath[realPath.length - 1]) {
              schema.propertyOrder[i] = name;
              foundInOrder = true;
              break;
            }
          }
          if (!foundInOrder) {
            schema.propertyOrder.push(name);
          }
          if (schema.propertyOrder.includes('tags')) {
            schema.propertyOrder.splice(schema.propertyOrder.indexOf('tags'), 1);
            schema.propertyOrder.push('tags');
          }
          if (schema.propertyOrder.includes('hazards')) {
            schema.propertyOrder.splice(schema.propertyOrder.indexOf('hazards'), 1);
            schema.propertyOrder.push('hazards');
          }
        }
        realPath[realPath.length - 1] = name;
        window.schema_editor_path_mapping[path.join('__')] = realPath;
      }
      const propertySchema = {
        title: translatedTitle
      };
      if (hasNote) {
        propertySchema.note = translatedNote;
      }
      if (hasTooltip) {
        propertySchema.tooltip = translatedTooltip;
      }
      if (required) {
        if (!('required' in schema)) {
          schema.required = [];
        }
        if (!schema.required.includes(realPath[realPath.length - 1])) {
          schema.required.push(realPath[realPath.length - 1]);
        }
      } else if ('required' in schema) {
        for (let i = 0; i < schema.required.length; i++) {
          if (schema.required[i] === realPath[realPath.length - 1]) {
            schema.required.splice(i, 1);
          }
        }
      }
      schema.properties[realPath[realPath.length - 1]] = propertySchema;

      inputSchema.val(JSON.stringify(schema, null, 2));
      window.code_mirror_editor.setValue(inputSchema.val());

      window.schema_editor_errors[path.join('__') + '__generic'] = true;
      if (!hasError) {
        delete window.schema_editor_errors[path.join('__') + '__generic'];
      }
      $('button[name="action_submit"]').prop('disabled', (JSON.stringify(window.schema_editor_errors) !== '{}'));
    }

    function updateSpecificProperty (path, realPath, schema, propertySchema, hasError) {
      schema.properties[realPath[realPath.length - 1]] = propertySchema;

      inputSchema.val(JSON.stringify(schema, null, 2));
      window.code_mirror_editor.setValue(inputSchema.val());

      window.schema_editor_errors[path.join('__') + '__specific'] = true;
      if (!hasError) {
        delete window.schema_editor_errors[path.join('__') + '__specific'];
      }
      $('button[name="action_submit"]').prop('disabled', (JSON.stringify(window.schema_editor_errors) !== '{}'));
    }

    function updateTextProperty (path, realPath) {
      updateGenericProperty(path, realPath);
      let hasError = false;
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'text';

      setOptionalValueInPropertySchema(path, 'text', 'default', propertySchema);
      setOptionalValueInPropertySchema(path, 'text', 'placeholder', propertySchema);
      setOptionalValueInPropertySchema(path, 'text', 'pattern', propertySchema);
      hasError = setMinAndMaxLengthInPropertySchema(path, 'text', propertySchema, hasError);

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateChoiceProperty (path, realPath) {
      let hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'text';

      setOptionalValueInPropertySchema(path, 'choice', 'default', propertySchema);

      const choicesInput = getElementForProperty(path, 'choice-choices-input');
      const choicesGroup = choicesInput.parent();
      const choicesHelp = choicesGroup.find('.help-block');
      let choices = choicesInput.val();
      choices = choices.match(/[^\r\n]+/g);
      if (choices === null) {
        choices = [];
      }
      const nonEmptyChoices = [];
      for (let i = 0; i < choices.length; i++) {
        const choice = choices[i].trim();
        if (choice.length) {
          nonEmptyChoices.push(choice);
        }
      }
      choices = nonEmptyChoices;
      if (choices.length === 0) {
        choicesHelp.text(window.getTemplateValue('translations.choices_must_not_be_empty'));
        choicesGroup.addClass('has-error');
        hasError = true;
      } else {
        choicesHelp.text('');
        choicesGroup.removeClass('has-error');
      }
      propertySchema.choices = choices;

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateMultilineProperty (path, realPath) {
      let hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'text';
      propertySchema.multiline = true;

      setOptionalValueInPropertySchema(path, 'multiline', 'default', propertySchema);
      setOptionalValueInPropertySchema(path, 'multiline', 'placeholder', propertySchema);
      hasError = setMinAndMaxLengthInPropertySchema(path, 'multiline', propertySchema, hasError);

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateMarkdownProperty (path, realPath) {
      let hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'text';
      propertySchema.markdown = true;

      setOptionalValueInPropertySchema(path, 'markdown', 'default', propertySchema);
      setOptionalValueInPropertySchema(path, 'markdown', 'placeholder', propertySchema);
      hasError = setMinAndMaxLengthInPropertySchema(path, 'markdown', propertySchema, hasError);

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateBoolProperty (path, realPath) {
      const hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'bool';

      const hasDefault = getElementForProperty(path, 'bool-default-checkbox').prop('checked');
      const defaultValue = getElementForProperty(path, 'bool-default-input').prop('checked');

      if (hasDefault) {
        propertySchema.default = defaultValue;
      }

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updatePlotlyChartProperty (path, realPath) {
      const hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'plotly_chart';

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateTemplateObjectProperty (path, realPath) {
      let hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];

      propertySchema.type = 'object';
      propertySchema.template = null;
      propertySchema.properties = {};

      const templateInput = getElementForProperty(path, 'template-id-input');
      const templateGroup = templateInput.closest('.schema-editor-property-setting.schema-editor-template-property-setting');
      const templateHelp = templateGroup.find('.help-block');
      if (templateInput.is(':visible')) {
        const newTemplateID = templateInput.selectpicker('val');
        if (newTemplateID === '' || Number.isNaN(Number.parseInt(newTemplateID))) {
          templateHelp.text(window.getTemplateValue('translations.schema_template_must_be_set'));
          templateGroup.addClass('has-error');
          hasError = true;
        } else {
          propertySchema.template = Number.parseInt(newTemplateID);
          templateHelp.text('');
          templateGroup.removeClass('has-error');
        }
      }

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateSampleProperty (path, realPath) {
      const hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'sample';

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateMeasurementProperty (path, realPath) {
      const hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'measurement';

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateUserProperty (path, realPath) {
      const hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'user';

      const hasDefault = getElementForProperty(path, 'user-default-input').prop('checked');
      if (hasDefault) {
        propertySchema.default = 'self';
      } else {
        delete propertySchema.default;
      }

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateObjectReferenceProperty (path, realPath) {
      const hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'object_reference';

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateDatetimeProperty (path, realPath) {
      const hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'datetime';

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateQuantityProperty (path, realPath) {
      let hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'quantity';

      const unitsInput = getElementForProperty(path, 'quantity-units-input');
      let units = unitsInput.val();
      const unitsGroup = unitsInput.parent();
      const unitsHelp = unitsGroup.find('.help-block');
      // TODO: validate units
      if (units.length > 0) {
        // allow multiple units separated by a comma
        if (units.split(',').length > 1) {
          units = units.split(',');
          units = units.map(function (unit) {
            return unit.trim();
          });
        }
        propertySchema.units = units;
        unitsHelp.text('');
        unitsGroup.removeClass('has-error');
      } else {
        unitsHelp.text(window.getTemplateValue('translations.enter_units'));
        unitsGroup.addClass('has-error');
        hasError = true;
      }

      const hasDisplayDigits = getElementForProperty(path, 'quantity-display_digits-checkbox').prop('checked');
      const displayDigitsInput = getElementForProperty(path, 'quantity-display_digits-input');
      let displayDigitsValue = displayDigitsInput.val();
      const displayDigitsGroup = displayDigitsInput.parent();
      const displayDigitsHelp = displayDigitsGroup.find('.help-block');
      if (hasDisplayDigits) {
        if (isNaN(displayDigitsValue) || displayDigitsValue === null || displayDigitsValue === '' || Number.parseInt(displayDigitsValue) < 0 || Number.parseInt(displayDigitsValue) > 15) {
          displayDigitsHelp.text(window.getTemplateValue('translations.enter_display_digits'));
          displayDigitsGroup.addClass('has-error');
          hasError = true;
        } else {
          displayDigitsValue = Number.parseInt(displayDigitsValue);
          propertySchema.display_digits = displayDigitsValue;
          displayDigitsHelp.text('');
          displayDigitsGroup.removeClass('has-error');
        }
      } else {
        displayDigitsHelp.text('');
        displayDigitsGroup.removeClass('has-error');
      }

      const hasDefault = getElementForProperty(path, 'quantity-default-checkbox').prop('checked');
      const defaultInput = getElementForProperty(path, 'quantity-default-input');
      let defaultValue = defaultInput.val();
      const defaultGroup = defaultInput.parent();
      const defaultHelp = defaultGroup.find('.help-block');

      if (hasDefault) {
        if (isNaN(defaultValue) || defaultValue === null || defaultValue === '') {
          defaultHelp.text(window.getTemplateValue('translations.enter_default_magnitude'));
          defaultGroup.addClass('has-error');
          hasError = true;
        } else {
          defaultValue = Number.parseFloat(defaultValue);
          propertySchema.default = defaultValue;
          defaultHelp.text('');
          defaultGroup.removeClass('has-error');
        }
      } else {
        defaultHelp.text('');
        defaultGroup.removeClass('has-error');
      }

      const hasPlaceholder = getElementForProperty(path, 'quantity-placeholder-checkbox').prop('checked');
      const placeholderValue = getElementForProperty(path, 'quantity-placeholder-input').val();

      if (hasPlaceholder) {
        propertySchema.placeholder = placeholderValue;
      }

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateTimeseriesProperty (path, realPath) {
      let hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'timeseries';

      const unitsInput = getElementForProperty(path, 'timeseries-units-input');
      let units = unitsInput.val();
      const unitsGroup = unitsInput.parent();
      const unitsHelp = unitsGroup.find('.help-block');
      // TODO: validate units
      if (units.length > 0) {
        // allow multiple units separated by a comma
        if (units.split(',').length > 1) {
          units = units.split(',');
          units = units.map(function (unit) {
            return unit.trim();
          });
        }
        propertySchema.units = units;
        unitsHelp.text('');
        unitsGroup.removeClass('has-error');
      } else {
        unitsHelp.text(window.getTemplateValue('translations.enter_units'));
        unitsGroup.addClass('has-error');
        hasError = true;
      }

      const hasDisplayDigits = getElementForProperty(path, 'timeseries-display_digits-checkbox').prop('checked');
      const displayDigitsInput = getElementForProperty(path, 'timeseries-display_digits-input');
      let displayDigitsValue = displayDigitsInput.val();
      const displayDigitsGroup = displayDigitsInput.parent();
      const displayDigitsHelp = displayDigitsGroup.find('.help-block');
      if (hasDisplayDigits) {
        if (isNaN(displayDigitsValue) || displayDigitsValue === null || displayDigitsValue === '' || Number.parseInt(displayDigitsValue) < 0 || Number.parseInt(displayDigitsValue) > 15) {
          displayDigitsHelp.text(window.getTemplateValue('translations.enter_display_digits'));
          displayDigitsGroup.addClass('has-error');
          hasError = true;
        } else {
          displayDigitsValue = Number.parseInt(displayDigitsValue);
          propertySchema.display_digits = displayDigitsValue;
          displayDigitsHelp.text('');
          displayDigitsGroup.removeClass('has-error');
        }
      } else {
        displayDigitsHelp.text('');
        displayDigitsGroup.removeClass('has-error');
      }

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    function updateFileProperty (path, realPath) {
      let hasError = false;
      updateGenericProperty(path, realPath);
      const schema = JSON.parse(inputSchema.val());
      const propertySchema = schema.properties[realPath[realPath.length - 1]];
      propertySchema.type = 'file';

      const hasExtensions = getElementForProperty(path, 'file-extensions-checkbox').prop('checked');
      const extensionsInput = getElementForProperty(path, 'file-extensions-input');
      let extensions = extensionsInput.val();
      const extensionsGroup = extensionsInput.parent();
      const extensionsHelp = extensionsGroup.find('.help-block');
      if (hasExtensions) {
        extensionsInput.prop('disabled', false);
        if (extensions.length > 0) {
          // allow multiple extensions separated by a comma
          extensions = extensions.split(',');
          extensions = extensions.map(function (unit) {
            return unit.trim();
          });
          propertySchema.extensions = extensions;
          extensionsHelp.text('');
          extensionsGroup.removeClass('has-error');
        } else {
          delete propertySchema.extensions;
          extensionsHelp.text(window.getTemplateValue('translations.enter_extensions'));
          extensionsGroup.addClass('has-error');
          hasError = true;
        }
      } else {
        extensionsInput.prop('disabled', true);
        delete propertySchema.extensions;
        extensionsHelp.text('');
        extensionsGroup.removeClass('has-error');
      }

      const hasPreview = getElementForProperty(path, 'file-preview-input').prop('checked');
      propertySchema.preview = hasPreview;

      updateSpecificProperty(path, realPath, schema, propertySchema, hasError);
    }

    const requiredLabel = node.find('.schema-editor-generic-property-required-label');
    const requiredInput = node.find('.schema-editor-generic-property-required-input');
    requiredInput.attr('id', 'schema-editor-object__' + path.join('__') + '-required-input');
    requiredLabel.attr('for', requiredInput.attr('id'));
    requiredInput.prop('checked', isRequired);
    requiredInput.bootstrapToggle();
    requiredInput.on('change', function () { updateProperty(path); });

    function setupValueFromSchema (path, type, name, schema, isType, isTranslatable) {
      const valueLabel = node.find('.schema-editor-' + type + '-property-' + name.toLowerCase() + '-label');
      const valueInput = node.find('.schema-editor-' + type + '-property-' + name.toLowerCase() + '-input');
      const valueCheckbox = node.find('.schema-editor-' + type + '-property-' + name.toLowerCase() + '-checkbox');
      valueCheckbox.attr('id', 'schema-editor-object__' + path.join('__') + '-' + type + '-' + name.toLowerCase() + '-checkbox');
      if (isTranslatable) {
        valueInput.each(function (_, languageValueInput) {
          const langCode = $(languageValueInput).data('sampledbLangCode');
          const id = 'schema-editor-object__' + path.join('__') + '-' + type + '-' + name.toLowerCase() + '-input-' + langCode;
          $(languageValueInput).attr('id', id);
          $(languageValueInput).parent().find('label').attr('for', 'id');
        });
      } else {
        valueInput.attr('id', 'schema-editor-object__' + path.join('__') + '-' + type + '-' + name.toLowerCase() + '-input');
        valueLabel.attr('for', valueInput.attr('id'));
      }
      if (isType && name in schema) {
        if (isTranslatable) {
          if (typeof schema[name] === 'string') {
            schema[name] = { en: schema[name] };
          }
          for (const langCode in schema[name]) {
            const languageValueInput = valueInput.filter('[data-sampledb-lang-code="' + langCode + '"]');
            if (languageValueInput.length > 0) {
              languageValueInput.val(schema[name][langCode]);
            } else {
              window.schema_editor_missing_type_support = true;
            }
          }
          valueCheckbox.prop('checked', true);
          valueInput.prop('disabled', false);
        } else {
          if (typeof schema[name] === 'object') {
            // translations for text properties only supported for some properties in graphical editor
            window.schema_editor_missing_type_support = true;
            if ('en' in schema[name]) {
              valueInput.val(schema[name].en);
              valueCheckbox.prop('checked', true);
              valueInput.prop('disabled', false);
            } else {
              valueInput.val('');
              valueCheckbox.prop('checked', false);
              valueInput.prop('disabled', true);
            }
          } else {
            valueInput.val(schema[name]);
            valueCheckbox.prop('checked', true);
            valueInput.prop('disabled', false);
          }
        }
      } else {
        valueInput.val('');
        valueCheckbox.prop('checked', false);
        valueInput.prop('disabled', true);
      }
      valueCheckbox.on('change', function () {
        if ($(this).prop('checked')) {
          valueInput.prop('disabled', false);
        } else {
          valueInput.prop('disabled', true);
        }
      });
      valueCheckbox.on('change', function () { updateProperty(path); });
      valueInput.on('change', function () { updateProperty(path); });
    }

    // Every supported type has a note and tooltip input
    setupValueFromSchema(path, 'generic', 'note', schema, true, true);
    setupValueFromSchema(path, 'generic', 'tooltip', schema, true, true);

    setupValueFromSchema(path, 'text', 'default', schema, type === 'text', false);
    setupValueFromSchema(path, 'text', 'placeholder', schema, type === 'text', false);
    setupValueFromSchema(path, 'text', 'pattern', schema, type === 'text', false);
    setupValueFromSchema(path, 'text', 'minLength', schema, type === 'text', false);
    setupValueFromSchema(path, 'text', 'maxLength', schema, type === 'text', false);

    setupValueFromSchema(path, 'choice', 'default', schema, type === 'choice', false);

    const choicesLabel = node.find('.schema-editor-choice-property-choices-label');
    const choicesInput = node.find('.schema-editor-choice-property-choices-input');
    choicesInput.attr('id', 'schema-editor-object__' + path.join('__') + '-choice-choices-input');
    choicesLabel.attr('for', choicesInput.attr('id'));
    if (type === 'choice' && 'choices' in schema) {
      let choicesText = '';
      for (const i in schema.choices) {
        if (typeof schema.choices[i] === 'object') {
          // translations for text properties not supported in graphical editor
          window.schema_editor_missing_type_support = true;
          if ('en' in schema.choices[i]) {
            choicesText += schema.choices[i].en + '\n';
          }
        } else {
          choicesText += schema.choices[i] + '\n';
        }
      }
      choicesInput.val(choicesText);
    } else {
      choicesInput.val('');
    }
    choicesInput.on('change', function () { updateProperty(path); });

    setupValueFromSchema(path, 'multiline', 'default', schema, type === 'multiline', false);
    setupValueFromSchema(path, 'multiline', 'placeholder', schema, type === 'multiline', false);
    setupValueFromSchema(path, 'multiline', 'minLength', schema, type === 'multiline', false);
    setupValueFromSchema(path, 'multiline', 'maxLength', schema, type === 'multiline', false);

    setupValueFromSchema(path, 'markdown', 'default', schema, type === 'markdown', false);
    setupValueFromSchema(path, 'markdown', 'placeholder', schema, type === 'markdown', false);
    setupValueFromSchema(path, 'markdown', 'minLength', schema, type === 'markdown', false);
    setupValueFromSchema(path, 'markdown', 'maxLength', schema, type === 'markdown', false);

    {
      const defaultLabel = node.find('.schema-editor-bool-property-default-label');
      const defaultInput = node.find('.schema-editor-bool-property-default-input');
      const defaultCheckbox = node.find('.schema-editor-bool-property-default-checkbox');
      defaultCheckbox.attr('id', 'schema-editor-object__' + path.join('__') + '-bool-default-checkbox');
      defaultInput.attr('id', 'schema-editor-object__' + path.join('__') + '-bool-default-input');
      defaultLabel.attr('for', defaultInput.attr('id'));
      defaultInput.bootstrapToggle();
      if (type === 'bool' && 'default' in schema) {
        defaultInput.prop('checked', schema.default);
        if (schema.default) {
          defaultInput.bootstrapToggle('on');
        } else {
          defaultInput.bootstrapToggle('off');
        }
        defaultCheckbox.prop('checked', true);
        defaultInput.prop('disabled', false);
        defaultInput.closest('.toggle').removeClass('disabled');
      } else {
        defaultInput.prop('checked', false);
        defaultCheckbox.prop('checked', false);
        defaultInput.prop('disabled', true);
        defaultInput.closest('.toggle').addClass('disabled');
      }
      defaultCheckbox.on('change', function () {
        const defaultInput = $(this).parent().parent().find('.schema-editor-bool-property-default-input');
        if ($(this).prop('checked')) {
          defaultInput.prop('disabled', false);
          defaultInput.closest('.toggle').removeClass('disabled');
        } else {
          defaultInput.prop('disabled', true);
          defaultInput.closest('.toggle').addClass('disabled');
        }
      });
      defaultCheckbox.on('change', function () { updateProperty(path); });
      defaultInput.on('change', function () { updateProperty(path); });
    }

    setupValueFromSchema(path, 'quantity', 'default', schema, type === 'quantity', false);
    setupValueFromSchema(path, 'quantity', 'placeholder', schema, type === 'quantity', false);
    setupValueFromSchema(path, 'quantity', 'display_digits', schema, type === 'quantity', false);

    for (const propertyType of ['quantity', 'timeseries']) {
      const unitsLabel = node.find('.schema-editor-' + propertyType + '-property-units-label');
      const unitsInput = node.find('.schema-editor-' + propertyType + '-property-units-input');
      unitsInput.attr('id', 'schema-editor-object__' + path.join('__') + '-' + propertyType + '-units-input');
      unitsLabel.attr('for', unitsInput.attr('id'));
      if (type === propertyType && 'units' in schema) {
        unitsInput.val(schema.units);
      } else {
        unitsInput.val('');
      }
      unitsInput.on('change', function () { updateProperty(path); });
      if (window.schema_editor_error_message !== null && window.schema_editor_error_message === ('invalid units (at ' + path[0] + ')')) {
        const unitsGroup = unitsInput.parent();
        unitsGroup.addClass('has-error');
        unitsGroup.find('.help-block').text(window.getTemplateValue('translations.enter_valid_units'));
        window.schema_editor_errors[path.join('__') + '__specific'] = true;
        unitsInput.on('change', function () {
          window.schema_editor_error_message = null;
        });
      }
    }

    setupValueFromSchema(path, 'timeseries', 'display_digits', schema, type === 'timeseries', false);

    const extensionsCheckbox = node.find('.schema-editor-file-property-extensions-checkbox');
    const extensionsLabel = node.find('.schema-editor-file-property-extensions-label');
    const extensionsInput = node.find('.schema-editor-file-property-extensions-input');
    extensionsCheckbox.attr('id', 'schema-editor-object__' + path.join('__') + '-file-extensions-checkbox');
    extensionsInput.attr('id', 'schema-editor-object__' + path.join('__') + '-file-extensions-input');
    extensionsLabel.attr('for', extensionsInput.attr('id'));
    if (type === 'file' && 'extensions' in schema) {
      extensionsInput.val(schema.extensions);
      extensionsCheckbox.prop('checked', true);
    } else {
      extensionsInput.val('');
      extensionsCheckbox.prop('checked', false);
    }
    extensionsCheckbox.on('change', function () { updateProperty(path); });
    extensionsInput.on('change', function () { updateProperty(path); });

    {
      const defaultLabel = node.find('.schema-editor-user-property-default-label');
      const defaultInput = node.find('.schema-editor-user-property-default-input');
      defaultInput.attr('id', 'schema-editor-object__' + path.join('__') + '-user-default-input');
      defaultLabel.attr('for', defaultInput.attr('id'));
      defaultInput.bootstrapToggle();
      if (type === 'user' && 'default' in schema) {
        if (schema.default === 'self') {
          defaultInput.prop('checked', true);
          defaultInput.bootstrapToggle('on');
        } else {
          window.schema_editor_missing_type_support = true;
        }
      } else {
        defaultInput.prop('checked', false);
        defaultInput.bootstrapToggle('off');
      }
      defaultInput.on('change', function () { updateProperty(path); });
    }

    const previewLabel = node.find('.schema-editor-file-property-preview-label');
    const previewInput = node.find('.schema-editor-file-property-preview-input');
    previewInput.attr('id', 'schema-editor-object__' + path.join('__') + '-file-preview-input');
    previewLabel.attr('for', previewInput.attr('id'));
    previewInput.bootstrapToggle();
    if (type === 'file' && 'preview' in schema) {
      previewInput.prop('checked', schema.preview);
      if (schema.preview) {
        previewInput.bootstrapToggle('on');
      } else {
        previewInput.bootstrapToggle('off');
      }
    } else {
      previewInput.prop('checked', false);
      previewInput.bootstrapToggle('off');
    }
    previewInput.on('change', function () { updateProperty(path); });

    const templateIDInput = node.find('.schema-editor-generic-property-template-id-input');
    templateIDInput.attr('id', 'schema-editor-object__' + path.join('__') + '-template-id-input');
    templateIDInput.val(type);
    templateIDInput.selectpicker();
    templateIDInput.on('change', function () { updateProperty(path); });

    const advancedSchemaFeatures = [
      'conditions', 'action_type_id', 'action_id',
      'may_copy', 'dataverse_export', 'languages',
      'min_magnitude', 'max_magnitude', 'statistics',
      'calculation', 'style', 'filter_operator', 'workflow_view', 'workflow_views'
    ];

    for (const name of advancedSchemaFeatures) {
      if (name in schema) {
        window.schema_editor_missing_type_support = true;
        break;
      }
    }

    window.schema_editor_initial_updates.push(function () { updateProperty(path); });

    return node;
  }

  const rootObjectNode = buildRootObjectNode(schema);
  schemaEditor[0].appendChild(rootObjectNode[0]);
  inputSchema.val(JSON.stringify(schema, null, 2));
  window.code_mirror_editor.setValue(inputSchema.val());
  globallyValidateSchema();
  $.each(window.schema_editor_initial_updates, function (_, updateFunction) {
    updateFunction();
  });
  if (window.schema_editor_missing_type_support) {
    $('#schemaEditorWarningModal').modal('show');
    inputSchema.val(schemaText);
  }
}

/**
 * Disables the graphical schema editor and shows the JSON editor.
 */
function disableSchemaEditor () {
  window.schema_editor_enabled = false;
  const schemaEditor = $('#schema-editor');
  const inputSchema = $('#input-schema');
  schemaEditor.hide();
  window.code_mirror_editor.setValue(inputSchema.val());
  if (window.schema_editor_error_lines.length > 0) {
    const errorLineRanges = [];
    for (let i = 0; i < window.schema_editor_error_lines.length; i += 1) {
      const errorLine = window.schema_editor_error_lines[i];
      if (errorLineRanges.length > 0 && errorLineRanges[errorLineRanges.length - 1][1] === errorLine - 1) {
        errorLineRanges[errorLineRanges.length - 1][1] = errorLine;
      } else {
        errorLineRanges.push([errorLine - 1, errorLine]);
      }
    }
    const markers = [];
    errorLineRanges.forEach(function (errorLineRange) {
      markers.push(window.code_mirror_editor.doc.markText(
        { line: errorLineRange[0], ch: 0 },
        { line: errorLineRange[1], ch: 0 },
        { inclusiveRight: false, css: 'background-color: #ffdddd !important' }
      ));
    });
    window.code_mirror_editor.on('change', function () {
      const currentContent = window.code_mirror_editor.getValue();
      if (window.schema_editor_initial_content === null) {
        window.schema_editor_initial_content = currentContent;
      }
      if (currentContent !== window.schema_editor_initial_content) {
        window.schema_editor_error_lines = [];
        markers.forEach(function (marker) {
          marker.clear();
        });
      }
    });
  }
  $('#input-schema ~ .CodeMirror').show();
  window.code_mirror_editor.refresh();
  if (window.schema_editor_initial_content === null) {
    window.schema_editor_initial_content = window.code_mirror_editor.getValue();
  }
  $('button[name="action_submit"]').prop('disabled', false);
  $('#form-action').off('submit');
}

$(function () {
  window.schema_editor_error_message = window.getTemplateValue('error_message');
  window.schema_editor_error_lines = window.getTemplateValue('error_lines');
  window.schema_editor_initial_content = null;
  window.code_mirror_editor = CodeMirror.fromTextArea($('#input-schema')[0], {
    lineNumbers: true,
    mode: { name: 'javascript', json: true },
    scrollbarStyle: null
  });

  // Add function to hide alert onclick
  $('#schema-editor-type-is-template-close').on('click', function () {
    $('.schema-editor-type-is-template').hide();
  });
  // Add function to show alert if action_type data-is-template is True on change
  const typeInput = $('#input-type');
  typeInput.on('change', function () {
    const chosenActionType = typeInput.find('[value=' + typeInput.val() + ']');
    if (chosenActionType.data('isTemplate') === 'True') {
      $('.schema-editor-type-is-template').show();
    } else {
      $('.schema-editor-type-is-template').hide();
    }
  }).change();

  const schemaEditorToggle = $('#toggle-schema-editor');
  window.schema_editor_enabled = null;
  schemaEditorToggle.on('change', function () {
    if (schemaEditorToggle.prop('checked')) {
      if (window.schema_editor_enabled !== true) {
        enableSchemaEditor();
      }
    } else {
      if (window.schema_editor_enabled !== false) {
        disableSchemaEditor();
      }
    }
  });
  schemaEditorToggle.change();

  $('#button-use-text-editor').on('click', function () {
    schemaEditorToggle.bootstrapToggle('off');
  });
});
