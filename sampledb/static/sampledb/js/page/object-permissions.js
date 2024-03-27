'use strict';
/* eslint-env jquery */

let newPolicySelectedProjects = {};
let newPolicySelectedGroups = {};
let newPolicySelectedUsers = {};
let editPolicySelectedProjects = {};
let editPolicySelectedGroups = {};
let editPolicySelectedUsers = {};
const users = window.getTemplateValue('component_users');
const policies = window.getTemplateValue('policies');
let addSelectedComponentID = NaN;
let editSelectedComponentID = NaN;

$(function () {
  $('#add_share_component_picker').on('change', setNewPolicyData);
  $('#edit-share-component-picker').on('change', setEditPolicyData);
  $('#add_component_policy_user_select_btn').on('click', newPolicyAddUserSelect);
  $('#add_component_policy_user_input_btn').on('click', newPolicyAddUserText);
  $('#add_component_policy_group_input_btn').on('click', newPolicyAddGroupText);
  $('#add_component_policy_project_input_btn').on('click', newPolicyAddProjectText);
  $('#edit_component_policy_user_select_btn').on('click', editPolicyAddUserSelect);
  $('#edit_component_policy_user_input_btn').on('click', editPolicyAddUserText);
  $('#edit_component_policy_group_input_btn').on('click', editPolicyAddGroupText);
  $('#edit_component_policy_project_input_btn').on('click', editPolicyAddProjectText);
});

function setNewPolicyData () {
  const selectedComponentID = +$('#add_share_component_picker').val();
  if (!Number.isNaN(selectedComponentID) && selectedComponentID !== addSelectedComponentID) {
    const projectsTableBody = $('#new_policy_projects_tbody');
    projectsTableBody.empty();
    projectsTableBody.append(`<tr><td></td><th scope="rowgroup">${window.getTemplateValue('translations.project_groups')}</th><td></td><td></td><td></td></tr>`);
    projectsTableBody.hide();
    const groupsTableBody = $('#new_policy_groups_tbody');
    groupsTableBody.empty();
    groupsTableBody.append(`<tr><td></td><th scope="rowgroup">${window.getTemplateValue('translations.basic_groups')}</th><td></td><td></td><td></td></tr>`);
    groupsTableBody.hide();
    const usersTableBody = $('#new_policy_users_tbody');
    usersTableBody.empty();
    usersTableBody.append(`<tr><td></td><th scope="rowgroup">${window.getTemplateValue('translations.users')}</th><td></td><td></td><td></td></tr>`);
    usersTableBody.hide();
    newPolicySelectedProjects = {};
    newPolicySelectedGroups = {};
    newPolicySelectedUsers = {};
    addSelectedComponentID = selectedComponentID;
    updateAddSelect();
  }
}

