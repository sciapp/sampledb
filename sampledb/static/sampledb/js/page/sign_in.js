'use strict';
/* eslint-env jquery */
/* jshint esversion: 8 */
/* globals Cookies */

import {
  get,
  supported,
  parseRequestOptionsFromJSON
} from '../../../webauthn-json/js/webauthn-json.browser-ponyfill.js';

if (window.getTemplateValue('config.enable_fido2_passkey_authentication')) {
  const authenticate = async function (e) {
    if (e) {
      e.preventDefault();
    }
    const options = window.getTemplateValue('fido2_options');
    const publicKeyCredentialRequestOptions = parseRequestOptionsFromJSON(options);
    const form = $('#fido2-authenticate-form');
    form.removeClass('has-error');
    updateFormHiddenFields(form);
    const helpBock = form.find('.help-block');
    helpBock.text('');
    try {
      const assertion = await get(publicKeyCredentialRequestOptions);
      form.find('[name="assertion"]').val(JSON.stringify(assertion));
      form[0].submit();
      return true;
    } catch (error) {
      form.addClass('has-error');
      helpBock.text(window.getTemplateValue('translations.passkey_failed') + error);
      return false;
    }
  };

  $(function () {
    if (supported()) {
      $('#fido2-authenticate-form').on('submit', authenticate);
    } else {
      $('#alert-fido2-not-supported').show();
      $('#fido2-authenticate-form button').prop('disabled', true);
    }
  });
}

function updateFormHiddenFields (form) {
  if ($('#input-shared_device').prop('checked')) {
    form.find('[name="shared_device"]').val('shared_device');
    form.find('[name="remember_me"]').val('');
  } else {
    if ($('#input-rememberme').prop('checked')) {
      form.find('[name="remember_me"]').val('remember_me');
    } else {
      form.find('[name="remember_me"]').val('');
    }
    form.find('[name="shared_device"]').val('');
  }
}

$(function () {
  $('#form-signin').on('submit', function () {
    const form = $('#form-signin');
    updateFormHiddenFields(form);
    return true;
  });

  $('.federated-login-form').on('submit', function () {
    updateFormHiddenFields($(this));
    return true;
  });

  $('#input-shared_device').on('change', function () {
    Cookies.set('SAMPLEDB_SHARED_DEVICE_DEFAULT', $(this).prop('checked') || '', { sameSite: 'Lax' });
    if ($(this).prop('checked')) {
      $('#input-rememberme').prop('disabled', true).prop('checked', false);
    } else {
      $('#input-rememberme').prop('disabled', false);
    }
  }).trigger('change');
});
