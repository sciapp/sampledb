'use strict';
/* eslint-env jquery */

import {
  fileEventHandler
} from '../sampledb-file-form-handler.js';

$(function () {
  const temporaryFileUploadURL = window.getTemplateValue('temporary_file_upload_url');
  $('input[type="file"][data-id-prefix]').each(function () {
    const filePickerInput = $(this);
    const idPrefix = filePickerInput.data('id-prefix');
    if (!idPrefix.includes('!')) {
      filePickerInput.on('change', fileEventHandler(filePickerInput.data('context-id-token'), temporaryFileUploadURL));
    }
  });
});
