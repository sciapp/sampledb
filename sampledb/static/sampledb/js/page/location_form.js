import {
  updateTranslationJSON,
  setTranslationHandler,
  updateTranslationLanguages
} from '../sampledb-internationalization.js';

$(function (){
  window.translations = window.getTemplateValue('translations');
  if (window.translations.length === 0) {
    window.translations.push({
      'language_id': '' + window.getTemplateValue('language_info.english_id'),
      'lang_name': '',
      'name': '',
      'description': ''
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

  $('[data-name="input-names"] [data-language-id], [data-name="input-descriptions"] [data-language-id]').each(function() {
    setTranslationHandler(this);
  });

  $('form').on('submit', function() {
    $('input').change();
    $('textarea').change();
    window.translations = $.map(window.translations, function(translation, index){
      if (translation.name  === '' && translation.description === '' && translation.language_id !== window.getTemplateValue('language_info.english_id')){
        return null;
      }
      return translation
    });
    updateTranslationJSON();
    return $(this).find('.has-error').length === $(this).find('.has-error.may-have-error').length;
  });

  let location_type_picker = $('select#input-location-type');
  location_type_picker.on('changed.bs.select', function() {
      let selected_option = location_type_picker.find('option:selected');
      if (selected_option.data('enableParentLocation')) {
          $('select#input-parent-location').prop('disabled', false).closest('.form-group').show();
          $('input#input-parent-location-replacement').prop('disabled', true);
      } else {
          $('select#input-parent-location').prop('disabled', true).closest('.form-group').hide();
          $('input#input-parent-location-replacement').prop('disabled', false);
      }
      if (selected_option.data('enableResponsibleUsers')) {
          $('select#input-responsible_users').prop('disabled', false).closest('.form-group').show();
      } else {
          $('select#input-responsible_users').prop('disabled', true).closest('.form-group').hide();
      }
      if (selected_option.data('enableCapacities')) {
          $('#capacity-field-list').show();
      } else {
          $('#capacity-field-list').hide();
      }
  }).trigger('changed.bs.select');
  $('.capacity-toggle').on('change', function() {
    let capacity_toggle = $(this)
    let capacity_input = capacity_toggle.closest('.form-group').find('input[type="number"]');
    if (capacity_toggle.prop('checked')) {
      capacity_input.prop('disabled', true);
    } else {
      capacity_input.prop('disabled', false);
      if (capacity_input.val() === "") {
        capacity_input.val("0");
      }
    }
  }).change();
});
