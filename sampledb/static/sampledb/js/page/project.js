import {
  updateTranslationJSON,
  setTranslationHandler,
  updateTranslationLanguages,
} from '../sampledb-internationalization.js';

$(function (){
  window.translations = window.getTemplateValue('translations');

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

  $('.form-group[data-name="input-names"] [data-language-id], .form-group[data-name="input-descriptions"] [data-language-id]').each(function () {
    setTranslationHandler(this);
  });

  $('form').on('submit', function() {
    $('input').change();
    $('textarea').change();
    window.translations = $.map(window.translations, function(translation, index){
      if (translation.name  === '' && translation.description === '' && translation.language_id !== ('' + window.getTemplateValue('language_info.english_id'))) {
        return null;
      }
      return translation;
    });
    updateTranslationJSON();
    return $(this).find('.has-error').length === 0;
  })

  if (window.getTemplateValue('show_edit_form')) {
    var edit_modal = $('#editProjectModal');
    edit_modal.removeClass('fade');
    edit_modal.modal('show');
    edit_modal.addClass('fade');
  }
});
