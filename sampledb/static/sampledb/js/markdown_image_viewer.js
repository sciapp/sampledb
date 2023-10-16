'use strict';
/* eslint-env jquery */

// Sets event handlers for showing previews of markdown images when clicking on them.
$(function () {
  $('.action-user-content img, .instrument-user-content img, .object-user-content img').each(function (_, img) {
    $(img).click(function () {
      const preview = $(
        '<span class="fullscreen-image-preview">' +
        '  <span class="close-fullscreen-image-preview"><i class="fa fa-close fa-fw"></i></span>' +
        '  <a href="#">' +
        '    <span class="download-fullscreen-image-preview"><i class="fa fa-download fa-fw"></i></span>' +
        '  </a>' +
        '  <img src="" alt="Fullscreen Image Preview">' +
        '</span>'
      );
      $(this).parent().append(preview);
      preview.find('img').attr('src', $(this).attr('src'));
      preview.find('a').attr('href', $(this).attr('src'));
      preview.on('click', function (e) {
        $(this).hide();
      });
      preview.find('img').on('click', function (e) {
        e.stopPropagation();
      });
      preview.find('.download-fullscreen-image-preview').on('click', function (e) {
        e.stopPropagation();
      });
      preview.show();
    });
  });
});
