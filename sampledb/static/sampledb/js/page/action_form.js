'use strict';
/* eslint-env jquery */

import {
  updateTranslationJSON,
  setTranslationHandler,
  updateTranslationLanguages,
  updateMarkdownField
} from '../sampledb-internationalization.js';

window.mdeFields = {
  descriptions: [],
  short_descriptions: []
};

$(function () {
  window.languages = window.getTemplateValue('language_info.languages');

  window.translations = window.getTemplateValue('translations');
  updateTranslationJSON();

  if (!window.getTemplateValue('load_translations')) {
    $('.select-language').selectpicker('val', ['' + window.getTemplateValue('language_info.english_id')]);
  }

  $('#select-language-name').on('change', function () {
    updateTranslationLanguages(this, 'name-template', 'input-name-', ['name', 'description', 'short_description']);
  }).change();

  $('#select-language-description').on('change', function () {
    updateTranslationLanguages(this, 'description-template', 'input-description-', ['name', 'description', 'short_description']);
    updateDescriptionMarkdown();
  }).change();

  $('#select-language-short-description').on('change', function () {
    updateTranslationLanguages(this, 'short-description-template', 'input-short-description-', ['name', 'description', 'short_description']);
    updateShortDescriptionMarkdown();
  }).change();

  $('.form-group[data-name="input-names"] [data-language-id], .form-group[data-name="input-descriptions"] [data-language-id], .form-group[data-name="input-short-descriptions"] [data-language-id]').each(function (_, element) {
    setTranslationHandler(element);
  });

  $('form').on('submit', function () {
    $('input').change();
    $('textarea').change();
    window.translations = $.map(window.translations, function (translation, index) {
      if (translation.name === '' && translation.description === '' &&
           translation.short_description === '' && +translation.language_id !== window.getTemplateValue('language_info.english_id')) {
        return null;
      }
      return translation;
    });
    updateTranslationJSON();
    return $(this).find('.has-error').length === 0;
  });

  function updateDescriptionMarkdown () {
    updateMarkdownField('input-markdown', 'descriptions', 'input-descriptions', '300px');
  }
  $('#input-markdown').change(updateDescriptionMarkdown);
  updateDescriptionMarkdown();

  function updateShortDescriptionMarkdown () {
    updateMarkdownField('input-short-description-is-markdown', 'short_descriptions', 'input-short-descriptions', '100px');
  }
  $('#input-short-description-is-markdown').change(updateShortDescriptionMarkdown);
  updateShortDescriptionMarkdown();

  function updateTopicsUseInstrumentTopicsFields () {
    const instrumentSelectpicker = $('#input-instrument');
    const hasInstrument = (instrumentSelectpicker.length === 1) && instrumentSelectpicker.selectpicker('val') !== '-1';
    const useInstrumentTopicsCheckbox = $('#input-use-instrument-topics');
    useInstrumentTopicsCheckbox.prop('disabled', !hasInstrument);
    useInstrumentTopicsCheckbox.closest('.control-label').toggleClass('text-muted', !hasInstrument);
    if (!hasInstrument) {
      useInstrumentTopicsCheckbox.prop('checked', false);
    }
    const useInstrumentTopics = (useInstrumentTopicsCheckbox.length === 1) && useInstrumentTopicsCheckbox.prop('checked');
    const topicsSelectpicker = $('#input-topics');
    topicsSelectpicker.prop('disabled', useInstrumentTopics);
    topicsSelectpicker.selectpicker('refresh');
  }
  updateTopicsUseInstrumentTopicsFields();
  $('#input-instrument').on('change', updateTopicsUseInstrumentTopicsFields);
  $('#input-use-instrument-topics').on('change', updateTopicsUseInstrumentTopicsFields);
});
