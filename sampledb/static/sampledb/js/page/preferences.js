 import {
  create,
  supported,
  parseCreationOptionsFromJSON
} from '../../../webauthn-json/js/webauthn-json.browser-ponyfill.js';

if (window.getTemplateValue("config.timezone_not_set")) {
  const tz_pref = moment.tz.guess(true);
  var auto_tz = document.getElementById("auto_tz");
  auto_tz.textContent += tz_pref;
}

if (window.getTemplateValue("has_created_api_token")) {
  $('#viewApiTokenModal').modal('show');
  $('#api-token button').bind('click', function() {
    var input = document.querySelector('#api-token input');
    input.setSelectionRange(0, input.value.length + 1);
    $(input).focus();
    try {
      var success = document.execCommand('copy');
      if (success) {
        $('#api-token-copy-notes').text(window.getTemplateValue("translations.copied"));
        $('#api-token').removeClass('has-error').addClass('has-success');
      } else {
        $('#api-token-copy-notes').text(window.getTemplateValue("translations.could_not_copy"));
        $('#api-token').removeClass('has-success').addClass('has-error');
      }
    } catch (err) {
        $('#api-token-copy-notes').text(window.getTemplateValue("translations.could_not_copy"));
        $('#api-token').removeClass('has-success').addClass('has-error');
    }
  });
}

if (window.getTemplateValue("show_api_token_modal")) {
  $('#createApiTokenModal').modal('show');
}

if (window.getTemplateValue("show_add_webhook_form")) {
  $(document).ready(function() {
    var add_modal = $('#addWebhookModal');
    add_modal.removeClass('fade');
    add_modal.modal('show');
    add_modal.addClass('fade');
  });
}

if (window.getTemplateValue("has_created_webhook_secret")) {
  $('#viewWebhookSecretModal').modal('show');
  $('#webhook-secret button').bind('click', function() {
    var input = document.querySelector('#webhook-secret input');
    input.setSelectionRange(0, input.value.length + 1);
    $(input).focus();
    try {
      var success = document.execCommand('copy');
      if (success) {
        $('#webhook-secret-copy-notes').text(window.getTemplateValue("translations.copied"));
        $('#webhook-secret').removeClass('has-error').addClass('has-success');
      } else {
        $('#webhook-secret-copy-notes').text(window.getTemplateValue("translations.could_not_copy"));
        $('#webhook-secret').removeClass('has-success').addClass('has-error');
      }
    } catch (err) {
        $('#webhook-secret-copy-notes').text(window.getTemplateValue("translations.could_not_copy"));
        $('#webhook-secret').removeClass('has-success').addClass('has-error');
    }
  });
}

export async function register() {
  const options = window.getTemplateValue('fido2_options');
  const form = $('#form-add-authentication-methods');
  const type_form_group = $('#addAuthenticationMethodTypeSelect').closest('.form-group');
  type_form_group.removeClass('has-error');
  const help_block = type_form_group.find('.help-block');
  help_block.text('');
  try {
    const publicKeyCredentialCreationOptions = parseCreationOptionsFromJSON(options);
    const credential = await create(publicKeyCredentialCreationOptions);
    form.find("[name='fido2_passkey_credentials']").val(JSON.stringify(credential));
    form[0].submit();
    return true;
  } catch (error) {
    type_form_group.addClass('has-error');
    help_block.text(window.getTemplateValue('translations.passkey_failed') + error);
    return false;
  }
}

$(function() {
  const add_authentication_method_type_select = $('#addAuthenticationMethodTypeSelect');
  add_authentication_method_type_select.on('changed.bs.select', function () {
    if (add_authentication_method_type_select.val() === 'FIDO2_PASSKEY') {
      $('#addAuthenticationMethodDescriptionGroup').show().find('input').prop('disabled', false);
      $('#addAuthenticationMethodLoginGroup, #addAuthenticationMethodPasswordGroup').hide().find('input').prop('disabled', true);
    } else {
      add_authentication_method_type_select.closest('.form-group').removeClass('has-error').find('.help-block').text('');
      $('#addAuthenticationMethodDescriptionGroup').hide().find('input').prop('disabled', true);
      $('#addAuthenticationMethodLoginGroup, #addAuthenticationMethodPasswordGroup').show().find('input').prop('disabled', false);
    }
  });
  if (supported()) {
    $('#form-add-authentication-methods').on('submit', function (event) {
      if (add_authentication_method_type_select.val() === 'FIDO2_PASSKEY') {
        event && event.preventDefault();
        if ($("#input-passkey-description").val() === "") {
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
    if (add_authentication_method_type_select.val() === 'FIDO2_PASSKEY') {
      add_authentication_method_type_select.val('E');
    }
    add_authentication_method_type_select.find('option[value="FIDO2_PASSKEY"]').prop('disabled', true);
    add_authentication_method_type_select.selectpicker('refresh');
  }
  add_authentication_method_type_select.trigger('changed.bs.select');
});