'use strict';
/* eslint-env jquery */
/* globals structuredClone */

const users = window.getTemplateValue('component_users');
const policies = structuredClone(window.getTemplateValue('policies'));
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
    const policy = policies[addSelectedComponentID];
    setPolicyPermissionsTables(policy.permissions.projects, {}, window.getTemplateValue('translations.project_group'), window.getTemplateValue('translations.project_groups'), 'new_policy_projects_', 'permissions_add_policy_project_');
    setPolicyPermissionsTables(policy.permissions.groups, {}, window.getTemplateValue('translations.basic_group'), window.getTemplateValue('translations.basic_groups'), 'new_policy_groups_', 'permissions_add_policy_group_');
    setPolicyPermissionsTables(policy.permissions.users, users[addSelectedComponentID], window.getTemplateValue('translations.user'), window.getTemplateValue('translations.users'), 'new_policy_users_', 'permissions_add_policy_user_');
    updateAddSelect();
  }
}

function setEditPolicyData () {
  const selectedComponentID = +$('#edit-share-component-picker').val();
  if (!Number.isNaN(selectedComponentID) && selectedComponentID !== editSelectedComponentID) {
    if (!Number.isNaN(editSelectedComponentID)) {
      // reset current policy to original before switching, discarding previous changes
      policies[editSelectedComponentID] = structuredClone(window.getTemplateValue('policies')[editSelectedComponentID]);
    }
    editSelectedComponentID = selectedComponentID;
    const policy = policies[editSelectedComponentID];
    $('#policy-edit-data').prop('checked', policy.access.data).change();
    $('#policy-edit-action').prop('checked', policy.access.action).change();
    $('#policy-edit-users').prop('checked', policy.access.users).change();
    $('#policy-edit-files').prop('checked', policy.access.files).change();
    $('#policy-edit-comments').prop('checked', policy.access.comments).change();
    $('#policy-edit-object-location-assignments').prop('checked', policy.access.object_location_assignments).change();
    setPolicyPermissionsTables(policy.permissions.projects, {}, window.getTemplateValue('translations.project_group'), window.getTemplateValue('translations.project_groups'), 'edit_policy_projects_', 'permissions_edit_policy_project_');
    setPolicyPermissionsTables(policy.permissions.groups, {}, window.getTemplateValue('translations.basic_group'), window.getTemplateValue('translations.basic_groups'), 'edit_policy_groups_', 'permissions_edit_policy_group_');
    setPolicyPermissionsTables(policy.permissions.users, users[editSelectedComponentID], window.getTemplateValue('translations.user'), window.getTemplateValue('translations.users'), 'edit_policy_users_', 'permissions_edit_policy_user_');
    updateEditSelect();
  }
}

function setPolicyPermissionsTables (permissionsObject, nameObject, labelSingular, labelPlural, tablePrefix, fieldPrefix) {
  const permissionsTableBody = $(`#${tablePrefix}tbody`);
  permissionsTableBody.empty();
  permissionsTableBody.append(`
    <tr>
      <td></td>
      <th scope="rowgroup">${labelPlural}</th>
      <td></td>
      <td></td>
      <td></td>
    </tr>
  `);
  permissionsTableBody.hide();
  for (const id in permissionsObject) {
    let name = `${labelSingular} #${id}`;
    if (id in nameObject) {
      name = nameObject[id];
    }
    addPermissionsToPolicy(id, name, permissionsObject, tablePrefix, fieldPrefix);
  }
}

function addPermissionsToPolicy (id, name, permissionsObject, tablePrefix, fieldPrefix) {
  const permissions = permissionsObject[id];
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
    removePermissionsFromPolicy(id, permissionsObject, tablePrefix);
  });
  if (permissionsTableBody.find('tr').length > 1) {
    permissionsTableBody.show();
  }
}

function newPolicyAddUserSelect () {
  const $select = $('#add_share_user_picker');
  const userID = $select.val();
  const policy = policies[addSelectedComponentID];
  if (!(userID in policy.permissions.users)) {
    const userName = users[addSelectedComponentID][userID];
    policy.permissions.users[userID] = 'read';
    addPermissionsToPolicy(userID, userName, policy.permissions.users, 'new_policy_users_', 'permissions_add_policy_user_');
  }
  updateAddSelect();
}