function setEditPolicyData () {
  const selectedComponentID = +$('#edit-share-component-picker').val();
  if (!Number.isNaN(selectedComponentID) && selectedComponentID !== editSelectedComponentID) {
    editPolicySelectedProjects = {};
    editPolicySelectedGroups = {};
    editPolicySelectedUsers = {};
    editSelectedComponentID = selectedComponentID;
    $('#policy-edit-data').prop('checked', policies[editSelectedComponentID].access.data).change();
    $('#policy-edit-action').prop('checked', policies[editSelectedComponentID].access.action).change();
    $('#policy-edit-users').prop('checked', policies[editSelectedComponentID].access.users).change();
    $('#policy-edit-files').prop('checked', policies[editSelectedComponentID].access.files).change();
    $('#policy-edit-comments').prop('checked', policies[editSelectedComponentID].access.comments).change();
    $('#policy-edit-object-location-assignments').prop('checked', policies[editSelectedComponentID].access.object_location_assignments).change();
    const projectsTableBody = $('#edit_policy_projects_tbody');
    projectsTableBody.empty();
    projectsTableBody.append(`<tr><td></td><th scope="rowgroup">${window.getTemplateValue('translations.project_groups')}</th><td></td><td></td><td></td></tr>`);
    if (policies[editSelectedComponentID].permissions.projects) {
      projectsTableBody.show();
    } else {
      projectsTableBody.hide();
    }
    for (const projectID in policies[editSelectedComponentID].permissions.projects) {
      const permissions = policies[editSelectedComponentID].permissions.projects[projectID];
      editPolicySelectedProjects[projectID] = `${window.getTemplateValue('translations.project_group')} #${projectID}`;
      const projectName = editPolicySelectedProjects[projectID];
      projectsTableBody.append(createPermissionsRow(projectID, projectName, permissions, 'edit_policy_projects_', 'permissions_edit_policy_project_'));
      $(`#edit_policy_projects_${projectID} button`).on('click', function () {
        editPolicyRemoveProject(projectID);
      });
    }
    const groupsTableBody = $('#edit_policy_groups_tbody');
    groupsTableBody.empty();
    groupsTableBody.append(`<tr><td></td><th scope="rowgroup">${window.getTemplateValue('translations.basic_groups')}</th><td></td><td></td><td></td></tr>`);
    if (policies[editSelectedComponentID].permissions.groups) {
      groupsTableBody.show();
    } else {
      groupsTableBody.hide();
    }
    for (const groupID in policies[editSelectedComponentID].permissions.groups) {
      const permissions = policies[editSelectedComponentID].permissions.groups[groupID];
      editPolicySelectedGroups[groupID] = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
      const groupName = editPolicySelectedGroups[groupID];
      groupsTableBody.append(createPermissionsRow(groupID, groupName, permissions, 'edit_policy_groups_', 'permissions_edit_policy_group_'));
      $(`#edit_policy_groups_${groupID} button`).on('click', function () {
        editPolicyRemoveGroup(groupID);
      });
    }
    const usersTableBody = $('#edit_policy_users_tbody');
    usersTableBody.empty();
    usersTableBody.append(`<tr><td></td><th scope="rowgroup">${window.getTemplateValue('translations.users')}</th><td></td><td></td><td></td></tr>`);
    if (policies[editSelectedComponentID].permissions.users) {
      usersTableBody.show();
    } else {
      usersTableBody.hide();
    }
    for (const userID in policies[editSelectedComponentID].permissions.users) {
      const permissions = policies[editSelectedComponentID].permissions.users[userID];
      if (userID in users[editSelectedComponentID]) {
        editPolicySelectedUsers[userID] = users[editSelectedComponentID][userID];
      } else {
        editPolicySelectedUsers[userID] = `${window.getTemplateValue('translations.user')} #${userID}`;
      }
      const userName = editPolicySelectedUsers[userID];
      usersTableBody.append(createPermissionsRow(userID, userName, permissions, 'edit_policy_users_', 'permissions_edit_policy_user_'));
      $(`#edit_policy_users_${userID} button`).on('click', function () {
        editPolicyRemoveUser(userID);
      });
    }
    updateEditSelect();
  }
}

function createPermissionsRow (id, name, permissions, rowPrefix, fieldPrefix) {
  const row = $(`
      <tr id="${rowPrefix}${id}">
        <td class="text-center"><button class="btn btn-xs btn-danger" type="button"><i class="fa fa-times" aria-hidden="true"></i></button></td>
        <td>${name}</td>
      </tr>
    `);
    for (const possiblePermissions of ['read', 'write', 'grant']) {
      row.append(`
        <td class="text-center" style="vertical-align: middle">
          <label for="${fieldPrefix}${id}_${possiblePermissions}" class="sr-only">${possiblePermissions}</label>
          <input type="radio" name="${fieldPrefix}${id}" id="${fieldPrefix}${id}_${possiblePermissions}" value="${possiblePermissions}" ${(possiblePermissions === permissions) ? 'checked="checked"' : ''} />
        </td>
      `);
    }
    return row;
}

function newPolicyAddUserSelect () {
  const $select = $('#add_share_user_picker');
  const userID = $select.val();
  if (!(userID in newPolicySelectedUsers)) {
    newPolicySelectedUsers[userID] = users[addSelectedComponentID][userID];
    const userName = newPolicySelectedUsers[userID];
    const usersTableBody = $('#new_policy_users_tbody');
    const permissions = 'read';
    usersTableBody.append(createPermissionsRow(userID, userName, permissions, 'new_policy_users_', 'permissions_add_policy_user_'));
    $(`#new_policy_users_${userID} button`).on('click', function () {
      newPolicyRemoveUser(userID);
    });
    if ($('#new_policy_users_tbody > tr').length > 1) {
      usersTableBody.show();
    }
  }
  updateAddSelect();
}

