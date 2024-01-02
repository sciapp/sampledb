$(function(){
  const language_picker = $('#select-languages');
  function updateEnabledLanguages() {
    let language_ids = $.map(language_picker.selectpicker('val'), function(language_id) {
      return +language_id;
    });
    language_ids.push(window.getTemplateValue('language_info.english_id'));
    $('[data-language-id]').each(function(_, e) {
      let element = $(e);
      if (language_ids.includes(+element.data('languageId'))) {
        element.show();
        element.find('input').prop('disabled', false);
      } else {
        element.hide();
        element.find('input').prop('disabled', true);
      }
    });
  }
  language_picker.on('changed.bs.select', updateEnabledLanguages);
  updateEnabledLanguages();

  // enforce text length limits
  $('[data-language-id] input').on('change', function(e) {
    const input = $(this);
    const input_text = input.val();
    let error_text = '';
    if (input_text.length === 0) {
      error_text = input.data('emptyText');
    } else if (input_text.length > input.data('maxLength')) {
      error_text = input.data('maxLengthText');
    }
    const input_group = input.parent();
    const input_help_block = input_group.next('.help-block');
    input_help_block.text(error_text);

    input_group.parent().toggleClass('has-error', error_text !== '');
  }).change();
});
