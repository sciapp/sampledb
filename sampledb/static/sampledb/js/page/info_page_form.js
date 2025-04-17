'use strict';
/* eslint-env jquery */

import {
  updateTranslationJSON,
  setTranslationHandler,
  updateTranslationLanguagesForAllAttributes,
  updateMarkdownField
} from '../sampledb-internationalization.js';

window.mdeFields = {
  contents: []
};

$(function () {
  window.translations = window.getTemplateValue('translations');

  window.languages = window.getTemplateValue('language_info.languages');
  updateTranslationJSON();

  $('#select-languages').on('change', function () {
    updateTranslationLanguagesForAllAttributes(
      this,
      [
        ['title', 'title', 'titles'],
        ['content', 'content', 'contents']
      ]
    );
    updateTranslationJSON();
    updateContentMarkdown();
  });

  function updateContentMarkdown () {
    updateMarkdownField(null, 'contents', 'input-contents', '300px');
  }
  updateContentMarkdown();

  if (window.getTemplateValue('is_create_form')) {
    $('#select-languages').selectpicker('val', ['' + window.getTemplateValue('language_info.english_id')]);
  }
  $('#select-languages').change();
  $('.form-group[data-name="input-titles"] .input-group[data-language-id], .form-group[data-name="input-contents"] .input-group[data-language-id]').each(function (_, element) {
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
