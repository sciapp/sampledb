'use strict';
/* eslint-env jquery */

$(function () {
  const languagePicker = $('#select-languages');
  function updateEnabledLanguages () {
    const languageIDs = $.map(languagePicker.selectpicker('val'), function (languageID) {
      return +languageID;
    });
    languageIDs.push(window.getTemplateValue('language_info.english_id'));
    $('[data-language-id]').each(function (_, e) {
      const element = $(e);
      if (languageIDs.includes(+element.data('languageId'))) {
        element.show();
        element.find('input').prop('disabled', false);
      } else {
        element.hide();
        element.find('input').prop('disabled', true);
      }
    });
  }
  languagePicker.on('changed.bs.select', updateEnabledLanguages);
  updateEnabledLanguages();

  // enforce text length limits
  $('[data-language-id] input').on('change', function (e) {
    const input = $(this);
    const inputText = input.val();
    let errorText = '';
    if (inputText.length === 0) {
      errorText = input.data('emptyText');
    } else if (inputText.length > input.data('maxLength')) {
      errorText = input.data('maxLengthText');
    }
    const inputGroup = input.parent();
    const inputHelpBlock = inputGroup.next('.help-block');
    inputHelpBlock.text(errorText);

    inputGroup.parent().toggleClass('has-error', errorText !== '');
  }).change();
});
