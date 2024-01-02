$('#input-file-upload').on('change', function() {
  var files = $(this).get(0).files;
  var submitButton = $('button[type=submit]');
  if (files.length === 0) {
    submitButton.attr('disabled', 'disabled');
    submitButton.addClass('disabled');
  } else {
    submitButton.removeAttr('disabled');
    submitButton.removeClass('disabled');
  }
});
