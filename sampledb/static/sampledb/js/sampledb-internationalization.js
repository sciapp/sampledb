const ENGLISH_ID = -99;

function updateTranslationJSON() {
  let translation_json = JSON.stringify(window.translations);
  $('#input-translations').val(translation_json);
}

function setTranslationHandler(element) {
  let language_id = $(element).data('languageId');
  $(element).find('input, textarea.form-control').on('change', function() {
    const input = $(this);
    let translated_text = input.val();
    let translation_attribute = input.data('translationAttribute');
    let empty_text = input.data('emptyText');
    let max_length = input.data('maxLength');
    let max_length_text = input.data('maxLengthText');
    let required_in_all_languages = input.data('requiredInAllLanguages') !== undefined;

    if ((required_in_all_languages || language_id === ENGLISH_ID) && translated_text === "" && empty_text) {
      $(this).parent().addClass('has-error').next('.help-block').text(empty_text).css('color', 'red');
    } else if (translated_text.length > max_length) {
      $(this).parent().addClass('has-error').next('.help-block').text(max_length_text).css('color', 'red');
    } else {
      $(this).parent().removeClass('has-error').next('.help-block').text("");
    }
    window.translations.forEach(function (translation) {
      if (translation.language_id === language_id || translation.language_id === language_id.toString()) {
        translation[translation_attribute] = translated_text;
      }
    });
    updateTranslationJSON();
  });
  $(element).find('input, textarea.form-control').change();
}

function updateTranslationLanguages(language_select, template_id, input_id_prefix, translation_attributes) {
  let existing_languages = [];
  $.each(window.translations, function (key, value) {
     existing_languages.push("" + value.language_id);
  })
  let selected = [ENGLISH_ID.toString()];
  selected = selected.concat($(language_select).val());
  let remove_languages = existing_languages.filter(n => !selected.includes(n));
  let add_languages = selected.filter(n => !existing_languages.includes(n));
  let form_group = $(language_select).parent().parent().parent();
  for (const del_language of remove_languages){
    let input_group = form_group.find('[data-language-id=' + del_language.toString() + ']');
    if (input_group.length > 0) {
      let translation_attribute = input_group.children('input, textarea').data('translationAttribute');
      input_group.remove();
      window.translations.forEach(function (translation) {
        if (translation.language_id.toString() === del_language) {
          translation[translation_attribute] = '';
        }
      });
    }
  }
  for (const language of selected) {
    if (!$('#' + input_id_prefix + language).length) {
      $($('#' + template_id).html()).insertAfter(form_group.children().last());
      let input_group = form_group.find('[data-language-id]').last();
      let lang_name = window.languages.find(lang => lang.id.toString() === language).name;
      $(input_group).children('input, textarea').attr('id', input_id_prefix + language);
      $(input_group).children('.input-group-addon[data-name="language"]').text(lang_name);
      $(input_group).attr('data-language-id', language);
      setTranslationHandler(input_group);
    }
    if (add_languages.includes(language)) {
      window.translations.push({
        'language_id': language.toString(),
      });
      for (const translation_attribute of translation_attributes) {
        window.translations[window.translations.length - 1][translation_attribute] = '';
      }
    }
  }
}

function getMarkdownButtonTranslation(button_text) {
  if (window.markdown_button_translations && window.markdown_button_translations.hasOwnProperty(button_text)) {
    return window.markdown_button_translations[button_text];
  }
  return button_text;
}

function initMarkdownField(element, height) {
  let mde_field = new InscrybMDE({
    element: element,
    indentWithTabs: false,
    spellChecker: false,
    status: false,
    minHeight: height,
    forceSync: true,
    toolbar: [
        {
          name: "bold",
          action: InscrybMDE.toggleBold,
          className: "fa fa-bold",
          title: getMarkdownButtonTranslation("Bold"),
        },
        {
          name: "italic",
          action: InscrybMDE.toggleItalic,
          className: "fa fa-italic",
          title: getMarkdownButtonTranslation("Italic"),
        },
        {
          name: "heading",
          action: InscrybMDE.toggleHeadingSmaller,
          className: "fa fa-header",
          title: getMarkdownButtonTranslation("Heading"),
        },
        "|",
        {
          name: "code",
          action: InscrybMDE.toggleCodeBlock,
          className: "fa fa-code",
          title: getMarkdownButtonTranslation("Code"),
        },
        {
          name: "unordered-list",
          action: InscrybMDE.toggleUnorderedList,
          className: "fa fa-list-ul",
          title: getMarkdownButtonTranslation("Generic List"),
        },
        {
          name: "ordered-list",
          action: InscrybMDE.toggleOrderedList,
          className: "fa fa-list-ol",
          title: getMarkdownButtonTranslation("Numbered List"),
        },
        "|",
        {
          name: "link",
          action: InscrybMDE.drawLink,
          className: "fa fa-link",
          title: getMarkdownButtonTranslation("Create Link"),
        },
        {
          name: "image",
          action: function uploadImage(editor) {
            let file_input = document.createElement("input");
            file_input.setAttribute("type", "file");
            file_input.setAttribute("accept", ".png,.jpg,.jpeg");
            file_input.addEventListener("change", function() {
              element.mde_field.codemirror.fileHandler(file_input.files);
            });
            file_input.click();
          },
          className: "fa fa-picture-o",
          title: getMarkdownButtonTranslation("Upload Image"),
        },
        {
          name: "table",
          action: InscrybMDE.drawTable,
          className: "fa fa-table",
          title: getMarkdownButtonTranslation("Insert Table"),
        },
        "|",
        {
          name: "preview",
          action: InscrybMDE.togglePreview,
          className: "fa fa-eye no-disable",
          title: getMarkdownButtonTranslation("Toggle Preview"),
          noDisable: true,
        }
    ]
  });
  element.mde_field = mde_field;
  mde_field.codemirror.on('change', function() {
    $(element).change();
  });
  return mde_field;
}

function updateMarkdownField(checkbox_id, mde_attribute, data_name, height) {
  window.mde_fields[mde_attribute].forEach(function (item){
    item.toTextArea();
  })
  window.mde_fields[mde_attribute] = [];
  if ($('#' + checkbox_id).prop('checked')) {
    $('.form-group[data-name="' +data_name + '"] [data-language-id]').each(function() {
      const textarea = $(this).find('textarea.form-control')[0];
      window.mde_fields[mde_attribute].push(initMarkdownField(textarea, height));
    });
    window.mde_fields[mde_attribute].forEach(function (item){
      setupImageDragAndDrop(item);
    });
  }
}
