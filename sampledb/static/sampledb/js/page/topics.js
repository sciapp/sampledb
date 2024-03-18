'use strict';
/* eslint-env jquery */
/* globals Sortable */

$(function () {
  if ($('#sortingModal').length > 0) {
    const elem = document.getElementById('topicTypesModalList');
    const options = {
      handle: '.handle',
      animation: 150,
      dataIdAttr: 'data-id'
    };
    const sortable = new Sortable(elem, options);
    $('#form-sort-order').on('submit', function () {
      document.getElementById('encoded_order').value = sortable.toArray().join();
    });
  }
});
