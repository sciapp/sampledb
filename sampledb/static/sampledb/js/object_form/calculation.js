'use strict';
/* eslint-env jquery */
/* globals math */

/**
 * Resolves a property path using relative path elements, e.g. .., +x or -x.
 * @param propertyPath a property path
 * @returns {*[]} the resolved property path
 */
function resolvePropertyPath (propertyPath) {
  const resolvedPropertyPath = [];
  const relativePathStack = [];
  for (let pathElement of propertyPath) {
    if (pathElement === '..') {
      relativePathStack.push(resolvedPropertyPath.pop());
    } else {
      if (relativePathStack.length > 0) {
        const relativePathElement = relativePathStack.pop();
        if (pathElement.length > 1 && (pathElement[0] === '+' || pathElement[0] === '-')) {
          const updatedPathElement = Number.parseInt(relativePathElement) + Number.parseInt(pathElement.substr(1)) * (pathElement[0] === '-' ? -1 : 1);
          if (Number.isFinite(updatedPathElement)) {
            pathElement = updatedPathElement;
          }
        }
      }
      resolvedPropertyPath.push(pathElement);
    }
  }
  return resolvedPropertyPath;
}

/**
 * Gets the schema of a property.
 * @param rootSchema the root schema
 * @param propertyPath an absolute property path
 * @returns {*} the property schema
 */
function getPropertySchema (rootSchema, propertyPath) {
  let propertySchema = rootSchema;
  for (const pathElement of propertyPath) {
    if (propertySchema.type === 'object') {
      propertySchema = propertySchema.properties[pathElement];
    } else {
      propertySchema = propertySchema.items;
    }
  }
  return propertySchema;
}

/**
 * Sets up the calculation for a form field.
 * @param idPrefix the ID prefix of the field
 * @param schema the schema for the field
 * @param rootSchema the root schema
 */
