'use strict';
/* eslint-env jquery */

$(function () {
  $('.scicat-export-select-all').click(function () {
    $(this).parent().parent().find('input[type="checkbox"]:not(:disabled)').prop('checked', true);
  });
  $('.scicat-export-select-none').click(function () {
    $(this).parent().parent().find('input[type="checkbox"]:not(:disabled)').prop('checked', false);
  });
});
