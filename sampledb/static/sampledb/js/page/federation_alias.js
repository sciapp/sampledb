'use strict';
/* eslint-env jquery */

const aliasesByComponent = window.getTemplateValue('aliases_by_component');
const componentNames = window.getTemplateValue('component_names');
const userData = window.getTemplateValue('user_data');

function setEditAliasForm (componentID) {
  copyAliasFrom(componentID, '-edit');
  $('#editAliasModalLabel').text(window.getTemplateValue('translations.edit_alias') + componentNames[componentID]);
  $('#input-component-edit').val(componentID);
  const copyFromSelect = $('#input-copy-from-edit');
  copyFromSelect.find('option').prop('disabled', false);
  copyFromSelect.find('option[value=' + componentID + ']').prop('disabled', true);
  copyFromSelect.selectpicker('val', '-1');
  copyFromSelect.selectpicker('refresh');
}
function copyAliasFromInput (suffix) {
  copyAliasFrom($('#input-copy-from' + suffix).val(), suffix);
}
function copyAliasFrom (componentID, suffix) {
  if (componentID === null || +componentID === -1) {
    $('#checkbox-use-real-email' + suffix).prop('checked', true);
    $('#checkbox-use-real-orcid' + suffix).prop('checked', true);
    for (const field of ['name', 'affiliation', 'role']) {
      $('#checkbox-use-real-' + field + suffix).prop('checked', true);
      useRealDataInputChanged(field, suffix);
    }
  } else {
    $('#input-name' + suffix).val(aliasesByComponent[componentID].name);
    $('#input-email' + suffix).val(aliasesByComponent[componentID].email);
    $('#input-affiliation' + suffix).val(aliasesByComponent[componentID].affiliation);
    $('#input-role' + suffix).val(aliasesByComponent[componentID].role);
    $('#checkbox-use-real-email' + suffix).prop('checked', aliasesByComponent[componentID].use_real_email);
    $('#checkbox-use-real-orcid' + suffix).prop('checked', aliasesByComponent[componentID].use_real_orcid);
    for (const field of ['name', 'affiliation', 'role']) {
      $('#checkbox-use-real-' + field + suffix).prop('checked', aliasesByComponent[componentID]['use_real_' + field]);
      useRealDataInputChanged(field, suffix);
    }
  }
}
function useRealDataInputChanged (field, suffix) {
  if ($('#checkbox-use-real-' + field + suffix).is(':checked')) {
    $('#input-' + field + suffix).prop('disabled', true);
    $('#input-' + field + suffix).val(userData[field]);
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

$(function () {
  $('#checkbox-use-real-name-add').on('change', function () {
    useRealDataInputChanged('name', '-add');
  });

  $('#checkbox-use-real-email-add').on('change', function () {
    useRealDataInputChanged('email', '-add');
  });

  $('#checkbox-use-real-orcid-add').on('change', function () {
    useRealDataInputChanged('orcid', '-add');
  });

  $('#checkbox-use-real-affiliation-add').on('change', function () {
    useRealDataInputChanged('affiliation', '-add');
  });

  $('#checkbox-use-real-role-add').on('change', function () {
    useRealDataInputChanged('role', '-add');
  });

  $('#checkbox-use-real-name-edit').on('change', function () {
    useRealDataInputChanged('name', '-edit');
  });

  $('#checkbox-use-real-email-edit').on('change', function () {
    useRealDataInputChanged('email', '-edit');
  });

  $('#checkbox-use-real-orcid-edit').on('change', function () {
    useRealDataInputChanged('orcid', '-edit');
  });

  $('#checkbox-use-real-affiliation-edit').on('change', function () {
    useRealDataInputChanged('affiliation', '-edit');
  });

  $('#checkbox-use-real-role-edit').on('change', function () {
    useRealDataInputChanged('role', '-edit');
  });

  $('#button-copy-from-add').on('click', function () {
    copyAliasFromInput('-add');
  });

  $('#button-copy-from-edit').on('click', function () {
    copyAliasFromInput('-edit');
  });

  $('.button-edit-alias').on('click', function () {
    setEditAliasForm($(this).data('componentId'));
  });
  if (window.getTemplateValue('show_edit_form')) {
    const editModal = $('#editAliasModal');
    editModal.removeClass('fade');
    editModal.modal('show');
    editModal.addClass('fade');
  }
});
