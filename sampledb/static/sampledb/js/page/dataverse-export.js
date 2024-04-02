'use strict';
/* eslint-env jquery */

$(function () {
  $('.dataverse-export-select-all').click(function () {
    $(this).parent().parent().find('input[type="checkbox"]:not(:disabled)').prop('checked', true);
  });
  $('.dataverse-export-select-none').click(function () {
    $(this).parent().parent().find('input[type="checkbox"]:not(:disabled)').prop('checked', false);
  });
});
