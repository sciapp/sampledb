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
});
