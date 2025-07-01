'use strict';
/* eslint-env jquery */

/**
 * Set up event handlers for timeline arrays.
 * @param container a DOM element
 */
function setUpTimelineArrayHandlers (container) {
  $(container).find('.div-timeline-array').on('plotly_click plotly_hover', function (event, data) {
    const toggleContainer = $(this).next('div');
    const toggleInput = toggleContainer.find('input');
    if (!toggleInput.prop('checked') && data.points.length === 1) {
      const itemIndex = data.points[0].pointIndex;
      const allItemContainers = $(this).siblings('div').slice(1);
      const itemContainer = $(allItemContainers[itemIndex]);
      allItemContainers.hide();
      itemContainer.show();
    }
  });
  $('.div-timeline-array ~ div.checkbox input').on('change', function () {
    const allItemContainers = $(this).closest('div.checkbox').siblings('div').slice(1);
    if ($(this).prop('checked')) {
      allItemContainers.show();
    } else {
      allItemContainers.hide();
    }
  }).trigger('change');
}

$(function () {
  setUpTimelineArrayHandlers(document);
  window.setUpFunctions.push(setUpTimelineArrayHandlers);
});
