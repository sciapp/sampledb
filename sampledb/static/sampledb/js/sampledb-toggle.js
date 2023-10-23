'use strict';
/* eslint-env jquery */

/**
 * Toggles showing plots in plotly chart lists.
 * @param plotID the ID of the plot to toggle
 */
function togglePlotlyChartDiv (plotID) {
  const plotDiv = $('#plotly_plot_div_' + plotID);
  const toggleLink = $('#plotly_info_link_' + plotID);
  plotDiv.toggle();
  if (plotDiv.is(':hidden')) {
    toggleLink.text(toggleLink.data('showText'));
  } else {
    toggleLink.text(toggleLink.data('hideText'));
  }
}

export {
  togglePlotlyChartDiv
};
