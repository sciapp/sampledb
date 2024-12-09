'use strict';
/* eslint-env jquery */

if (!window.conditionalWrapperScripts) {
  window.conditionalWrapperScripts = [];
}
if (!window.conditionalWrapperConditions) {
  window.conditionalWrapperConditions = {};
}

/**
 * Set up condition handling for a form field.
 * @param conditionsElement the element that contains the conditions for the field
 * @param idPrefix the ID prefix of the field
 * @param schemaConditions the conditions for the field
 */
function conditionalWrapper (conditionsElement, idPrefix, schemaConditions) {
  if (typeof (idPrefix) !== 'string' || idPrefix.includes('!')) {
    return;
  }
  const parentIDPrefix = idPrefix.split('__').slice(0, -1).join('__') + '_';
  if (typeof window.conditionalWrapperConditions[idPrefix] === 'undefined') {
    window.conditionalWrapperConditions[idPrefix] = { type: 'all', conditions: [], result: null };
    schemaConditions.forEach(function () {
      window.conditionalWrapperConditions[idPrefix].conditions.push(null);
    });
  }
  const parentElement = conditionsElement.closest(`[data-id-prefix="${parentIDPrefix}"]`);
  const conditionWrapperElement = parentElement.find(`[data-condition-wrapper-for="${idPrefix}"]`);
  if (!conditionWrapperElement.data('id-prefix')) {
    conditionWrapperElement.data('id-prefix', idPrefix);
    conditionWrapperElement.attr('data-id-prefix', idPrefix);
  }
  function checkConditionFulfilled (condition) {
    if (condition === true) {
      return true;
    } else if (condition === false || condition === null) {
      return false;
    } else {
      return checkConditionFulfilled(condition.result);
    }
  }
  function checkAllConditionsFulfilled (conditions) {
    for (let i = 0; i < conditions.length; i++) {
      if (!checkConditionFulfilled(conditions[i])) {
        return false;
      }
    }
    return true;
  }
  function checkAnyConditionsFulfilled (conditions) {
    for (let i = 0; i < conditions.length; i++) {
      if (checkConditionFulfilled(conditions[i])) {
        return true;
      }
    }
    return false;
  }
  window.conditionalWrapperScripts.push(function () {
    function updateConditionsResult () {
      const idPrefix = conditionWrapperElement.data('id-prefix');
      const allConditionsFulfilled = checkConditionFulfilled(window.conditionalWrapperConditions[idPrefix]);
      if (allConditionsFulfilled) {
        conditionWrapperElement.removeClass('hidden').show();
        conditionWrapperElement.siblings(`[data-condition-replacement-for="${idPrefix}"]`).hide();
      } else {
        conditionWrapperElement.hide();
        conditionWrapperElement.siblings(`[data-condition-replacement-for="${idPrefix}"]`).removeClass('hidden').show();
      }
      conditionWrapperElement.find('input, textarea, select').each(function () {
        const disabledByCondition = !allConditionsFulfilled;
        let disabledByConditionList = $(this).data('sampledb-disabled-by-conditions');
        if (!disabledByConditionList) {
          disabledByConditionList = [];
        }
        const disabledByConditionsBefore = disabledByConditionList.length > 0;
        if (disabledByConditionList.includes(idPrefix) === disabledByCondition) {
          return;
        }
        if (disabledByCondition) {
          disabledByConditionList.push(idPrefix);
        } else {
          disabledByConditionList = disabledByConditionList.filter(function (item) { return item !== idPrefix; });
        }
        $(this).attr('data-sampledb-disabled-by-conditions', disabledByConditionList).data('sampledb-disabled-by-conditions', disabledByConditionList);
        const disabledByConditionsAfter = disabledByConditionList.length > 0;
        if (disabledByConditionsBefore === disabledByConditionsAfter) {
          return;
        }
        $(this).prop('disabled', disabledByConditionsAfter).trigger('conditions_state_changed.sampledb');
        if ($(this).is('select:not(.template-select)')) {
          $(this).selectpicker('refresh');
        }
      });
    }

    function handleCondition (condition, setConditionEntry) {
      if (condition.type === 'choice_equals') {
        const choiceElement = parentElement.find(`[name="${parentIDPrefix}_${condition.property_name}__text"]`);

        const evaluateCondition = function () {
          if (condition.choice === undefined || condition.choice === null) {
            setConditionEntry(!choiceElement.prop('disabled') && (choiceElement.selectpicker('val') === ''));
          } else {
            setConditionEntry(!choiceElement.prop('disabled') && (!!choiceElement.selectpicker('val') && choiceElement.find('option:selected').data('valueBase64') === condition.encoded_choice));
          }
        };

        choiceElement.on('changed.bs.select', evaluateCondition);
        choiceElement.on('loaded.bs.select', evaluateCondition);
        choiceElement.on('refreshed.bs.select', evaluateCondition);
        choiceElement.on('conditions_state_changed.sampledb', evaluateCondition);
        evaluateCondition();
      } else if (condition.type === 'user_equals') {
        const userElement = parentElement.find(`[name="${parentIDPrefix}_${condition.property_name}__uid"]`);

        const evaluateCondition = function () {
          setConditionEntry(!userElement.prop('disabled') && (userElement.selectpicker('val') === (condition.user_id !== null ? condition.user_id.toString() : '')));
        };
        userElement.on('changed.bs.select', evaluateCondition);
        userElement.on('loaded.bs.select', evaluateCondition);
        userElement.on('refreshed.bs.select', evaluateCondition);
        userElement.on('conditions_state_changed.sampledb', evaluateCondition);
        evaluateCondition();
      } else if (condition.type === 'bool_equals') {
        const boolElement = parentElement.find(`[name="${parentIDPrefix}_${condition.property_name}__value"]`);

        const evaluateCondition = function () {
          setConditionEntry(!boolElement.prop('disabled') && (boolElement.prop('checked') === Boolean(condition.value)));
        };
        boolElement.on('change', evaluateCondition);
        boolElement.on('conditions_state_changed.sampledb', evaluateCondition);
        evaluateCondition();
      } else if (condition.type === 'object_equals') {
        const objectElement = parentElement.find(`[name="${parentIDPrefix}_${condition.property_name}__oid"]`);
        const evaluateCondition = function () {
          setConditionEntry((!objectElement.data('sampledb-disabled-by-conditions') || objectElement.data('sampledb-disabled-by-conditions').length === 0) && ((objectElement.val() === (condition.object_id !== null ? condition.object_id.toString() : '')) || (objectElement.val() === condition.object_id)));
        };
        objectElement.on('object_change.sampledb', evaluateCondition); // typeahead cases
        objectElement.on('changed.bs.select', evaluateCondition);
        objectElement.on('loaded.bs.select', evaluateCondition);
        objectElement.on('refreshed.bs.select', evaluateCondition);
        objectElement.on('conditions_state_changed.sampledb', evaluateCondition);
        evaluateCondition();
      } else if (condition.type === 'any') {
        const conditionEntry = { type: 'any', conditions: [], result: null };
        condition.conditions.forEach(function (subCondition, i) {
          conditionEntry.conditions[i] = null;
          handleCondition(subCondition, function (value) {
            conditionEntry.conditions[i] = value;
            const valueResult = checkConditionFulfilled(value);
            if (valueResult === conditionEntry.result) {
              return;
            }
            const newResult = valueResult || checkAnyConditionsFulfilled(conditionEntry.conditions);
            if (newResult === conditionEntry.result) {
              return;
            }
            conditionEntry.result = newResult;
            setConditionEntry(conditionEntry);
          });
        });
      } else if (condition.type === 'all') {
        const conditionEntry = { type: 'all', conditions: [], result: null };
        condition.conditions.forEach(function (subCondition, i) {
          conditionEntry.conditions[i] = null;
          handleCondition(subCondition, function (value) {
            conditionEntry.conditions[i] = value;
            const valueResult = checkConditionFulfilled(value);
            if (valueResult === conditionEntry.result) {
              return;
            }
            const newResult = valueResult && checkAllConditionsFulfilled(conditionEntry.conditions);
            if (newResult === conditionEntry.result) {
              return;
            }
            conditionEntry.result = newResult;
            setConditionEntry(conditionEntry);
          });
        });
      } else if (condition.type === 'not') {
        const conditionEntry = { type: 'not', condition: null, result: null };
        handleCondition(condition.condition, function (value) {
          conditionEntry.condition = value;
          const valueResult = checkConditionFulfilled(value);
          const newResult = !valueResult;
          if (newResult === conditionEntry.result) {
            return;
          }
          conditionEntry.result = newResult;
          setConditionEntry(conditionEntry);
        });
      }
    }

    if (schemaConditions !== undefined) {
      handleCondition({ type: 'all', conditions: schemaConditions }, function (value) {
        const idPrefix = conditionWrapperElement.data('id-prefix');
        window.conditionalWrapperConditions[idPrefix] = value;
        updateConditionsResult();
      });
    }
  });
}

/**
 * Apply schema conditions to condition wrapper elements in a given element.
 * @param element a DOM element
 */
function applySchemaConditions (element) {
  $(element).find('.condition-wrapper[data-id-prefix]').each(function () {
    const idPrefix = $(this).data('id-prefix');
    const conditions = $(this).data('conditions');
    conditionalWrapper($(this), idPrefix, conditions);
  });

  $.each(window.conditionalWrapperScripts, function () {
    this();
  });
  window.conditionalWrapperScripts = [];
}

export {
  applySchemaConditions
};
