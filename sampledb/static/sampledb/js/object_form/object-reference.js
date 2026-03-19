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

function setUpVersionPicker (picker) {
  const objectPicker = picker.find('[name$="__oid"]');
  const objectIDName = objectPicker.attr('name');
  const idPrefix = objectIDName.substring(0, objectIDName.length - 4);
  const versionIDName = idPrefix + '_vid';
  const versionPicker = picker.parent().find(`[name="${versionIDName}"]`);
  if (versionPicker.attr('type') === 'hidden') {
    return;
  }
  versionPicker.off('change');
  versionPicker.on('change', function () {
    versionPicker.data('sampledb-default-object-selected', '');
    versionPicker.data('sampledb-default-version-selected', '');
    versionPicker.attr('data-sampledb-default-object-selected', '');
    versionPicker.attr('data-sampledb-default-version-selected', '');
  });
  const inputGroup = versionPicker.closest('.input-group');
  const checkbox = inputGroup.find('[type="checkbox"');
  checkbox.off('change');
  checkbox.on('change', function () {
    const isChecked = checkbox.prop('checked');
    versionPicker.prop('disabled', !isChecked);
    if (isChecked && objectPicker.val() !== '' && versionPicker.attr('max') !== '' && versionPicker.val() === '') {
      versionPicker.val(versionPicker.attr('max'));
    }
  });
  checkbox.trigger('change');
  checkbox.on('change', function () {
    versionPicker.trigger('change');
  });
  function handleObjectChange () {
    if (objectPicker.val() === '') {
      checkbox.prop('checked', false);
      checkbox.prop('disabled', true);
      versionPicker.prop('disabled', true);
    } else {
      checkbox.prop('checked', false);
      checkbox.prop('disabled', false);
      versionPicker.prop('disabled', true);
      versionPicker.val('');
      const defaultObject = versionPicker.data('sampledb-default-object-selected');
      const defaultVersion = versionPicker.data('sampledb-default-version-selected');
      if (defaultObject !== '' && defaultVersion !== '' && +defaultObject === +objectPicker.val()) {
        checkbox.prop('checked', true);
        checkbox.prop('disabled', false);
        versionPicker.prop('disabled', false);
        versionPicker.val(defaultVersion);
      }
      if (objectPicker.prop('tagName') === 'SELECT') {
        const currentOption = objectPicker.find(`option[value="${objectPicker.val()}"]`);
        const currentVersionId = currentOption.data('version-id');
        if (currentVersionId || currentVersionId === 0) {
          versionPicker.attr('max', currentVersionId);
        }
      }
    }
  }
  objectPicker.on('object_change.sampledb', handleObjectChange); // typeahead cases
  objectPicker.on('changed.bs.select', handleObjectChange);
  objectPicker.on('loaded.bs.select', handleObjectChange);
  objectPicker.on('refreshed.bs.select', handleObjectChange);
}

export {
  addActionFilterButton,
  setUpVersionPicker
};