function editPolicyAddUserSelect () {
  const $select = $('#edit_share_user_picker');
  const userID = $select.val();
  if (!(userID in editPolicySelectedUsers)) {
    editPolicySelectedUsers[userID] = users[editSelectedComponentID][userID];
    const userName = editPolicySelectedUsers[userID];
    const usersTableBody = $('#edit_policy_users_tbody');
    const permissions = 'read';
    usersTableBody.append(createPermissionsRow(userID, userName, permissions, 'edit_policy_users_', 'permissions_edit_policy_user_'));
    $(`#edit_policy_users_${userID} button`).on('click', function () {
      editPolicyRemoveUser(userID);
    });
    if ($('#edit_policy_users_tbody > tr').length > 1) {
      usersTableBody.show();
    }
  }
  updateEditSelect();
}

$('#add_share_project_text').keydown(function (evt) {
  if (evt.key === 'Enter' || evt.keyCode === 13) {
    newPolicyAddProjectText();
    evt.preventDefault();
    return false;
  }
});

$('#add_share_group_text').keydown(function (evt) {
  if (evt.key === 'Enter' || evt.keyCode === 13) {
    newPolicyAddGroupText();
    evt.preventDefault();
    return false;
  }
});

$('#add_share_user_text').keydown(function (evt) {
  if (evt.key === 'Enter' || evt.keyCode === 13) {
    newPolicyAddUserText();
    evt.preventDefault();
    return false;
  }
});

$('#edit_share_project_text').keydown(function (evt) {
  if (evt.key === 'Enter' || evt.keyCode === 13) {
    editPolicyAddProjectText();
    evt.preventDefault();
    return false;
  }
});

$('#edit_share_group_text').keydown(function (evt) {
  if (evt.key === 'Enter' || evt.keyCode === 13) {
    editPolicyAddGroupText();
    evt.preventDefault();
    return false;
  }
});

$('#edit_share_user_text').keydown(function (evt) {
  if (evt.key === 'Enter' || evt.keyCode === 13) {
    editPolicyAddUserText();
    evt.preventDefault();
    return false;
  }
});

function validateId ($input, $err, existingValuesObject, alreadyAddedText) {
  let idText = $input.val();
  if (idText.charAt(0) === '#') {
    idText = idText.substring(1);
  }
  const id = parseInt(idText);
  if (isNaN(id) || id < 1 || id > 2147483647) {
    $err.text(window.getTemplateValue('translations.not_a_valid_id'));
    $input.parent().parent().addClass('has-error');
    $err.show();
    return 0;
  } else if (id in existingValuesObject) {
    $err.text(alreadyAddedText);
    $input.parent().parent().addClass('has-error');
    $err.show();
    return 0;
  } else {
    $input.parent().parent().removeClass('has-error');
    $err.hide();
    return id;
  }
}

function newPolicyAddProjectText () {
  const $input = $('#add_share_project_text');
  const $err = $('#add_share_project_text_help_block');
  const projectID = validateId($input, $err, newPolicySelectedProjects, window.getTemplateValue('translations.project_group_already_added'));
  if (projectID > 0) {
    newPolicySelectedProjects[projectID] = `${window.getTemplateValue('translations.project_group')}  #${projectID}`;
    $input.val('');
    const projectsTableBody = $('#new_policy_projects_tbody');
    const permissions = 'read';
    const projectName = newPolicySelectedProjects[projectID];
    projectsTableBody.append(createPermissionsRow(projectID, projectName, permissions, 'new_policy_projects_', 'permissions_add_policy_project_'));
    $(`#new_policy_projects_${projectID} button`).on('click', function () {
      newPolicyRemoveProject(projectID);
    });
    if ($('#new_policy_projects_tbody > tr').length > 1) {
      projectsTableBody.show();
    }
  }
}

