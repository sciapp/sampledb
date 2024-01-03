'use strict';
/* eslint-env jquery */

import {
  updateTranslationJSON,
  setTranslationHandler
} from '../sampledb-internationalization.js';

$(function () {
  window.translations = window.getTemplateValue('translations');

  window.languages = window.getTemplateValue('language_info.languages');
  updateTranslationJSON();

  $('#select-languages').on('change', function () {
    const existingLanguages = [];
    $.each(window.translations, function (key, value) {
      existingLanguages.push(value.language_id);
    });
    let selected = ['' + window.getTemplateValue('language_info.english_id')];
    selected = selected.concat($(this).val());
    const languagesToRemove = existingLanguages.filter(n => !selected.includes(n));
    const languagesToAdd = selected.filter(n => !existingLanguages.includes(n));

    for (const languageToRemove of languagesToRemove) {
      window.translations = window.translations.filter(function (translation) {
        return translation.language_id.toString() !== languageToRemove;
      });
      $('[data-language-id="' + languageToRemove + '"]').each(function () {
        $(this).next('.help-block').remove();
        $(this).remove();
      });
    }

    const attributes = [
      ['name', 'names'],
      ['description', 'descriptions'],
      ['object-name-singular', 'object-names-singular'],
      ['object-name-plural', 'object-names-plural'],
      ['view-text', 'view-texts'],
      ['perform-text', 'perform-texts']
    ];
    for (const languageToAdd of languagesToAdd) {
      const languageName = window.languages.find(lang => lang.id.toString() === languageToAdd).name;

      for (let i = 0; i < attributes.length; i++) {
        const attribute = attributes[i][0];
        const attributeGroup = attributes[i][1];
        const formGroup = $('.form-group[data-name="input-' + attributeGroup + '"]');
        $($('#' + attribute + '-template').html()).insertAfter(formGroup.children().last());
        const inputGroup = formGroup.children('.input-group').last();
        $(inputGroup).children('input').attr('id', 'input-' + attribute + '-' + languageToAdd.toString());
        $(inputGroup).children('.input-group-addon[data-name="language"]').text(languageName);
        $(inputGroup).attr('data-language-id', languageToAdd);
        setTranslationHandler(inputGroup);
      }

      // add new object to translations if no object exists with the language_id
      window.translations.push({
        language_id: languageToAdd.toString(),
        name: '',
        description: '',
        object_name: '',
        object_name_plural: '',
        view_text: '',
        perform_text: ''
      });
    }
  });

  if (window.getTemplateValue('is_create_form')) {
    $('#select-languages').selectpicker('val', ['' + window.getTemplateValue('language_info.english_id')]);
  }
  $('#select-languages').change();
  $('.form-group[data-name="input-names"] .input-group[data-language-id], .form-group[data-name="input-descriptions"] .input-group[data-language-id], .form-group[data-name="input-object-names-singular"] .input-group[data-language-id], .form-group[data-name="input-object-names-plural"] .input-group[data-language-id], .form-group[data-name="input-view-texts"] .input-group[data-language-id], .form-group[data-name="input-perform-texts"] .input-group[data-language-id]').each(function (_, element) {
    setTranslationHandler(element);
  });

  if (window.getTemplateValue('is_create_form')) {
    $('#button-new-translation').click();
  }

  $('form').on('submit', function () {
    $('input').change();
    return $(this).find('.has-error').length === 0;
  });
});
