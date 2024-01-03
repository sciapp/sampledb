var aliases_by_component = window.getTemplateValue('aliases_by_component');
var component_names = window.getTemplateValue('component_names');
var user_data = window.getTemplateValue('user_data');
function setEditAliasForm(component_id) {
  copyAliasFrom(component_id, '-edit');
  $('#editAliasModalLabel').text(window.getTemplateValue('translations.edit_alias') + component_names[component_id]);
  $('#input-component-edit').val(component_id);
  let copy_from_select = $('#input-copy-from-edit');
  copy_from_select.find('option').prop('disabled', false);
  copy_from_select.find('option[value=' + component_id + ']').prop('disabled', true);
  copy_from_select.selectpicker('val', '-1');
  copy_from_select.selectpicker('refresh');
}
function copyAliasFromInput(suffix) {
  copyAliasFrom($('#input-copy-from' + suffix).val(), suffix);
}
function copyAliasFrom(component_id, suffix) {
  if (component_id == null || component_id == -1) {
    $('#checkbox-use-real-email' + suffix).prop('checked', true);
    $('#checkbox-use-real-orcid' + suffix).prop('checked', true);
    for (const field of ['name', 'affiliation', 'role']) {
      $('#checkbox-use-real-' + field + suffix).prop('checked', true);
      useRealDataInputChanged(field, suffix);
    }
  } else {
    $('#input-name' + suffix).val(aliases_by_component[component_id]['name']);
    $('#input-email' + suffix).val(aliases_by_component[component_id]['email']);
    $('#input-affiliation' + suffix).val(aliases_by_component[component_id]['affiliation']);
    $('#input-role' + suffix).val(aliases_by_component[component_id]['role']);
    $('#checkbox-use-real-email' + suffix).prop('checked', aliases_by_component[component_id]['use_real_email']);
    $('#checkbox-use-real-orcid' + suffix).prop('checked', aliases_by_component[component_id]['use_real_orcid']);
    for (const field of ['name', 'affiliation', 'role']) {
      $('#checkbox-use-real-' + field + suffix).prop('checked', aliases_by_component[component_id]['use_real_' + field]);
      useRealDataInputChanged(field, suffix);
    }
  }
}
function useRealDataInputChanged(field, suffix) {
  if ($('#checkbox-use-real-' + field + suffix).is(':checked')) {
    $('#input-' + field + suffix).prop('disabled', true);
    $('#input-' + field + suffix).val(user_data[field]);
  } else {
    $('#input-' + field + suffix).prop('disabled', false);
  }
}
for (const field of ['name', 'affiliation', 'role']) {
  useRealDataInputChanged(field, '-add');
  if (window.getTemplateValue('show_edit_form')) {
    useRealDataInputChanged(field, '-edit');
  }
}

$(function() {
  $('#checkbox-use-real-name-add').on('change', function() {
    useRealDataInputChanged('name', '-add');
  });

  $('#checkbox-use-real-email-add').on('change', function() {
    useRealDataInputChanged('email', '-add');
  });

  $('#checkbox-use-real-orcid-add').on('change', function() {
    useRealDataInputChanged('orcid', '-add');
  });

  $('#checkbox-use-real-affiliation-add').on('change', function() {
    useRealDataInputChanged('affiliation', '-add');
  });

  $('#checkbox-use-real-role-add').on('change', function() {
    useRealDataInputChanged('role', '-add');
  });

  $('#checkbox-use-real-name-edit').on('change', function() {
    useRealDataInputChanged('name', '-edit');
  });

  $('#checkbox-use-real-email-edit').on('change', function() {
    useRealDataInputChanged('email', '-edit');
  });

  $('#checkbox-use-real-orcid-edit').on('change', function() {
    useRealDataInputChanged('orcid', '-edit');
  });

  $('#checkbox-use-real-affiliation-edit').on('change', function() {
    useRealDataInputChanged('affiliation', '-edit');
  });

  $('#checkbox-use-real-role-edit').on('change', function() {
    useRealDataInputChanged('role', '-edit');
  });

  $('#button-copy-from-add').on('click', function() {
    copyAliasFromInput('-add');
  });

  $('#button-copy-from-edit').on('click', function() {
    copyAliasFromInput('-edit');
  });

  $('.button-edit-alias').on('click', function() {
    setEditAliasForm($(this).data('componentId'));
  });
  if (window.getTemplateValue('show_edit_form')) {
    var edit_modal = $('#editAliasModal');
    edit_modal.removeClass('fade');
    edit_modal.modal('show');
    edit_modal.addClass('fade');
  }
});
