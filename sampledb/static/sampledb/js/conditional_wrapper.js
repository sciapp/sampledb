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
 * @param idPrefix the ID prefix of the field
 * @param schemaConditions the conditions for the field
 */
function conditionalWrapper (idPrefix, schemaConditions) {
  if (typeof (idPrefix) !== 'string' || idPrefix.includes('!')) {
    return;
  }
  const parentIDPrefix = idPrefix.split('__').slice(0, -1).join('__') + '_';
  schemaConditions.forEach(function () {
    if (typeof window.conditionalWrapperConditions[idPrefix] === 'undefined') {
      window.conditionalWrapperConditions[idPrefix] = [];
    }
    window.conditionalWrapperConditions[idPrefix].push(false);
  });
  const conditionWrapperElement = $(`[data-condition-wrapper-for="${idPrefix}"]`);
  if (!conditionWrapperElement.data('id-prefix')) {
    conditionWrapperElement.data('id-prefix', idPrefix);
    conditionWrapperElement.attr('data-id-prefix', idPrefix);
  }
  window.conditionalWrapperScripts.push(function () {
    function updateConditionsResult () {
      function checkConditionFulfilled (condition) {
        if (condition === true) {
          return true;
        } else if (condition === false) {
          return false;
        } else if (condition.type === 'not') {
          return !checkConditionFulfilled(condition.condition);
        } else if (condition.type === 'all') {
          return checkAllConditionsFulfilled(condition.conditions);
        } else if (condition.type === 'any') {
          return checkAnyConditionsFulfilled(condition.conditions);
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
      const idPrefix = conditionWrapperElement.data('id-prefix');
      const allConditionsFulfilled = checkAllConditionsFulfilled(window.conditionalWrapperConditions[idPrefix]);
      if (allConditionsFulfilled) {
        conditionWrapperElement.removeClass('hidden').show();
        $(`[data-condition-replacement-for="${idPrefix}"]`).hide();
      } else {
        conditionWrapperElement.hide();
        $(`[data-condition-replacement-for="${idPrefix}"]`).removeClass('hidden').show();
      }
      $(`[data-condition-wrapper-for="${idPrefix}"] input, [data-condition-wrapper-for="${idPrefix}"] textarea, [data-condition-wrapper-for="${idPrefix}"] select`).prop('disabled', !allConditionsFulfilled).attr('data-sampledb-disabled-by-condition', !allConditionsFulfilled).data('sampledb-disabled-by-condition', !allConditionsFulfilled).trigger('conditions_state_changed.sampledb');
      $(`[data-condition-wrapper-for="${idPrefix}"] select`).not('.template-select').selectpicker('refresh');
    }

    function handleCondition (condition, setConditionEntry) {
      if (condition.type === 'choice_equals') {
        const choiceElement = $(`[name="${parentIDPrefix}_${condition.property_name}__text"]`);

        const evaluateCondition = function () {
          if (condition.choice === undefined) {
            setConditionEntry(!choiceElement.prop('disabled') && (choiceElement.selectpicker('val') === ''));
          } else {
            setConditionEntry(!choiceElement.prop('disabled') && (!!choiceElement.selectpicker('val') && choiceElement.find('option:selected').data('valueBase64') === condition.encoded_choice));
          }
          updateConditionsResult();
        };

        choiceElement.on('changed.bs.select', evaluateCondition);
        choiceElement.on('loaded.bs.select', evaluateCondition);
        choiceElement.on('refreshed.bs.select', evaluateCondition);
        choiceElement.on('conditions_state_changed.sampledb', evaluateCondition);
        evaluateCondition();
      } else if (condition.type === 'user_equals') {
        const userElement = $(`[name="${parentIDPrefix}_${condition.property_name}__uid"]`);

        const evaluateCondition = function () {
          setConditionEntry(!userElement.prop('disabled') && (userElement.selectpicker('val') === (condition.user_id !== null ? condition.user_id.toString() : '')));
          updateConditionsResult();
        };
        userElement.on('changed.bs.select', evaluateCondition);
        userElement.on('loaded.bs.select', evaluateCondition);
        userElement.on('refreshed.bs.select', evaluateCondition);
        userElement.on('conditions_state_changed.sampledb', evaluateCondition);
        evaluateCondition();
      } else if (condition.type === 'bool_equals') {
        const boolElement = $(`[name="${parentIDPrefix}_${condition.property_name}__value"]`);

        const evaluateCondition = function () {
          setConditionEntry(!boolElement.prop('disabled') && (boolElement.prop('checked') === Boolean(condition.value)));
          updateConditionsResult();
        };
        boolElement.on('change', evaluateCondition);
        boolElement.on('conditions_state_changed.sampledb', evaluateCondition);
        evaluateCondition();
      } else if (condition.type === 'object_equals') {
        const objectElement = $(`[name="${parentIDPrefix}_${condition.property_name}__oid"]`);
        const evaluateCondition = function () {
          setConditionEntry(!objectElement.data('sampledb-disabled-by-condition') && ((objectElement.val() === (condition.object_id !== null ? condition.object_id.toString() : '')) || (objectElement.val() === condition.object_id)));
          updateConditionsResult();
        };
        objectElement.on('object_change.sampledb', evaluateCondition); // typeahead cases
        objectElement.on('changed.bs.select', evaluateCondition);
        objectElement.on('loaded.bs.select', evaluateCondition);
        objectElement.on('refreshed.bs.select', evaluateCondition);
        objectElement.on('conditions_state_changed.sampledb', evaluateCondition);
        evaluateCondition();
      } else if (condition.type === 'any') {
        const conditionEntry = { type: 'any', conditions: [] };
        condition.conditions.forEach(function (subCondition, i) {
          conditionEntry.conditions[i] = false;
          handleCondition(subCondition, function (value) {
            conditionEntry.conditions[i] = value;
          });
        });
        setConditionEntry(conditionEntry);
      } else if (condition.type === 'all') {
        const conditionEntry = { type: 'all', conditions: [] };
        condition.conditions.forEach(function (subCondition, i) {
          conditionEntry.conditions[i] = false;
          handleCondition(subCondition, function (value) {
            conditionEntry.conditions[i] = value;
          });
        });
        setConditionEntry(conditionEntry);
      } else if (condition.type === 'not') {
        const conditionEntry = { type: 'not', condition: false };
        handleCondition(condition.condition, function (value) {
          conditionEntry.condition = value;
        });
        setConditionEntry(conditionEntry);
      }
    }

    if (schemaConditions !== undefined) {
      schemaConditions.forEach(function (condition, i) {
        handleCondition(condition, function (value) {
          const idPrefix = conditionWrapperElement.data('id-prefix');
          window.conditionalWrapperConditions[idPrefix][i] = value;
        });
      });
    }
  });
}

/**
 * Apply schema conditions to condition wrapper elements in a given element.
 * @param element a DOM element
 */
function applySchemaConditions (element) {
  $(element).find('.condition-wrapper').each(function () {
    const idPrefix = $(this).data('id-prefix');
    const conditions = $(this).data('conditions');
    conditionalWrapper(idPrefix, conditions);
  });

  $.each(window.conditionalWrapperScripts, function () {
    this();
  });
  window.conditionalWrapperScripts = [];
}

export {
  conditionalWrapper,
  applySchemaConditions
};
