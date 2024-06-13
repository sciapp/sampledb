'use strict';
/* eslint-env jquery */

$(function () {
  $('.input-group.date').each(function () {
    $(this).datetimepicker({
      locale: window.getTemplateValue('current_user.language.lang_code'),
      format: window.getTemplateValue('current_user.language.datetime_format_moment'),
      date: $(this).attr('data-datetime'),
      timeZone: window.getTemplateValue('current_user.timezone'),
      showTodayButton: true
    });
  });
});
