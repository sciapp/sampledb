'use strict';
/* eslint-env jquery */
/* globals FileReader */

/**
 * Sets up an event handler for dragging images onto a markdown editor.
 * @param element the markdown editor as a jQuery element
 */
function setupImageDragAndDrop (element) {
  element.codemirror.fileHandler = function (files) {
    if (files.length > 0) {
      const file = files[0];

      if (file && (file.type === 'image/png' || file.type === 'image/jpeg')) {
        const reader = new FileReader();
        reader.addEventListener('load', function () {
          $.post(
            window.getTemplateValue('application_root_path') + 'markdown_images/',
            reader.result,
            function (imageUrl) {
              element.value(element.value() + '![](' + imageUrl + ')');
            }
          );
        }, false);
        reader.readAsDataURL(file);
      }
    }
  };
  element.codemirror.on('drop', function (data, e) {
    e.preventDefault();
    e.stopPropagation();
    element.codemirror.fileHandler(e.dataTransfer.files);
    return false;
  });
}

export {
  setupImageDragAndDrop
};
