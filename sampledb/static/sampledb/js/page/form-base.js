'use strict';
/* eslint-env jquery */

import {
  setUpCalculations,
  applySchemaCalculations
} from '../object_form/calculation.js';

import {
  fileEventHandler
} from '../sampledb-file-form-handler.js';

import {
  applySchemaConditions
} from '../conditional_wrapper.js';

import {
  setupImageDragAndDrop
} from '../markdown_image_upload.js';

import {
  initMarkdownField
} from '../sampledb-internationalization.js';

import {
  updateObjectPickers
} from '../sampledb-load-objects.js';

import {
  addActionFilterButton
} from '../object_form/object-reference.js';

import {
  updateSelectLanguage
} from '../object_form/text.js';

window.mdeFields = [];
window.initPhase = true;
let fileNamesByID = {};
let formData = {};
window.arrayButtons = [];

window.local_decimal_delimiter = window.getTemplateValue('local_decimal_delimiter');
window.array_table_header_text = window.getTemplateValue('translations.field_index_placeholder');

window.temporaryFileUploadURL = window.getTemplateValue('temporary_file_upload_url');
window.currentUserTimezone = window.getTemplateValue('current_user.timezone');
window.currentUserLanguageCode = window.getTemplateValue('current_user.language.lang_code');
window.currentUserDatetimeFormat = window.getTemplateValue('current_user.language.datetime_format_moment');

fileNamesByID = window.getTemplateValue('file_names_by_id');
formData = window.getTemplateValue('form_data');

/**
   * Updates the event handler of an array container button.
   * @param button a DOM button
   */
function updateArrayButtonsHandler (button) {
  switch ($(button).data('object-form-button')) {
    case 'array_add':
    case 'list_array_add':
    case 'table_array_add':
      $(button).off('click').on('click', arrayFormAddHandler);
      break;
    case 'array_delete':
    case 'list_array_delete':
    case 'table_array_delete':
      $(button).off('click').on('click', arrayFormDeleteHandler);
      break;
    case 'array_clear':
    case 'list_array_clear':
    case 'table_array_clear':
      $(button).off('click').on('click', arrayFormClearHandler);
      break;
    case 'table_array_copy':
      $(button).off('click').on('click', arrayFormTableCopyHandler);
      break;
    case 'table_col_add':
      $(button).off('click').on('click', tableFormColAddHandler);
      break;
    case 'table_col_delete':
      $(button).off('click').on('click', tableFormColDeleteHandler);
      break;
    case 'table_row_add':
      $(button).off('click').on('click', tableFormRowAddHandler);
      break;
    case 'table_row_delete':
      $(button).off('click').on('click', tableFormRowDeleteHandler);
      break;
    case 'table_rows_clear':
      $(button).off('click').on('click', tableFormRowClearHandler);
      break;
  }
}

/**
   * Updates the event handlers of the buttons for all array containers within a given element.
   * @param element a jQuery element
   */
function updateArrayButtonsHandlerWithinElement (element) {
  if (element === undefined) {
    element = $(document);
  }
  element.find('[data-object-form-button]').each(function (_, button) {
    updateArrayButtonsHandler(button);
  });
}

$(function () {
  $('form').on('submit', function () {
    $('.array-template').remove();
    $('input').not('[type="file"]').change();
    $('textarea').change();
    $('.col-diff').each(function () {
      const value = Number($(this).data('value'));
      const jsonProps = JSON.stringify({ value, buttonID: (value >= 0) ? $(this).data('add-id') : $(this).data('delete-id') });
      $(this).val(jsonProps);
    });

    $('#input-array_buttons').val(window.arrayButtons.join());
    $('[data-sampledb-choice-array]').each(function () {
      const choicePicker = $(this);
      const wrapper = choicePicker.closest('.error-parent');
      const idPrefix = choicePicker.data('sampledb-choice-array');
      wrapper.find(`input[type="hidden"][name!="${idPrefix}_hidden"]`).remove();
      if (!choicePicker.prop('disabled')) {
        $.each(choicePicker.selectpicker('val'), function (index, value) {
          const name = `${idPrefix}_${index}__text`;
          const element = $('<input type="hidden" />');
          element.attr('name', name);
          element.attr('value', value);
          wrapper.append(element);
        });
      }
    });

    $('.typeahead').each(function () {
      $(this).val($(this).typeahead('val'));
    });
  });

  $('textarea[data-markdown-textarea="true"]').not('.template-markdown-editor').each(function (_, element) {
    setupImageDragAndDrop(initMarkdownField(element, '100px'));
  });

  $('textarea.plotly-chart-editor').each(function () {
    const jsonStr = $(this).text();
    try {
      const jsonObj = JSON.parse(jsonStr);
      const jsonPretty = JSON.stringify(jsonObj, null, '\t');
      $(this).text(jsonPretty);
    } catch (e) {

    }
  });

  applySchemaConditions(document);

  updateArrayButtonsHandlerWithinElement($(document));

  // set initial disabled / enabled state for all array buttons
  updateArrayButtonsEnabledWithinElement($(document));

  const arrayButtons = formData.array_buttons || '';
  if (arrayButtons !== '') {
    $.each(arrayButtons.split(','), function (_, buttonID) {
      $(`[id="${buttonID}"`).click();
    });
  }
  window.initPhase = false;

  $('.div-apply-recipe:visible').each(function () {
    updateRecipeState($(this));
  });

  updateJSInteractiveFields();
  insertFormData();
  replaceMarkdownTemplates();
  showErrors();

  $('select.file-select').each(function () {
    if ($(this).parents('.array-template').length > 0) {
      return;
    }
    const name = $(this).attr('name');
    if (formData[name]) {
      const value = formData[name];
      const option = $('<option></option>');
      option.attr('value', value);
      option.attr('data-sampledb-temporary-file', '1');
      option.text(fileNamesByID[value][0]);
      $(this).append(option);
      $(this).prop('disabled', false);
      $(this).selectpicker('refresh');
      $(this).selectpicker('val', formData[name]);
      $(this).selectpicker('refresh');
    }
  });

  $.each(window.conditionalWrapperScripts, function () {
    this();
  });

  window.conditionalWrapperScripts = [];

  setUpCalculations();

  $('div.objectpicker').each(function () {
    addActionFilterButton($(this));
  });
});

