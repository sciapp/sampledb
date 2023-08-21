function fileEventHandler(id_prefix, context_id_token, ajax_url) {
  return function() {
    const file_input = $(this);
    const file_id_input = $(`#${id_prefix}_file_id`);
    const file_name_input = $(this).closest('.input-group').find('input[type="text"]');
    file_id_input.val('');
    file_name_input.val('');
    file_id_input.find('option[data-sampledb-temporary-file]').remove();
    if (this.files.length === 1) {
      const file = this.files[0];
      const form_data = new FormData();
      form_data.append("file", file);
      form_data.append("context_id_token", context_id_token);
      $.ajax({
        url: ajax_url,
        data: form_data,
        processData: false,
        contentType: false,
        type: 'POST',
        success: function (data) {
          const temporary_file_option = $('<option></option>');
          temporary_file_option.attr('value', '-' + data);
          temporary_file_option.attr('data-sampledb-temporary-file', "1");
          temporary_file_option.text(file.name);
          file_id_input.append(temporary_file_option);
          file_id_input.prop('disabled', false);
          file_id_input.selectpicker('refresh');
          file_id_input.selectpicker('val', '-' + data);
          file_id_input.selectpicker('refresh');
          file_input.closest('.form-group').removeClass('has-error');
        },
        error: function (data) {
          file_input.val('');
          file_input.closest('.form-group').addClass('has-error');
        }
      });
    } else {
      file_input.closest('.form-group').addClass('has-error');
    }
  }
}
