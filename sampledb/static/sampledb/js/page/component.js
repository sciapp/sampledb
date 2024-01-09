'use strict';
/* eslint-env jquery */

$(document).ready(function () {
  if (window.getTemplateValue('show_edit_form')) {
    const editModal = $('#editComponentModal');
    editModal.removeClass('fade');
    editModal.modal('show');
    editModal.addClass('fade');
  }
  if (window.getTemplateValue('created_api_token')) {
    $('#viewApiTokenModal').modal('show');
    $('#api-token button').bind('click', function () {
      const input = document.querySelector('#api-token input');
      input.setSelectionRange(0, input.value.length + 1);
      $(input).focus();
      try {
        const success = document.execCommand('copy');
        if (success) {
          $('#api-token-copy-notes').text(window.getTemplateValue('translations.copied'));
          $('#api-token').removeClass('has-error').addClass('has-success');
        } else {
          $('#api-token-copy-notes').text(window.getTemplateValue('translations.could_not_copy_to_clipboard'));
          $('#api-token').removeClass('has-success').addClass('has-error');
        }
      } catch (err) {
        $('#api-token-copy-notes').text(window.getTemplateValue('translations.could_not_copy_to_clipboard'));
        $('#api-token').removeClass('has-success').addClass('has-error');
      }
    });
  }
});
if (window.getTemplateValue('create_api_token_form_has_errors')) {
  $('#createApiTokenModal').modal('show');
}
if (window.getTemplateValue('add_own_api_token_form_has_errors')) {
  $('#createOwnApiTokenModal').modal('show');
}
$('span.copy-uuid').on('click', function () {
  const button = $(this);
  navigator.clipboard.writeText(button.attr('data-uuid')).then(
    () => {
      const wrapper = button.parent();
      button.tooltip('hide');
      wrapper.tooltip('show');
      setTimeout(function () {
        wrapper.tooltip('hide');
      }, 500);
    }
  );
});