function newPolicyAddGroupText () {
  const $input = $('#add_share_group_text');
  const $err = $('#add_share_group_text_help_block');
  const groupID = validateId($input, $err, newPolicySelectedGroups, window.getTemplateValue('translations.basic_group_already_added'));
  if (groupID > 0) {
    newPolicySelectedGroups[groupID] = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
    $input.val('');
    const groupsTableBody = $('#new_policy_groups_tbody');
    const groupName = newPolicySelectedGroups[groupID];
    const permissions = 'read';
    groupsTableBody.append(createPermissionsRow(groupID, groupName, permissions, 'new_policy_groups_', 'permissions_add_policy_group_'));
    $(`#new_policy_groups_${groupID} button`).on('click', function () {
      newPolicyRemoveGroup(groupID);
    });
    if ($('#new_policy_groups_tbody > tr').length > 1) {
      groupsTableBody.show();
    }
  }
}

function newPolicyAddUserText () {
  const $input = $('#add_share_user_text');
  const $err = $('#add_share_user_text_help_block');
  const userID = validateId($input, $err, newPolicySelectedUsers, window.getTemplateValue('translations.user_already_added'));
  if (userID) {
    if (userID in users[addSelectedComponentID]) {
      newPolicySelectedUsers[userID] = users[addSelectedComponentID][userID];
    } else {
      newPolicySelectedUsers[userID] = `${window.getTemplateValue('translations.user')} #${userID}`;
    }
    $input.val('');
    const usersTableBody = $('#new_policy_users_tbody');
    const userName = newPolicySelectedUsers[userID];
    const permissions = 'read';
    usersTableBody.append(createPermissionsRow(userID, userName, permissions, 'new_policy_users_', 'permissions_add_policy_user_'));
    $(`#new_policy_users_${userID} button`).on('click', function () {
      newPolicyRemoveUser(userID);
    });
    if ($('#new_policy_users_tbody > tr').length > 1) {
      usersTableBody.show();
    }
    updateAddSelect();
  }
}

function editPolicyAddProjectText () {
  const $input = $('#edit_share_project_text');
  const $err = $('#edit_share_project_text_help_block');
  const projectID = validateId($input, $err, editPolicySelectedProjects, window.getTemplateValue('translations.project_group_already_added'));
  if (projectID > 0) {
    editPolicySelectedProjects[projectID] = `${window.getTemplateValue('translations.project_group')} #${projectID}`;
    $input.val('');
    const projectsTableBody = $('#edit_policy_projects_tbody');
    const permissions = 'read';
    const projectName = editPolicySelectedProjects[projectID];
    projectsTableBody.append(createPermissionsRow(projectID, projectName, permissions, 'edit_policy_projects_', 'permissions_edit_policy_project_'));
    $(`#edit_policy_projects_${projectID} button`).on('click', function () {
      editPolicyRemoveProject(projectID);
    });
    if ($('#edit_policy_projects_tbody > tr').length > 1) {
      projectsTableBody.show();
    }
  }
}

function editPolicyAddGroupText () {
  const $input = $('#edit_share_group_text');
  const $err = $('#edit_share_group_text_help_block');
  const groupID = validateId($input, $err, editPolicySelectedGroups, window.getTemplateValue('translations.basic_group_already_added'));
  if (groupID > 0) {
    editPolicySelectedGroups[groupID] = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
    $input.val('');
    const groupsTableBody = $('#edit_policy_groups_tbody');
    const groupName = editPolicySelectedGroups[groupID];
    const permissions = 'read';
    groupsTableBody.append(createPermissionsRow(groupID, groupName, permissions, 'edit_policy_groups_', 'permissions_edit_policy_group_'));
    $(`#edit_policy_groups_${groupID} button`).on('click', function () {
      editPolicyRemoveGroup(groupID);
    });
    if ($('#edit_policy_groups_tbody > tr').length > 1) {
      groupsTableBody.show();
    }
  }
}

