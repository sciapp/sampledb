'use strict';
/* eslint-env jquery */

$(function () {
  const input = $('#input-filter-by-name');
  const filterables = $('.filter-by-name[data-filter-text]');
  const resultsElement = $('#filter-by-name-result-text');
  const resultsTemplate = resultsElement.text();
  function filterByName (filterText) {
    if (filterText === '') {
      resultsElement.hide();
      filterables.show();
      return;
    }
    const visibleFilterables = filterables.filter(function () {
      const doesMatch = $(this).data('filterText').toLowerCase().includes(filterText.toLowerCase());
      $(this).toggle(doesMatch);
      return doesMatch;
    });
    resultsElement.show();
    resultsElement.text(resultsTemplate.replace('NUM_RESULTS_PLACEHOLDER', visibleFilterables.length).replace('FILTER_PLACEHOLDER', filterText));
  }
  input.on('input change', function () {
    filterByName(input.val());
  });
  input.closest('form').on('reset', function () {
    filterByName('');
  });
  filterByName(input.val());
});
