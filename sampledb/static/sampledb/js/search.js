'use strict';
/* eslint-env jquery */

$(function () {
  window.search_paths = window.getTemplateValue('search_paths.all');
  window.search_paths_by_action = window.getTemplateValue('search_paths.by_action');
  window.search_paths_by_action_type = window.getTemplateValue('search_paths.by_action_type');

  const searchForm = $('#form-search-standalone');
  const searchInput = searchForm.find('#search-field');
  const advancedSearchToggle = searchForm.find('input[name="advanced"]');

  /**
   * Set the correct search query placeholder depending on whether advanced search is used.
   */
  function handleAdvancedSearchToggle () {
    if ($(advancedSearchToggle).prop('checked')) {
      searchInput.attr('placeholder', window.getTemplateValue('translations.advanced_search'));
    } else {
      searchInput.attr('placeholder', window.getTemplateValue('translations.search'));
    }
  }
  advancedSearchToggle.on('change', handleAdvancedSearchToggle);

  const actionSelect = $('select[name="action"]');
  const actionTypeSelect = $('select[name="t"]');

  /**
   * Updates which actions are available to be selected.
   */
  function updateActionOptions () {
    actionSelect.find('option').show();
    actionSelect[0].disabled = false;
    if (actionTypeSelect.selectpicker('val')) {
      actionSelect.selectpicker('val', '');
      actionSelect.find('option[data-action-type-id!="' + actionTypeSelect.selectpicker('val') + '"][value!=""]').hide();
      if (actionSelect.find('option[data-action-type-id="' + actionTypeSelect.selectpicker('val') + '"]').length === 0) {
        actionSelect[0].disabled = true;
      }
    }
    actionSelect.selectpicker('refresh');
  }

  actionTypeSelect.change(updateActionOptions);

  /**
   * Returns the search query and state for a condition.
   * @param condition the condition jQuery element
   * @param searchPaths the enabled search paths
   * @returns {(string|{c: *, n: string})[]} the search query and state
   */
  function updateCondition (condition, searchPaths) {
    let propertyName = condition.find('.input-condition-property:visible').val();
    if (typeof propertyName === 'undefined') {
      propertyName = '';
    }
    if (!propertyName) {
      condition.find('.input-condition-property').closest('.form-group').addClass('has-error');
    } else {
      condition.find('.input-condition-property').closest('.form-group').removeClass('has-error');
    }
    condition.find('option').show();
    const selectpicker = condition.find('.input-condition-operator');
    if (propertyName in searchPaths) {
      const validOptions = [];
      const propertyTypes = searchPaths[propertyName].types;
      condition.find('option').each(function (_, option) {
        option = $(option);
        if ((propertyTypes.includes(option.data('type')) || option.data('type') === 'all') && (!option.data('property-name') || option.data('property-name') === propertyName)) {
          validOptions.push(option.val());
        } else {
          option.hide();
        }
      });
      if (!validOptions.includes(selectpicker.selectpicker('val'))) {
        selectpicker.selectpicker('val', validOptions[0]);
      }
    }
    selectpicker.selectpicker('refresh');
    const selectedCondition = condition.find('option:selected');
    const operator = selectedCondition.data('operator');
    const fieldName = selectedCondition.data('showField');
    const reverseOperator = selectedCondition.data('reverseOperator');
    const negateCondition = selectedCondition.data('negateCondition');
    const state = {
      n: propertyName,
      c: selectedCondition.attr('value')
    };
    let searchQuery = '';
    condition.find('.input-condition-field').closest('.form-group').hide();
    if (operator) {
      if (fieldName) {
        const operandField = condition.find('input.input-condition-' + fieldName + ', select.input-condition-' + fieldName);
        operandField.closest('.form-group').show();
        let operand;
        if (operandField[0].tagName === 'INPUT') {
          operand = operandField.val();
        } else if (operandField[0].tagName === 'SELECT') {
          // even though the select itself is hidden, the individual options must not be hidden or they will be excluded from the selectpicker
          operandField.find('option').show();
          operandField.selectpicker('refresh');
          operand = operandField.selectpicker('val');
        }
        state.f = operand;
        if (!operand && (fieldName === 'quantity' || fieldName === 'datetime')) {
          operandField.closest('.form-group').addClass('has-error');
        } else {
          operandField.closest('.form-group').removeClass('has-error');
        }
        if (fieldName === 'object_reference' || fieldName === 'user') {
          operand = '#' + operand;
        }
        if (fieldName === 'text') {
          operand = JSON.stringify(operand);
        }
        if (reverseOperator) {
          searchQuery = operand + ' ' + operator + ' ' + propertyName;
        } else {
          searchQuery = propertyName + ' ' + operator + ' ' + operand;
        }
        if (operator === '#' && propertyName === 'tags') {
          let validTag = '';
          for (const char of operand.toLowerCase()) {
            if ('abcdefghijklmnopqrstuvwxyz0123456789_-äöüß'.includes(char)) {
              validTag += char;
            }
          }
          searchQuery = operator + validTag;
        }
      } else {
        if (reverseOperator) {
          searchQuery = operator + ' ' + propertyName;
        } else {
          searchQuery = propertyName + ' ' + operator;
        }
      }
      if (negateCondition) {
        searchQuery = '!(' + searchQuery + ')';
      }
    } else {
      searchQuery = propertyName;
    }
    return [searchQuery, state];
  }

  /**
   * Updates search query based on the selected conditions.
   */
  function updateConditions () {
    const searchPaths = getCurrentSearchPaths();
    window.conditions = [];
    const subqueries = [];
    $('.advanced-search-condition').each(function (_, element) {
      const condition = $(element);
      if (!condition.attr('id')) {
        const conditionState = updateCondition(condition, searchPaths);
        subqueries.push(conditionState[0]);
        window.conditions.push(conditionState[1]);
      }
    });
    let searchQuery = '';
    if (subqueries.length === 1) {
      searchQuery = subqueries[0];
    } else if (subqueries.length > 1) {
      const joiningOperator = $('[name="c"]:checked').val();
      for (let i = 0; i < subqueries.length; i++) {
        if (i > 0) {
          searchQuery = searchQuery + ' ' + joiningOperator + ' ';
        }
        searchQuery = searchQuery + '(' + subqueries[i] + ')';
      }
    }
    $('#search-field').val(searchQuery);

    if ($('.advanced-search-condition').length > 2) {
      $('#advanced-search-join-and').closest('.form-group').show();
    } else {
      $('#advanced-search-join-and').closest('.form-group').hide();
    }

    updateHistory();
  }

  $('[name="c"]').change(function () {
    updateConditions();
  });

  // add a condition to the search query builder
  function addCondition () {
    const separator = $('.advanced-search-separator:last');
    const conditionTemplate = $('#advanced-search-condition-template');
    conditionTemplate.after(conditionTemplate.clone());
    conditionTemplate.before(separator.clone());
    $('#advanced-search-builder .advanced-search-separator + .advanced-search-separator').remove();
    $('.advanced-search-separator:not(:first):not(:last)').show();
    conditionTemplate.removeAttr('id');
    conditionTemplate.show();
    conditionTemplate.find('select.input-condition-operator').selectpicker();
    conditionTemplate.find('.input-group.date').each(function () {
      $(this).datetimepicker({
        format: 'YYYY-MM-DD',
        date: $(this).attr('data-datetime')
      });
      $(this).on('dp.change', function () {
        updateConditions();
      });
    });

    conditionTemplate.find('.input-condition-property').keydown(function (event) {
      if (event.keyCode === 13) {
        event.preventDefault();
        return false;
      }
    });

    const ta = conditionTemplate.find('.input-condition-property').typeahead({
      hint: true,
      highlight: true,
      minLength: 0
    }, {
      name: 'search_paths',
      limit: 10000,
      display: 'propertyName',
      source: substringMatcher(),
      templates: {
        suggestion: function (suggestion) {
          return '<span>' + suggestion.propertyName + ' – ' + suggestion.titles + '</span>';
        }
      }
    });
    updateConditions();

    ta.on('typeahead:change', function () {
      updateConditions();
    });
    ta.on('typeahead:select', function () {
      updateConditions();
    });

    conditionTemplate.find('select, input').change(function () {
      updateConditions();
    });

    conditionTemplate.find('.close').click(function () {
      conditionTemplate.remove();
      $('#advanced-search-builder .advanced-search-separator + .advanced-search-separator').remove();
      updateConditions();
    });
    return conditionTemplate;
  }

  // enable search query builder
  $('#button-use-builder').click(function () {
    addCondition();
    $('#advanced-search-builder').show();
    $('[name="advanced"]').prop('checked', 'checked');
    $('#button-use-builder').closest('.form-group').hide();
    $('#input-search-advanced').change();
  });

  window.conditions = [];
  // set URL whenever a field is changed
  function updateHistory () {
    const queryState = {
      q: $('#search-field').val(),
      action: $('[name="action"]').val(),
      t: $('[name="t"]').val(),
      c: $('[name="c"]:checked').val(),
      v: window.conditions
    };
    window.history.replaceState({}, '', '#' + encodeURIComponent(JSON.stringify(queryState)));
  }
  $('[name="t"], [name="action"], #search-field').change(function () {
    updateHistory();
  });

  // parse query state string from current URL and set up search query builder accordingly
  const queryStateString = window.location.hash.slice(1);
  if (queryStateString) {
    const queryState = JSON.parse(decodeURIComponent(queryStateString));
    $('#search-field').val(queryState.q);
    $('[name="action"]').selectpicker('val', queryState.action);
    $('[name="t"]').selectpicker('val', queryState.t);
    updateActionOptions();
    actionSelect.selectpicker('val', queryState.action);
    if (queryState.v.length > 0) {
      for (let i = 0; i < queryState.v.length; i++) {
        const condition = addCondition();
        condition.find('.input-condition-property').val(queryState.v[i].n);
        condition.find('.input-condition-operator').selectpicker('val', queryState.v[i].c);
        const selectedCondition = condition.find('option:selected');
        const fieldName = selectedCondition.data('showField');
        if (fieldName) {
          const field = condition.find('input.input-condition-' + fieldName + ', select.input-condition-' + fieldName);
          if (field[0].tagName === 'INPUT') {
            field.val(queryState.v[i].f);
          } else if (field[0].tagName === 'SELECT') {
            // even though the select itself is hidden, the individual options must not be hidden or they will be excluded from the selectpicker
            field.find('option').show();
            field.selectpicker('val', queryState.v[i].f);
            field.selectpicker('refresh');
          }
        }
      }
      $('#advanced-search-builder').show();
      $('[name="advanced"]').prop('checked', 'checked');
      $('#button-use-builder').closest('.form-group').hide();
    }
    if (queryState.c === 'or') {
      $("#advanced-search-builder [name='c'][value='or']").prop('checked', 'checked');
    } else {
      $("#advanced-search-builder [name='c'][value='and']").prop('checked', 'checked');
    }
    updateConditions();
  }

  // set event handler for add condition button
  $('#button-add-condition').click(addCondition);

  /**
   * Returns the search paths for the currently selected action or action type.
   * @returns {{}|*} search paths
   */
  function getCurrentSearchPaths () {
    const actionSelect = $('select[name="action"]');
    if (actionSelect.selectpicker('val')) {
      const selectedActionId = actionSelect.find('option:selected').data('actionId');
      if (selectedActionId in window.search_paths_by_action) {
        return window.search_paths_by_action[selectedActionId];
      } else {
        return {};
      }
    }
    const actionTypeSelect = $('select[name="t"]');
    if (actionTypeSelect.selectpicker('val')) {
      const selectedActionTypeId = actionTypeSelect.selectpicker('val');
      return window.search_paths_by_action_type[selectedActionTypeId];
    }
    return window.search_paths;
  }

  /**
   * Generates a substring match function for Bloodhound search for property names.
   * @returns {(function(*, *): void)|*} match function
   */
  function substringMatcher () {
    return function findMatches (q, cb) {
      const searchPaths = getCurrentSearchPaths();
      const propertyNames = Object.keys(searchPaths);
      const matches = [];
      const substrRegex = new RegExp(q, 'i');
      $.each(propertyNames, function (i, propertyName) {
        const titles = searchPaths[propertyName].titles.join(', ');
        if (substrRegex.test(propertyName) || substrRegex.test(titles)) {
          matches.push({
            propertyName,
            titles
          });
        }
      });
      cb(matches);
    };
  }
});
