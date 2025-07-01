'use strict';
/* eslint-env jquery */
/* globals Image, Cookies, Plotly, moment, ResizeObserver */

/**
 * Set up elements with a UTC datetime to display local datetimes for anonymous users if the timezone has not been set in the config
 * @param container a DOM element
 */
function setUpUTCDateTimeElements (container) {
  if (!window.getTemplateValue('current_user.has_timezone')) {
    $(container).find('span[data-utc-datetime]').each(function (_, element) {
      const utcDatetimeStr = $(element).data('utcDatetime');
      const utcDatetime = moment.utc(utcDatetimeStr);
      const localDatetime = utcDatetime.local();
      const langCode = window.getTemplateValue('current_user.language.lang_code');
      const format = $(element).data('sampledb-time-only') ? 'LTS' : window.getTemplateValue($(element).data('sampledb-date-only') ? 'current_user.language.date_format_moment_output' : 'current_user.language.datetime_format_moment_output');
      element.innerText = localDatetime.locale(langCode).format(format);
    });
  }
}

// functions that will need to be run on new containers inserted into the DOM.
window.setUpFunctions = [setUpUTCDateTimeElements];

$(function () {
  $('[data-toggle="tooltip"]').tooltip();
  if (typeof window.Plotly !== 'undefined') {
    const langCode = window.getTemplateValue('current_user.language.lang_code');
    if (langCode === 'de') {
      Plotly.setPlotConfig({ locale: langCode });
    }
  }

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

  setUpUTCDateTimeElements(document);

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
    const fullscreenImagePreview = $(this).next('.fullscreen-image-preview');
    fullscreenImagePreview.css('display', 'flex');
    fullscreenImagePreview.find('img[data-full-src]').each(function () {
      const imageElement = $(this);
      const image = new Image();
      if (!imageElement.attr('src')) {
        imageElement.hide();
      }
      const loadingElement = imageElement.siblings('.fullscreen-image-preview-loading');
      loadingElement.show();
      image.src = imageElement.data('full-src');
      imageElement.removeData('full-src');
      imageElement.removeAttr('full-src');
      function onload () {
        if (!image.complete) {
          setTimeout(onload, 10);
          return;
        }
        imageElement[0].src = image.src;
        imageElement.removeAttr('width');
        imageElement.removeAttr('height');
        imageElement.css('width', 'auto');
        imageElement.css('height', 'auto');
        loadingElement.hide();
        imageElement.show();
      }
      onload();
      // ensure aspect ratio is preserved for the placeholder image
      const originalWidth = imageElement.attr('width');
      const originalHeight = imageElement.attr('height');
      if (originalWidth && originalHeight) {
        imageElement.removeAttr('width');
        imageElement.removeAttr('height');
        imageElement.css('aspect-ratio', originalWidth / originalHeight);
        const onResize = function (width, height) {
          if (image.complete) {
            return;
          }
          if (width / height > originalWidth / originalHeight) {
            imageElement.css('width', 'auto');
            imageElement.css('height', '100%');
          } else {
            imageElement.css('width', '100%');
            imageElement.css('height', 'auto');
          }
        };
        onResize(fullscreenImagePreview.width() - 80, fullscreenImagePreview.height() - 80);
        const ro = new ResizeObserver(function (entries) {
          for (const entry of entries) {
            if (entry.target === fullscreenImagePreview[0]) {
              onResize(entry.contentRect.width, entry.contentRect.height);
            }
          }
        });
        ro.observe(fullscreenImagePreview[0]);
      }
    });
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

  $('.collapse-expand-button').each(function () {
    $(this).on('click', function () {
      const collapseExpandButton = $(this);
      const idPrefix = collapseExpandButton.data('idPrefix');
      const collapsibleDiv = $(`.collapsible-object-container[data-id-prefix=${idPrefix}]`);
      const isCollapsed = !collapsibleDiv.is(':visible');
      collapsibleDiv.toggle(isCollapsed);
      collapseExpandButton.toggleClass('fa-minus-square-o', isCollapsed);
      collapseExpandButton.toggleClass('fa-plus-square-o', !isCollapsed);
      const collapseTooltipText = collapseExpandButton.data(isCollapsed ? 'collapseText' : 'expandText');
      collapseExpandButton.attr('data-original-title', collapseTooltipText);
      collapseExpandButton.tooltip('setContent').tooltip('show');
    });
  });

  $('.collapse-all-button').each(function () {
    $(this).on('click', function () {
      const collapseExpandButton = $(this);
      const groupId = collapseExpandButton.data('collapse-group-id');
      const collapsibleDivs = $(`.collapsible-object-container[data-collapse-group-id=${groupId}]`);
      collapsibleDivs.each(function () {
        $(this).toggle(false);
      });
      const collapseExpandButtons = $(`.collapse-expand-button[data-collapse-group-id=${groupId}]`);
      collapseExpandButtons.each(function () {
        const collapseTooltipText = $(this).data('expandText');
        $(this).toggleClass('fa-minus-square-o', false);
        $(this).toggleClass('fa-plus-square-o', true);
        $(this).attr('data-original-title', collapseTooltipText);
      });
    });
  });

  $('.expand-all-button').each(function () {
    $(this).on('click', function () {
      const collapseExpandButton = $(this);
      const groupId = collapseExpandButton.data('collapse-group-id');
      const collapsibleDivs = $(`.collapsible-object-container[data-collapse-group-id=${groupId}]`);
      collapsibleDivs.each(function () {
        $(this).toggle(true);
      });
      const collapseExpandButtons = $(`.collapse-expand-button[data-collapse-group-id=${groupId}]`);
      collapseExpandButtons.each(function () {
        const collapseTooltipText = $(this).data('collapseText');
        $(this).attr('data-original-title', collapseTooltipText);
        $(this).toggleClass('fa-minus-square-o', true);
        $(this).toggleClass('fa-plus-square-o', false);
      });
    });
  });

  const infoPageModal = $('#infoPageModal');
  const infoPages = infoPageModal.find('.modal-content');
  infoPages.hide();
  infoPages.first().show();
  const infoPageModalButtons = infoPages.find('[data-info-page-button]');
  infoPageModalButtons.filter('[data-info-page-button="back"]').on('click', function () {
    const infoPage = $(this).closest('.modal-content');
    infoPage.hide();
    infoPage.prev('.modal-content').show();
  });
  infoPageModalButtons.filter('[data-info-page-button="next"]').on('click', function () {
    const infoPage = $(this).closest('.modal-content');
    infoPage.hide();
    infoPage.next('.modal-content').show();
  });
  infoPageModalButtons.filter('[data-info-page-button="acknowledge"]').on('click', function () {
    infoPageModal.modal('hide');
    const infoPageForm = $(this).closest('form');
    $.post(
      infoPageForm.attr('action'),
      infoPageForm.serialize()
    );
  });
  infoPageModal.modal({ keyboard: false, backdrop: 'static' });
});