function refreshRecipeTooltip (idPrefix, recipes, showTooltip = false) {
  const recipeDiv = $(`.div-apply-recipe[data-id-prefix=${idPrefix}]`);
  const input = recipeDiv.find('select').first();
  const recipe = recipes[input.val()];
  const changedValues = [];
  const recipeName = recipe.name;
  for (const value of Object.values(recipe.property_values)) {
    changedValues.push(value.title);
  }
  recipeDiv.attr('title', `${recipeName} ${window.getTemplateValue('translations.sets')} ${changedValues.join(', ')}`);
  recipeDiv.attr('data-original-title', `${recipeName} ${window.getTemplateValue('translations.sets')} ${changedValues.join(', ')}`);
  recipeDiv.tooltip('hide');
}

$('document').ready(function () { $('.div-apply-recipe select').change(); });

function applyRecipe (idPrefix, recipes, isTable) {
  const recipeDiv = $(`.div-apply-recipe[data-id-prefix=${idPrefix}]`);
  const input = recipeDiv.find('select').first();
  const codeMirrors = {};
  $('.CodeMirror').each(function (i, el) {
    codeMirrors[el.CodeMirror.getTextArea().name] = el.CodeMirror;
  });
  for (const [property, value] of Object.entries(recipes[input.val()].property_values)) {
    if (!isTable && value.value !== null && (value.type === 'text' || value.type === 'multiline' || value.type === 'markdown') && value.value.constructor === Object) {
      const languageSelect = $(`[name="${idPrefix}_${property}__text_languages"]`);
      if (languageSelect.length === 1) {
        let selectedLanguages = languageSelect.val();
        if (selectedLanguages === '' || selectedLanguages.length === 0) {
          selectedLanguages = ['en'];
        } else {
          selectedLanguages.push('en');
        }
        for (const lang of Object.keys(value.value)) {
          if (selectedLanguages.indexOf(lang) === -1) {
            selectedLanguages.push(lang);
          }
        }
        languageSelect.selectpicker('val', selectedLanguages);
      }
    }
    switch (value.type) {
      case 'text':
        if (typeof value.value === 'string' || value.value instanceof String) {
          if (isTable) {
            $('input[name="' + idPrefix + '_' + property + '__text"]').val(value.value || '');
          } else {
            $('input[name="' + idPrefix + '_' + property + '__text_en"]').val(value.value || '');
          }
        } else if (value.value === null) {
          if (isTable) {
            $('input[name="' + idPrefix + '_' + property + '__text"]').val('');
          } else {
            $('input[name^="' + idPrefix + '_' + property + '__text_"]').val('');
          }
        } else if (value.value.constructor === Object) {
          if (isTable) {
            $('input[name="' + idPrefix + '_' + property + '__text"]').val(value.value.en);
          } else {
            for (const [lang, text] of Object.entries(value.value)) {
              $('input[name="' + idPrefix + '_' + property + '__text_' + lang + '"]').val(text || '');
            }
          }
        }
        break;
      case 'multiline':
        if (typeof value.value === 'string' || value.value instanceof String) {
          if (isTable) {
            $('textarea[name="' + idPrefix + '_' + property + '__text"]').val(value.value || '');
          } else {
            $('textarea[name="' + idPrefix + '_' + property + '__text_en"]').val(value.value || '');
          }
        } else if (value.value === null) {
          if (isTable) {
            $('textarea[name="' + idPrefix + '_' + property + '__text"]').val('');
          } else {
            $('textarea[name^="' + idPrefix + '_' + property + '__text_"]').val('');
          }
        } else if (value.value.constructor === Object) {
          if (isTable) {
            $('textarea[name="' + idPrefix + '_' + property + '__text"]').val(value.value.en || '');
          } else {
            for (const [lang, text] of Object.entries(value.value)) {
              $('textarea[name="' + idPrefix + '_' + property + '__text_' + lang + '"]').val(text || '');
            }
          }
        }
        break;
      case 'markdown':
        if (!isTable) {
          if (typeof value.value === 'string' || value.value instanceof String) {
            codeMirrors[idPrefix + '_' + property + '__text_en'].setValue(value.value || '');
          } else if (value.value === null) {
            for (const name in codeMirrors) {
              if (name.startsWith(idPrefix + '_' + property + '__text_')) {
                codeMirrors[name].setValue('');
              }
            }
          } else if (value.value.constructor === Object) {
            for (const [lang, text] of Object.entries(value.value)) {
              codeMirrors[idPrefix + '_' + property + '__text_' + lang].setValue(text || '');
            }
          }
        } else {
          if (typeof value.value === 'string' || value.value instanceof String || value.value === null) {
            $('textarea[name="' + idPrefix + '_' + property + '__text"]').val(value.value || '');
          } else if (value.value.constructor === Object) {
            $('textarea[name="' + idPrefix + '_' + property + '__text"]').val(value.value.en || '');
          }
        }
        break;
      case 'choice':
        $('select[name="' + idPrefix + '_' + property + '__text"]').val(value.value || '').selectpicker('refresh');
        break;
      case 'quantity':
        $('input[name="' + idPrefix + '_' + property + '__magnitude"]').val(value.value || '');
        if (value.units) {
          $('select[name="' + idPrefix + '_' + property + '__units"]').selectpicker('val', value.units);
        }
        break;
      case 'bool':
        $('input[name="' + idPrefix + '_' + property + '__value"]').prop('checked', value.value);
        break;
      case 'datetime':
        $('input[name="' + idPrefix + '_' + property + '__datetime"]').val(value.value || '');
        break;
    }
  }
}

