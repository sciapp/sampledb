'use strict';
/* eslint-env jquery */

import {
  updateTranslationJSON,
  setTranslationHandler,
  updateTranslationLanguages
} from '../sampledb-internationalization.js';

$(function () {
  window.translations = window.getTemplateValue('translations');
  if (window.translations.length === 0) {
    window.translations.push({
      language_id: '' + window.getTemplateValue('language_info.english_id'),
      lang_name: '',
      name: '',
      description: ''
    });
  }

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

  $('[data-name="input-names"] [data-language-id], [data-name="input-descriptions"] [data-language-id]').each(function () {
    setTranslationHandler(this);
  });

  $('form').on('submit', function () {
    $('input').change();
    $('textarea').change();
    window.translations = $.map(window.translations, function (translation, index) {
      if (translation.name === '' && translation.description === '' && translation.language_id !== window.getTemplateValue('language_info.english_id')) {
        return null;
      }
      return translation;
    });
    updateTranslationJSON();
    return $(this).find('.has-error').length === $(this).find('.has-error.may-have-error').length;
  });

  const locationTypePicker = $('select#input-location-type');
  locationTypePicker.on('changed.bs.select', function () {
    const selectedOption = locationTypePicker.find('option:selected');
    if (selectedOption.data('enableParentLocation')) {
      $('select#input-parent-location').prop('disabled', false).closest('.form-group').show();
      $('input#input-parent-location-replacement').prop('disabled', true);
    } else {
      $('select#input-parent-location').prop('disabled', true).closest('.form-group').hide();
      $('input#input-parent-location-replacement').prop('disabled', false);
    }
    if (selectedOption.data('enableResponsibleUsers')) {
      $('select#input-responsible_users').prop('disabled', false).closest('.form-group').show();
    } else {
      $('select#input-responsible_users').prop('disabled', true).closest('.form-group').hide();
    }
    if (selectedOption.data('enableCapacities')) {
      $('#capacity-field-list').show();
    } else {
      $('#capacity-field-list').hide();
    }
  }).trigger('changed.bs.select');
  $('.capacity-toggle').on('change', function () {
    const capacityToggle = $(this);
    const capacityInput = capacityToggle.closest('.form-group').find('input[type="number"]');
    if (capacityToggle.prop('checked')) {
      capacityInput.prop('disabled', true);
    } else {
      capacityInput.prop('disabled', false);
      if (capacityInput.val() === '') {
        capacityInput.val('0');
      }
    }
  }).change();
});
