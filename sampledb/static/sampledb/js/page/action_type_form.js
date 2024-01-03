import {
  updateTranslationJSON,
  setTranslationHandler,
} from '../sampledb-internationalization.js';

$(function () {
  window.translations = window.getTemplateValue('translations');

  window.languages = window.getTemplateValue('language_info.languages');
  updateTranslationJSON();

  $('#select-languages').on('change', function () {
    let existing_languages = []
    $.each(window.translations, function (key, value) {
      existing_languages.push(value.language_id)
    })
    let selected = ['' + window.getTemplateValue('language_info.english_id')]
    selected = selected.concat($(this).val())
    let remove_languages = existing_languages.filter(n => !selected.includes(n))
    let add_languages = selected.filter(n => !existing_languages.includes(n))

    for (const del_language of remove_languages){
      window.translations = window.translations.filter(function (translation) {
        return translation.language_id.toString() !==  del_language;
      });
      $('[data-language-id="' + del_language + '"]').each(function () {
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
      ['perform-text', 'perform-texts'],
    ];
    for (const new_language of add_languages) {
      let lang_name = window.languages.find(lang => lang.id.toString() === new_language).name;

      for (let i = 0; i < attributes.length; i++) {
        let attribute = attributes[i][0];
        let attribute_group = attributes[i][1];
        let form_group = $('.form-group[data-name="input-' + attribute_group + '"]');
        $($('#' + attribute + '-template').html()).insertAfter(form_group.children().last());
        let input_group = form_group.children('.input-group').last()
        $(input_group).children('input').attr('id', 'input-' + attribute + '-' + new_language.toString())
        $(input_group).children('.input-group-addon[data-name="language"]').text(lang_name)
        $(input_group).attr('data-language-id', new_language);
        setTranslationHandler(input_group);
      }

      // add new object to translations if no object exists with the language_id
      window.translations.push({
        'language_id': new_language.toString(),
        'name': '',
        'description': '',
        'object_name': '',
        'object_name_plural': '',
        'view_text': '',
        'perform_text': '',
      });
      }
  });

  if (window.getTemplateValue('is_create_form')) {
    $('#select-languages').selectpicker('val', ['' + window.getTemplateValue('language_info.english_id')]);
  }
  $('#select-languages').change();
  $('.form-group[data-name="input-names"] .input-group[data-language-id], .form-group[data-name="input-descriptions"] .input-group[data-language-id], .form-group[data-name="input-object-names-singular"] .input-group[data-language-id], .form-group[data-name="input-object-names-plural"] .input-group[data-language-id], .form-group[data-name="input-view-texts"] .input-group[data-language-id], .form-group[data-name="input-perform-texts"] .input-group[data-language-id]').each(function(_, element) {
    setTranslationHandler(element);
  });

  if (window.getTemplateValue('is_create_form')) {
    $('#button-new-translation').click();
  }

  $('form').on('submit', function () {
    $('input').change();
    return $(this).find('.has-error').length === 0;
  })
});
