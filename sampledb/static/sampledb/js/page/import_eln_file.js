'use strict';
/* eslint-env jquery */

$(function () {
  $('#form-eln_import').on('submit', function () {
    const checkboxes = $('.checkboxes-fed-identities');
    const result = [];
    checkboxes.each(function () {
      if ($(this).is(':checked')) {
        result.push(btoa($(this).data('eln-user-id')));
      }
    });
    $('#federated-identities-list').val(result.join(','));
  });
});
