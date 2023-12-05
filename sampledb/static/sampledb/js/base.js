'use strict';
/* eslint-env jquery */
/* globals Cookies, moment */

$(function () {
  $('[data-toggle="tooltip"]').tooltip();

  // update timezone for users who use the auto_tz setting
  if (window.getTemplateValue('current_user').is_authenticated) {
    if (window.getTemplateValue('current_user').settings.auto_tz) {
      const tz = moment.tz.guess(true);
      if (tz !== window.getTemplateValue('current_user').settings.timezone) {
        $.post(window.getTemplateValue('current_user').timezone_url, {
          timezone: tz,
          csrf_token: window.getTemplateValue('current_user').timezone_csrf_token
        });
      }
    }
  }

  // localize datetimes for anonymous users if the timezone has not been set in the config
  if (window.getTemplateValue('current_user').has_timezone) {
    $('span[data-utc-datetime]').each(function (_, element) {
      const utcDatetimeStr = $(element).data('utcDatetime');
      const utcDatetime = moment.utc(utcDatetimeStr);
      const localDatetime = utcDatetime.local();
      const langCode = window.getTemplateValue('current_user').language.lang_code;
      const format = window.getTemplateValue('current_user').language.datetime_format_moment_output;
      element.innerText = localDatetime.locale(langCode).format(format);
    });
  }

  // handle scrolling for the sidebar navigation
  $(window).on('scroll', function () {
    let activeA = null;
    const scrollOffset = 50;
    $('#sidebar > nav a').removeClass('active').each(function (_, a) {
      a = $(a);
      const href = a.attr('href');
      if (href === '#top') {
        return;
      }
      const linkedElement = $(href);
      if (linkedElement.length === 1) {
        a.closest('li').show();
        if (activeA === null || window.scrollY + scrollOffset >= linkedElement.offset().top) {
          activeA = a;
        }
      } else {
        a.closest('li').hide();
      }
    });
    if (activeA !== null) {
      activeA.addClass('active');
      // show back to top link if sidebar is used
      $('#sidebar > nav a[href="#top"]').show();
    }
  }).trigger('scroll');

  // show navbar dropdowns on hover
  $('.navbar-nav > .dropdown').hover(function () {
    const dropdownMenu = $(this).children('.dropdown-menu');
    if (dropdownMenu.is(':visible')) {
      dropdownMenu.parent().toggleClass('open');
    }
  });

  // update text for search field when advanced search is toggled
  $('#input-search-advanced').on('change', function () {
    if (this.checked) {
      $('#input-search').attr('placeholder', window.getTemplateValue('translations').advanced_search);
    } else {
      $('#input-search').attr('placeholder', window.getTemplateValue('translations').advanced_search);
    }
  }).change();

  // fullscreen image preview event handlers
  $('.fullscreen-image-preview').on('click', function (e) {
    $(this).hide();
  });
  $('.fullscreen-image-preview img').on('click', function (e) {
    e.stopPropagation();
  });
  $('.download-fullscreen-image-preview').on('click', function (e) {
    e.stopPropagation();
  });
  $('.show-fullscreen-image-preview').on('click', function (e) {
    $(this).next('.fullscreen-image-preview').css('display', 'flex');
  });

  // show urgent notifications
  if (window.getTemplateValue('notifications').num_urgent_notifications) {
    const urgentNotificationModal = $('#urgentNotificationModal');
    urgentNotificationModal.on('shown.bs.modal', function () {
      urgentNotificationModal.focus();
    });
    $('.urgent-notifications-counter').on('click', function () {
      urgentNotificationModal.modal();
    });
    urgentNotificationModal.find('#button-hide-urgent-notifications').on('click', function () {
      Cookies.set('sampledb-hide-urgent-notifications-until', moment().add(1, 'hour').format(), {
        expires: 1,
        SameSite: 'Lax'
      });
      setTimeout(function () {
        urgentNotificationModal.modal();
      }, 60 * 60 * 1000);
    });
    let hideNotifications = window.getTemplateValue('notifications').hide_notifications;
    let hidingTime = Cookies.get('sampledb-hide-urgent-notifications-until');
    if (hidingTime) {
      hidingTime = moment(hidingTime);
      if (hidingTime && moment().isBefore(hidingTime)) {
        hideNotifications = true;
        setTimeout(function () {
          urgentNotificationModal.modal();
        }, hidingTime.diff(moment(), 'ms'));
      }
    }
    if (!hideNotifications) {
      urgentNotificationModal.modal();
    }
  }
});