/**
   * Returns the add, copy and delete buttons of an array container (not for array tables).
   * @param arrayContainer a jQuery array container element
   * @returns {Array} add button, copy buttons and delete buttons
   */
function getArrayButtons (arrayContainer) {
  const addButton = arrayContainer.find('[data-object-form-button$="_add"]').filter(function (_, button) {
    return $(button).closest('[data-array-container]')[0] === arrayContainer[0];
  });
  const copyButtons = arrayContainer.find('[data-object-form-button$="_copy"]').filter(function (_, button) {
    return $(button).closest('[data-array-container]')[0] === arrayContainer[0];
  });
  const deleteButtons = arrayContainer.find('[data-object-form-button$="_delete"]').filter(function (_, button) {
    return $(button).closest('[data-array-container]')[0] === arrayContainer[0];
  });
  const clearButton = arrayContainer.find('[data-object-form-button$="_clear"]').filter(function (_, button) {
    return $(button).closest('[data-array-container]')[0] === arrayContainer[0];
  });
  return [addButton, copyButtons, deleteButtons, clearButton];
}

/**
   * Applies modifications needed for user interaction to a new element.
   * @param clone a jQuery element
   * @param arrayContainer a jQuery array container element
   */
function applyInteractionModifications (clone, arrayContainer) {
  updateJSInteractiveFields();
  applySchemaConditions(clone);
  applySchemaCalculations(clone);
  updateLanguageSelects(clone);
  updateRecipeState(clone);
  updateArrayButtonsEnabled(arrayContainer);

  updateArrayButtonsHandlerWithinElement(clone);
  updateArrayButtonsEnabledWithinElement(clone);
  replaceMarkdownTemplates();
}

function clearUnusedConditions () {
  if (window.conditionalWrapperConditions) {
    for (const idPrefix of Object.keys(window.conditionalWrapperConditions)) {
      if ($(`[data-condition-wrapper-for^=${idPrefix}]`).length === 0) {
        delete window.conditionalWrapperConditions[idPrefix];
      }
    }
  }
}

/**
   * Replaces one ID prefix with another for a collection of elements and the condition list.
   * @param elements a collection of jQuery elements
   * @param oldIDPrefix the ID prefix to replace
   * @param newIDPrefix the ID prefix to replace it with
   */
function replaceIDPrefix (elements, oldIDPrefix, newIDPrefix) {
  elements.filter(`[name^="${oldIDPrefix}_"]`).each(function (_, element) {
    element.name = newIDPrefix + element.name.substring(oldIDPrefix.length);
  });
  elements.filter(`[name^="typeahead_text_${oldIDPrefix}_"]`).each(function (_, element) {
    element.name = 'typeahead_text_' + newIDPrefix + element.name.substring('typeahead_text_'.length + oldIDPrefix.length);
  });
  elements.filter(`[id^="action_${oldIDPrefix}_"]`).each(function (_, element) {
    element.id = 'action_' + newIDPrefix + element.id.substring('action_'.length + oldIDPrefix.length);
  });
  for (const dataAttribute of ['id-prefix', 'condition-wrapper-for', 'condition-replacement-for', 'sampledb-choice-array']) {
    elements.filter(`[data-${dataAttribute}^="${oldIDPrefix}_"], [data-${dataAttribute}="${oldIDPrefix}"]`).each(function (_, element) {
      $(element).attr(`data-${dataAttribute}`, newIDPrefix + $(element).data(dataAttribute).substring(oldIDPrefix.length));
      $(element).data(dataAttribute, $(element).attr(`data-${dataAttribute}`));
    });
  }
  elements.filter(`span[id^="${oldIDPrefix}_"][id$="_calculation_help"]`).each(function (_, element) {
    $(element).attr('id', newIDPrefix + $(element).attr('id').substring(oldIDPrefix.length));
  });
  if (window.conditionalWrapperConditions) {
    for (const [idPrefix, conditions] of Object.entries(window.conditionalWrapperConditions)) {
      if (idPrefix.startsWith(oldIDPrefix)) {
        delete window.conditionalWrapperConditions[idPrefix];
        window.conditionalWrapperConditions[newIDPrefix + idPrefix.substring(oldIDPrefix.length)] = conditions;
      }
    }
  }
}

