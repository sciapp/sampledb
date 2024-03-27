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
    projectsTableBody.hide();
    for (const projectID in policies[editSelectedComponentID].permissions.projects) {
      const permissions = policies[editSelectedComponentID].permissions.projects[projectID];
      editPolicySelectedProjects[projectID] = `${window.getTemplateValue('translations.project_group')} #${projectID}`;
      addPermissionsToPolicy(projectID, editPolicySelectedProjects[projectID], permissions, editPolicyRemoveProject, 'edit_policy_projects_', 'permissions_edit_policy_project_');
    }
    const groupsTableBody = $('#edit_policy_groups_tbody');
    groupsTableBody.empty();
    groupsTableBody.append(`<tr><td></td><th scope="rowgroup">${window.getTemplateValue('translations.basic_groups')}</th><td></td><td></td><td></td></tr>`);
    groupsTableBody.hide();
    for (const groupID in policies[editSelectedComponentID].permissions.groups) {
      const permissions = policies[editSelectedComponentID].permissions.groups[groupID];
      editPolicySelectedGroups[groupID] = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
      addPermissionsToPolicy(groupID, editPolicySelectedGroups[groupID], permissions, editPolicyRemoveGroup, 'edit_policy_groups_', 'permissions_edit_policy_group_');
    }
    const usersTableBody = $('#edit_policy_users_tbody');
    usersTableBody.empty();
    usersTableBody.append(`<tr><td></td><th scope="rowgroup">${window.getTemplateValue('translations.users')}</th><td></td><td></td><td></td></tr>`);
    usersTableBody.hide();
    for (const userID in policies[editSelectedComponentID].permissions.users) {
      const permissions = policies[editSelectedComponentID].permissions.users[userID];
      if (userID in users[editSelectedComponentID]) {
        editPolicySelectedUsers[userID] = users[editSelectedComponentID][userID];
      } else {
        editPolicySelectedUsers[userID] = `${window.getTemplateValue('translations.user')} #${userID}`;
      }
      addPermissionsToPolicy(userID, editPolicySelectedUsers[userID], permissions, editPolicyRemoveUser, 'edit_policy_users_', 'permissions_edit_policy_user_');
    }
    updateEditSelect();
  }
}

function addPermissionsToPolicy (id, name, permissions, removePermissionsHandler, tablePrefix, fieldPrefix) {
  const permissionsTableBody = $(`#${tablePrefix}tbody`);
  const permissionsRow = $(`
    <tr id="${tablePrefix}${id}">
      <td class="text-center"><button class="btn btn-xs btn-danger" type="button"><i class="fa fa-times" aria-hidden="true"></i></button></td>
      <td>${name}</td>
    </tr>
  `);
  for (const possiblePermissions of ['read', 'write', 'grant']) {
    permissionsRow.append(`
      <td class="text-center" style="vertical-align: middle">
        <label for="${fieldPrefix}${id}_${possiblePermissions}" class="sr-only">${possiblePermissions}</label>
        <input type="radio" name="${fieldPrefix}${id}" id="${fieldPrefix}${id}_${possiblePermissions}" value="${possiblePermissions}" ${(possiblePermissions === permissions) ? 'checked="checked"' : ''} />
      </td>
    `);
  }
  permissionsTableBody.append(permissionsRow);
  permissionsRow.find('button').on('click', function () {
    removePermissionsHandler(id);
  });
  if (permissionsTableBody.find('tr').length > 1) {
    permissionsTableBody.show();
  }
}

function newPolicyAddUserSelect () {
  const $select = $('#add_share_user_picker');
  const userID = $select.val();
  if (!(userID in newPolicySelectedUsers)) {
    newPolicySelectedUsers[userID] = users[addSelectedComponentID][userID];
    const permissions = 'read';
    addPermissionsToPolicy(userID, newPolicySelectedUsers[userID], permissions, newPolicyRemoveUser, 'new_policy_users_', 'permissions_add_policy_user_');
  }
  updateAddSelect();
}

function editPolicyAddUserSelect () {
  const $select = $('#edit_share_user_picker');
  const userID = $select.val();
  if (!(userID in editPolicySelectedUsers)) {
    editPolicySelectedUsers[userID] = users[editSelectedComponentID][userID];
    const permissions = 'read';
    addPermissionsToPolicy(userID, editPolicySelectedUsers[userID], permissions, editPolicyRemoveUser, 'edit_policy_users_', 'permissions_edit_policy_user_');
  }
  updateEditSelect();
}