function setUpCalculation (idPrefix, schema, rootSchema) { // eslint-disable-line no-unused-vars
  let propertyNames = schema.calculation.property_names;
  let allInputElementsAvailable = true;
  const inputElements = [];
  const propertyAliases = [];
  const propertyPaths = [];
  if (Array.isArray(propertyNames)) {
    const fixedPropertyNames = {};
    for (const propertyName of propertyNames) {
      fixedPropertyNames[propertyName] = [propertyName];
    }
    propertyNames = fixedPropertyNames;
  }
  for (const propertyAlias in propertyNames) {
    if (!Object.prototype.hasOwnProperty.call(propertyNames, propertyAlias)) {
      continue;
    }
    let relativePropertyPath = propertyNames[propertyAlias];
    if (typeof relativePropertyPath === 'string') {
      relativePropertyPath = [relativePropertyPath];
    }
    let propertyPath = (idPrefix + '_').split('__');
    propertyPath.shift();
    propertyPath.pop();
    propertyPath.push('..');
    propertyPath = propertyPath.concat(relativePropertyPath);
    propertyPath = resolvePropertyPath(propertyPath);
    const propertyIDPrefix = 'object__' + propertyPath.join('__') + '_';
    const propertyIDPrefixes = [];
    if (propertyPath.includes('*')) {
      const propertyIDPrefixWildcardPrefix = propertyIDPrefix.split('*').shift();
      const propertyIDPrefixWildcardSuffix = propertyIDPrefix.split('*').pop();
      const potentialPropertyMagnitudeElements = $(`[name^="${propertyIDPrefixWildcardPrefix}"][name$="${propertyIDPrefixWildcardSuffix}_magnitude"]`);
      potentialPropertyMagnitudeElements.each(function (_, element) {
        if (element.name.substr(element.name.length - '__magnitude'.length) !== '__magnitude') {
          return;
        }
        const propertyIDPrefix = element.name.substring(0, element.name.length - '_magnitude'.length);
        if (!propertyIDPrefix.startsWith('object__') || !propertyIDPrefix.endsWith('_')) {
          return;
        }
        const propertyIDPrefixParts = propertyIDPrefix.substring('object__'.length, propertyIDPrefix.length - 1).split('__');
        if (propertyIDPrefixParts.length !== propertyPath.length) {
          return;
        }
        for (let i = 0; i < propertyIDPrefixParts.length; i++) {
          if (propertyPath[i] === '*') {
            const index = Number.parseInt(propertyIDPrefixParts[i]);
            if (!Number.isFinite(index) || index < 0 || index.toString() !== propertyIDPrefixParts[i]) {
              return;
            }
          } else if (propertyPath[i] !== propertyIDPrefixParts[i]) {
            return;
          }
        }
        propertyIDPrefixes.push(propertyIDPrefix);
      });
    } else {
      propertyIDPrefixes.push(propertyIDPrefix);
    }
    const elements = [];
    propertyIDPrefixes.forEach(function (propertyIDPrefix) {
      const propertyMagnitudeElement = $(`[name="${propertyIDPrefix}_magnitude"]`);
      const propertyUnitsElement = $(`[name="${propertyIDPrefix}_units"]`);
      const propertyUnit = propertyUnitsElement.val();
      const schema = getPropertySchema(rootSchema, propertyPath);
      let schemaUnit = schema.units;
      if (typeof schemaUnit !== 'string') {
        schemaUnit = schemaUnit[0];
      }
      if (propertyMagnitudeElement.length === 1 && (schemaUnit === propertyUnit || typeof propertyUnit === 'undefined')) {
        elements.push(propertyMagnitudeElement);
      } else {
        allInputElementsAvailable = false;
      }
    });
    if (allInputElementsAvailable) {
      propertyAliases.push(propertyAlias);
      inputElements.push(elements);
      propertyPaths.push(propertyPath);
    } else {
      break;
    }
  }

  const targetElement = $(`[name="${idPrefix}_magnitude"]`);
  const targetUnitsElement = $(`[name="${idPrefix}_units"]`);
  const targetUnit = targetUnitsElement.val();
  let schemaUnit = schema.units;
  if (typeof schemaUnit !== 'string') {
    schemaUnit = schemaUnit[0];
  }

  if (targetElement.length === 1 && inputElements.every(function (elements) { return !elements.includes(targetElement[0]); }) && (schemaUnit === targetUnit || typeof targetUnit === 'undefined') && allInputElementsAvailable) {
    const evaluateCalculation = function (event, eventChain) {
      if (!eventChain) {
        eventChain = [];
      }
      const formula = schema.calculation.formula;
      const values = {};
      let allInputValuesAvailable = true;
      for (let i = 0; i < inputElements.length; i++) {
        values[propertyAliases[i]] = [];
        for (let j = 0; j < inputElements[i].length; j++) {
          if (inputElements[i][j].prop('disabled')) {
            continue;
          }
          let valueString = inputElements[i][j].val();
          if (valueString === '') {
            continue;
          }
          valueString = valueString.trim();
          if (window.local_decimal_delimiter !== '.') {
            valueString = valueString.replace(window.local_decimal_delimiter, '.');
          }
          const value = parseFloat(valueString);
          if (!isFinite(value)) {
            allInputValuesAvailable = false;
            break;
          }
          values[propertyAliases[i]].push(value);
        }
        if (!allInputValuesAvailable || values[propertyAliases[i]].length === 0) {
          allInputValuesAvailable = false;
          break;
        }
        if (values[propertyAliases[i]].length === 1 && !propertyPaths[i].includes('*')) {
          values[propertyAliases[i]] = values[propertyAliases[i]][0];
        }
      }
      if (allInputValuesAvailable) {
        let result = math.evaluate(formula, values);
        if ('digits' in schema.calculation) {
          result = math.round(result, schema.calculation.digits);
        }
        let resultString = String(result);
        if (!isFinite(result)) {
          if (isNaN(result)) {
            resultString = '—';
          } else if (result > 0) {
            resultString = '∞';
          } else {
            resultString = '-∞';
          }
        }
        if (window.local_decimal_delimiter !== '.') {
          resultString = resultString.replace('.', window.local_decimal_delimiter);
        }
        const currentValueString = targetElement.val();
        if (resultString !== currentValueString) {
          const previousCalculatedValueString = targetElement.data('sampleDBCalculatedValue');
          targetElement.data('sampleDBCalculatedValue', resultString);
          if (!eventChain.includes(targetElement.attr('name')) && (currentValueString === previousCalculatedValueString || (currentValueString === '' && typeof previousCalculatedValueString === 'undefined')) && isFinite(result)) {
            targetElement.val(resultString);
            // ensure the change is propagated to dependant fields
            eventChain.push(targetElement.attr('name'));
            targetElement.trigger('sampledb.calculation.change', [eventChain]);
          } else {
            const helpBlock = $(`#${idPrefix}_calculation_help`);
            if (helpBlock.length === 1) {
              helpBlock.find('span').text(resultString);
              const helpBlockButton = helpBlock.find('button');
              if (isFinite(result)) {
                helpBlockButton.show();
              } else {
                helpBlockButton.hide();
              }
              helpBlockButton.off('click');
              helpBlockButton.on('click', function () {
                targetElement.val(resultString);
                // ensure the change is propagated to dependant fields
                targetElement.trigger('sampledb.calculation.change', [[targetElement]]);
                helpBlock.hide();
              });
              helpBlock.show();
            }
          }
        } else {
          const helpBlock = $(`#${idPrefix}_calculation_help`);
          if (helpBlock.length === 1) {
            helpBlock.hide();
          }
        }
      }
    };
    targetElement.on('change', function () {
      const helpBlock = $(`#${idPrefix}_calculation_help`);
      if (helpBlock.length === 1) {
        const currentValueString = targetElement.val();
        const previousCalculatedValueString = targetElement.data('sampleDBCalculatedValue');
        if (currentValueString === previousCalculatedValueString) {
          helpBlock.hide();
        }
      }
    });
    targetElement.off('sampledb.calculation.evaluate');
    targetElement.on('sampledb.calculation.evaluate', evaluateCalculation);
    inputElements.forEach(function (elements) {
      elements.forEach(function (inputElement) {
        inputElement.on('change', function () {
          inputElement.trigger('sampledb.calculation.change', [[inputElement.attr('name')]]);
        });
        inputElement.on('conditions_state_changed.sampledb', function () {
          inputElement.trigger('sampledb.calculation.change', [[inputElement.attr('name')]]);
        });
        inputElement.on('sampledb.calculation.change', function (event, eventChain) {
          targetElement.trigger('sampledb.calculation.evaluate', [eventChain]);
        });
      });
    });
    evaluateCalculation();
  }
}

const calculationSetupScripts = [];

/**
 * Run all calculation setup scripts.
 * This will also re-set up existing calculations, as available fields for the
 * calculations may have changed due to array operations, conditions, etc.
 */
function setUpCalculations () {
  $.each(calculationSetupScripts, function () {
    this();
  });
}

/**
 * Set up calculations from calculation wrapper elements.
 * @param element the DOM element to search for calculation wrappers
 */
function applySchemaCalculations (element) {
  $(element).find('.calculation-wrapper').each(function () {
    if ($(this).parents('.array-template').length === 0) {
      const idPrefix = $(this).data('id-prefix');
      const schema = $(this).data('schema');
      const rootSchema = $(this).data('root-schema');
      calculationSetupScripts.push(function () {
        setUpCalculation(idPrefix, schema, rootSchema);
      });
    }
  });
  setUpCalculations();
}

$(function () {
  applySchemaCalculations(document);
});

export {
  setUpCalculations,
  applySchemaCalculations
};
