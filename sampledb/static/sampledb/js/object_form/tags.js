'use strict';
/* eslint-env jquery */
/* globals Bloodhound */

const tags = new Bloodhound({
  initialize: true,
  local: window.getTemplateValue('tags'),
  datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
  queryTokenizer: Bloodhound.tokenizers.whitespace
});
$('input[name^=\'object__\'][name$=\'__tags\']').each(function () {
  const tagsInput = $(this);
  tagsInput.tagsinput({
    trimValue: true,
    confirmKeys: [13, 32],
    typeaheadjs: {
      name: 'Tags',
      valueKey: 'name',
      displayKey: 'name',
      source: tags.ttAdapter(),
      templates: {
        suggestion: function (item) {
          return '<div>' + item.name + ' (×' + item.uses + ')' + '</div>';
        }
      }
    }
  });
  tagsInput.on('beforeItemAdd', function (event) {
    const sanitizedTag = event.item.toLowerCase().replace(/\s/g, '').replace(/[^a-z0-9_\-äüöß]/g, '');
    if (event.item !== sanitizedTag) {
      if (!event.options || !event.options.fromHandler) {
        event.cancel = true;
        $(this).tagsinput('add', sanitizedTag, { fromHandler: true });
      }
    }
  });
  $(tagsInput.tagsinput('input')).on('blur', function () {
    let item = $(this).tagsinput('input').val();
    $(this).tagsinput('input').val('');
    item = item.trim();
    if (item) {
      $(this).tagsinput('add', item);
    }
  }.bind(tagsInput));
});