/**
   * Update ID prefixes to ensure array indices do not have gaps and start at 0.
   * @param arrayContainer a jQuery array container element
   * @param sortedArrayIndices an optional array of sorted indices
   */
function updateArrayIDPrefixes (arrayContainer, sortedArrayIndices) {
  const prefix = arrayContainer.data('id-prefix');
  if (sortedArrayIndices === undefined) {
    const elements = arrayContainer.find(`[name^="${prefix}_"]`);
    const usedArrayIndices = [];
    elements.each(function (_, element) {
      const indexString = element.name.substring(prefix.length + 1).split('_', 1)[0];
      const index = Number.parseInt(indexString);
      if (index.toString() === indexString && !usedArrayIndices.includes(index)) {
        usedArrayIndices.push(index);
      }
    });
    // custom comparator to sort numbers numerically instead of lexicographically
    usedArrayIndices.sort(function (a, b) {
      return a - b;
    });
    sortedArrayIndices = usedArrayIndices;
  }
  // replace ID prefixes using a temporary prefix to avoid conflicts
  for (let i = 0; i < sortedArrayIndices.length; i++) {
    const oldIDPrefix = `${prefix}_${sortedArrayIndices[i]}_`;
    const tmpIDPrefix = `updateArrayIDPrefixes_tmpIDPrefix_${i}_`;
    replaceIDPrefix(arrayContainer.find('*'), oldIDPrefix, tmpIDPrefix);
  }
  for (let i = 0; i < sortedArrayIndices.length; i++) {
    const tmpIDPrefix = `updateArrayIDPrefixes_tmpIDPrefix_${i}_`;
    const newIDPrefix = `${prefix}_${i}_`;
    replaceIDPrefix(arrayContainer.find('*'), tmpIDPrefix, newIDPrefix);
  }
}

/**
   * Replace an index placeholder with the actual index for an element and its descendents.
   * @param element a jQuery element
   * @param indexPlaceholder the index placeholder to replace
   * @param index the index to replace the placeholder with
   */
function replaceTemplateIndex (element, indexPlaceholder, index) {
  const arrayContainer = element.closest('[data-array-container]');
  const arrayPrefix = arrayContainer.data('id-prefix');
  replaceIDPrefix(element.find('*').add(element), `${arrayPrefix}_${indexPlaceholder}_`, `${arrayPrefix}_${index}_`);
}

/**
   * Handles array add button events.
   * @param event a PointerEvent
   */
function arrayFormAddHandler (event) {
  const button = $(event.currentTarget);
  const arrayContainer = button.closest('[data-array-container]');
  const arrayPrefix = arrayContainer.data('id-prefix');
  if (arrayPrefix.includes('!')) {
    return;
  }
  window.arrayButtons.push(button.attr('id'));
  const indexOrderPlaceholder = `!index${arrayContainer.data('template-order-index')}!`;
  // the template is the .array-template element which has the current array container as the closest container
  // it is not always a direct child of arrayContainer, though, e.g. table rows are located in a tbody tag
  const template = arrayContainer.find('.array-template').filter(function (_, element) {
    return $(element).closest('[data-array-container]')[0] === arrayContainer[0];
  });
  const clone = $(template.clone(true));
  clone.removeClass('array-template');
  const existingDeleteButtons = getArrayButtons(arrayContainer)[2];
  // array has one more delete button than items because of the array template
  const nextIndex = existingDeleteButtons.length - 1;

  template.before(clone);
  replaceTemplateIndex(clone, indexOrderPlaceholder, nextIndex);
  applyInteractionModifications(clone, arrayContainer);

  if (arrayContainer.data('array-container') === 'list') {
    // the first entry of a list is right of the label, all others need an additional offset
    arrayContainer.children('div').not('.control-label').addClass('col-md-offset-3').first().removeClass('col-md-offset-3');
  }
}

/**
   * Handles object table array copy button events.
   * @param event a PointerEvent
   */
