'use strict';
/* eslint-env jquery */

import {
  isObjectSelected,
  getSelectableObjectIDs,
  checkSubmittable
} from './multiselect-base.js';

const normalEntities = ['user', 'group', 'project-group'];
const specialGroups = ['signed-in-users', 'anonymous'];
const disabledSpecialGroupPermissions = ['write', 'grant'];
const currentPermissionsSpecialGroups = window.getTemplateValue('current_permissions_special_groups');
const currentPermissionsNormalEntities = window.getTemplateValue('current_permissions_normal_entities');

let activePermissions;

window.checkSubmittableImpl = function (submitTooltip, submitButton) {
  const targetType = $('#edit-permissions-target-type').val();
  const updateMode = $('input:radio[name="update_mode"]:checked').val();
  const permission = $("input:radio[name='permission']:checked").val();

  if (targetType === null) {
    submitTooltip.attr('data-original-title', window.getTemplateValue('translations.you_have_to_select_a_target_type')).tooltip('setContent').tooltip('enable');
    submitButton.prop('disabled', true);
    return false;
  } else if (targetType === 'group' && $('#edit-permissions-groups').val() === null) {
    submitTooltip.attr('data-original-title', window.getTemplateValue('translations.you_have_to_select_a_basic_group')).tooltip('setContent').tooltip('enable');
    submitButton.prop('disabled', true);
    return false;
  } else if (targetType === 'project-group' && $('#edit-permissions-project-groups').val() === null) {
    submitTooltip.attr('data-original-title', window.getTemplateValue('translations.you_have_to_select_a_project_group')).tooltip('setContent').tooltip('enable');
    submitButton.prop('disabled', true);
    return false;
  } else if (targetType === 'user' && $('#edit-permissions-users').val() === null) {
    submitTooltip.attr('data-original-title', window.getTemplateValue('translations.you_have_to_select_a_user')).tooltip('setContent').tooltip('enable');
    submitButton.prop('disabled', true);
    return false;
  }

  if (updateMode === undefined) {
    submitTooltip.attr('data-original-title', window.getTemplateValue('translations.you_have_to_select_how_to_update')).tooltip('setContent').tooltip('enable');
    submitButton.prop('disabled', true);
    return false;
  }

  if (permission === undefined) {
    submitTooltip.attr('data-original-title', window.getTemplateValue('translations.you_have_to_select_a_permission')).tooltip('setContent').tooltip('enable');
    submitButton.prop('disabled', true);
    return false;
  } else if (specialGroups.includes($('#edit-permissions-target-type')) && disabledSpecialGroupPermissions.includes($("input:radio[name='permission']:checked").val())) {
    submitTooltip.attr('data-original-title', window.getTemplateValue('translations.you_have_selected_write_grant_permissions_for_special_group')).tooltip('setContent').tooltip('enable');
    submitButton.prop('disabled', true);
    return false;
  }
  return true;
};

function updateActivePermissionData () {
  const targetType = $('#edit-permissions-target-type').val();
  const permissionRadioButtons = $("input:radio[name='permission']");

  if (specialGroups.includes(targetType)) {
    activePermissions = currentPermissionsSpecialGroups[targetType];
    for (const permission of disabledSpecialGroupPermissions) {
      if (permission === $(permissionRadioButtons).filter(':checked').val()) {
        $(permissionRadioButtons).filter("[value='none']").prop('checked', true);
      }
      $(permissionRadioButtons).filter(`[value='${permission}']`).prop('disabled', true).parent().addClass('permission-entry-disabled');
    }
  } else {
    const entityID = $(`#edit-permissions-${targetType}s`).val();
    activePermissions = currentPermissionsNormalEntities[targetType][entityID] || {};
    for (const permission of disabledSpecialGroupPermissions) {
      $(permissionRadioButtons).filter(`[value='${permission}']`).prop('disabled', false).parent().removeClass('permission-entry-disabled');
    }
  }
}

function updatePermissionForm () {
  const targetType = $('#edit-permissions-target-type').val();
  for (const type of normalEntities) {
    $(`#edit-permissions-${type}s-container`).toggle(targetType === type);
    $(`#edit-permissions-${type}s`).prop('disabled', targetType !== type).selectpicker('refresh');
  }
}

function updatePermissionsTable () {
  for (const objectID of getSelectableObjectIDs()) {
    const availablePermissions = ['none', 'read', 'write', 'grant'];
    const updateMode = $("input:radio[name='update_mode']:checked").val();
    const newPermission = $("input:radio[name='permission']:checked").val();
    const newPermissionIndex = availablePermissions.indexOf(newPermission);
    const currentPermission = activePermissions[objectID] || 'none';
    const currentPermissionIndex = availablePermissions.indexOf(currentPermission);
    const objectIsSelected = isObjectSelected(objectID);

    let resultPermission = currentPermission;
    if (((updateMode === 'set-min' && currentPermissionIndex <= newPermissionIndex) || (updateMode === 'set-max' && currentPermissionIndex >= newPermissionIndex)) && objectIsSelected) {
      resultPermission = newPermission;
    }
    for (const availablePermission of availablePermissions) {
      $(`#permission-${objectID}-${availablePermission} i`).attr('class', (availablePermission === resultPermission) ? 'fa fa-check' : 'fa fa-times');
    }
    $(`.permissions-entry-${objectID}`).toggleClass('permission-entry-disabled', !objectIsSelected);
  }
}

$(function () {
  updateActivePermissionData();

  $('#edit-permissions-target-type').on('change', function () {
    updatePermissionForm();
    updateActivePermissionData();
  });
  $('#edit-permissions-groups').on('change', updateActivePermissionData);
  $('#edit-permissions-users').on('change', updateActivePermissionData);
  $('#edit-permissions-project-groups').on('change', updateActivePermissionData);
  $('#checkbox-select-overall, .checkbox-select-child').on('change', updatePermissionsTable);
  $('#multiselect-form').on('change', function () {
    updatePermissionsTable();
    checkSubmittable();
  });
});
