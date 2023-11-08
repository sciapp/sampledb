$(function() {
  $('[data-toggle="tooltip"]').tooltip();
  if (window.template_values.current_user.is_authenticated) {
    if (window.template_values.current_user.settings.auto_tz) {
      const tz = moment.tz.guess(true);
      if (tz !== window.template_values.current_user.settings.timezone) {
        $.post(window.template_values.current_user.timezone_url, {
          "timezone": tz,
          "csrf_token": window.template_values.current_user.timezone_csrf_token
        });
      }
    }
  }
  // localize datetimes for anonymous users if the timezone has not been set in the config
  if (window.template_values.current_user.has_timezone) {
    $('span[data-utc-datetime]').each(function(_, element) {
        let utc_datetime_str = $(element).data('utcDatetime');
        let utc_datetime = moment.utc(utc_datetime_str);
        let local_datetime = utc_datetime.local();
        let lang_code = window.template_values.current_user.language.lang_code;
        let format = window.template_values.current_user.language.datetime_format_moment_output;
        element.innerText = local_datetime.locale(lang_code).format(format);
    });
  }

  $(window).on('scroll', function () {
    let active_a = null;
    let scroll_offset = 50;
    $('#sidebar > nav a').removeClass('active').each(function(_, a) {
      a = $(a);
      let href = a.attr('href');
      if (href === "#top") {
        return;
      }
      let linked_element = $(href);
      if (linked_element.length === 1) {
        a.closest('li').show();
        if (active_a === null || window.scrollY + scroll_offset >= linked_element.offset().top) {
          active_a = a;
        }
      } else {
        a.closest('li').hide();
      }
    });
    if (active_a !== null) {
      active_a.addClass('active');
      // show back to top link if sidebar is used
      $('#sidebar > nav a[href="#top"]').show();
    }
  }).trigger('scroll');

  $(".navbar-nav > .dropdown").hover(function(){
    var dropdown_menu = $(this).children(".dropdown-menu");
    if(dropdown_menu.is(":visible")){
      dropdown_menu.parent().toggleClass("open");
    }
  });
  $('#input-search-advanced').on('change', function () {
    if (this.checked) {
      $('#input-search').attr('placeholder', window.template_values.translations.advanced_search);
    } else {
      $('#input-search').attr('placeholder', window.template_values.translations.advanced_search);
    }
  }).change();
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

if (window.template_values.notifications.num_urgent_notifications) {
  let urgent_notification_modal = $('#urgentNotificationModal');
  urgent_notification_modal.on('shown.bs.modal', function () {
    urgent_notification_modal.focus();
  });
  $('.urgent-notifications-counter').on('click', function () {
    urgent_notification_modal.modal();
  });
  urgent_notification_modal.find('#button-hide-urgent-notifications').on('click', function () {
    Cookies.set('sampledb-hide-urgent-notifications-until', moment().add(1, 'hour').format(), {
      expires: 1,
      SameSite: 'Lax'
    });
    setTimeout(function () {
      urgent_notification_modal.modal();
    }, 60 * 60 * 1000);
  });
  let hide_notifications = window.template_values.notifications.hide_notifications;
  let hiding_time = Cookies.get('sampledb-hide-urgent-notifications-until');
  if (hiding_time) {
    hiding_time = moment(hiding_time);
    if (hiding_time && moment().isBefore(hiding_time)) {
      hide_notifications = true;
      setTimeout(function () {
        urgent_notification_modal.modal();
      }, hiding_time.diff(moment(), 'ms'));
    }
  }
  if (!hide_notifications) {
    urgent_notification_modal.modal();
  }
}
});
