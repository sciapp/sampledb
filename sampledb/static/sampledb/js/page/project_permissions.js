'use strict';
/* eslint-env jquery */

$(function () {
  // show warnings or delete modal in special cases
  $('#form-permissions').find('button[type=submit]').on('click', function () {
    const numReadUsers = $('.permissions_user_read:checked').length;
    const numWriteUsers = $('.permissions_user_write:checked').length;
    const numGrantUsers = $('.permissions_user_grant:checked').length;
    const numReadGroups = $('.permissions_group_read:checked').length;
    const numWriteGroups = $('.permissions_group_write:checked').length;
    const numGrantGroups = $('.permissions_group_grant:checked').length;
    if (numGrantUsers === 0 && (numReadUsers + numWriteUsers + numReadGroups + numWriteGroups + numGrantGroups) !== 0) {
      $('#alert-no-grant-user').html(`<div class="alert alert-danger alert-dismissible" role="alert"><button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>${window.getTemplateValue('min_grant_user_warning')}</div>`);
      return false;
    }
    if (numReadUsers + numWriteUsers + numGrantUsers + numReadGroups + numWriteGroups + numGrantGroups === 0) {
      $('#deleteProjectModal').modal('show');
      return false;
    }
    return true;
  });
  $('#button-delete-project').on('click', function () {
    $('#form-permissions').submit();
  });
});
