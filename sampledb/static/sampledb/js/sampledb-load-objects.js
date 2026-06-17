'use strict';
/* eslint-env jquery */
/* global Bloodhound */

const objectpickerDatasets = {};
const objectPickerTemplatePlaceholder = 'PLACEHOLDER';
const manualObjectIDTextTemplate = window.getTemplateValue('translations.object_picker_use_id_text_template');
const escapedManualObjectIDTextTemplate = manualObjectIDTextTemplate.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const manualObjectIDTextRegex = new RegExp('^' + escapedManualObjectIDTextTemplate.replace(objectPickerTemplatePlaceholder, '0*([1-9][0-9]*)') + '$');
const externalObjectURLTemplate = window.getTemplateValue('external_object_url_template');
const escapedExternalObjectURLTemplate = externalObjectURLTemplate.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const objectURLRegex = new RegExp('^' + escapedExternalObjectURLTemplate.replace(objectPickerTemplatePlaceholder, '0*([1-9][0-9]*)') + '$');

/**
 * Converts IDs in various forms into an array of numbers.
 * @param ids IDs as comma-separated string, array, number, or undefined
 * @returns {number[]} an array of IDs
 */
function idsToArray (ids) {
  if (typeof ids === 'string') {
    ids = ids.split(',').filter(function (id) {
      return id !== '';
    });
    ids = $.map(ids, function (id) {
      return +id;
    });
  } else if (Array.isArray(ids)) {
    ids = ids.filter(function (id) {
      return id !== '';
    });
    ids = $.map(ids, function (id) {
      return +id;
    });
  } else if (typeof ids === 'undefined') {
    ids = [];
  } else {
    ids = [ids];
  }
  return ids;
}

/**
 * Extracts an object ID from a plain number, #number or object URL.
 * @param text user input
 * @returns {?number} the parsed object ID or null
 */
