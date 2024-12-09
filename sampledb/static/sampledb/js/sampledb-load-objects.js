'use strict';
/* eslint-env jquery */
/* global Bloodhound */

const objectpickerDatasets = {};

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
          let dataTokens = '';
          if (el.tags.length) {
            dataTokens = 'data-tokens="';
            for (const tag of el.tags) {
              dataTokens += '#' + tag + ' ';
            }
            dataTokens += el.text + '"';
          }
          let isFederationImported = ' ';
          if (el.is_fed) {
            isFederationImported = ' data-icon="fa fa-share-alt" ';
          }
          let isELNImported = ' ';
          if (el.is_eln_imported) {
            isELNImported = ' data-icon="fa fa-file-archive-o" ';
          }
          return '<option' + isFederationImported + isELNImported + 'value="' + el.id + '" ' + dataTokens + ' data-action-id="' + el.action_id + '">' + el.text + '</option>';
        }).join(''));
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
          $x.num_results = results.length;
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

    $x.selectpicker('refresh');
    const data = $x.data('sampledbDefaultSelected');
    if (typeof (data) !== 'undefined' && data !== 'None') {
      if (isSelectpicker) {
        $x.selectpicker('val', data);
      } else {
        if (data === -1) {
          $x.typeahead('val', $x.data('sampledbCurrentValueText'));
        } else {
          for (const object of objectsToAdd) {
            if (object.id === data) {
              $x.typeahead('val', object.unescaped_text);
              break;
            }
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
