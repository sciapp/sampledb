'use strict';
/* eslint-env jquery */
/* globals InscrybMDE */

import {
  setupImageDragAndDrop
} from './markdown_image_upload.js';

const ENGLISH_ID = -99;

function updateTranslationJSON () {
  $('#input-translations').val(JSON.stringify(window.translations));
}

function setTranslationHandler (element) {
  const languageID = $(element).data('languageId');
  $(element).find('input, textarea.form-control').on('change blur', function () {
    const input = $(this);
    const translatedText = input.val();
    const translationAttribute = input.data('translationAttribute');
    const emptyText = input.data('emptyText');
    const maxLength = input.data('maxLength');
    const maxLengthText = input.data('maxLengthText');
    const requiredInAllLanguages = input.data('requiredInAllLanguages') !== undefined;

    if ((requiredInAllLanguages || languageID === ENGLISH_ID) && translatedText.trim() === '' && emptyText) {
      $(this).parent().addClass('has-error').next('.help-block').text(emptyText).css('color', 'red');
    } else if (translatedText.length > maxLength) {
      $(this).parent().addClass('has-error').next('.help-block').text(maxLengthText).css('color', 'red');
    } else {
      $(this).parent().removeClass('has-error').next('.help-block').text('');
    }
    window.translations.forEach(function (translation) {
      if (translation.language_id === languageID || translation.language_id === languageID.toString()) {
        translation[translationAttribute] = translatedText;
      }
    });
    updateTranslationJSON();
  });
  $(element).find('input, textarea.form-control').change();
}

function updateTranslationLanguages (languageSelect, templateID, inputIDPrefix, translationAttributes) {
  const existingLanguages = [];
  $.each(window.translations, function (key, value) {
    existingLanguages.push('' + value.language_id);
  });
  let selected = [ENGLISH_ID.toString()];
  selected = selected.concat($(languageSelect).val());
  const languagesToRemove = existingLanguages.filter(n => !selected.includes(n));
  const languagesToAdd = selected.filter(n => !existingLanguages.includes(n));
  const formGroup = $(languageSelect).closest('.form-group[data-name]');
  for (const languageToRemove of languagesToRemove) {
    const inputGroup = formGroup.find('[data-language-id=' + languageToRemove.toString() + ']');
    if (inputGroup.length > 0) {
      const translationAttribute = inputGroup.children('input, textarea').data('translationAttribute');
      inputGroup.remove();
      window.translations.forEach(function (translation) {
        if (translation.language_id.toString() === languageToRemove) {
          translation[translationAttribute] = '';
        }
      });
    }
  }
  for (const language of selected) {
    if (!$('#' + inputIDPrefix + language).length) {
      $($('#' + templateID).html()).insertAfter(formGroup.children().last());
      const inputGroup = formGroup.find('[data-language-id]').last();
      const languageName = window.languages.find(lang => lang.id.toString() === language).name;
      $(inputGroup).children('input, textarea').attr('id', inputIDPrefix + language);
      $(inputGroup).children('.input-group-addon[data-name="language"]').text(languageName);
      $(inputGroup).attr('data-language-id', language);
      setTranslationHandler(inputGroup);
    }
    if (languagesToAdd.includes(language)) {
      window.translations.push({
        language_id: language.toString()
      });
      for (const translationAttribute of translationAttributes) {
        window.translations[window.translations.length - 1][translationAttribute] = '';
      }
    }
  }
}

function updateTranslationLanguagesForAllAttributes (languageSelect, translationAttributes) {
  const existingLanguages = [];
  $.each(window.translations, function (key, value) {
    existingLanguages.push(value.language_id);
  });
  let selected = [ENGLISH_ID.toString()];
  selected = selected.concat($(languageSelect).val());
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
  for (const languageToAdd of languagesToAdd) {
    const languageName = window.languages.find(lang => lang.id.toString() === languageToAdd).name;

    const newTranslation = {
      language_id: languageToAdd.toString()
    };
    for (const translationAttribute of translationAttributes) {
      const attributeKey = translationAttribute[0];
      const attribute = translationAttribute[1];
      const attributeGroup = translationAttribute[2];
      const formGroup = $('.form-group[data-name="input-' + attributeGroup + '"]');
      $($('#' + attribute + '-template').html()).insertAfter(formGroup.children().last());
      const inputGroup = formGroup.children('.input-group').last();
      $(inputGroup).children('input').attr('id', 'input-' + attribute + '-' + languageToAdd.toString());
      $(inputGroup).children('.input-group-addon[data-name="language"]').text(languageName);
      $(inputGroup).attr('data-language-id', languageToAdd);
      setTranslationHandler(inputGroup);
      newTranslation[attributeKey] = '';
    }
    window.translations.push(newTranslation);
  }
}