function getObjectIDFromObjectPickerText (text) {
  text = (text || '').trim();
  let match = text.match(/^#?0*([1-9][0-9]*)$/);
  if (match !== null) {
    return Number.parseInt(match[1]);
  }
  match = text.match(manualObjectIDTextRegex);
  if (match !== null) {
    return Number.parseInt(match[1]);
  }
  match = text.match(objectURLRegex);
  if (match !== null) {
    return Number.parseInt(match[1]);
  }
  return null;
}

function escapeHTMLAttribute (text) {
  return (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function findSelectpickerMenuOption (menu, option) {
  let menuOption = menu.find('li[data-original-index="' + option.index() + '"]').first();
  if (menuOption.length === 0) {
    const optionText = option.text().trim();
    menuOption = menu.find('li').filter(function () {
      return $(this).find('.text').text().trim() === optionText;
    }).first();
  }
  return menuOption;
}

function objectHasID (object, objectID) {
  return Number.parseInt(object.id) === objectID;
}

function getExternalObjectURLTokens (objectID) {
  return [externalObjectURLTemplate.replace(objectPickerTemplatePlaceholder, objectID)];
}

function getSelectpickerObjectTokens (object) {
  const tokens = [object.text, '#' + object.id, '' + object.id];
  for (const tag of object.tags) {
    tokens.push('#' + tag);
  }
  tokens.push.apply(tokens, getExternalObjectURLTokens(object.id));
  return tokens.map(escapeHTMLAttribute).join(' ');
}

function updateSelectpickerManualObjectIDOption (selectpicker, query) {
  const objectID = getObjectIDFromObjectPickerText(query);
  const manualOption = selectpicker.find('option[data-sampledb-manual-object-id="true"]');
  const removedManualOption = manualOption.length !== 0 && (objectID === null || manualOption.val() !== '' + objectID);
  if (removedManualOption) {
    manualOption.remove();
  }
  if (objectID === null) {
    return removedManualOption;
  }
  const manualOptionTokens = '#' + objectID + ' ' + objectID + ' ' + escapeHTMLAttribute(query);
  if (selectpicker.find('option[data-sampledb-manual-object-id="true"][value="' + objectID + '"]').length !== 0) {
    const tokensChanged = manualOption.attr('data-tokens') !== manualOptionTokens;
    manualOption.attr('data-tokens', manualOptionTokens);
    return tokensChanged;
  }
  if (selectpicker.find('option:not([data-sampledb-manual-object-id="true"])[value="' + objectID + '"]:not(:disabled)').length !== 0) {
    return removedManualOption;
  }
  selectpicker.append(
    '<option value="' + objectID + '" data-sampledb-manual-object-id="true" data-icon="fa fa-hashtag" data-tokens="' + manualOptionTokens + '">' +
    window.getTemplateValue('translations.object_picker_use_id_text_template').replace(objectPickerTemplatePlaceholder, objectID) +
    '</option>'
  );
  return true;
}

function renderSelectpickerManualObjectIDResult (selectpicker, query) {
  const objectID = getObjectIDFromObjectPickerText(query);
  const bootstrapSelect = selectpicker.parents('.bootstrap-select').first();
  const menu = bootstrapSelect.find('.dropdown-menu.inner').first();
  const manualOption = selectpicker.find('option[data-sampledb-manual-object-id="true"]');
  menu.find('.sampledb-object-id-search-icon').remove();
  if (manualOption.length !== 0 && (objectID === null || manualOption.val() !== '' + objectID)) {
    findSelectpickerMenuOption(menu, manualOption).remove();
  }
  if (objectID === null) {
    return;
  }
  const existingOption = selectpicker.find('option:not([data-sampledb-manual-object-id="true"])[value="' + objectID + '"]:not(:disabled)');
  if (existingOption.length !== 0) {
    const existingMenuOption = findSelectpickerMenuOption(menu, existingOption);
    if (existingMenuOption.length !== 0) {
      existingMenuOption.find('.text').first().prepend('<i class="fa fa-hashtag fa-fw sampledb-object-id-search-icon"></i> ');
      menu.find('.no-results').remove();
      return;
    }
    return;
  }
  if (manualOption.length !== 0) {
    menu.find('.no-results').remove();
  }
}

$(function () {
  const objectpickers = $('[data-sampledb-default-selected], [data-sampledb-remove]');
  if (objectpickers.length > 0) {
    objectpickers.prop('disabled', 'true');
    let minimumPermissions = 4;
    const actionIDsHelper = {};
    objectpickers.each(function () {
      const $x = $(this);
      if ($x.prop('tagName') === 'SELECT') {
        if (!$x.hasClass('template-select') && !$x.hasClass('template-typeahead')) {
          $x.selectpicker('refresh');
        }
      } else {
        $x.closest('.objectpicker-container').find('input[type="hidden"]').trigger('object_change.sampledb'); // Replacing loaded.bs.select for typeahead condition validation
      }
      const perm = $x.data('sampledbRequiredPerm') || 1;
      minimumPermissions = minimumPermissions < perm ? minimumPermissions : perm;
      const validActionIDs = idsToArray($x.data('sampledbValidActionIds'));
      if (validActionIDs.length > 0) {
        for (const actionID of validActionIDs) {
          actionIDsHelper[actionID] = true;
        }
      } else {
        actionIDsHelper[-1] = true;
      }

      $($x.data('sampledbStartEnable')).prop('disabled', false);
      $($x.data('sampledbStartDisable')).prop('disabled', true);
      $($x.data('sampledbStartShow')).show();
      $($x.data('sampledbStartHide')).hide();
    });

    const actionIDs = [];
    for (const actionID in actionIDsHelper) {
      actionIDs.push(Number.parseInt(actionID));
    }
    const data = {
      required_perm: minimumPermissions,
      action_ids: JSON.stringify(actionIDs)
    };

    $.get({
      url: window.getTemplateValue('application_root_path') + 'objects/referencable',
      data,
      json: true
    }, function (data) {
      window.referencable_objects = data.referencable_objects;
      updateObjectPickers();

      $('.typeahead').filter('[data-previous-data]').each(function () {
        $(this).typeahead('val', $(this).data('previous-data'));
      });
    });
  }
});

/**
 * Updates all uninitialized non-template object pickers.
 */
function updateObjectPickers () {
  if (!window.referencable_objects) {
    return;
  }
  const referencableObjects = window.referencable_objects;
  $('[data-sampledb-default-selected], [data-sampledb-remove]').not('.template-select').not('.template-typeahead').not('[data-objects-initialized]').each(function (x) {
    const $x = $(this);
    $x.attr('data-objects-initialized', 'true');
    const isSelectpicker = ($x.prop('tagName') === 'SELECT');
    const actionIDs = idsToArray($x.data('sampledbValidActionIds'));
    const requiredPermissions = $x.data('sampledbRequiredPerm') || 1;
    const idsToRemove = idsToArray($x.data('sampledbRemove'));
    const objectsToAdd = referencableObjects
      .filter(function (el) {
        return el.max_permission >= requiredPermissions && $.inArray(el.id, idsToRemove) === -1;
      }).filter(function (el) {
        return actionIDs.length === 0 || $.inArray(el.action_id, actionIDs) !== -1;
      });
    if (isSelectpicker) {
      $x.find('option[value != ""][value != "-1"]').remove();
      $x.append(
        objectsToAdd.map(function (el) {
          let isFederationImported = ' ';
          if (el.is_fed) {
            isFederationImported = ' data-icon="fa fa-share-alt" ';
          }
          let isELNImported = ' ';
          if (el.is_eln_imported) {
            isELNImported = ' data-icon="fa fa-file-archive-o" ';
          }
          return '<option' + isFederationImported + isELNImported + 'value="' + el.id + '" data-tokens="' + getSelectpickerObjectTokens(el) + '" data-action-id="' + el.action_id + '" data-version-id="' + el.version_id + '">' + el.text + '</option>';
        }).join(''));
      $x.on('shown.bs.select', function () {
        const bootstrapSelect = $x.parents('.bootstrap-select').first();
        const searchInput = bootstrapSelect.find('.bs-searchbox input');
        searchInput.off('input.sampledb-manual-object-id').on('input.sampledb-manual-object-id', function () {
          const query = $(this).val();
          window.setTimeout(function () {
            if (updateSelectpickerManualObjectIDOption($x, query)) {
              $x.selectpicker('refresh');
              $x.parents('.bootstrap-select').first().find('.bs-searchbox input').val(query).trigger('input');
              return;
            }
            renderSelectpickerManualObjectIDResult($x, query);
          }, 0);
        });
      });
    } else {
      $x.typeahead('destroy');
      const bloodhound = new Bloodhound({
        datumTokenizer: function (item) {
          const tokens = new Set([]);
          Bloodhound.tokenizers.whitespace(item.unescaped_text).forEach(function (token) {
            tokens.add(token);
            // search by substrings (except for ID)
            if (token !== '(#' + item.id + ')') {
              for (let i = 1; i < token.length - 1; i++) {
                tokens.add(token.substring(i, token.length));
              }
            }
          });
          // search by ID
          tokens.add('#' + item.id);
          tokens.add('' + item.id);
          // search tags
          tokens.add.apply(tokens, item.tags);
          return Array.from(tokens);
        },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        local: objectsToAdd,
        identify: function (item) { return item.unescaped_text; }
      });
      const source = function (q, sync) {
        const syncWrap = function (results) {
          const objectID = getObjectIDFromObjectPickerText(q);
          $x.num_results = results.length;
          $x.num_manual_results = 0;
          if (objectID !== null) {
            const objectIDResult = objectsToAdd.find(function (object) {
              return objectHasID(object, objectID);
            });
            results = results.filter(function (object) {
              return !objectHasID(object, objectID);
            });
            if (objectIDResult !== undefined) {
              results.unshift(objectIDResult);
            } else {
              const manualObjectIDText = manualObjectIDTextTemplate.replace(objectPickerTemplatePlaceholder, objectID);
              results.unshift({
                text: manualObjectIDText,
                unescaped_text: manualObjectIDText,
                object_id: objectID,
                is_fed: false,
                is_eln_imported: false,
                is_manual_object_id: true
              });
              $x.num_manual_results = 1;
            }
          }
          if ($x.data('sampledbDefaultSelected') === -1) {
            results.unshift({
              text: $x.data('sampledbCurrentValueText').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;'),
              unescaped_text: $x.data('sampledbCurrentValueText'),
              is_fed: $x.data('sampledbCurrentValueIsFed') === true,
              is_eln_imported: false
            });
          }
          if (!$x.prop('required')) {
            // add placeholder for not selecting an object
            results.unshift({
              text: null,
              is_fed: false,
              is_eln_imported: false
            });
          }
          sync(results);
        };
        if (q === '') {
          syncWrap(bloodhound.all()); // This is the only change needed to get 'ALL' items as the defaults
        } else {
          bloodhound.search(q, syncWrap);
        }
      };
      const objectPickerLimit = window.getTemplateValue('typeahead_object_limit');
      const dataset = {
        name: 'object_picker',
        source,
        limit: ((objectPickerLimit === null || objectPickerLimit < 1) ? 'Infinity' : objectPickerLimit + (!$x.prop('required') ? 1 : 0)),
        display: function (item) {
          return item.unescaped_text;
        },
        templates: {
          suggestion: function (data) {
            if (data.text === null) {
              return '<div>—</div>';
            }
            if (data.is_manual_object_id) {
              return '<div><i class="fa fa-hashtag fa-fw" style="margin-left: -1.43571429em; margin-right:0.15em;"></i>' + data.text + '</div>';
            }
            if (data.is_fed) {
              return '<div><i class="fa fa-share-alt fa-fw" style="margin-left: -1.43571429em; margin-right:0.15em;"></i>' + data.text + '</div>';
            } else if (data.is_eln_imported) {
              return '<div><i class="fa fa-file-archive-o fa-fw" style="margin-left: -1.43571429em; margin-right:0.15em;"></i>' + data.text + '</div>';
            } else {
              return '<div>' + data.text + '</div>';
            }
          },
          header: function (context) {
            const numResultsTotal = $x.num_results;
            let numResultsShown = context.suggestions.length;
            const query = $x.typeahead('val');
            numResultsShown -= $x.num_manual_results || 0;
            if (!$x.prop('required')) {
              // the placeholder for not selecting an object does not count
              numResultsShown -= 1;
            }
            let headerTextTemplate = '';
            if (numResultsShown === 0) {
              if (query === '') {
                headerTextTemplate = window.getTemplateValue('translations.object_picker_no_results_text_template_no_query');
              } else {
                headerTextTemplate = window.getTemplateValue('translations.object_picker_no_results_text_template');
              }
            } else if (numResultsShown === numResultsTotal) {
              if (query === '') {
                headerTextTemplate = window.getTemplateValue('translations.object_picker_all_results_text_template_no_query');
              } else {
                headerTextTemplate = window.getTemplateValue('translations.object_picker_all_results_text_template');
              }
            } else {
              if (query === '') {
                headerTextTemplate = window.getTemplateValue('translations.object_picker_some_results_text_template_no_query');
              } else {
                headerTextTemplate = window.getTemplateValue('translations.object_picker_some_results_text_template');
              }
            }
            const headerText = headerTextTemplate.replace('PLACEHOLDER1', numResultsShown).replace('PLACEHOLDER2', numResultsTotal);
            const header = $('<div class="tt-header">' + headerText + '</div>');
            header.find('.objectpicker-button-clear').on('click', function (event) { objectpickerClear(this, event); });
            header.find('.objectpicker-button-show-all').on('click', function (event) { objectpickerShowAll(this, event); });
            header.find('.query-container').text(query);
            return header;
          },
          empty: function (context) {
            const query = $x.typeahead('val');
            let emptyTextTemplate = '';
            if (query === '') {
              emptyTextTemplate = window.getTemplateValue('translations.object_picker_no_results_text_template_no_query');
            } else {
              emptyTextTemplate = window.getTemplateValue('translations.object_picker_no_results_text_template');
            }
            const emptyText = emptyTextTemplate;
            const empty = $('<div class="tt-header">' + emptyText + '</div>');
            empty.find('.query-container').text(query);
            return empty;
          }
        }
      };
      objectpickerDatasets[$x.closest('.objectpicker-container').find('input[type=hidden]')[0].name] = dataset;
      $x.typeahead(
        {
          hint: true,
          highlight: true,
          minLength: 0
        },
        dataset
      );
      const changeHandler = function (event) {
        $x.blur();
        const field = $(event.currentTarget);
        const text = field.typeahead('val');
        let isValid = false;
        let objectID = null;
        if (text) {
          if (text === $x.data('sampledbCurrentValueText')) {
            objectID = -1;
            isValid = true;
          } else {
            for (const object of objectsToAdd) {
              if (object.unescaped_text === text) {
                objectID = object.id;
                isValid = true;
                break;
              }
            }
            if (!isValid) {
              const selectedObjectID = field.data('sampledbSelectedManualObjectID');
              if (typeof selectedObjectID !== 'undefined') {
                const selectedObjectIDText = manualObjectIDTextTemplate.replace(objectPickerTemplatePlaceholder, selectedObjectID);
                if (text === selectedObjectIDText) {
                  objectID = selectedObjectID;
                  isValid = true;
                }
              }
            }
          }
        } else if (!field.prop('required')) {
          isValid = true;
          objectID = '';
        }
        const formGroup = field.closest('.form-group');
        const objectHiddenInput = field.closest('.objectpicker-container').find('input[type="hidden"]');
        if (isValid) {
          field[0].setCustomValidity('');
          formGroup.removeClass('has-error');
          formGroup.find('.error-note').first().text('');
          objectHiddenInput.val(objectID);
        } else {
          field[0].setCustomValidity(window.getTemplateValue('translations.object_picker_select_text'));
          formGroup.addClass('has-error');
          formGroup.find('.error-note').first().text('').first().text(window.getTemplateValue('translations.object_picker_select_text'));
          objectHiddenInput.val('');
        }
        objectHiddenInput.trigger('object_change.sampledb'); // event to trigger object conditions evaluation if registered
      };
      $x.on('typeahead:selected', function (_event, suggestion) {
        if (suggestion.is_manual_object_id) {
          $x.data('sampledbSelectedManualObjectID', suggestion.object_id);
        } else {
          $x.removeData('sampledbSelectedManualObjectID');
        }
      });
      $x.on('typeahead:selected', changeHandler);
      $x.on('change', changeHandler);
    }
    if (!$x.data('sampledbDisabledByConditions') || $x.data('sampledbDisabledByConditions').length === 0) {
      $x.prop('disabled', false);
    }

    $($x.data('sampledbStopEnable')).prop('disabled', false);
    $($x.data('sampledbStopDisable')).prop('disabled', true);
    $($x.data('sampledbStopShow')).show();
    $($x.data('sampledbStopHide')).hide();
    if (objectsToAdd.length !== 0) {
      $($x.data('sampledbNonemptyEnable')).prop('disabled', false);
      $($x.data('sampledbNonemptyDisable')).prop('disabled', true);
      $($x.data('sampledbNonemptyShow')).show();
      $($x.data('sampledbNonemptyHide')).hide();
    } else {
      $($x.data('sampledbEmptyEnable')).prop('disabled', false);
      $($x.data('sampledbEmptyDisable')).prop('disabled', true);
      $($x.data('sampledbEmptyShow')).show();
      $($x.data('sampledbEmptyHide')).hide();
    }

    const data = $x.data('sampledbDefaultSelected');
    const defaultObjectID = getObjectIDFromObjectPickerText('#' + data);
    if (isSelectpicker && defaultObjectID !== null) {
      updateSelectpickerManualObjectIDOption($x, '#' + defaultObjectID);
    }
    $x.selectpicker('refresh');
    if (typeof (data) !== 'undefined' && data !== 'None') {
      if (isSelectpicker) {
        $x.selectpicker('val', defaultObjectID !== null ? '' + defaultObjectID : data);
      } else {
        if (data === -1) {
          $x.typeahead('val', $x.data('sampledbCurrentValueText'));
        } else {
          const defaultObject = objectsToAdd.find(function (object) {
            return objectHasID(object, defaultObjectID);
          });
          if (defaultObject !== undefined) {
            $x.typeahead('val', defaultObject.unescaped_text);
            $x.removeData('sampledbSelectedManualObjectID');
          } else if (defaultObjectID !== null) {
            $x.data('sampledbSelectedManualObjectID', defaultObjectID);
            $x.typeahead('val', manualObjectIDTextTemplate.replace(objectPickerTemplatePlaceholder, defaultObjectID));
          }
        }
      }
    } else {
      if (isSelectpicker) {
        $x.selectpicker('val', null);
      } else {
        $x.typeahead('val', '');
      }
    }
    if (!isSelectpicker) {
      $x.closest('.objectpicker-container').find('input[type="hidden"]').trigger('object_change.sampledb'); // event to trigger object conditions evaluation if registered
    }
  });
}

/**
 * Shows all objects for a typehead object picker.
 * @param button the "Show All" button that was pressed
 * @param event the event
 */
function objectpickerShowAll (button, event) {
  const objectpickerContainer = $(button).closest('.objectpicker-container');
  const objectpicker = objectpickerContainer.find('.typeahead.tt-input');
  const name = objectpickerContainer.find('input[type=hidden]')[0].name;
  const dataset = objectpickerDatasets[name];
  dataset.limit = 'Infinity';
  objectpicker.typeahead('destroy');
  objectpicker.typeahead(
    {
      hint: true,
      highlight: true,
      minLength: 0
    },
    dataset
  );
  objectpicker.focus();
  event.preventDefault();
  event.stopPropagation();
}

/**
 * Clears the input for a typehead object picker.
 * @param button the "Clear" button that was pressed
 * @param event the event
 */
function objectpickerClear (button, event) {
  const objectpickerContainer = $(button).closest('.objectpicker-container');
  const objectpicker = objectpickerContainer.find('.typeahead.tt-input');
  objectpicker.typeahead('val', '');
  event.preventDefault();
  event.stopPropagation();
}

export {
  updateObjectPickers
};
