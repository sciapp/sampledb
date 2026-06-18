'use strict';
/* eslint-env jquery */

import {
  selectedObjectIDs
} from './multiselect-base.js';

$(function () {
  window.checkSubmittableImpl = function (submitTooltip, submitButton) {
    selectedObjectIDs.sort();
    const joinedSelectedObjectIDs = selectedObjectIDs.join(',');
    submitButton.each(function () {
      const link = $(this);
      link.attr('href', link.data('href').replaceAll(link.data('id-placeholder'), joinedSelectedObjectIDs));
    });
    return true;
  };
});
