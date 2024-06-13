'use strict';
/* eslint-env jquery */

function addActionFilterButton (picker) {
  const filterButton = $(`<button type="button" class="btn btn-default objectpicker-filter-button"  data-toggle="tooltip" data-placement="left" title="${window.getTemplateValue('translations.filter_by_action')}"><i class="fa fa-filter"></i></button>`);
  picker.append(filterButton);
  const objectpicker = picker.find('.selectpicker');
  const actionpicker = picker.parent().find('select.objectpicker-actionpicker');

  filterButton.tooltip();
  filterButton.on('click', function () {
    actionpicker.selectpicker('toggle');
  });
  actionpicker.on('hidden.bs.select', function () {
    const actionID = actionpicker.selectpicker('val');
    if (actionID === '') {
      objectpicker.find('option').prop('disabled', false);
    } else {
      objectpicker.find('option').prop('disabled', true);
      objectpicker.find(`option[data-action-id="${actionID}"]`).prop('disabled', false);
    }
    objectpicker.find('option[value=""]').prop('disabled', false);
    objectpicker.selectpicker('refresh');
    objectpicker.selectpicker('toggle');
    if (objectpicker.selectpicker('val') === null) {
      objectpicker.selectpicker('val', '-');
    }
  });
}

export {
  addActionFilterButton
};
