'use strict';
/* eslint-env jquery */

const selectedObjectIDs = [];
const objectsAllowedToSelect = window.getTemplateValue('objects_allowed_to_select');

function isObjectSelected (objectID) {
  return selectedObjectIDs.includes(objectID);
}

function getSelectableObjectIDs () {
  return objectsAllowedToSelect;
}

window.checkSubmittableImpl = function (submitTooltip, submitButton) {
  return true;
};

function checkSubmittable () {
  const submitTooltip = $('#multiselect-submit-tooltip');
  const submitButton = $('#multiselect-submit');
  const hasInvalidIDs = selectedObjectIDs.some(id => !objectsAllowedToSelect.includes(id));

  if (selectedObjectIDs.length === 0) {
    submitTooltip.attr('data-original-title', window.getTemplateValue('translations.select_at_least_one_object')).tooltip('setContent').tooltip('enable');
    submitButton.prop('disabled', true);
    return false;
  } else if (hasInvalidIDs) {
    submitTooltip.attr('data-original-title', window.getTemplateValue('translations.you_do_not_have_write_permissions')).tooltip('setContent').tooltip('enable');
    submitButton.prop('disabled', true);
    return false;
  }
  if (!window.checkSubmittableImpl(submitTooltip, submitButton)) {
    return false;
  }
  submitTooltip.tooltip('disable');
  submitButton.prop('disabled', false);
  return true;
}

// multiple object selection actions
$(function () {
  $('#multiselect-form').on('submit', function () {
    $('#object-selection').val(selectedObjectIDs.join(','));
  });

  $('[data-toggle="tooltip"]').tooltip({ trigger: 'hover' });

  $('.checkbox-select-child').on('click', function () {
    handleObjectSelection(this);
  });

  checkSubmittable();

  $('.checkbox-select-child').prop('checked', false);

  $('#checkbox-select-overall').prop('checked', false);
  $('#checkbox-select-overall').prop('indeterminate', false);

  $('[data-multiselect-check-submittable="true"]').on('change', checkSubmittable);

  const checkboxSelectOverall = $('#checkbox-select-overall');
  const checkboxSelectChilds = $('.checkbox-select-child');

  function handleObjectSelection (cb) {
    const handledObjectID = Number(cb.value);
    const objectIndex = selectedObjectIDs.indexOf(handledObjectID);
    if (!cb.checked && objectIndex >= 0) {
      selectedObjectIDs.splice(objectIndex, 1);
    } else if (cb.checked && objectIndex < 0) {
      selectedObjectIDs.push(handledObjectID);
    }

    const someAvailableSelected = objectsAllowedToSelect.some(id => selectedObjectIDs.includes(id));
    const allAvailableSelected = someAvailableSelected && objectsAllowedToSelect.every(id => selectedObjectIDs.includes(id));
    checkboxSelectOverall.prop('checked', allAvailableSelected);
    checkboxSelectOverall.prop('indeterminate', someAvailableSelected && !allAvailableSelected);
    checkSubmittable();
  }

  checkboxSelectOverall.on('change', function (e) {
    const checked = $(this).prop('checked');
    checkboxSelectChilds.each(function (i, element) {
      if (objectsAllowedToSelect.includes(Number($(element).prop('value')))) {
        $(element).prop('checked', checked);
        handleObjectSelection(element);
      }
    });
    checkboxSelectOverall.prop('indeterminate', false);
  });
});

export {
  isObjectSelected,
  getSelectableObjectIDs,
  checkSubmittable
};