function arrayFormTableCopyHandler (event) {
  const button = $(event.currentTarget);
  // add a new row first, which will then be filled and moved
  arrayFormAddHandler(event);
  const arrayContainer = button.closest('[data-array-container]');
  const arrayPrefix = arrayContainer.data('id-prefix');
  if (arrayPrefix.includes('!')) {
    return;
  }
  const tableBody = button.closest('tbody');
  const sourceRow = button.closest('tr');
  const targetRow = tableBody.children('tr').not('.array-template').last();
  // move target row right behind source row
  sourceRow.after(targetRow);
  const sourceFieldPrefix = sourceRow.data('id-prefix');
  const targetFieldPrefix = targetRow.data('id-prefix');
  const targetFields = targetRow.find(`[name^="${targetFieldPrefix}"]`);
  for (const targetField of targetFields) {
    const sourceFieldName = sourceFieldPrefix + targetField.name.substring(targetFieldPrefix.length);
    const sourceField = $(`[name=${sourceFieldName}]`)[0];
    if (sourceField.tagName === 'INPUT' || sourceField.tagName === 'TEXTAREA') {
      if (sourceField.type === 'checkbox') {
        $(targetField).prop('checked', $(sourceField).prop('checked'));
      } else {
        $(targetField).val($(sourceField).val());
      }
      if (sourceField.tagName === 'INPUT' && sourceField.name.endsWith('__oid')) {
        // typeahead fields have an additional text field that needs to be copied
        const targetFieldTextInput = $(targetField).closest('.objectpicker-container').find('.typeahead[name^="typeahead_text_"]');
        const sourceFieldTextInput = $(sourceField).closest('.objectpicker-container').find('.typeahead[name^="typeahead_text_"]');
        targetFieldTextInput.typeahead('val', sourceFieldTextInput.typeahead('val'));
      }
    } else if (sourceField.tagName === 'SELECT') {
      const sourceValue = $(sourceField).selectpicker('val');
      if ($(targetField).find(`option[value="${sourceValue}"]`).length === 0) {
        $(targetField).append($(sourceField).find('option:selected').clone());
        $(targetField).prop('disabled', $(sourceField).prop('disabled'));
        $(targetField).selectpicker('refresh');
      }
      $(targetField).selectpicker('val', $(sourceField).selectpicker('val'));
    }
    $(targetField).trigger('change');
  }
  // update array ID prefixes to match the changed order of rows
  const sortedRowIndices = [];
  for (const row of tableBody.find('tr').not('.array-template')) {
    const rowPrefix = $(row).data('id-prefix');
    const rowIndex = (rowPrefix + '_').split('__').slice(-2)[0];
    sortedRowIndices.push(Number.parseInt(rowIndex));
  }
  updateArrayIDPrefixes(arrayContainer, sortedRowIndices);
}

/**
   * Handles array delete button events.
   * @param event a PointerEvent
   */
function arrayFormDeleteHandler (event) {
  const button = $(event.currentTarget);
  const arrayContainer = button.closest('[data-array-container]');
  const arrayPrefix = arrayContainer.data('id-prefix');
  if (arrayPrefix.includes('!')) {
    return;
  }
  window.arrayButtons.push(button.attr('id'));
  button.closest('[data-array-item]').remove();
  if (arrayContainer.data('array-container') === 'list') {
    const [addButton, _copyButtons, deleteButtons, _clearButton] = getArrayButtons(arrayContainer); // eslint-disable-line no-unused-vars
    // array has one more delete button than items because of the array template
    const numItems = deleteButtons.length - 1;
    if (numItems === 0) {
      addButton.parent().removeClass('col-md-offset-3');
    } else {
      deleteButtons.first().parent().parent().removeClass('col-md-offset-3');
    }
  }
  updateArrayButtonsEnabled(arrayContainer);
  updateArrayIDPrefixes(arrayContainer);
  clearUnusedConditions();
  setUpCalculations();
}

/**
   * Handle array clear button events.
   * @param event a PointerEvent
   */
function arrayFormClearHandler (event) {
  const button = $(event.currentTarget);
  const arrayContainer = button.closest('[data-array-container]');
  const arrayPrefix = arrayContainer.data('id-prefix');
  if (arrayPrefix.includes('!')) {
    return;
  }
  window.arrayButtons.push(button.attr('id'));
  arrayContainer.find('[data-array-item]:not(.array-template)').remove();
  if (arrayContainer.data('array-container') === 'list') {
    const [addButton, _copyButtons, deleteButtons, _clearButton] = getArrayButtons(arrayContainer); // eslint-disable-line no-unused-vars
    // array has one more delete button than items because of the array template
    const numItems = deleteButtons.length - 1;
    if (numItems === 0) {
      addButton.parent().removeClass('col-md-offset-3');
    } else {
      deleteButtons.first().parent().parent().removeClass('col-md-offset-3');
    }
  }
  updateArrayButtonsEnabled(arrayContainer);
  updateArrayIDPrefixes(arrayContainer);
  clearUnusedConditions();
  setUpCalculations();
}

/**
   * Handles array table add column button events.
   * @param event a PointerEvent
   */
function tableFormColAddHandler (event) {
  const button = $(event.currentTarget);
  const arrayContainer = button.closest('[data-array-container]');
  const arrayPrefix = arrayContainer.data('id-prefix');
  if (arrayPrefix.includes('!')) {
    return;
  }
  window.arrayButtons.push(button.attr('id'));

  // add new column to table header and footer
  updateTableFormHead(arrayContainer, +1);
  // add new column to all real rows
  const columnIndex = arrayContainer.find('> thead > tr > th').not('.control-buttons').length - 1;
  arrayContainer.find('> tbody > tr').not('[data-template-table-type]').each(function () {
    appendFieldToRow($(this), arrayContainer, $(this).data('row-id'), columnIndex);
  });

  updateArrayButtonsEnabled(arrayContainer);
  updateArrayIDPrefixes(arrayContainer);
  updateJSInteractiveFields();
}

/**
   * Handles array table delete column button events.
   * @param event a PointerEvent
   */
