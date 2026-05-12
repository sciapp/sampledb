'use strict';
/* eslint-env jquery */

import {
  isObjectSelected,
  getSelectableObjectIDs
} from './multiselect-base.js';

$(function () {
  const existingAccessPolicies = {};
  for (const objectID of getSelectableObjectIDs()) {
    const existingPolicyLinks = $(`a[data-sampledb-object-id="${objectID}"][data-sampledb-component-id]`);
    if (existingPolicyLinks.length === 0) {
      continue;
    }
    existingAccessPolicies[objectID] = {};
    for (const existingPolicyLink of existingPolicyLinks) {
      const componentID = $(existingPolicyLink).data('sampledb-component-id');
      existingAccessPolicies[objectID][componentID] = {};
      for (const key of ['data', 'action', 'users', 'files', 'comments', 'object_location_assignments']) {
        existingAccessPolicies[objectID][componentID][key] = $(existingPolicyLink).data(`sampledb-policy-access-${key}`) === true;
      }
    }
  }
  $('.checkbox-select-child, #checkbox-select-overall, #add_share_component_picker, [data-toggle]').on('click, change', function () {
    const componentID = $('#add_share_component_picker').val();
    const newAccessKeys = [];
    for (const key of ['data', 'action', 'users', 'files', 'comments', 'object_location_assignments']) {
      if ($(`input[name=${key}]`).prop('checked')) {
        newAccessKeys.push(key);
      }
    }
    let hasNewAccess = false;
    for (const objectID of Object.keys(existingAccessPolicies)) {
      if (isObjectSelected(Number.parseInt(objectID)) && Object.hasOwn(existingAccessPolicies[objectID], componentID)) {
        for (const key of newAccessKeys) {
          if (!existingAccessPolicies[objectID][componentID][key]) {
            hasNewAccess = true;
            break;
          }
        }
      }
      if (hasNewAccess) {
        break;
      }
    }
    $('#new-access-warning').toggle(hasNewAccess);
  });
});
