'use strict';
/* eslint-env jquery */

import {
  updateTranslationJSON,
  setTranslationHandler,
  updateTranslationLanguages
} from '../sampledb-internationalization.js';

$(function () {
  window.translations = window.getTemplateValue('translations');

  window.languages = window.getTemplateValue('language_info.languages');
  updateTranslationJSON();

  $('#select-language-name').selectpicker('val', window.getTemplateValue('name_language_ids').map(String));
  $('#select-language-description').selectpicker('val', window.getTemplateValue('description_language_ids').map(String));

  $('#select-language-name').on('change', function () {
    updateTranslationLanguages(this, 'name-template', 'input-name-', ['name', 'description']);
  }).change();

  $('#select-language-description').on('change', function () {
    updateTranslationLanguages(this, 'description-template', 'input-description-', ['name', 'description']);
  }).change();

  $('.form-group[data-name="input-names"] [data-language-id], .form-group[data-name="input-descriptions"] [data-language-id]').each(function () {
    setTranslationHandler(this);
  });

  $('form').on('submit', function () {
    $('input').change();
    $('textarea').change();
    window.translations = $.map(window.translations, function (translation, index) {
      if (translation.name === '' && translation.description === '' && translation.language_id !== ('' + window.getTemplateValue('language_info.english_id'))) {
        return null;
      }
      return translation;
    });
    updateTranslationJSON();
    return $(this).find('.has-error').length === 0;
  });

  if (window.getTemplateValue('show_edit_form')) {
    const editModal = $('#editProjectModal');
    editModal.removeClass('fade');
    editModal.modal('show');
    editModal.addClass('fade');
  }

  const inviteUserModal = $('#inviteUserModal');
  inviteUserModal.find('input[name="add_directly"]').on('change', function () {
    let buttonText = window.getTemplateValue('translations.invite_user');
    if ($(this).prop('checked')) {
      buttonText = window.getTemplateValue('translations.add_user');
    }
    inviteUserModal.find('button[name="add_user"]').text(buttonText);
  });
});
