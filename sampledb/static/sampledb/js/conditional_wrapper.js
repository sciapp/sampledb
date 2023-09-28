if (!window.conditional_wrapper_scripts) {
  window.conditional_wrapper_scripts = [];
}
if (!window.conditional_wrapper_conditions) {
  window.conditional_wrapper_conditions = {};
}

function conditional_wrapper(id_prefix, schema_conditions) {
  if (typeof(id_prefix) !== "string") {
    return;
  }
  const parent_id_prefix = id_prefix.split('__').slice(0, -1).join('__') + '_';
  for(let condition in schema_conditions) {
    if (typeof conditional_wrapper_conditions[id_prefix] === 'undefined') {
      conditional_wrapper_conditions[id_prefix] = [];
    }
    window.conditional_wrapper_conditions[id_prefix].push(false);
  }
  const condition_wrapper_element = $(`[data-condition-wrapper-for="${id_prefix}"]`);
  if (!condition_wrapper_element.data('id-prefix')) {
    condition_wrapper_element.data('id-prefix', id_prefix);
    condition_wrapper_element.attr('data-id-prefix', id_prefix);
  }
  window.conditional_wrapper_scripts.push(function () {
    function update_conditions_result() {
      function check_condition_fulfilled(condition) {
        if (condition === true) {
          return true;
        } else if (condition === false) {
          return false;
        } else if (condition.type === 'not') {
          return !check_condition_fulfilled(condition.condition);
        } else if (condition.type === 'all') {
          return check_all_conditions_fulfilled(condition.conditions);
        } else if (condition.type === 'any') {
          return check_any_conditions_fulfilled(condition.conditions);
        }
      }
      function check_all_conditions_fulfilled(conditions) {
        for (let i = 0; i < conditions.length; i++) {
          if (!check_condition_fulfilled(conditions[i])) {
            return false;
          }
        }
        return true;
      }
      function check_any_conditions_fulfilled(conditions) {
        for (let i = 0; i < conditions.length; i++) {
          if (check_condition_fulfilled(conditions[i])) {
            return true;
          }
        }
        return false;
      }
      const id_prefix = condition_wrapper_element.data('id-prefix');
      const all_conditions_fulfilled = check_all_conditions_fulfilled(window.conditional_wrapper_conditions[id_prefix]);
      if (all_conditions_fulfilled) {
        condition_wrapper_element.removeClass('hidden').show();
        $(`[data-condition-replacement-for="${id_prefix}"]`).hide();
      } else {
        condition_wrapper_element.hide();
        $(`[data-condition-replacement-for="${id_prefix}"]`).removeClass('hidden').show();
      }
      $(`[data-condition-wrapper-for="${id_prefix}"] input, [data-condition-wrapper-for="${id_prefix}"] textarea, [data-condition-wrapper-for="${id_prefix}"] select`).prop('disabled', !all_conditions_fulfilled).attr('data-sampledb-disabled-by-condition', !all_conditions_fulfilled).trigger('conditions_state_changed.sampledb');
      $(`[data-condition-wrapper-for="${id_prefix}"] select`).not('.template-select').selectpicker('refresh');
    }

    function handle_condition(condition, set_condition_entry){

      if(condition['type'] === 'choice_equals')
        {
          let choice_element = $(`[name="${parent_id_prefix}_${condition['property_name']}__text"]`);

          let evaluateCondition = function () {
            if(condition['choice'] === undefined) {
              set_condition_entry(!choice_element.prop('disabled') && (choice_element.selectpicker('val')  === ""));
            } else {
              set_condition_entry(!choice_element.prop('disabled') && (!!choice_element.selectpicker('val') && choice_element.find('option:selected').data('valueBase64') === condition['encoded_choice']));
            }
            update_conditions_result();
          }

          choice_element.on('changed.bs.select', evaluateCondition);
          choice_element.on('loaded.bs.select', evaluateCondition);
          choice_element.on('refreshed.bs.select', evaluateCondition);
          choice_element.on('conditions_state_changed.sampledb', evaluateCondition);
          evaluateCondition();
        }
      else if(condition['type'] === 'user_equals')
        {
          let user_element = $(`[name="${parent_id_prefix}_${condition['property_name']}__uid"]`);

          let evaluateCondition = function () {
            set_condition_entry(!user_element.prop('disabled') && (user_element.selectpicker('val') === (condition['user_id'] !== null ? condition['user_id'].toString() : '')));
            update_conditions_result();
          }
          user_element.on('changed.bs.select', evaluateCondition);
          user_element.on('loaded.bs.select', evaluateCondition);
          user_element.on('refreshed.bs.select', evaluateCondition);
          user_element.on('conditions_state_changed.sampledb', evaluateCondition);
          evaluateCondition();
        }
      else if(condition['type'] === 'bool_equals')
        {
          let bool_element = $(`[name="${parent_id_prefix}_${condition['property_name']}__value"]`);

          let evaluateCondition = function () {
            set_condition_entry(!bool_element.prop('disabled') && (bool_element.prop('checked') === (condition['value'] ? true : false)));
            update_conditions_result();
          }
          bool_element.on('change', evaluateCondition);
          bool_element.on('conditions_state_changed.sampledb', evaluateCondition);
          evaluateCondition();
        }
      else if(condition['type'] === 'object_equals')
        {
          let object_element = $(`[name="${parent_id_prefix}_${condition['property_name']}__oid"]`);

          let evaluateCondition = function () {
            set_condition_entry(!object_element.prop('disabled') && (object_element.selectpicker('val') === (condition['object_id'] !== null ? condition['object_id'].toString() : '')));
            update_conditions_result();
          }
          object_element.on('changed.bs.select', evaluateCondition);
          object_element.on('loaded.bs.select', evaluateCondition);
          object_element.on('refreshed.bs.select', evaluateCondition);
          object_element.on('conditions_state_changed.sampledb', evaluateCondition);
          evaluateCondition();
        }
      else if(condition['type'] === 'any') {
        let condition_entry = {type: 'any', conditions: []};
        condition.conditions.forEach(function(sub_condition, i) {
          condition_entry["conditions"][i] = false;
          handle_condition(sub_condition, function(value) {
            condition_entry["conditions"][i] = value;
          });
        });
        set_condition_entry(condition_entry);
      }
      else if(condition['type'] === 'all') {
        let condition_entry = {type: 'all', conditions: []};
        condition.conditions.forEach(function(sub_condition, i) {
          condition_entry["conditions"][i] = false;
          handle_condition(sub_condition, function(value) {
            condition_entry["conditions"][i] = value;
          });
        });
        set_condition_entry(condition_entry);
      }
      else if(condition['type'] === 'not') {
        let condition_entry = {type: 'not', condition: false};
        handle_condition(condition['condition'], function(value) {
          condition_entry["condition"] = value;
        });
        set_condition_entry(condition_entry);
      }
    }

    if(schema_conditions !== undefined) {
      schema_conditions.forEach(function(condition, i) {
        handle_condition(condition, function(value) {
          const id_prefix = condition_wrapper_element.data('id-prefix');
          window.conditional_wrapper_conditions[id_prefix][i] = value;
        });
      });
    }

  });
}
