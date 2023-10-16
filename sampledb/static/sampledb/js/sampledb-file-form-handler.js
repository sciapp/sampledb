'use strict';
/* eslint-env jquery */

/**
 * Generates a file form field event handler with the parameters needed to upload temporary files bound to it.
 * @param idPrefix the ID prefix of the form field
 * @param contextIDToken the context ID token for this form
 * @param ajaxURL the URL to upload the file to
 * @returns {(function(): void)|*} the event handler
 */
function fileEventHandler (idPrefix, contextIDToken, ajaxURL) {
  return function () {
    const fileInput = $(this);
    const fileIDInput = $(`#${idPrefix}_file_id`);
    const fileNameInput = $(this).closest('.input-group').find('input[type="text"]');
    fileIDInput.val('');
    fileNameInput.val('');
    fileIDInput.find('option[data-sampledb-temporary-file]').remove();
    if (this.files.length === 1) {
      const file = this.files[0];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('context_id_token', contextIDToken);
      $.ajax({
        url: ajaxURL,
        data: formData,
        processData: false,
        contentType: false,
        type: 'POST',
        success: function (data) {
          const temporaryFileOption = $('<option></option>');
          temporaryFileOption.attr('value', '-' + data);
          temporaryFileOption.attr('data-sampledb-temporary-file', '1');
          temporaryFileOption.text(file.name);
          fileIDInput.append(temporaryFileOption);
          fileIDInput.prop('disabled', false);
          fileIDInput.selectpicker('refresh');
          fileIDInput.selectpicker('val', '-' + data);
          fileIDInput.selectpicker('refresh');
          fileInput.closest('.form-group').removeClass('has-error');
        },
        error: function (data) {
          fileInput.val('');
          fileInput.closest('.form-group').addClass('has-error');
        }
      });
    } else {
      fileInput.closest('.form-group').addClass('has-error');
    }
  };
}

export {
  fileEventHandler
};
