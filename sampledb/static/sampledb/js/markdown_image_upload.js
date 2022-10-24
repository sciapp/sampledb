function setupImageDragAndDrop(element) {
  element.codemirror.fileHandler = function(files) {
    if (files.length > 0) {
      let file = files[0];

      if (file && (file.type === "image/png" || file.type === "image/jpeg")) {
        var reader = new FileReader();
        reader.addEventListener("load", function () {
          $.post(
              window.application_root_path + 'markdown_images/',
              reader.result,
              function(image_url) {
                element.value(element.value() + "![](" + image_url + ")");
              }
          );
        }, false);
        reader.readAsDataURL(file);
      }
    }
  };
  element.codemirror.on('drop', function(data, e) {
    e.preventDefault();
    e.stopPropagation();
    element.codemirror.fileHandler(e.dataTransfer.files);
    return false;
  });
}
