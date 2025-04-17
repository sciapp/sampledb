'use strict';
/* eslint-env jquery */

$(function () {
  $('#deleteInfoPageModal').on('show.bs.modal', function (event) {
    const button = $(event.relatedTarget);
    const infoPageId = button.data('infoPageId');
    const infoPageTitle = button.data('infoPageTitle');
    const modal = $(this);
    modal.find('#deleteInfoPageTitle').text(infoPageTitle);
    const form = modal.find('form');
    const formAction = form.attr('action');
    form.attr('action', formAction.substring(0, formAction.lastIndexOf('/') + 1) + infoPageId);
  });
});
