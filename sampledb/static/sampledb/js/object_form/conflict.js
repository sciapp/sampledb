'use strict';
/* eslint-env jquery */

const NUM_HAZARDS = 10;

$(function () {
  const fieldsWithUnits = ['quantity', 'timeseries'];
  $('[data-conflict="true"]').each(function () {
    $(this).find('.apply-local').click(solveConflictButtonHandler(true, $(this)));
    $(this).find('.apply-imported').click(solveConflictButtonHandler(false, $(this)));
  });

  function solveConflictButtonHandler (local, baseField) {
    let suffix = 'local';
    if (!local) {
      suffix = 'imported';
    }

    const content = JSON.parse(atob(baseField.data(`content-${suffix}`)));
    const type = baseField.data('field-type');
    const referenceField = $(baseField.data('reference-field'));

    return function () {
      if (type === 'hazards') {
        if (content.length === 0) {
          referenceField.filter('[value="true"]').prop('checked', true);
        } else {
          referenceField.filter('[value="false"]').prop('checked', true);
        }
        const hazardPrefix = baseField.data('ghs-hazard-prefix');
        for (let hazardId = 1; hazardId < NUM_HAZARDS; hazardId++) {
          $(`[name="${hazardPrefix}${hazardId}"]`).prop('checked', content.includes(hazardId));
        }
      } else if (type !== 'tags') {
        referenceField.val(content);
        if (fieldsWithUnits.includes(type) && baseField.data('unit-field') !== undefined) {
          const unitField = $(baseField.data('unit-field'));
          const unit = JSON.parse(atob(baseField.data(`unit-${suffix}`)));
          unitField.val(unit);
          unitField.selectpicker('refresh');
        } else if (type === 'text-markdown') {
          window.markdownEditors[referenceField.attr('name')].value(content);
        }
      } else {
        referenceField.tagsinput('removeAll');
        for (const tag of content) {
          referenceField.tagsinput('add', tag);
        }
      }
    };
  }
});