function getMarkdownButtonTranslation (buttonText) {
  const markdownButtonTranslations = window.getTemplateValue('translations.markdown_buttons');
  if (markdownButtonTranslations && Object.prototype.hasOwnProperty.call(markdownButtonTranslations, buttonText)) {
    return markdownButtonTranslations[buttonText];
  }
  return buttonText;
}

function initMarkdownField (element, height) {
  const mdeField = new InscrybMDE({
    element,
    indentWithTabs: false,
    spellChecker: false,
    status: false,
    minHeight: height,
    forceSync: true,
    autoDownloadFontAwesome: false,
    toolbar: [
      {
        name: 'bold',
        action: InscrybMDE.toggleBold,
        className: 'fa fa-bold',
        title: getMarkdownButtonTranslation('Bold')
      },
      {
        name: 'italic',
        action: InscrybMDE.toggleItalic,
        className: 'fa fa-italic',
        title: getMarkdownButtonTranslation('Italic')
      },
      {
        name: 'heading',
        action: InscrybMDE.toggleHeadingSmaller,
        className: 'fa fa-header',
        title: getMarkdownButtonTranslation('Heading')
      },
      '|',
      {
        name: 'code',
        action: InscrybMDE.toggleCodeBlock,
        className: 'fa fa-code',
        title: getMarkdownButtonTranslation('Code')
      },
      {
        name: 'unordered-list',
        action: InscrybMDE.toggleUnorderedList,
        className: 'fa fa-list-ul',
        title: getMarkdownButtonTranslation('Generic List')
      },
      {
        name: 'ordered-list',
        action: InscrybMDE.toggleOrderedList,
        className: 'fa fa-list-ol',
        title: getMarkdownButtonTranslation('Numbered List')
      },
      '|',
      {
        name: 'link',
        action: InscrybMDE.drawLink,
        className: 'fa fa-link',
        title: getMarkdownButtonTranslation('Create Link')
      },
      {
        name: 'image',
        action: function uploadImage (editor) {
          const fileInput = document.createElement('input');
          fileInput.setAttribute('type', 'file');
          fileInput.setAttribute('accept', '.png,.jpg,.jpeg');
          fileInput.addEventListener('change', function () {
            element.mdeField.codemirror.fileHandler(fileInput.files);
          });
          fileInput.click();
        },
        className: 'fa fa-picture-o',
        title: getMarkdownButtonTranslation('Upload Image')
      },
      {
        name: 'table',
        action: InscrybMDE.drawTable,
        className: 'fa fa-table',
        title: getMarkdownButtonTranslation('Insert Table')
      },
      '|',
      {
        name: 'preview',
        action: InscrybMDE.togglePreview,
        className: 'fa fa-eye no-disable',
        title: getMarkdownButtonTranslation('Toggle Preview'),
        noDisable: true
      }
    ]
  });
  element.mdeField = mdeField;
  mdeField.codemirror.on('change', function () {
    $(element).change();
  });
  // override .CodeMirror default height, so InscrybMDE min-height can work
  $(element).siblings('.CodeMirror').css('height', 'auto');
  return mdeField;
}

function updateMarkdownField (checkboxID, mdeAttribute, dataName, height) {
  window.mdeFields[mdeAttribute].forEach(function (item) {
    item.toTextArea();
  });
  window.mdeFields[mdeAttribute] = [];
  if (checkboxID === null || $('#' + checkboxID).prop('checked')) {
    $(`.form-group[data-name="${dataName}"] [data-language-id], .inline-edit-regular-property[data-name="${dataName}"] [data-language-id], .inline-edit-horizontal-property[data-name="${dataName}"] [data-language-id]`).each(function () {
      const textarea = $(this).find('textarea.form-control');
      if (textarea.length === 1) {
        window.mdeFields[mdeAttribute].push(initMarkdownField(textarea[0], height));
      }
    });
    window.mdeFields[mdeAttribute].forEach(function (item) {
      setupImageDragAndDrop(item);
    });
  }
}

export {
  updateTranslationJSON,
  setTranslationHandler,
  updateTranslationLanguages,
  updateTranslationLanguagesForAllAttributes,
  initMarkdownField,
  updateMarkdownField
};
