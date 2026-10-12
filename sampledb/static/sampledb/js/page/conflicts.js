'use strict';
/* eslint-env jquery */

$(function () {
  selectView();
  $('select[name="select-view"]').on('change', function () {
    selectView();
  });

  function selectView () {
    const selection = $('select[name="select-view"]').val();
    $('.version-view').each(function () {
      const selected = $(this).attr('id') === selection;
      $(this).css('display', selected ? 'block' : 'none');
    });
  }
});
