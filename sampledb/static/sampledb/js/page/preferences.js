'use strict';
/* eslint-env jquery */
/* jshint esversion: 8 */
/* globals moment */

import {
  create,
  supported,
  parseCreationOptionsFromJSON
} from '../../../webauthn-json/js/webauthn-json.browser-ponyfill.js';

if (window.getTemplateValue('config.timezone_not_set')) {
  const localTimezone = moment.tz.guess(true);
  const automaticTimezoneField = document.getElementById('auto_tz');
  automaticTimezoneField.textContent += localTimezone;
}

if (window.getTemplateValue('has_created_api_token')) {
  $('#viewApiTokenModal').modal('show');
  $('#api-token button').bind('click', function () {
    const input = document.querySelector('#api-token input');
    input.setSelectionRange(0, input.value.length + 1);
    $(input).focus();
    try {
      const success = document.execCommand('copy');
      if (success) {
        $('#api-token-copy-notes').text(window.getTemplateValue('translations.copied'));
        $('#api-token').removeClass('has-error').addClass('has-success');
      } else {
        $('#api-token-copy-notes').text(window.getTemplateValue('translations.could_not_copy'));
        $('#api-token').removeClass('has-success').addClass('has-error');
      }
    } catch (err) {
      $('#api-token-copy-notes').text(window.getTemplateValue('translations.could_not_copy'));
      $('#api-token').removeClass('has-success').addClass('has-error');
    }
  });
}

if (window.getTemplateValue('show_api_token_modal')) {
  $('#createApiTokenModal').modal('show');
}

if (window.getTemplateValue('show_add_webhook_form')) {
  $(document).ready(function () {
    const addWebhookModal = $('#addWebhookModal');
    addWebhookModal.removeClass('fade');
    addWebhookModal.modal('show');
    addWebhookModal.addClass('fade');
  });
}

if (window.getTemplateValue('has_created_webhook_secret')) {
  $('#viewWebhookSecretModal').modal('show');
  $('#webhook-secret button').bind('click', function () {
    const input = document.querySelector('#webhook-secret input');
    input.setSelectionRange(0, input.value.length + 1);
    $(input).focus();
    try {
      const success = document.execCommand('copy');
      if (success) {
        $('#webhook-secret-copy-notes').text(window.getTemplateValue('translations.copied'));
        $('#webhook-secret').removeClass('has-error').addClass('has-success');
      } else {
        $('#webhook-secret-copy-notes').text(window.getTemplateValue('translations.could_not_copy'));
        $('#webhook-secret').removeClass('has-success').addClass('has-error');
      }
    } catch (err) {
      $('#webhook-secret-copy-notes').text(window.getTemplateValue('translations.could_not_copy'));
      $('#webhook-secret').removeClass('has-success').addClass('has-error');
    }
  });
}

export async function register () {
  const options = window.getTemplateValue('fido2_options');
  const form = $('#form-add-authentication-methods');
  const typeFormGroup = $('#addAuthenticationMethodTypeSelect').closest('.form-group');
  typeFormGroup.removeClass('has-error');
  const helpBlock = typeFormGroup.find('.help-block');
  helpBlock.text('');
  try {
    const publicKeyCredentialCreationOptions = parseCreationOptionsFromJSON(options);
    const credential = await create(publicKeyCredentialCreationOptions);
    form.find("[name='fido2_passkey_credentials']").val(JSON.stringify(credential));
    form[0].submit();
    return true;
  } catch (error) {
    typeFormGroup.addClass('has-error');
    helpBlock.text(window.getTemplateValue('translations.passkey_failed') + error);
    return false;
  }
}

$(function () {
  const addAuthenticationMethodTypeSelect = $('#addAuthenticationMethodTypeSelect');
  addAuthenticationMethodTypeSelect.on('changed.bs.select', function () {
    if (addAuthenticationMethodTypeSelect.val() === 'FIDO2_PASSKEY') {
      $('#addAuthenticationMethodDescriptionGroup').show().find('input').prop('disabled', false);
      $('#addAuthenticationMethodLoginGroup, #addAuthenticationMethodPasswordGroup').hide().find('input').prop('disabled', true);
    } else {
      addAuthenticationMethodTypeSelect.closest('.form-group').removeClass('has-error').find('.help-block').text('');
      $('#addAuthenticationMethodDescriptionGroup').hide().find('input').prop('disabled', true);
      $('#addAuthenticationMethodLoginGroup, #addAuthenticationMethodPasswordGroup').show().find('input').prop('disabled', false);
    }
  });
  if (supported()) {
    $('#form-add-authentication-methods').on('submit', function (event) {
      if (addAuthenticationMethodTypeSelect.val() === 'FIDO2_PASSKEY') {
        if (event) {
          event.preventDefault();
        }
        if ($('#input-passkey-description').val() === '') {
          $('#addAuthenticationMethodDescriptionGroup').addClass('has-error').find('.help-block:last').text(window.getTemplateValue('translations.enter_at_least_1_character'));
          return false;
        } else {
          $('#addAuthenticationMethodDescriptionGroup').removeClass('has-error').find('.help-block:last').text('');
          return register();
        }
      }
      return true;
    });
  } else {
    if (addAuthenticationMethodTypeSelect.val() === 'FIDO2_PASSKEY') {
      addAuthenticationMethodTypeSelect.val('E');
    }
    addAuthenticationMethodTypeSelect.find('option[value="FIDO2_PASSKEY"]').prop('disabled', true);
    addAuthenticationMethodTypeSelect.selectpicker('refresh');
  }
  addAuthenticationMethodTypeSelect.trigger('changed.bs.select');
});