function editPolicyAddUserText () {
  const $input = $('#edit_share_user_text');
  const $err = $('#edit_share_user_text_help_block');
  const userID = validateId($input, $err, editPolicySelectedUsers, window.getTemplateValue('translations.user_already_added'));
  if (userID > 0) {
    if (userID in users[editSelectedComponentID]) {
      editPolicySelectedUsers[userID] = users[editSelectedComponentID][userID];
    } else {
      editPolicySelectedUsers[userID] = `${window.getTemplateValue('translations.user')} #${userID}`;
    }
    $input.val('');
    const usersTableBody = $('#edit_policy_users_tbody');
    const userName = editPolicySelectedUsers[userID];
    const permissions = 'read';
    usersTableBody.append(createPermissionsRow(userID, userName, permissions, 'edit_policy_users_', 'permissions_edit_policy_user_'));
    $(`#edit_policy_users_${userID} button`).on('click', function () {
      editPolicyRemoveUser(userID);
    });
    if ($('#edit_policy_users_tbody > tr').length > 1) {
      usersTableBody.show();
    }
    updateEditSelect();
  }
}

function newPolicyRemoveProject (projectID) {
  if (projectID in newPolicySelectedProjects) {
    delete newPolicySelectedProjects[projectID];
    $(`#new_policy_projects_${projectID}`).remove();
  }
  if ($('#new_policy_projects_tbody > tr').length === 1) {
    $('#new_policy_projects_tbody').hide();
  }
}

function newPolicyRemoveGroup (groupID) {
  if (groupID in newPolicySelectedGroups) {
    delete newPolicySelectedGroups[groupID];
    $(`#new_policy_groups_#{groupID}`).remove();
  }
  if ($('#new_policy_groups_tbody > tr').length === 1) {
    $('#new_policy_groups_tbody').hide();
  }
}

function newPolicyRemoveUser (userID) {
  if (userID in newPolicySelectedUsers) {
    delete newPolicySelectedUsers[userID];
    $(`#new_policy_users_${userID}`).remove();
  }
  if ($('#new_policy_users_tbody > tr').length === 1) {
    $('#new_policy_users_tbody').hide();
  }
  updateAddSelect();
}

function editPolicyRemoveProject (projectID) {
  if (projectID in editPolicySelectedProjects) {
    delete editPolicySelectedProjects[projectID];
    $(`#edit_policy_projects_${projectID}`).remove();
  }
  if ($('#edit_policy_projects_tbody > tr').length === 1) {
    $('#edit_policy_projects_tbody').hide();
  }
}

function editPolicyRemoveGroup (groupID) {
  if (groupID in editPolicySelectedGroups) {
    delete editPolicySelectedGroups[groupID];
    $(`#edit_policy_groups_${groupID}`).remove();
  }
  if ($('#edit_policy_groups_tbody > tr').length === 1) {
    $('#edit_policy_groups_tbody').hide();
  }
}

function editPolicyRemoveUser (userID) {
  if (userID in editPolicySelectedUsers) {
    delete editPolicySelectedUsers[userID];
    $(`#edit_policy_users_${userID}`).remove();
  }
  if ($('#edit_policy_users_tbody > tr').length === 1) {
    $('#edit_policy_users_tbody').hide();
  }
  updateEditSelect();
}

function updateAddSelect () {
  const $select = $('#add_share_user_picker');
  $select.empty();
  let noUsers = true;
  for (const userID in users[addSelectedComponentID]) {
    if (!(userID in newPolicySelectedUsers)) {
      noUsers = false;
      $select.append($('<option></option>').attr('value', userID).text(users[addSelectedComponentID][userID]));
    }
  }
  $select.prop('disabled', noUsers);
  $('#add_component_policy_user_select_btn').prop('disabled', noUsers);
  $select.selectpicker('refresh');
  $select.change();
}

function updateEditSelect () {
  const $select = $('#edit_share_user_picker');
  $select.empty();
  let noUsers = true;
  for (const userID in users[editSelectedComponentID]) {
    if (!(userID in editPolicySelectedUsers)) {
      noUsers = false;
      $select.append($('<option></option>').attr('value', userID).text(users[editSelectedComponentID][userID]));
    }
  }
  $select.prop('disabled', noUsers);
  $('#edit_component_policy_user_select_btn').prop('disabled', noUsers);
  $select.selectpicker('refresh');
  $select.change();
}

$(function () {
  setNewPolicyData();
  setEditPolicyData();
  $('.select-group-button').css('margin-top', '-=2px');
});
