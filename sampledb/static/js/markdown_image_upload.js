function setupImageDragAndDrop(element) {
  element.codemirror.on('drop', function(data, e) {
    var file;
    var files;
    // Check if files were dropped
    files = e.dataTransfer.files;
    if (files.length > 0) {
      e.preventDefault();
      e.stopPropagation();
      file = files[0];

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
      return false;
    }
  });
}