function tableFormColDeleteHandler (event) {
  const button = $(event.currentTarget);
  const arrayContainer = button.closest('[data-array-container]');
  const arrayPrefix = arrayContainer.data('id-prefix');
  if (arrayPrefix.includes('!')) {
    return;
  }
  window.arrayButtons.push(button.attr('id'));

  // remove column from all real rows
  arrayContainer.find('> tbody > tr').not('[data-template-table-type]').each(function () {
    $(this).children().not('.control-buttons').last().remove();
  });
  // remove column from table header and footer
  updateTableFormHead(arrayContainer, -1);

  updateArrayButtonsEnabled(arrayContainer);
  updateArrayIDPrefixes(arrayContainer);
  clearUnusedConditions();
  setUpCalculations();
}

/**
   * Handles array table add row button events.
   * @param event a PointerEvent
   */
function tableFormRowAddHandler (event) {
  const button = $(event.currentTarget);
  const arrayContainer = button.closest('[data-array-container]');
  const arrayPrefix = arrayContainer.data('id-prefix');
  if (arrayPrefix.includes('!')) {
    return;
  }
  window.arrayButtons.push(button.attr('id'));

  const existingRows = arrayContainer.find('> tbody > tr').not('.array-template');
  const templateRow = arrayContainer.find('> tbody > tr.array-template[data-template-table-type="row"]');
  const numHeaderCols = arrayContainer.find('> thead > tr > th').not('.control-buttons').length;

  const rowIndex = existingRows.length;
  const newRow = templateRow.clone();
  newRow.attr('data-row-id', rowIndex);
  newRow.removeClass('array-template');
  newRow.removeAttr('data-template-table-type');
  replaceIDPrefix(newRow.find('*').add(newRow), `${arrayPrefix}_!index${arrayContainer.data('template-order-index')}!_`, `${arrayPrefix}_${rowIndex}_`);
  updateArrayButtonsHandlerWithinElement(newRow);
  arrayContainer.find('> tbody').append(newRow);

  const numRowCols = newRow.find('> td').not('.control-buttons').length;
  if (numRowCols > numHeaderCols) {
    // the new row has more columns than the current table, e.g. because of the default number of columns
    // add new columns to table header and footer
    updateTableFormHead(arrayContainer, numRowCols - numHeaderCols);
    // add them to all previously existing rows (if any)
    for (let columnIndex = numHeaderCols; columnIndex < numRowCols; columnIndex++) {
      existingRows.each(function (_, row) {
        appendFieldToRow($(row), arrayContainer, $(row).data('row-id'), columnIndex);
      });
    }
  } else {
    // add columns to the new row until it has as many as all other real rows
    for (let columnIndex = numRowCols; columnIndex < numHeaderCols; columnIndex++) {
      appendFieldToRow(newRow, arrayContainer, rowIndex, columnIndex);
    }
  }

  updateArrayButtonsEnabled(arrayContainer);
  updateArrayIDPrefixes(arrayContainer);
  updateJSInteractiveFields();
}

/**
   * Handles array table delete row button events.
   * @param event a PointerEvent
   */
function tableFormRowDeleteHandler (event) {
  const button = $(event.currentTarget);
  const arrayContainer = button.closest('[data-array-container]');
  const arrayPrefix = arrayContainer.data('id-prefix');
  if (arrayPrefix.includes('!')) {
    return;
  }
  window.arrayButtons.push(button.attr('id'));

  // remove row containing the button
  button.closest('tr').remove();
  // remove all columns from table header and footer if this was the last real row
  if (arrayContainer.find('tbody > tr').not('.array-template').length === 0) {
    updateTableFormHead(arrayContainer, -arrayContainer.find('> thead > tr > th').not('.control-buttons').length);
  }

  updateArrayButtonsEnabled(arrayContainer);
  updateArrayIDPrefixes(arrayContainer);
  clearUnusedConditions();
  setUpCalculations();
}

/**
   * Handles array table clear button events.
   * @param event a PointerEvent
   */
function tableFormRowClearHandler (event) {
  const button = $(event.currentTarget);
  const arrayContainer = button.closest('[data-array-container]');
  const arrayPrefix = arrayContainer.data('id-prefix');
  if (arrayPrefix.includes('!')) {
    return;
  }
  window.arrayButtons.push(button.attr('id'));

  // remove row containing the button
  arrayContainer.find('tbody > tr').not('.array-template').remove();
  updateTableFormHead(arrayContainer, -arrayContainer.find('> thead > tr > th').not('.control-buttons').length);

  updateArrayButtonsEnabled(arrayContainer);
  updateArrayIDPrefixes(arrayContainer);
  clearUnusedConditions();
  setUpCalculations();
}

/**
   * Adds a new field to an array table row.
   * @param row a jQuery row element to add the field to
   * @param table a jQuery array table element
   * @param rowIndex the index of the row
   * @param columnIndex the index of the new column
   */
function appendFieldToRow (row, table, rowIndex, columnIndex) {
  const td = table.find('> tbody > tr.array-template[data-template-table-type="col"] > td').clone(true);
  td.removeClass('array-col-template');
  td.insertBefore(row.children().last());
  replaceTemplateIndex(td, `!index${table.data('template-order-index')}!`, rowIndex);
  replaceTemplateIndex(td, `${rowIndex}__!cindex${table.data('col-order-index')}!`, columnIndex);
}

/**
   * Updates array table header and footer.
   * @param table a jQuery array table element
   * @param diff how many columns to add (or remove) to the header/footer
   */
