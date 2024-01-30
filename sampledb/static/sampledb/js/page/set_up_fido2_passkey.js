'use strict';
/* eslint-env jquery */
/* jshint esversion: 8 */

import {
  create,
  supported,
  parseCreationOptionsFromJSON
} from '../../../webauthn-json/js/webauthn-json.browser-ponyfill.js';

export async function register () {
  const options = window.getTemplateValue('fido2_options');
  const form = $('#setup-form');
  form.removeClass('has-error');
  const helpBlock = form.find('.help-block');
  helpBlock.text('');
  try {
    const publicKeyCredentialCreationOptions = parseCreationOptionsFromJSON(options);
    const credential = await create(publicKeyCredentialCreationOptions);
    form.find("[name='fido2_passkey_credentials']").val(JSON.stringify(credential));
    form[0].submit();
    return true;
  } catch (error) {
    $('#descriptionFormGroup').addClass('has-error');
    helpBlock.text(window.getTemplateValue('translations.passkey_failed') + error);
    return false;
  }
}

$(function () {
  if (supported()) {
    $('#setup-form').on('submit', function (event) {
      if (event) {
        event.preventDefault();
      }
      if ($('#input-passkey-description').val() === '') {
        $('#descriptionFormGroup').addClass('has-error').find('.help-block').text(window.getTemplateValue('translations.enter_at_least_1_character'));
        return false;
      } else {
        $('#descriptionFormGroup').removeClass('has-error').find('.help-block').text('');
        return register();
      }
    });
  } else {
    $('#alert-fido2-not-supported').show();
    $('#setup-form input').prop('disabled', true);
  }
});
