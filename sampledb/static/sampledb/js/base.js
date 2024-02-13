'use strict';
/* eslint-env jquery */
/* globals Cookies, moment */

$(function () {
  $('[data-toggle="tooltip"]').tooltip();

  // update timezone for users who use the auto_tz setting
  if (window.getTemplateValue('current_user.is_authenticated')) {
    if (window.getTemplateValue('current_user.settings.auto_tz')) {
      const tz = moment.tz.guess(true);
      if (tz !== window.getTemplateValue('current_user.settings.timezone')) {
        $.post(window.getTemplateValue('current_user.timezone_url'), {
          timezone: tz,
          csrf_token: window.getTemplateValue('current_user.timezone_csrf_token')
        });
      }
    }
  }

  // localize datetimes for anonymous users if the timezone has not been set in the config
  if (!window.getTemplateValue('current_user.has_timezone')) {
    $('span[data-utc-datetime]').each(function (_, element) {
      const utcDatetimeStr = $(element).data('utcDatetime');
      const utcDatetime = moment.utc(utcDatetimeStr);
      const localDatetime = utcDatetime.local();
      const langCode = window.getTemplateValue('current_user.language.lang_code');
      const format = window.getTemplateValue('current_user.language.datetime_format_moment_output');
      element.innerText = localDatetime.locale(langCode).format(format);
    });
  }

  if (window.getTemplateValue('current_user.is_authenticated') && $('#session-timeout-marker').length > 0) {
    // there will be a small offset between client and server which can be ignored, however this can help catch larger offsets due to a wrongly set computer clock
    const millisecondOffset = moment.utc().diff(moment.utc(window.getTemplateValue('current_utc_datetime')));
    Cookies.set('SAMPLEDB_LAST_ACTIVITY_MILLISECOND_OFFSET', '' + millisecondOffset, { sameSite: 'Lax' });
    let lastActivityTime = null;
    let lastActivityTimeString = '';

    const resetLastActivityTime = function () {
      lastActivityTime = moment.utc();
      lastActivityTimeString = lastActivityTime.format('YYYY-MM-DDTHH:mm:ss');
      Cookies.set('SAMPLEDB_LAST_ACTIVITY_DATETIME', lastActivityTimeString, { sameSite: 'Lax' });
    };

    $(window).on('blur focus resize mousemove mousedown mouseup scroll keydown keyup', resetLastActivityTime);
    resetLastActivityTime();

    const reloadIfNecessary = function () {
      $.get(window.getTemplateValue('shared_device_state_url'), function (data) {
        // if data is true, the shared device session has not timed out yet, otherwise a reload is necessary
        if (data !== true) {
          window.location.reload();
        }
      });
    };

    const updateSessionTimeout = function () {
      const idleSignOutMinutes = window.getTemplateValue('idle_sign_out_minutes');
      if (lastActivityTimeString !== Cookies.get('SAMPLEDB_LAST_ACTIVITY_DATETIME')) {
        if (Cookies.get('SAMPLEDB_LAST_ACTIVITY_DATETIME') === 'reload') {
          reloadIfNecessary();
        } else {
          lastActivityTimeString = Cookies.get('SAMPLEDB_LAST_ACTIVITY_DATETIME');
        }
        if (lastActivityTimeString === '') {
          resetLastActivityTime();
        } else {
          lastActivityTime = moment.utc(lastActivityTimeString);
        }
      }
      if (lastActivityTime === null) {
        resetLastActivityTime();
      } else {
        // allow 5 seconds of delay before inactivity is detected
        const idleDuration = moment.utc().diff(lastActivityTime) / 1000.0 - 5;
        if (idleDuration <= 0) {
          $('#session-timeout-marker').text(window.getTemplateValue('translations.automatic_sign_out_after_x_minutes_of_inactivity').replaceAll('PLACEHOLDER', idleSignOutMinutes.toString() + ':00'));
        } else if (idleDuration > idleSignOutMinutes * 60) {
          reloadIfNecessary();
        } else {
          const idleSignOutDuration = idleSignOutMinutes * 60 - idleDuration;
          const idleSignOutDurationSeconds = Math.floor(idleSignOutDuration % 60);
          const idleSignOutDurationMinutes = Math.floor(idleSignOutDuration / 60);
          const idleSignOutDurationString = idleSignOutDurationMinutes.toString() + ':' + (100 + idleSignOutDurationSeconds).toString().substring(1);
          $('#session-timeout-marker').text(window.getTemplateValue('translations.automatic_sign_out_after_x_minutes_of_inactivity').replaceAll('PLACEHOLDER', idleSignOutDurationString));
        }
      }
    };
    updateSessionTimeout();
    setInterval(updateSessionTimeout, 500);
  } else {
    // this triggers a reload check in all tabs with a shared device session still opened
    Cookies.set('SAMPLEDB_LAST_ACTIVITY_DATETIME', 'reload', { sameSite: 'Lax' });
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
      $('#input-search').attr('placeholder', window.getTemplateValue('translations.advanced_search'));
    } else {
      $('#input-search').attr('placeholder', window.getTemplateValue('translations.search'));
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
  if (window.getTemplateValue('notifications.num_urgent_notifications')) {
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
    let hideNotifications = window.getTemplateValue('notifications.hide_notifications');
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