function updateTableFormHead (table, diff) {
  const headerRow = table.find('thead > tr');
  const footerRow = table.find('tfoot > tr');
  if (diff < 0) {
    for (let i = 0; i < -diff; i++) {
      headerRow.children().not('.control-buttons').last().remove();
      footerRow.children().not('.control-buttons').last().remove();
    }
  } else {
    const numColumns = headerRow.children().not('.control-buttons').length;
    for (let columnIndex = numColumns; columnIndex < numColumns + diff; columnIndex++) {
      const headerText = window.array_table_header_text.replace('INDEX_PLACEHOLDER', columnIndex + 1);
      headerRow.children().last().before($('<th>').text(headerText));
      footerRow.children().last().before($('<th>').text(headerText));
    }
  }
}

function insertFormData () {
  if (Object.keys(formData).length === 0) {
    return;
  }
  const initializedChoiceArrayPickers = [];

  $.each(formData, function (key, value) {
    const field = $(`[name="${key}"]`);
    if (field.length === 0) {
      if (!key.endsWith('__text')) {
        return;
      }
      const idPrefix = key.split('__').slice(0, -2).join('__') + '_';
      const choicepickerField = $(`[data-sampledb-choice-array="${idPrefix}"]`);
      if (choicepickerField.length === 0) {
        return;
      }
      if (!initializedChoiceArrayPickers.includes(idPrefix)) {
        initializedChoiceArrayPickers.push(idPrefix);
        choicepickerField.selectpicker('val', []);
      }
      choicepickerField.selectpicker('val', choicepickerField.selectpicker('val').concat([value]));
      return;
    }
    if (field.hasClass('objectpicker')) {
      field.data('sampledb-default-selected', value);
    } else if (field.hasClass('choicepicker')) {
      field.data('sampledb-default', value);
      field.selectpicker('val', value);
    } else if (field.parents('.date').length > 0) {
      field.val(value);
    } else if (field.hasClass('typeahead')) {
      field.attr('data-previous-data', value);
    } else if (field.data('markdown-textarea')) {
      field.text(value);
    }
    field.val(value);
    field.trigger('change');
  });

  $('[type="checkbox"]').each(function () {
    const name = $(this).attr('name');
    $(this).prop('checked', Object.prototype.hasOwnProperty.call(formData, name));
    $(this).trigger('change');
  });

  $('.selectpicker').selectpicker('refresh');
}

function showErrors () {
  const errors = window.getTemplateValue('errors');
  if (errors === null || Object.keys(errors).length === 0) {
    return;
  }

  $.each(formData, function (key, value) {
    if (Object.prototype.hasOwnProperty.call(errors, key)) {
      return;
    }
    const errorParent = $(`[name="${key}"]`).closest('.error-parent');
    errorParent.addClass('has-success');
  });

  $.each(errors, function (key, value) {
    const errorParent = $(`[name="${key}"]`).closest('.error-parent');
    if (errorParent.hasClass('has-success')) {
      errorParent.removeClass('has-success');
    }
    errorParent.addClass('has-error');
    errorParent.find('.error-note').html(`<strong>${window.getTemplateValue('translations.error')} </strong>${value}`);
  });
}

/**
   * Updates the enabled/disabled state of the buttons for an array container.
   * @param arrayContainer a jQuery array container element
   */
function updateArrayButtonsEnabled (arrayContainer) {
  if ($(arrayContainer).data('array-container') === 'array-table') {
    const numRows = arrayContainer.find('> tbody [data-object-form-button="table_row_delete"]').length - 1;
    const numColumns = arrayContainer.find('> thead > tr > th').not('.control-buttons').length;

    const minRows = arrayContainer.data('min-rows');
    const maxRows = arrayContainer.data('max-rows');
    const minColumns = arrayContainer.data('min-cols');
    const maxColumns = arrayContainer.data('max-cols');
    const isRequired = arrayContainer.data('is-required');

    const addColumnButton = arrayContainer.find('[data-object-form-button="table_col_add"]');
    const deleteColumnButton = arrayContainer.find('[data-object-form-button="table_col_delete"]');
    const addRowButton = arrayContainer.find('[data-object-form-button="table_row_add"]');
    const deleteRowButtons = arrayContainer.find('[data-object-form-button="table_row_delete"]');
    const clearButton = arrayContainer.find('[data-object-form-button="table_rows_clear"]');

    deleteRowButtons.prop('disabled', (numRows <= minRows) && (numRows !== 1 || isRequired));
    addRowButton.prop('disabled', maxRows !== -1 && numRows >= maxRows);
    clearButton.prop('disabled', (numRows === 0) || (isRequired && minRows > 0));

    if (numRows === 0) {
      // tables without rows also do not have columns
      addColumnButton.prop('disabled', true);
      deleteColumnButton.prop('disabled', true);
      updateTableFormHead(arrayContainer, -numColumns);
    } else {
      addColumnButton.prop('disabled', maxColumns !== -1 && numColumns >= maxColumns);
      deleteColumnButton.prop('disabled', numColumns <= minColumns);
    }
  } else {
    const [addButton, copyButtons, deleteButtons, clearButton] = getArrayButtons(arrayContainer);

    // array has one more delete button than items because of the array template
    const numItems = deleteButtons.length - 1;
    const minItems = arrayContainer.data('min-items');
    const maxItems = arrayContainer.data('max-items');
    const isRequired = arrayContainer.data('is-required');
    addButton.prop('disabled', maxItems !== -1 && numItems >= maxItems);
    copyButtons.prop('disabled', maxItems !== -1 && numItems >= maxItems);
    deleteButtons.prop('disabled', (numItems <= minItems) && (numItems !== 1 || isRequired));
    clearButton.prop('disabled', (numItems === 0) || (isRequired && minItems > 0));
  }
}

