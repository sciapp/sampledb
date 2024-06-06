'use strict';
/* eslint-env jquery */

function updateSelectLanguage (selectpicker) {
  let enabledLanguages = $(selectpicker).selectpicker('val');
  if (!Array.isArray(enabledLanguages)) {
    return;
  }
  if (enabledLanguages === '' || enabledLanguages.length === 0) {
    enabledLanguages = ['en'];
  } else {
    enabledLanguages.push('en');
  }
  const parentFormGroup = $(selectpicker).closest('.form-group, .inline-edit-regular-property, .inline-edit-horizontal-property');
  parentFormGroup.find('[data-sampledb-language-input-for]').each(function () {
    const langCode = $(this).data('sampledb-language-input-for');
    if (enabledLanguages.includes(langCode)) {
      $(this).show();
    } else {
      $(this).hide();
    }
  });

  const disabledLanguagesError = $('[data-sampledb-disabled-languages-picker="' + selectpicker.id + '"');
  if (disabledLanguagesError.length === 1) {
    const disabledLanguageCodes = disabledLanguagesError.data('sampledbDisabledLanguagesCodes').split(',');
    let allDisabledLanguagesRemoved = true;
    for (let i = 0; i < disabledLanguageCodes.length; i++) {
      if (enabledLanguages.includes(disabledLanguageCodes[i])) {
        allDisabledLanguagesRemoved = false;
        break;
      }
    }
    if (allDisabledLanguagesRemoved) {
      disabledLanguagesError.hide();
    } else {
      disabledLanguagesError.show();
    }
  }
}

$(function () {
  const selectLanguageSelectpicker = $('.select-language');
  selectLanguageSelectpicker.on('changed.bs.select', function () {
    updateSelectLanguage(this);
  });
  selectLanguageSelectpicker.each(function (_, selectpicker) {
    updateSelectLanguage(selectpicker);
  });
});

export {
  updateSelectLanguage
};
