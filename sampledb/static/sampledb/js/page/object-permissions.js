'use strict';
/* eslint-env jquery */

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
    delete policies[addSelectedComponentID];
    addSelectedComponentID = selectedComponentID;
    policies[addSelectedComponentID] = {
      permissions: {
        projects: {},
        groups: {},
        users: {}
      }
    };
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
    updateAddSelect();
  }
}

function setEditPolicyData () {
  const selectedComponentID = +$('#edit-share-component-picker').val();
  if (!Number.isNaN(selectedComponentID) && selectedComponentID !== editSelectedComponentID) {
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
      const projectName = `${window.getTemplateValue('translations.project_group')} #${projectID}`;
      addPermissionsToPolicy(projectID, projectName, permissions, editPolicyRemoveProject, 'edit_policy_projects_', 'permissions_edit_policy_project_');
    }
    const groupsTableBody = $('#edit_policy_groups_tbody');
    groupsTableBody.empty();
    groupsTableBody.append(`<tr><td></td><th scope="rowgroup">${window.getTemplateValue('translations.basic_groups')}</th><td></td><td></td><td></td></tr>`);
    groupsTableBody.hide();
    for (const groupID in policies[editSelectedComponentID].permissions.groups) {
      const permissions = policies[editSelectedComponentID].permissions.groups[groupID];
      const groupName = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
      addPermissionsToPolicy(groupID, groupName, permissions, editPolicyRemoveGroup, 'edit_policy_groups_', 'permissions_edit_policy_group_');
    }
    const usersTableBody = $('#edit_policy_users_tbody');
    usersTableBody.empty();
    usersTableBody.append(`<tr><td></td><th scope="rowgroup">${window.getTemplateValue('translations.users')}</th><td></td><td></td><td></td></tr>`);
    usersTableBody.hide();
    for (const userID in policies[editSelectedComponentID].permissions.users) {
      const permissions = policies[editSelectedComponentID].permissions.users[userID];
      let userName = `${window.getTemplateValue('translations.user')} #${userID}`;
      if (userID in users[editSelectedComponentID]) {
        userName = users[editSelectedComponentID][userID];
      }
      addPermissionsToPolicy(userID, userName, permissions, editPolicyRemoveUser, 'edit_policy_users_', 'permissions_edit_policy_user_');
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
  if (!(userID in policies[addSelectedComponentID].permissions.users)) {
    const userName = users[addSelectedComponentID][userID];
    const permissions = 'read';
    policies[addSelectedComponentID].permissions.users[userID] = permissions;
    addPermissionsToPolicy(userID, userName, permissions, newPolicyRemoveUser, 'new_policy_users_', 'permissions_add_policy_user_');
  }
  updateAddSelect();
}

function editPolicyAddUserSelect () {
  const $select = $('#edit_share_user_picker');
  const userID = $select.val();
  if (!(userID in policies[editSelectedComponentID].permissions.users)) {
    const userName = users[editSelectedComponentID][userID];
    const permissions = 'read';
    policies[editSelectedComponentID].permissions.users[userID] = permissions;
    addPermissionsToPolicy(userID, userName, permissions, editPolicyRemoveUser, 'edit_policy_users_', 'permissions_edit_policy_user_');
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

function validateId ($input, $err, existingIDs, alreadyAddedText) {
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
  } else if (existingIDs.includes(id)) {
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
  const existingIDs = [];
  for (const id in policies[addSelectedComponentID].permissions.projects) {
    existingIDs.push(+id);
  }
  const projectID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.project_group_already_added'));
  if (projectID > 0) {
    const projectName = `${window.getTemplateValue('translations.project_group')}  #${projectID}`;
    $input.val('');
    const permissions = 'read';
    policies[addSelectedComponentID].permissions.projects[projectID] = permissions;
    addPermissionsToPolicy(projectID, projectName, permissions, newPolicyRemoveProject, 'new_policy_projects_', 'permissions_add_policy_project_');
  }
}

function newPolicyAddGroupText () {
  const $input = $('#add_share_group_text');
  const $err = $('#add_share_group_text_help_block');
  const existingIDs = [];
  for (const id in policies[addSelectedComponentID].permissions.groups) {
    existingIDs.push(+id);
  }
  const groupID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.basic_group_already_added'));
  if (groupID > 0) {
    const groupName = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
    $input.val('');
    const permissions = 'read';
    policies[addSelectedComponentID].permissions.groups[groupID] = permissions;
    addPermissionsToPolicy(groupID, groupName, permissions, newPolicyRemoveGroup, 'new_policy_groups_', 'permissions_add_policy_group_');
  }
}

function newPolicyAddUserText () {
  const $input = $('#add_share_user_text');
  const $err = $('#add_share_user_text_help_block');
  const existingIDs = [];
  for (const id in policies[addSelectedComponentID].permissions.users) {
    existingIDs.push(+id);
  }
  const userID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.user_already_added'));
  if (userID) {
    let userName = `${window.getTemplateValue('translations.user')} #${userID}`;
    if (userID in users[addSelectedComponentID]) {
      userName = users[addSelectedComponentID][userID];
    }
    $input.val('');
    const permissions = 'read';
    policies[addSelectedComponentID].permissions.users[userID] = permissions;
    addPermissionsToPolicy(userID, userName, permissions, editPolicyRemoveUser, 'new_policy_users_', 'permissions_add_policy_user_');
    updateAddSelect();
  }
}

function editPolicyAddProjectText () {
  const $input = $('#edit_share_project_text');
  const $err = $('#edit_share_project_text_help_block');
  const existingIDs = [];
  for (const id in policies[editSelectedComponentID].permissions.projects) {
    existingIDs.push(+id);
  }
  const projectID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.project_group_already_added'));
  if (projectID > 0) {
    const projectName = `${window.getTemplateValue('translations.project_group')} #${projectID}`;
    $input.val('');
    const permissions = 'read';
    policies[editSelectedComponentID].permissions.projects[projectID] = permissions;
    addPermissionsToPolicy(projectID, projectName, permissions, editPolicyRemoveProject, 'edit_policy_projects_', 'permissions_edit_policy_project_');
  }
}

function editPolicyAddGroupText () {
  const $input = $('#edit_share_group_text');
  const $err = $('#edit_share_group_text_help_block');
  const existingIDs = [];
  for (const id in policies[editSelectedComponentID].permissions.groups) {
    existingIDs.push(+id);
  }
  const groupID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.basic_group_already_added'));
  if (groupID > 0) {
    const groupName = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
    $input.val('');
    const permissions = 'read';
    policies[editSelectedComponentID].permissions.groups[groupID] = permissions;
    addPermissionsToPolicy(groupID, groupName, permissions, editPolicyRemoveGroup, 'edit_policy_groups_', 'permissions_edit_policy_group_');
  }
}

function editPolicyAddUserText () {
  const $input = $('#edit_share_user_text');
  const $err = $('#edit_share_user_text_help_block');
  const existingIDs = [];
  for (const id in policies[editSelectedComponentID].permissions.users) {
    existingIDs.push(+id);
  }
  const userID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.user_already_added'));
  if (userID > 0) {
    let userName = `${window.getTemplateValue('translations.user')} #${userID}`;
    if (userID in users[editSelectedComponentID]) {
      userName = users[editSelectedComponentID][userID];
    }
    $input.val('');
    const permissions = 'read';
    policies[editSelectedComponentID].permissions.users[userID] = permissions;
    addPermissionsToPolicy(userID, userName, permissions, editPolicyRemoveUser, 'edit_policy_users_', 'permissions_edit_policy_user_');
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
  removePermissionsFromPolicy(projectID, policies[addSelectedComponentID].permissions.projects, 'new_policy_projects_');
}

function newPolicyRemoveGroup (groupID) {
  removePermissionsFromPolicy(groupID, policies[addSelectedComponentID].permissions.groups, 'new_policy_groups_');
}

function newPolicyRemoveUser (userID) {
  removePermissionsFromPolicy(userID, policies[addSelectedComponentID].permissions.users, 'new_policy_users_');
  updateAddSelect();
}

function editPolicyRemoveProject (projectID) {
  removePermissionsFromPolicy(projectID, policies[editSelectedComponentID].permissions.projects, 'edit_policy_projects_');
}

function editPolicyRemoveGroup (groupID) {
  removePermissionsFromPolicy(groupID, policies[editSelectedComponentID].permissions.groups, 'edit_policy_groups_');
}

function editPolicyRemoveUser (userID) {
  removePermissionsFromPolicy(userID, policies[editSelectedComponentID].permissions.users, 'edit_policy_users_');
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
  updateUserSelect($select, $selectButton, addSelectedComponentID, policies[addSelectedComponentID].permissions.users);
}

function updateEditSelect () {
  const $select = $('#edit_share_user_picker');
  const $selectButton = $('#edit_component_policy_user_select_btn');
  updateUserSelect($select, $selectButton, editSelectedComponentID, policies[editSelectedComponentID].permissions.users);
}

$(function () {
  setNewPolicyData();
  setEditPolicyData();
  $('.select-group-button').css('margin-top', '-=2px');
});
