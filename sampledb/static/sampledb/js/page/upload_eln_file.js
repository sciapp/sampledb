'use strict';
/* eslint-env jquery */

$(function () {
  const fileUpload = $('#input-file-upload');
  const fileSubmit = $('#button-file-submit');
  const fileText = $('#input-file-text');
  function changeHandler () {
    const files = fileUpload[0].files;
    if (files.length === 1) {
      fileText.val(files[0].name);
      fileSubmit.prop('disabled', false);
      fileSubmit.removeClass('disabled');
    } else {
      fileText.val('');
      fileSubmit.prop('disabled', true);
      fileSubmit.addClass('disabled');
    }
  }
  fileUpload.on('change', changeHandler);
  changeHandler();
});
