'use strict';
/* eslint-env jquery */

import {
  updateTranslationJSON,
  setTranslationHandler,
  updateTranslationLanguagesForAllAttributes, updateMarkdownField
} from '../sampledb-internationalization.js';

window.mdeFields = {
  descriptions: [],
  short_descriptions: []
};

$(function () {
  window.translations = window.getTemplateValue('translations');

  window.languages = window.getTemplateValue('language_info.languages');
  updateTranslationJSON();

  $('#select-languages').on('change', function () {
    updateTranslationLanguagesForAllAttributes(
      this,
      [
        ['name', 'name', 'names'],
        ['description', 'description', 'descriptions'],
        ['short_description', 'short-description', 'short-descriptions']
      ]
    );
    updateTranslationJSON();
    updateDescriptionMarkdown();
    updateShortDescriptionMarkdown();
  });

  if (window.getTemplateValue('is_create_form')) {
    $('#select-languages').selectpicker('val', ['' + window.getTemplateValue('language_info.english_id')]);
  }
  $('#select-languages').change();
  $('.form-group[data-name="input-names"] .input-group[data-language-id], .form-group[data-name="input-descriptions"] .input-group[data-language-id], .form-group[data-name="input-short-descriptions"] .input-group[data-language-id]').each(function (_, element) {
    setTranslationHandler(element);
  });

  if (window.getTemplateValue('is_create_form')) {
    $('#button-new-translation').click();
  }

  $('form').on('submit', function () {
    $('input').change();
    return $(this).find('.has-error').length === 0;
  });

  function updateDescriptionMarkdown () {
    updateMarkdownField('input-description-is-markdown', 'descriptions', 'input-descriptions', '300px');
  }
  $('#input-description-is-markdown').change(updateDescriptionMarkdown);
  updateDescriptionMarkdown();

  function updateShortDescriptionMarkdown () {
    updateMarkdownField('input-short-description-is-markdown', 'short_descriptions', 'input-short-descriptions', '100px');
  }
  $('#input-short-description-is-markdown').change(updateShortDescriptionMarkdown);
  updateShortDescriptionMarkdown();
});
