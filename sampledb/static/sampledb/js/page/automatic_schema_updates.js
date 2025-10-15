'use strict';
/* eslint-env jquery */

$(function () {
  const selectAllObjectsButton = $('#selectAllObjectsButton');
  const deselectAllObjectsButton = $('#deselectAllObjectsButton');
  const table = selectAllObjectsButton.closest('table');
  const checkboxes = table.find('input[type="checkbox"]:not([disabled])');
  const submitButtons = table.closest('form').find('[type="submit"]');
  submitButtons.prop('disabled', true);
  selectAllObjectsButton.on('click', function () {
    checkboxes.prop('checked', true);
    submitButtons.prop('disabled', checkboxes.length === 0);
  });
  deselectAllObjectsButton.on('click', function () {
    checkboxes.prop('checked', false);
    submitButtons.prop('disabled', true);
  });
  checkboxes.on('change', function () {
    const anyChecked = checkboxes.toArray().some(function (checkbox) {
      return $(checkbox).prop('checked');
    });
    submitButtons.prop('disabled', checkboxes.length === 0 || !anyChecked);
  }).change();

  const currentStatus = window.getTemplateValue('automatic_schema_updates.current_status');
  function checkStatus () {
    $.get(window.getTemplateValue('application_root_path') + 'admin/automatic_schema_updates/status', function (data) {
      if (JSON.stringify(data.updatable_objects_checks) !== JSON.stringify(currentStatus.updatable_objects_checks)) {
        $('#updatableObjectsCheckReloadText').show();
        $('#automaticSchemaUpdateReloadText').hide();
        $('#refreshModal').modal('show');
      } else if (JSON.stringify(data.automatic_schema_updates) !== JSON.stringify(currentStatus.automatic_schema_updates)) {
        $('#updatableObjectsCheckReloadText').hide();
        $('#automaticSchemaUpdateReloadText').show();
        $('#refreshModal').modal('show');
      } else {
        setTimeout(checkStatus, 30 * 1000);
      }
    });
  }
  setTimeout(checkStatus, 30 * 1000);
});
