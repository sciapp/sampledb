'use strict';
/* eslint-env jquery */
/* globals Plotly */

/**
 * Toggles showing additional object properties.
 * @param prefix the object prefix
 */
function toggleShowMore (prefix) {
  const properties = $('.show-more-' + prefix);
  const btn = $('#show-more-' + prefix + '-btn');
  if (properties.hasClass('hidden')) {
    properties.addClass('show').removeClass('hidden');
    btn.text(window.getTemplateValue('translations.show_less'));
  } else {
    properties.addClass('hidden').removeClass('show');
    btn.text(window.getTemplateValue('translations.show_more'));
  }
}

$(document).ready(function () {
  $(window.plotly_charts).each(function (index, element) {
    Plotly.newPlot(element[0], element[1]);
  });
});

export {
  toggleShowMore
};
