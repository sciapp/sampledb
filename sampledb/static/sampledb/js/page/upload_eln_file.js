$(function() {
  let file_upload = $('#input-file-upload');
  let file_submit = $('#button-file-submit');
  let file_text = $('#input-file-text');
  function changeHandler() {
    var files = file_upload[0].files;
    if (files.length === 1) {
      file_text.val(files[0].name);
      file_submit.prop('disabled', false);
      file_submit.removeClass('disabled');
    } else {
      file_text.val("");
      file_submit.prop('disabled', true);
      file_submit.addClass('disabled');
    }
  }
  file_upload.on('change', changeHandler);
  changeHandler();
});
