'use strict';
/* eslint-env jquery */

$(function () {
  const first = $('[name="input_first_number_batch"]');
  const last = $('[name="input_last_number_batch"]');
  const count = $('[name="input_num_batch_objects"]');
  function updateLastNumber () {
    const firstnum = Number(first.val());
    const countnum = Number(count.val());
    let err = false;
    if (Number.isInteger(firstnum) && first.val() !== '') {
      first.parent().removeClass('has-error');
    } else {
      first.parent().addClass('has-error');
      err = true;
    }
    if (Number.isInteger(countnum) && count.val() !== '' && countnum > 0) {
      count.parent().removeClass('has-error');
    } else {
      count.parent().addClass('has-error');
      err = true;
    }
    if (err) {
      last.val();
    } else {
      last.val(firstnum + countnum - 1);
    }
  }
  first.on('change', updateLastNumber);
  first.on('keyup', updateLastNumber);
  count.on('change', updateLastNumber);
  count.on('keyup', updateLastNumber);
  updateLastNumber();
  $('form').on('submit', function () {
    const permissionsMethod = $('[name="permissions_method"]:checked').val();
    const permissionsHelpBlock = $('#permissionsHelpBlock');
    permissionsHelpBlock.text('');
    permissionsHelpBlock.parent().parent().find('.has-error').removeClass('has-error');
    if (permissionsMethod === 'copy_permissions') {
      const permissionsObjectIDSelect = $('[name="copy_permissions_object_id"]');
      if (permissionsObjectIDSelect.selectpicker().val() === null) {
        permissionsHelpBlock.text(window.getTemplateValue('translations.select_an_object_to_copy_permissions_from'));
        permissionsHelpBlock.parent().addClass('has-error');
        permissionsObjectIDSelect.parent().parent().addClass('has-error');
        return false;
      }
    } else if (permissionsMethod === 'permissions_for_project') {
      const permissionsProjectIDSelect = $('[name="permissions_for_project_project_id"]');
      if (permissionsProjectIDSelect.selectpicker().val() === null) {
        permissionsHelpBlock.text(window.getTemplateValue('translations.select_a_project_group_to_give_permissions_to'));
        permissionsHelpBlock.parent().addClass('has-error');
        permissionsProjectIDSelect.parent().parent().addClass('has-error');
        return false;
      }
    } else if (permissionsMethod === 'permissions_for_group') {
      const permissionsGroupIDSelect = $('[name="permissions_for_group_group_id"]');
      if (permissionsGroupIDSelect.selectpicker().val() === null) {
        permissionsHelpBlock.text(window.getTemplateValue('translations.select_a_basic_group_to_give_permissions_to'));
        permissionsHelpBlock.parent().addClass('has-error');
        permissionsGroupIDSelect.parent().parent().addClass('has-error');
        return false;
      }
    }

    return true;
  });
  if (window.getTemplateValue('user_has_basic_groups')) {
    $('select[name="permissions_for_group_group_id"]').on('show.bs.select', function () {
      $('input[name="permissionsMethod"][value="permissions_for_group"]').prop('checked', true);
    }).selectpicker('val', window.getTemplateValue('permissions_for_group_group_id'));
  }
  if (window.getTemplateValue('user_has_project_groups')) {
    $('select[name="permissions_for_project_project_id"]').on('show.bs.select', function () {
      $('input[name="permissions_method"][value="permissions_for_project"]').prop('checked', true);
    }).selectpicker('val', window.getTemplateValue('permissions_for_project_project_id'));
  }
  if (window.getTemplateValue('user_can_copy_permissions')) {
    const permissionsObjectIDSelect = $('select[name="copy_permissions_object_id"]');
    permissionsObjectIDSelect.on('show.bs.select', function () {
      $('input[name="permissions_method"][value="copy_permissions"]').prop('checked', true);
    });
    if (permissionsObjectIDSelect.data('sampledbDefaultSelected')) {
      permissionsObjectIDSelect.selectpicker('val', permissionsObjectIDSelect.data('sampledbDefaultSelected'));
    } else {
      permissionsObjectIDSelect.selectpicker('val', null);
    }
  }
  if (window.getTemplateValue('show_selecting_modal')) {
    $('#selectionModal').modal('show');
  }
});
