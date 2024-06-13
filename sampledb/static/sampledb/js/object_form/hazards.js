'use strict';
/* eslint-env jquery */

function setHasNoHazards (radioButton) {
  if (radioButton.prop('checked')) {
    const hazardsSelection = radioButton.closest('.radio').parent().find('.ghs-hazards-selection');
    $(hazardsSelection).find('input').prop('checked', false);
  }
}

function setHasHazard (checkbox) {
  const hazardsSelection = checkbox.closest('.ghs-hazards-selection');
  const hasHazards = $(hazardsSelection).find('input').filter(function () {
    return this.checked;
  }).length > 0;
  const hasNoHazardsTrue = $(hazardsSelection).parent().find('input[name$="_hasnohazards"][value=true]');
  hasNoHazardsTrue.prop('checked', !hasHazards);
  const hasNoHazardsFalse = $(hazardsSelection).parent().find('input[name$="_hasnohazards"][value=false]');
  hasNoHazardsFalse.prop('checked', hasHazards);
}

$(function () {
  $('input[name^=\'object__\'][name$=\'__hasnohazards\'][value="true"]').each(function () {
    const radioButton = $(this);
    radioButton.on('change', function () {
      setHasNoHazards(radioButton);
    });
  });
  $('.ghs-hazards-selection input[name^=\'object__\'][type="checkbox"]').each(function () {
    const checkbox = $(this);
    checkbox.on('change', function () {
      setHasHazard(checkbox);
    });
  });
});
