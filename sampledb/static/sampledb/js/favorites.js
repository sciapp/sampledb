'use strict';
/* eslint-env jquery */

$(function () {
  const applicationRootPath = window.getTemplateValue('application_root_path');
  $('button[type="button"].fav-star-on, button[type="button"].fav-star-off').on('click', function () {
    const button = $(this);
    if (button.hasClass('fav-star-loading')) {
      return;
    }
    let url = null;
    if (button.data('actionId')) {
      url = `${applicationRootPath}api/frontend/favorite_actions/${button.data('actionId')}`;
    }
    if (button.data('instrumentId')) {
      url = `${applicationRootPath}api/frontend/favorite_instruments/${button.data('instrumentId')}`;
    }
    if (!url) {
      return;
    }
    const method = button.hasClass('fav-star-on') ? 'DELETE' : 'PUT';
    button.addClass('fav-star-loading');
    button.toggleClass('fav-star-on');
    button.toggleClass('fav-star-off');
    $.ajax({
      url,
      type: method
    }).fail(function (xhr) {
      if (xhr.status !== 404 && xhr.status !== 409) {
        button.toggleClass('fav-star-on');
        button.toggleClass('fav-star-off');
      }
    }).always(function () {
      button.removeClass('fav-star-loading');
    });
  });
});
