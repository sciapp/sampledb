'use strict';
/* eslint-env jquery */

import {
  checkSubmittable
} from './multiselect-base.js';

const descriptionTranslations = { en: '' };

$(function () {
  const locationPicker = $('#object-location');
  const responsibleUserPicker = $('#object-responsible-user');
  locationPicker.selectpicker('val', '-1');
  responsibleUserPicker.selectpicker('val', '-1');
  locationPicker.on('change', checkSubmittable);
  responsibleUserPicker.on('change', checkSubmittable);

  window.checkSubmittableImpl = function (submitTooltip, submitButton) {
    if (responsibleUserPicker.val() === '-1' && locationPicker.val() === '-1') {
      submitTooltip.attr('data-original-title', window.getTemplateValue('translations.you_have_to_select_a_location_or_responsible_user')).tooltip('setContent').tooltip('enable');
      submitButton.prop('disabled', true);
      return false;
    }
    return true;
  };

  function updateObjectLocationTranslationJSON () {
    const translationJSON = JSON.stringify(descriptionTranslations);
    $('#input-object_location-translations').val(translationJSON);
  }

  $('#select-language-object_location').on('change', function () {
    const inputDescriptions = $('[data-name="input-descriptions"]');
    for (const languageOption of $(this).find('option')) {
      const language = $(languageOption).val();
      let inputGroup = $(`#input-group-object_location-${language}`);
      if ($(languageOption).prop('selected')) {
        if (!inputGroup.length) {
          inputGroup = $($('#object_location-template').html());
          inputDescriptions.append(inputGroup);
          inputGroup.attr('id', `input-group-object_location-${language}`);
          inputGroup.children('.input-group-addon[data-name="language"]').text($(languageOption).text());
          inputGroup.find('textarea').on('change blur', function () {
            descriptionTranslations[language] = $(this).val();
            updateObjectLocationTranslationJSON();
          }).trigger('change');
        }
      } else {
        inputGroup.remove();
        delete descriptionTranslations[language];
      }
    }

    updateObjectLocationTranslationJSON();
  }).trigger('change');
});
