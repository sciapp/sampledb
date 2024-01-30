
import {
  get,
  supported,
  parseRequestOptionsFromJSON,
} from '../../../webauthn-json/js/webauthn-json.browser-ponyfill.js';

async function authenticate(e) {
  e && e.preventDefault();
  const options = window.getTemplateValue('fido2_options');
  const publicKeyCredentialRequestOptions = parseRequestOptionsFromJSON(options);
  const form = $('#fido2-authenticate-form');
  form.removeClass('has-error');
  const help_bock = form.find('.help-block');
  help_bock.text('');
  try {
    const assertion = await get(publicKeyCredentialRequestOptions);
    form.find('[name="assertion"]').val(JSON.stringify(assertion));
    form[0].submit();
    return true;
  } catch (error) {
    form.addClass('has-error');
    help_bock.text(window.getTemplateValue('translations.passkey_failed') + error)
    return false;
  }
}
$(function() {
  if (supported()) {
    $("#fido2-authenticate-form").on('submit', authenticate);
  } else {
    $('#alert-fido2-not-supported').show();
    $('#fido2-authenticate-form input').prop('disabled', true);
  }
});
