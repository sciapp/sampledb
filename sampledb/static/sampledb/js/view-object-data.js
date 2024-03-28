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
  $('[data-sampledb-plotly-chart]').each(function () {
    const plotDivID = $(this).data('sampledb-plotly-chart');
    Plotly.newPlot(plotDivID, JSON.parse($(this).text()));
    const toggleLinkID = $(this).data('sampledb-plotly-chart-toggle');
    if (toggleLinkID) {
      const plotDiv = $('#' + plotDivID);
      const toggleLink = $('#' + toggleLinkID);
      toggleLink.on('click', function () {
        plotDiv.toggle();
        if (plotDiv.is(':hidden')) {
          toggleLink.text(toggleLink.data('showText'));
        } else {
          toggleLink.text(toggleLink.data('hideText'));
        }
      });
    }
  });
});

export {
  toggleShowMore
};
