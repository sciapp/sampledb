'use strict';
/* eslint-env jquery */

const POLLING_SLEEP_TIME = 10000;
const POLLING_URL = window.getTemplateValue('polling_url');

function poll () {
  $.ajax({
    url: POLLING_URL,
    success: function (data, statusText, xhr) {
      if (xhr.status === 200) { // dataverse upload was successful
        window.location.replace(data.dataverse_url);
      } else if (xhr.status === 202) { // continue polling
        setTimeout(poll, POLLING_SLEEP_TIME);
      }
    },
    error: function (xhr, statusText, err) {
      if (xhr.status === 404 || xhr.status === 406) { // task id does not exist or uploading object has failed
        window.location.replace(xhr.responseJSON.url);
      }
    }
  });
}

poll();
