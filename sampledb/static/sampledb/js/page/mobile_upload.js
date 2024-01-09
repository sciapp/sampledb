'use strict';
/* eslint-env jquery */

$('#input-file-upload').on('change', function () {
  const files = $(this).get(0).files;
  const submitButton = $('button[type=submit]');
  if (files.length === 0) {
    submitButton.attr('disabled', 'disabled');
    submitButton.addClass('disabled');
  } else {
    submitButton.removeAttr('disabled');
    submitButton.removeClass('disabled');
  }
});
