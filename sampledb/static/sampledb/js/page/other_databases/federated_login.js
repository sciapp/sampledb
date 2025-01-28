'use strict';
/* eslint-env jquery */

$(function () {
  const usernameInput = $('#input-username');
  usernameInput.parents('form').submit(function () {
    const usernameData = usernameInput.val().trim();
    if (usernameData === '' || (window.getTemplateValue('config.enforce_split_names') && !usernameData.substring(1, usernameData.length - 2).includes(', '))) {
      usernameInput.parents('.form-group').addClass('has-error');
      return false;
    }
    return true;
  });
});
