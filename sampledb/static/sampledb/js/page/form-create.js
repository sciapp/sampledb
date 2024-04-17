$(function() {
  $('form').on('submit', function() {
    let permissions_method = $('[name="permissions_method"]:checked').val();
    let permissions_help_block = $('#permissionsHelpBlock');
    permissions_help_block.text('');
    permissions_help_block.parent().parent().find('.has-error').removeClass('has-error');
    if (permissions_method === 'copy_permissions') {
        let permissions_object_id_select = $('[name="copy_permissions_object_id"]');
        if (permissions_object_id_select.selectpicker().val() === null) {
            permissions_help_block.text('{{ _("Please select an object to copy the permissions from.") }}');
            permissions_help_block.parent().addClass('has-error');
            permissions_object_id_select.parent().parent().addClass('has-error');
            return false;
        }
    } else if (permissions_method === 'permissions_for_project') {
        let permissions_project_id_select = $('[name="permissions_for_project_project_id"]');
        if (permissions_project_id_select.selectpicker().val() === null) {
            permissions_help_block.text('{{ _("Please select a project group to give permissions to.") }}');
            permissions_help_block.parent().addClass('has-error');
            permissions_project_id_select.parent().parent().addClass('has-error');
            return false;
        }
    } else if (permissions_method === 'permissions_for_group') {
        let permissions_group_id_select = $('[name="permissions_for_group_group_id"]');
        if (permissions_group_id_select.selectpicker().val() === null) {
            permissions_help_block.text('{{ _("Please select a basic group to give permissions to.") }}');
            permissions_help_block.parent().addClass('has-error');
            permissions_group_id_select.parent().parent().addClass('has-error');
            return false;
        }
    }

    return true;
  });
  if (window.getTemplateValue('user_has_basic_groups')) {
    $('select[name="permissions_for_group_group_id"]').on('show.bs.select', function () {
      $('input[name="permissions_method"][value="permissions_for_group"]').prop('checked', true);
    }).selectpicker('val', window.getTemplateValue('permissions_for_group_group_id'));
  }
  if (window.getTemplateValue('user_has_project_groups')) {
    $('select[name="permissions_for_project_project_id"]').on('show.bs.select', function () {
      $('input[name="permissions_method"][value="permissions_for_project"]').prop('checked', true);
    }).selectpicker('val', window.getTemplateValue('permissions_for_project_project_id'));
  }
  if (window.getTemplateValue('user_can_copy_permissions')) {
    let permissions_object_id_select = $('select[name="copy_permissions_object_id"]');
    permissions_object_id_select.on('show.bs.select', function () {
      $('input[name="permissions_method"][value="copy_permissions"]').prop('checked', true);
    });
    if (permissions_object_id_select.data('sampledbDefaultSelected')) {
      permissions_object_id_select.selectpicker('val', permissions_object_id_select.data('sampledbDefaultSelected'));
    } else {
      permissions_object_id_select.selectpicker('val', null);
    }
  }
  if (window.getTemplateValue('show_selecting_modal')) {
    $('#selectionModal').modal('show');
  }
});