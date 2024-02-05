'use strict';

window._template_values = JSON.parse(document.getElementById('sampledb-template-values').innerText);
window.getTemplateValue = function (name) {
  return window._template_values[name];
};
