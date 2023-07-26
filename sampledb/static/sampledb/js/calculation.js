function resolvePropertyPath(property_path) {
  let resolved_property_path = [];
  let relative_path_stack = [];
  for (let path_element of property_path) {
    if (path_element === '..') {
      relative_path_stack.push(resolved_property_path.pop());
    } else {
      if (relative_path_stack.length > 0) {
        let relative_path_element = relative_path_stack.pop();
        if (path_element.length > 1 && (path_element[0] === '+' || path_element[0] === '-')) {
          let updated_path_element = Number.parseInt(relative_path_element) + Number.parseInt(path_element.substr(1)) * (path_element[0] === '-' ? -1 : 1);
          if (Number.isFinite(updated_path_element)) {
            path_element = updated_path_element;
          }
        }
      }
      resolved_property_path.push(path_element)
    }
  }
  return resolved_property_path;
}

function getPropertySchema(root_schema, property_path) {
  let property_schema = root_schema;
  for (const path_element of property_path) {
    if (property_schema['type'] === 'object') {
      property_schema = property_schema['properties'][path_element];
    } else {
      property_schema = property_schema['items'];
    }
  }
  return property_schema;
}

function setUpCalculation(id_prefix, schema, root_schema) {
  let property_names = schema.calculation.property_names;
  let all_input_elements_available = true;
  let input_elements = [];
  let property_aliases = [];
  if (Array.isArray(property_names)) {
    fixed_property_names = {};
    for (let property_name of property_names) {
      fixed_property_names[property_name] = [property_name];
    }
    property_names = fixed_property_names;
  }
  for (const property_alias in property_names) {
    if (!property_names.hasOwnProperty(property_alias)) {
      continue;
    }
    let relative_property_path = property_names[property_alias];
    if (typeof relative_property_path === "string") {
       relative_property_path = [relative_property_path];
    }
    let property_path = (id_prefix + '_').split('__');
    property_path.shift();
    property_path.pop();
    property_path.push('..');
    property_path = property_path.concat(relative_property_path);
    property_path = resolvePropertyPath(property_path);
    const property_id_prefix = 'object__' + property_path.join('__') + '_';
    const property_magnitude_element = $(`[name="${property_id_prefix}_magnitude"]`);
    const property_units_element = $(`[name="${property_id_prefix}_units"]`);
    const property_unit = property_units_element.val();
    const schema = getPropertySchema(root_schema, property_path);
    let schema_unit = schema.units;
    if (typeof schema_unit !== "string") {
      schema_unit = schema_unit[0];
    }
    if (property_magnitude_element.length === 1 && !property_magnitude_element.prop('disabled') && (schema_unit === property_unit || typeof property_unit === "undefined")) {
      property_aliases.push(property_alias);
      input_elements.push(property_magnitude_element);
    } else {
      all_input_elements_available = false;
      break;
    }
  }

  const target_element = $(`[name="${id_prefix}_magnitude"]`);
  const target_units_element = $(`[name="${id_prefix}_units"]`);
  const target_unit = target_units_element.val();
  let schema_unit = schema.units;
  if (typeof schema_unit !== "string") {
    schema_unit = schema_unit[0];
  }

  if (target_element.length === 1 && !input_elements.includes(target_element[0]) && (schema_unit === target_unit || typeof target_unit === "undefined") && all_input_elements_available) {
    let evaluateCalculation = function (event, event_chain) {
      if (!event_chain) {
        event_chain = [];
      }
      const formula = schema.calculation.formula;
      let values = {};
      let all_input_values_available = true;
      for (i = 0; i < input_elements.length; i++) {
        let value_string = input_elements[i].val();
        value_string = value_string.trim();
        if (window.local_decimal_delimiter !== ".") {
          value_string = value_string.replace(window.local_decimal_delimiter, ".");
        }
        let value = parseFloat(value_string);
        if (!isFinite(value)) {
          all_input_values_available = false;
          break;
        }
        values[property_aliases[i]] = value;
      }
      if (all_input_values_available) {
        let result = math.evaluate(formula, values);
        if ("digits" in schema.calculation) {
          result = math.round(result, schema.calculation.digits);
        }
        let result_string = String(result);
        if (!isFinite(result)) {
          if (isNaN(result)) {
            result_string = '—';
          } else if (result > 0) {
            result_string = '∞';
          } else {
            result_string = '-∞';
          }
        }
        if (window.local_decimal_delimiter !== ".") {
          result_string = result_string.replace('.', window.local_decimal_delimiter);
        }
        const current_value_string = target_element.val();
        if (result_string !== current_value_string) {
          const previous_calculated_value_string = target_element.data('sampleDBCalculatedValue');
          target_element.data('sampleDBCalculatedValue', result_string);
          if (!event_chain.includes(target_element.attr('name')) && (current_value_string === previous_calculated_value_string || (current_value_string === '' && typeof previous_calculated_value_string === 'undefined')) && isFinite(result)) {
            target_element.val(result_string);
            // ensure the change is propagated to dependant fields
            event_chain.push(target_element.attr('name'));
            target_element.trigger('sampledb.calculation.change', [event_chain]);
          } else {
            const help_block = $(`#${id_prefix}_calculation_help`);
            if (help_block.length === 1) {
              help_block.find('span').text(result_string);
              const help_block_button = help_block.find('button');
              if (isFinite(result)) {
                help_block_button.show();
              } else {
                help_block_button.hide();
              }
              help_block_button.off('click');
              help_block_button.on('click', function() {
                target_element.val(result_string);
                // ensure the change is propagated to dependant fields
                target_element.trigger('sampledb.calculation.change', [[target_element]]);
                help_block.hide();
              });
              help_block.show();
            }
          }
        } else {
          const help_block = $(`#${id_prefix}_calculation_help`);
          if (help_block.length === 1) {
            help_block.hide();
          }
        }

      }
    }
    target_element.on('change', function() {
      const help_block = $(`#${id_prefix}_calculation_help`);
      if (help_block.length === 1) {
        const current_value_string = target_element.val();
        const previous_calculated_value_string = target_element.data('sampleDBCalculatedValue');
        if (current_value_string === previous_calculated_value_string) {
          help_block.hide();
        }
      }
    });
    input_elements.forEach(function (input_element) {
      input_element.on('change', function() {
        input_element.trigger('sampledb.calculation.change', [[input_element.attr('name')]]);
      });
      input_element.on('sampledb.calculation.change', evaluateCalculation);
    });
    evaluateCalculation();
  }
}
