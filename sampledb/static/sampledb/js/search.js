$(function () {
  window.search_paths = window.template_values.search_paths.all;
  window.search_paths_by_action = window.template_values.search_paths.by_action;
  window.search_paths_by_action_type = window.template_values.search_paths.by_action_type;

  var search_form = $('#form-search-standalone');
  var search_input = search_form.find('#search-field');
  var advanced_search_toggle = search_form.find('input[name=advanced]');
  function handle_advanced_search_toggle() {
    if ($(this).prop('checked')) {
      search_input.attr('placeholder', window.template_values.translations.advanced_search);
    } else {
      search_input.attr('placeholder', window.template_values.translations.search);
    }
  }
  advanced_search_toggle.on('change', handle_advanced_search_toggle);
  handle_advanced_search_toggle.bind(advanced_search_toggle)();

  var action_select = $('select[name="action"]');
  var action_type_select = $('select[name="t"]');

  function updateActionOptions() {
    action_select.find('option').show();
    action_select[0].disabled = false;
    if (action_type_select.selectpicker('val')) {
      action_select.selectpicker('val', '');
      action_select.find('option[data-action-type-id!="' + action_type_select.selectpicker('val') + '"][value!=""]').hide();
      if (action_select.find('option[data-action-type-id="' + action_type_select.selectpicker('val') + '"]').length == 0) {
        action_select[0].disabled = true;
      }
    }
    action_select.selectpicker('refresh');
  }

  action_type_select.change(updateActionOptions);

  function updateCondition(condition, search_paths) {
    var property_name = condition.find('.input-condition-property:visible').val();
    if (typeof property_name === "undefined") {
      property_name = "";
    }
    if (!property_name) {
      condition.find('.input-condition-property').closest('.form-group').addClass('has-error');
    } else {
      condition.find('.input-condition-property').closest('.form-group').removeClass('has-error');
    }
    condition.find('option').show();
    var selectpicker = condition.find('.input-condition-operator');
    if (property_name in search_paths) {
      var valid_options = [];
      var property_types = search_paths[property_name].types;
      condition.find('option').each(function(_, option) {
        option = $(option);
        if ((property_types.includes(option.data('type')) || option.data('type') === 'all') && (!option.data('property-name') || option.data('property-name') === property_name)) {
          valid_options.push(option.val());
        } else {
          option.hide();
        }
      });
      if (!valid_options.includes(selectpicker.selectpicker('val'))) {
        selectpicker.selectpicker('val', valid_options[0]);
      }
    }
    selectpicker.selectpicker('refresh');
    var selected_condition = condition.find('option:selected');
    var operator = selected_condition.data('operator');
    var field_name = selected_condition.data('showField');
    var reverse_operator = selected_condition.data('reverseOperator');
    var negate_condition = selected_condition.data('negateCondition');
    var state = {
      'n': property_name,
      'c': selected_condition.attr('value')
    };
    var search_query = "";
    condition.find('.input-condition-field').closest('.form-group').hide();
    if (operator) {
      if (field_name) {
        var operand_field = condition.find('input.input-condition-' + field_name + ', select.input-condition-' + field_name);
        operand_field.closest('.form-group').show();
        let operand = undefined;
        if (operand_field[0].tagName === 'INPUT') {
            operand = operand_field.val();
        } else if (operand_field[0].tagName === 'SELECT') {
            // even though the select itself is hidden, the individual options must not be hidden or they will be excluded from the selectpicker
            operand_field.find('option').show();
            operand_field.selectpicker('refresh');
            operand = operand_field.selectpicker('val');
        }
        state['f'] = operand;
        if (!operand && (field_name === "quantity" || field_name === "datetime")) {
          operand_field.closest('.form-group').addClass('has-error');
        } else {
          operand_field.closest('.form-group').removeClass('has-error');
        }
        if (field_name === "object_reference" || field_name === "user") {
            operand = "#" + operand;
        }
        if (field_name === "text") {
          operand = JSON.stringify(operand);
        }
        if (reverse_operator) {
          search_query = operand + " " + operator + " " + property_name;
        } else {
          search_query = property_name + " " + operator + " " + operand;
        }
        if (operator === "#" && property_name === "tags") {
          let valid_tag = "";
          for (const char of operand.toLowerCase()) {
            if ("abcdefghijklmnopqrstuvwxyz0123456789_-äöüß".includes(char)) {
              valid_tag += char;
            }
          }
          search_query = operator + valid_tag;
        }
      } else {
        if (reverse_operator) {
          search_query = operator + " " + property_name;
        } else {
          search_query = property_name + " " + operator;
        }
      }
      if (negate_condition) {
        search_query = "!("+ search_query + ")";
      }
    } else {
      search_query = property_name;
    }
    return [search_query, state];
  }

  function updateConditions() {
    var search_paths = getCurrentSearchPaths();
    window.conditions = [];
    var subqueries = [];
    $('.advanced-search-condition').each(function(_, element) {
      var condition = $(element);
      if (!condition.attr('id')) {
        var condition_state = updateCondition(condition, search_paths);
        subqueries.push(condition_state[0]);
        window.conditions.push(condition_state[1]);
      }
    });
    var search_query = "";
    if (subqueries.length === 1) {
      search_query = subqueries[0];
    } else if (subqueries.length > 1) {
      var joining_operator = $('[name="c"]:checked').val();
      for (var i = 0; i < subqueries.length; i++) {
        if (i > 0) {
          search_query = search_query + " " + joining_operator + " ";
        }
        search_query = search_query + "(" + subqueries[i] + ")";
      }
    }
    $('#search-field').val(search_query);

    if ($('.advanced-search-condition').length > 2) {
      $('#advanced-search-join-and').closest('.form-group').show();
    } else {
      $('#advanced-search-join-and').closest('.form-group').hide();
    }

    updateHistory();
  }

  $('[name="c"]').change(function() {
    updateConditions();
  });

  function addCondition() {
    var separator = $('.advanced-search-separator:last');
    var condition_template = $('#advanced-search-condition-template');
    condition_template.after(condition_template.clone());
    condition_template.before(separator.clone());
    $('#advanced-search-builder .advanced-search-separator + .advanced-search-separator').remove();
    $('.advanced-search-separator:not(:first):not(:last)').show();
    condition_template.removeAttr('id');
    condition_template.show();
    condition_template.find('select.input-condition-operator').selectpicker();
    condition_template.find('.input-group.date').each(function() {
      $(this).datetimepicker({
        format: 'YYYY-MM-DD',
          date: $(this).attr('data-datetime'),
      });
      $(this).on('dp.change', function() {
        updateConditions();
      });
    });

    condition_template.find('.input-condition-property').keydown(function(event){
      if(event.keyCode === 13) {
        event.preventDefault();
        return false;
      }
    });

    var ta = condition_template.find('.input-condition-property').typeahead({
      hint: true,
      highlight: true,
      minLength: 0,
    }, {
      name: 'search_paths',
      limit: 10000,
      display: 'property_name',
      source: substringMatcher(),
        templates: {
            suggestion: function (suggestion) {
                return "<span>" + suggestion.property_name + " – " + suggestion.titles + "</span>";
            },
        }
    });
    updateConditions();

    ta.on('typeahead:change', function() {
      updateConditions();
    });
    ta.on('typeahead:select', function() {
      updateConditions();
    });

    condition_template.find('select, input').change(function() {
      updateConditions();
    });

    condition_template.find('.close').click(function() {
      condition_template.remove();
      $('#advanced-search-builder .advanced-search-separator + .advanced-search-separator').remove();
      updateConditions();
    });
    return condition_template;
  }

  $('#button-use-builder').click(function () {
    addCondition();
    $('#advanced-search-builder').show();
    $('[name="advanced"]').prop('checked', 'checked');
    $('#button-use-builder').closest('.form-group').hide();
    $('#input-search-advanced').change();
  });

  window.conditions = [];
  function updateHistory() {
    var query_state = {
      'q': $('#search-field').val(),
      'action': $('[name="action"]').val(),
      't': $('[name="t"]').val(),
      'c': $('[name="c"]:checked').val(),
      'v': window.conditions
    }
    window.history.replaceState({}, '', '#' + encodeURIComponent(JSON.stringify(query_state)));
  }
  $('[name="t"], [name="action"], #search-field').change(function() {
    updateHistory();
  });

  var query_state = window.location.hash.substr(1);
  if (query_state) {
    query_state = JSON.parse(decodeURIComponent(query_state));
    $('#search-field').val(query_state['q']);
    $('[name="action"]').selectpicker('val', query_state['action']);
    $('[name="t"]').selectpicker('val', query_state['t']);
    updateActionOptions();
    action_select.selectpicker('val', query_state['action']);
    if (query_state['v'].length > 0) {
      for (var i = 0; i < query_state['v'].length; i++) {
        var condition = addCondition();
        condition.find('.input-condition-property').val(query_state['v'][i]['n']);
        condition.find('.input-condition-operator').selectpicker('val', query_state['v'][i]['c']);
        var selected_condition = condition.find('option:selected');
        var field_name = selected_condition.data('showField');
        if (field_name) {
          var field = condition.find('input.input-condition-' + field_name + ', select.input-condition-' + field_name);
          if (field[0].tagName === 'INPUT') {
              field.val(query_state['v'][i]['f']);
          } else if (field[0].tagName === 'SELECT') {
              // even though the select itself is hidden, the individual options must not be hidden or they will be excluded from the selectpicker
              field.find('option').show();
              field.selectpicker('val', query_state['v'][i]['f']);
              field.selectpicker('refresh');
          }
        }
      }
      $('#advanced-search-builder').show();
      $('[name="advanced"]').prop('checked', 'checked');
      $('#button-use-builder').closest('.form-group').hide();
    }
    if (query_state['c'] === 'or') {
      $("#advanced-search-builder [name='c'][value='or']").prop("checked", "checked");
    } else {
      $("#advanced-search-builder [name='c'][value='and']").prop("checked", "checked");
    }
    updateConditions();
  }
  $('#button-add-condition').click(addCondition);

  function getCurrentSearchPaths() {
    var action_select = $('select[name="action"]');
    if (action_select.selectpicker('val')) {
      var selected_action_id = action_select.find('option:selected').data('actionId');
      if (selected_action_id in search_paths_by_action) {
          return search_paths_by_action[selected_action_id];
      } else {
          return {};
      }
    }
    var action_type_select = $('select[name="t"]');
    if (action_type_select.selectpicker('val')) {
      var selected_action_type_id = action_type_select.selectpicker('val');
      return search_paths_by_action_type[selected_action_type_id];
    }
    return search_paths;
  }
  function substringMatcher() {
    return function findMatches(q, cb) {
      var search_paths = getCurrentSearchPaths();
      var property_names = Object.keys(search_paths);
      var matches = [];
      var substrRegex = new RegExp(q, 'i');
      $.each(property_names, function(i, property_name) {
        let titles = search_paths[property_name]['titles'].join(', ');
        if (substrRegex.test(property_name) || substrRegex.test(titles)) {
          matches.push({
              property_name: property_name,
              titles: titles
          });
        }
      });
      cb(matches);
    };
  }
});