for (const idAndHandler of [
  ['add_share_project_text', newPolicyAddProjectText],
  ['add_share_group_text', newPolicyAddGroupText],
  ['add_share_user_text', newPolicyAddUserText],
  ['edit_share_project_text', editPolicyAddProjectText],
  ['edit_share_group_text', editPolicyAddGroupText],
  ['edit_share_user_text', editPolicyAddUserText]
]) {
  const id = idAndHandler[0];
  const handler = idAndHandler[1];
  $(`#${id}`).keydown(function (evt) {
    if (evt.key === 'Enter' || evt.keyCode === 13) {
      handler();
      evt.preventDefault();
      return false;
    }
  });
}

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
    const permissions = 'read';
    addPermissionsToPolicy(projectID, newPolicySelectedProjects[projectID], permissions, newPolicyRemoveProject, 'new_policy_projects_', 'permissions_add_policy_project_');
  }
}

function newPolicyAddGroupText () {
  const $input = $('#add_share_group_text');
  const $err = $('#add_share_group_text_help_block');
  const groupID = validateId($input, $err, newPolicySelectedGroups, window.getTemplateValue('translations.basic_group_already_added'));
  if (groupID > 0) {
    newPolicySelectedGroups[groupID] = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
    $input.val('');
    const permissions = 'read';
    addPermissionsToPolicy(groupID, newPolicySelectedGroups[groupID], permissions, newPolicyRemoveGroup, 'new_policy_groups_', 'permissions_add_policy_group_');
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
    const permissions = 'read';
    addPermissionsToPolicy(userID, newPolicySelectedUsers[userID], permissions, editPolicyRemoveUser, 'new_policy_users_', 'permissions_add_policy_user_');
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
    const permissions = 'read';
    addPermissionsToPolicy(projectID, editPolicySelectedProjects[projectID], permissions, editPolicyRemoveProject, 'edit_policy_projects_', 'permissions_edit_policy_project_');
  }
}

function editPolicyAddGroupText () {
  const $input = $('#edit_share_group_text');
  const $err = $('#edit_share_group_text_help_block');
  const groupID = validateId($input, $err, editPolicySelectedGroups, window.getTemplateValue('translations.basic_group_already_added'));
  if (groupID > 0) {
    editPolicySelectedGroups[groupID] = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
    $input.val('');
    const permissions = 'read';
    addPermissionsToPolicy(groupID, editPolicySelectedGroups[groupID], permissions, editPolicyRemoveGroup, 'edit_policy_groups_', 'permissions_edit_policy_group_');
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
    const permissions = 'read';
    addPermissionsToPolicy(userID, editPolicySelectedUsers[userID], permissions, editPolicyRemoveUser, 'edit_policy_users_', 'permissions_edit_policy_user_');
    updateEditSelect();
  }
}

function removePermissionsFromPolicy (id, policySelectedElements, tablePrefix) {
  if (id in policySelectedElements) {
    delete policySelectedElements[id];
    $(`#${tablePrefix}${id}`).remove();
  }
  const permissionsTableBody = $(`${tablePrefix}_tbody`);
  if (permissionsTableBody.find('tr').length === 1) {
    permissionsTableBody.hide();
  }
}

function newPolicyRemoveProject (projectID) {
  removePermissionsFromPolicy(projectID, newPolicySelectedProjects, 'new_policy_projects_');
}

function newPolicyRemoveGroup (groupID) {
  removePermissionsFromPolicy(groupID, newPolicySelectedGroups, 'new_policy_groups_');
}

function newPolicyRemoveUser (userID) {
  removePermissionsFromPolicy(userID, newPolicySelectedUsers, 'new_policy_users_');
  updateAddSelect();
}

function editPolicyRemoveProject (projectID) {
  removePermissionsFromPolicy(projectID, editPolicySelectedProjects, 'edit_policy_projects_');
}

function editPolicyRemoveGroup (groupID) {
  removePermissionsFromPolicy(groupID, editPolicySelectedGroups, 'edit_policy_groups_');
}

function editPolicyRemoveUser (userID) {
  removePermissionsFromPolicy(userID, editPolicySelectedUsers, 'edit_policy_users_');
  updateEditSelect();
}

function updateUserSelect ($select, $selectButton, componentID, policySelectedUsers) {
  $select.empty();
  let noUsers = true;
  for (const userID in users[componentID]) {
    if (!(userID in policySelectedUsers)) {
      noUsers = false;
      $select.append($('<option></option>').attr('value', userID).text(users[componentID][userID]));
    }
  }
  $select.prop('disabled', noUsers);
  $selectButton.prop('disabled', noUsers);
  $select.selectpicker('refresh');
  $select.change();
}

function updateAddSelect () {
  const $select = $('#add_share_user_picker');
  const $selectButton = $('#add_component_policy_user_select_btn');
  updateUserSelect($select, $selectButton, addSelectedComponentID, newPolicySelectedUsers);
}

function updateEditSelect () {
  const $select = $('#edit_share_user_picker');
  const $selectButton = $('#edit_component_policy_user_select_btn');
  updateUserSelect($select, $selectButton, editSelectedComponentID, editPolicySelectedUsers);
}

$(function () {
  setNewPolicyData();
  setEditPolicyData();
  $('.select-group-button').css('margin-top', '-=2px');
});
