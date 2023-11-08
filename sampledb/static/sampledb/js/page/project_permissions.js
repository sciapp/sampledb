$(function () {
  $('#form-permissions').find('button[type=submit]').on('click', function() {
    num_read_users = $('.permissions_user_read:checked').length;
    num_write_users = $('.permissions_user_write:checked').length;
    num_grant_users = $('.permissions_user_grant:checked').length;
    num_read_groups = $('.permissions_group_read:checked').length;
    num_write_groups = $('.permissions_group_write:checked').length;
    num_grant_groups = $('.permissions_group_grant:checked').length;
    if (num_grant_users === 0 && (num_read_users + num_write_users + num_read_groups + num_write_groups + num_grant_groups) !== 0) {
      $('#alert-no-grant-user').html(`<div class="alert alert-danger alert-dismissible" role="alert"><button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>${window.template_values.min_grant_user_warning}</div>`);
      return false;
    }
    if (num_read_users + num_write_users + num_grant_users + num_read_groups + num_write_groups + num_grant_groups === 0) {
      $('#deleteProjectModal').modal('show');
      return false;
    }
    return true;
  });
  $('#button-delete-project').on('click', function() {
    $('#form-permissions').submit();
  });
})