function editPolicyAddUserSelect () {
  const $select = $('#edit_share_user_picker');
  const userID = $select.val();
  const policy = policies[editSelectedComponentID];
  if (!(userID in policy.permissions.users)) {
    const userName = users[editSelectedComponentID][userID];
    policy.permissions.users[userID] = 'read';
    addPermissionsToPolicy(userID, userName, policy.permissions.users, 'edit_policy_users_', 'permissions_edit_policy_user_');
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
  const policy = policies[addSelectedComponentID];
  const existingIDs = [];
  for (const id in policy.permissions.projects) {
    existingIDs.push(+id);
  }
  const projectID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.project_group_already_added'));
  if (projectID > 0) {
    const projectName = `${window.getTemplateValue('translations.project_group')}  #${projectID}`;
    $input.val('');
    policy.permissions.projects[projectID] = 'read';
    addPermissionsToPolicy(projectID, projectName, policy.permissions.projects, 'new_policy_projects_', 'permissions_add_policy_project_');
  }
}

function newPolicyAddGroupText () {
  const $input = $('#add_share_group_text');
  const $err = $('#add_share_group_text_help_block');
  const policy = policies[addSelectedComponentID];
  const existingIDs = [];
  for (const id in policy.permissions.groups) {
    existingIDs.push(+id);
  }
  const groupID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.basic_group_already_added'));
  if (groupID > 0) {
    const groupName = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
    $input.val('');
    policy.permissions.groups[groupID] = 'read';
    addPermissionsToPolicy(groupID, groupName, policy.permissions.groups, 'new_policy_groups_', 'permissions_add_policy_group_');
  }
}

function newPolicyAddUserText () {
  const $input = $('#add_share_user_text');
  const $err = $('#add_share_user_text_help_block');
  const policy = policies[addSelectedComponentID];
  const existingIDs = [];
  for (const id in policy.permissions.users) {
    existingIDs.push(+id);
  }
  const userID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.user_already_added'));
  if (userID) {
    let userName = `${window.getTemplateValue('translations.user')} #${userID}`;
    if (userID in users[addSelectedComponentID]) {
      userName = users[addSelectedComponentID][userID];
    }
    $input.val('');
    policy.permissions.users[userID] = 'read';
    addPermissionsToPolicy(userID, userName, policy.permissions.users, 'new_policy_users_', 'permissions_add_policy_user_');
    updateAddSelect();
  }
}

function editPolicyAddProjectText () {
  const $input = $('#edit_share_project_text');
  const $err = $('#edit_share_project_text_help_block');
  const policy = policies[editSelectedComponentID];
  const existingIDs = [];
  for (const id in policy.permissions.projects) {
    existingIDs.push(+id);
  }
  const projectID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.project_group_already_added'));
  if (projectID > 0) {
    const projectName = `${window.getTemplateValue('translations.project_group')} #${projectID}`;
    $input.val('');
    policy.permissions.projects[projectID] = 'read';
    addPermissionsToPolicy(projectID, projectName, policy.permissions.projects, 'edit_policy_projects_', 'permissions_edit_policy_project_');
  }
}

function editPolicyAddGroupText () {
  const $input = $('#edit_share_group_text');
  const $err = $('#edit_share_group_text_help_block');
  const policy = policies[editSelectedComponentID];
  const existingIDs = [];
  for (const id in policy.permissions.groups) {
    existingIDs.push(+id);
  }
  const groupID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.basic_group_already_added'));
  if (groupID > 0) {
    const groupName = `${window.getTemplateValue('translations.basic_group')} #${groupID}`;
    $input.val('');
    policy.permissions.groups[groupID] = 'read';
    addPermissionsToPolicy(groupID, groupName, policy.permissions.groups, 'edit_policy_groups_', 'permissions_edit_policy_group_');
  }
}

function editPolicyAddUserText () {
  const $input = $('#edit_share_user_text');
  const $err = $('#edit_share_user_text_help_block');
  const policy = policies[editSelectedComponentID];
  const existingIDs = [];
  for (const id in policy.permissions.users) {
    existingIDs.push(+id);
  }
  const userID = validateId($input, $err, existingIDs, window.getTemplateValue('translations.user_already_added'));
  if (userID > 0) {
    let userName = `${window.getTemplateValue('translations.user')} #${userID}`;
    if (userID in users[editSelectedComponentID]) {
      userName = users[editSelectedComponentID][userID];
    }
    $input.val('');
    policy.permissions.users[userID] = 'read';
    addPermissionsToPolicy(userID, userName, policy.permissions.users, 'edit_policy_users_', 'permissions_edit_policy_user_');
    updateEditSelect();
  }
}

function removePermissionsFromPolicy (id, policySelectedElements, tablePrefix) {
  if (id in policySelectedElements) {
    delete policySelectedElements[id];
    $(`#${tablePrefix}${id}`).remove();
  }
  const permissionsTableBody = $(`#${tablePrefix}tbody`);
  if (permissionsTableBody.find('tr').length === 1) {
    permissionsTableBody.hide();
  }
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