/**
   * Updates the enabled/disabled state of the buttons for all array containers within a given element.
   * @param element a jQuery element
   */
function updateArrayButtonsEnabledWithinElement (element) { // eslint-disable-line no-unused-vars
  element.find('[data-array-container]').each(function (_, arrayContainer) {
    updateArrayButtonsEnabled($(arrayContainer));
  });
}

function updateLanguageSelects (clone) {
  clone.find('select').each(function () {
    if ($(this).hasClass('select-language')) {
      $(this).on('changed.bs.select', function () {
        updateSelectLanguage(this);
      });

      updateSelectLanguage($(this));
    }
  });
}

/**
   * Initializes fields created as templates.
   */
function updateJSInteractiveFields () {
  const objectpickers = [];
  $('.template-select').each(function () {
    if ($(this).parents('.array-template').length === 0) {
      $(this).attr('class', $(this).data('template-class'));
      $(this).removeData('template-class');
      if ($(this).hasClass('objectpicker')) {
        objectpickers.push($(this));
      }
    }
  });

  $('.template-file-select').each(function () {
    if ($(this).parents('.array-template').length === 0) {
      const filePicker = $(this);
      const parent = filePicker.parent();
      const input = parent.find('input:file');
      const hasOptions = filePicker.children('option').length !== 0;
      filePicker.prop('disabled', !hasOptions);
      filePicker.attr('class', filePicker.data('template-class'));
      filePicker.selectpicker();
      input.change(fileEventHandler(input.data('context-id-token'), window.temporaryFileUploadURL));
    }
  });

  $('.template-typeahead-container').each(function () {
    if ($(this).parents('.array-template').length === 0) {
      $(this).removeClass('template-typeahead-container');
      $(this).addClass('objectpicker-container');
      const inputChild = $(this).find('.template-typeahead');
      inputChild.removeClass('template-typeahead');
      inputChild.addClass('typeahead');
    }
  });

  $('.date-template').each(function () {
    if ($(this).parents('.array-template').length === 0) {
      $(this).removeClass('date-template');
      $(this).addClass('date');
      $(this).datetimepicker({
        locale: window.currentUserLanguageCode,
        format: window.currentUserDatetimeFormat,
        date: $(this).attr('data-datetime'),
        timeZone: window.currentUserTimezone,
        showTodayButton: true
      });
    }
  });

  $('.objectpicker').each(function () {
    $(this).data('sampledb-default-selected', $(this).val());
  });

  updateObjectPickers();

  $.each(objectpickers, function () {
    if ($(this).closest('.error-parent').find('.objectpicker-filter-button').length === 0) {
      addActionFilterButton($(this).parents('.bootstrap-select'));
    }
  });

  $('.choicepicker').each(function () {
    if ($(this).parents('.array-template').length === 0) {
      if ($(this).data('sampledb-default')) {
        $(this).selectpicker('val', $(this).data('sampledb-default'));
        $(this).removeAttr('data-sampledb-default');
        $(this).removeData('sampledb-default');
      }
    }
  });

  $('[data-template-toggle="tooltip"]').each(function () {
    if ($(this).parents('.array-template').length === 0) {
      $(this).attr('data-toggle', $(this).attr('data-template-toggle'));
      $(this).removeAttr('data-template-toggle');
      $(this).removeData('template-toggle');
      $(this).tooltip();
    }
  });

  $('.selectpicker').selectpicker('refresh');
  $('[data-toggle="tooltip"]').tooltip('hide');
}

/**
   * Initialize markdown editor fields created as templates.
   */
function replaceMarkdownTemplates () {
  if (!window.initPhase) {
    $('.template-markdown-editor').each(function (_, element) {
      if ($(this).parents('.array-template').length === 0) {
        $(this).removeClass('template-markdown-editor');
        setupImageDragAndDrop(initMarkdownField(element, '100px'));
      }
    });
  }
}

function updateRecipeState (clone) {
  if (!clone.data('id-prefix')) {
    return;
  }
  const idPrefix = clone.data('id-prefix');
  const recipeDiv = $(`.div-apply-recipe[data-id-prefix=${idPrefix}]`);
  if (recipeDiv.length === 0) {
    return;
  }
  recipeDiv.attr('data-toggle', 'tooltip');
  recipeDiv.tooltip();
  const isTable = recipeDiv.closest('table').length > 0;
  const recipes = recipeDiv.data('sampledb-recipes');
  refreshRecipeTooltip(idPrefix, recipes);
  recipeDiv.children('select').first().on('change', function () {
    refreshRecipeTooltip(idPrefix, recipes);
  }).addClass('selectpicker').selectpicker();
  recipeDiv.children('button.input-group-button-for-selectpicker').first().on('click', function () {
    applyRecipe(idPrefix, recipes, isTable);
  });
}
