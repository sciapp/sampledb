'use strict';
/* eslint-env jquery */

import {
  setupImageDragAndDrop
} from '../markdown_image_upload.js';

$(function () {
  window.categoriesShown = window.getTemplateValue('categories_shown');
  window.filterDate = null;
  window.filterUser = null;
  window.log_entries = {};
});
function setup_instrument_log_filter_states() {
  for (const categoryID in window.categoriesShown) {
    $(`#instrument_log_filter_${categoryID}`).prop('checked', window.categoriesShown[categoryID]);
  }
  $('#instrument_log_filter_none').prop('checked', window.categoriesShown['none']);
  $('#instrument_log_counter').html($('.instrument-log-entry:not(:hidden)').length.toString()+ " / " + $('.instrument-log-entry').length.toString());
    $('.input-group.date').each(function() {
      const datetimepicker = $(this).datetimepicker({
        date: window.filterDate,
        locale: window.getTemplateValue('language.lang_code'),
        format: 'YYYY-MM',
        showClear: true,
        showClose: true,
        maxDate: moment(new Date()),
        timeZone: window.getTemplateValue('current_user.timezone')
      });
      datetimepicker.on('dp.change', function() {
        update_instrument_log_filter_states();
      });
      $('#input-instrument-log-filter-date').on('click', function() {
        datetimepicker.data("DateTimePicker").toggle();
      });
    });
    var selectpicker = $('#input-instrument-log-filter-user');
    selectpicker.selectpicker('val', window.filterUser);
    selectpicker.on('changed.bs.select', function() {
        update_instrument_log_filter_states();
    });
}
function update_instrument_log_filter_states() {
  const filter_date = $('#input-instrument-log-filter-date').val();
  if (filter_date === "") {
    window.filterDate = null;
  } else {
    window.filterDate = filter_date;
  }
  const filter_user = $('#input-instrument-log-filter-user').val();
  if (filter_user === "") {
    window.filterUser = null;
  } else {
    window.filterUser = filter_user;
  }
  $('.instrument-log-entry').hide();
  for (const categoryID in window.categoriesShown) {
    window.categoriesShown[categoryID] = $(`#instrument_log_filter_${categoryID}`).prop('checked');
    if (window.categoriesShown[categoryID]) {
      let filter_selector = `div[data-instrument-log-category-${categoryID}="yes"]`;
      if (filter_date !== "") {
        filter_selector = filter_selector + '[data-instrument-log-date='+filter_date+']';
      }
      if (filter_user !== "") {
        filter_selector = filter_selector + '[data-instrument-log-user-id='+filter_user+']';
      }
      $(filter_selector).show();
    }
  }
  $('#instrument_log_counter').html($('.instrument-log-entry:not(:hidden)').length.toString()+ " / " + $('.instrument-log-entry').length.toString());
}
function reset_instrument_log_filter_states() {
  for (const categoryID in window.categoriesShown) {
    window.categoriesShown[categoryID] = true;
  }
  window.filterUser = null;
  window.filterDate = null;
  const numEntries = $('#instrument-log-container > div > .instrument-log-entry').length;
  $('#instrument_log_counter').html(numEntries.toString() + " / " + numEntries.toString());
}
$(function () {
  setup_instrument_log_filter_states();
  $('[data-toggle="popover"]').popover();

  function updateNewLogEntryMarkdown() {
    if ($('#input-content-is-markdown').prop('checked')) {
      window.new_log_entry = new InscrybMDE({
        element: $("#textarea-log-entry-text")[0],
        indentWithTabs: false,
        spellChecker: false,
        status: false,
        hideIcons: ["guide", "fullscreen", "side-by-side", "quote"],
        showIcons: ["code", "table"],
        minHeight: '100px',
        autoDownloadFontAwesome: false,
      });
      setupImageDragAndDrop(window.new_log_entry);
    } else {
      if (window.new_log_entry) {
        window.new_log_entry.toTextArea();
        window.new_log_entry = null;
      }
    }
  }
  $('#input-content-is-markdown').change(updateNewLogEntryMarkdown);
  updateNewLogEntryMarkdown();

  for (const logEntryID of window.getTemplateValue("instrument_log_entries.editable_ids")) {
    const changeHandler = function () {
      const files =  $(`#input-file-upload-${logEntryID}`).get(0).files;
      if (files.length === 0) {
        $(`#input-file-text-${logEntryID}`).val("");
      } else if (files.length === 1) {
        $(`#input-file-text-${logEntryID}`).val(files[0].name);
      } else {
        $(`#input-file-text-${logEntryID}`).val(files.length + " files selected");
      }
    }
    $(`#input-file-upload-${logEntryID}`).on('change', changeHandler);
    const dropHandler = function (e) {
      e.preventDefault();
      $(`#input-file-upload-${logEntryID}`)[0].files = e.dataTransfer.files;
      changeHandler();
    }
    const dragOverHandler = function (e) {
      e.preventDefault();
    }
    const upload_area = $(`#upload-area-${logEntryID}`)[0];
    upload_area.ondrop = dropHandler;
    upload_area.ondragover = dragOverHandler;

    const updateLogEntryMarkdown = function () {
      if ($(`#input-edit-content-is-markdown-${logEntryID}`).prop('checked')) {
        if (window.log_entries[logEntryID]) {
          window.log_entries[logEntryID].toTextArea();
        }
        window.log_entries[logEntryID] = new InscrybMDE({
          element: $(`#textarea-log-entry-text-${logEntryID}`)[0],
          indentWithTabs: false,
          spellChecker: false,
          status: false,
          hideIcons: ["guide", "fullscreen", "side-by-side", "quote"],
          showIcons: ["code", "table"],
          minHeight: '100px',
          autoDownloadFontAwesome: false,
        });
        setupImageDragAndDrop(window.log_entries[logEntryID]);
      } else {
        if (window.log_entries[logEntryID]) {
          window.log_entries[logEntryID].toTextArea();
          delete window.log_entries[logEntryID];
        }
      }
    }
    $(`#input-edit-content-is-markdown-${logEntryID}`).change(updateLogEntryMarkdown);
    $(`#logEntryContentModal_${logEntryID}`).on('shown.bs.modal', updateLogEntryMarkdown);
    updateLogEntryMarkdown();
  }
  function changeHandler() {
    var files =  $('#input-file-upload').get(0).files;
    if (files.length === 0) {
      $('#input-file-text').val("");
    } else if (files.length === 1) {
      $('#input-file-text').val(files[0].name);
    } else {
      $('#input-file-text').val(files.length + " files selected");
    }
  }
  if (window.getTemplateValue('can_create_instrument_log_entries')) {
    $('#input-file-upload').on('change', changeHandler);
    function dropHandler(e) {
      e.preventDefault();
      $('#input-file-upload')[0].files = e.dataTransfer.files;
      changeHandler();
    }
    function dragOverHandler(e) {
      e.preventDefault();
    }
    const upload_area = $('#upload-area')[0];
    upload_area.ondrop = dropHandler;
    upload_area.ondragover = dragOverHandler;
  }

  function applySortOrder(log_order_button, attribute) {
    var log_order_button_indicator = log_order_button.find('i');
    if (log_order_button_indicator.css('visibility') === 'hidden') {
      $('.button-switch-instrument-log-order i').css('visibility', 'hidden');
      log_order_button_indicator.css('visibility', 'visible');
    } else {
      log_order_button_indicator.toggleClass('fa-sort-asc').toggleClass('fa-sort-desc');
    }

    var ascending = (log_order_button.find('i.fa-sort-asc').length !== 0);

    var container = $('#instrument-log-container');
    container.children().sort(function(a, b) {
      a_datetime = $(a).find('.instrument-log-entry').data('instrumentLog' + attribute);
      b_datetime = $(b).find('.instrument-log-entry').data('instrumentLog' + attribute);
      if (ascending) {
        return a_datetime > b_datetime;
      } else {
        return a_datetime < b_datetime;
      }
    }).appendTo(container);

    var form = $('#form-instrument-log-order');
    form.find('input[type="checkbox"]').prop('checked', ascending);
    form.find('input[type="text"]').val(attribute.toLowerCase());
    $.ajax({
      type: "POST",
      url: window.getTemplateValue('set_instrument_log_order_url'),
      data: form.serialize()
    });
  }
  var log_order_button_date = $('#button-switch-instrument-log-order-date');
  log_order_button_date.on('click', function () {
    applySortOrder(log_order_button_date, "Datetime");
  });
  var log_order_button_user_name = $('#button-switch-instrument-log-order-user-name');
  log_order_button_user_name.on('click', function () {
    applySortOrder(log_order_button_user_name, "UserName");
  });

  let show_list_button = $('.button-show-instrument-log-list');
  let show_tree_button_date_author = $('.button-show-instrument-log-tree-date-author');
  let show_tree_button_author_date = $('.button-show-instrument-log-tree-author-date');
  show_list_button.on('click', function() {
    reset_instrument_log_filter_states();
    show_list_button.prop('disabled', true);
    show_tree_button_date_author.prop('disabled', false);
    show_tree_button_author_date.prop('disabled', false);
    $('.button-switch-instrument-log-order, #button-instrument-log-list-filter').prop('disabled', false);
    $('#instrument-log-tree').html('');
    $('.instrument-log-entry').show();
  });
  function sort_tree_container_children(container) {
    container.children('.instrument-log-tree-container').sort(function(a, b) {
      let a_value = $(a).data('instrumentLogTreeSortValue');
      let b_value = $(b).data('instrumentLogTreeSortValue');
      let a_number = Number.parseInt(a_value);
      let b_number = Number.parseInt(b_value);
      if (Number.isNaN(a_number) || Number.isNaN(b_number)) {
        return a_value > b_value;
      } else {
        return a_number > b_number;
      }
    }).appendTo(container);
  }
  show_tree_button_date_author.on('click', function() {
    reset_instrument_log_filter_states();
    show_list_button.prop('disabled', false);
    show_tree_button_date_author.prop('disabled', true);
    show_tree_button_author_date.prop('disabled', false);
    $('.button-switch-instrument-log-order, #button-instrument-log-list-filter').prop('disabled', true);
    let log_entries = $('#instrument-log-container > div > .instrument-log-entry');
    $('#button-instrument-log-list-filter').popover('hide');
    log_entries.hide();
    let tree_container = $('#instrument-log-tree');
    if (log_entries.length) {
      tree_container.html(`<div class="instrument-log-tree-container"><div class="instrument-log-tree-block" id="instrument-log-tree-root-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_years') }</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_years') }</button></div></div></div>`);
    } else {
      tree_container.html("");
    }
    let containers_by_date = {};
    let i = 0;
    const MONTH_NAMES = window.getTemplateValue('translations.month_names');
    log_entries.each(function(_, element) {
      let log_entry = $(element);
      let author = log_entry.data('instrumentLogUserName');
      let utc_datetime_string = log_entry.data('instrumentLogDatetime');
      let utc_datetime = moment.utc(utc_datetime_string);
      let local_datetime = utc_datetime.local();
      let year = local_datetime.year();
      let month = local_datetime.month();
      let day = local_datetime.date();
      if (!(year in containers_by_date)) {
        let parent_container = tree_container.find('#instrument-log-tree-root-block');
        let container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${year}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${year}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_months') }</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_months') }</button></div></div></div>`);
        container.appendTo(parent_container);
        sort_tree_container_children(parent_container);
        containers_by_date[year] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(month in containers_by_date[year][1])) {
        let parent_container = containers_by_date[year][0];
        let container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${month}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${MONTH_NAMES[month]}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_days') }</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_days') }</button></div></div></div>`);
        container.appendTo(parent_container);
        sort_tree_container_children(parent_container);
        containers_by_date[year][1][month] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(day in containers_by_date[year][1][month][1])) {
        let parent_container = containers_by_date[year][1][month][0];
        let container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${day}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${day}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_authors') }</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_authors') }</button></div></div></div>`);
        container.appendTo(parent_container);
        sort_tree_container_children(parent_container);
        containers_by_date[year][1][month][1][day] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(author in containers_by_date[year][1][month][1][day][1])) {
        let parent_container = containers_by_date[year][1][month][1][day][0];
        let container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${author}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${author}</label></h3><div class="instrument-log-tree-block"></div></div>`);
        container.appendTo(parent_container);
        sort_tree_container_children(parent_container);
        containers_by_date[year][1][month][1][day][1][author] = [container.find('.instrument-log-tree-block'), {}];
      }
      let log_entry_clone = $(log_entry).clone();
      log_entry_clone.show();
      log_entry_clone.appendTo(containers_by_date[year][1][month][1][day][1][author][0]);
    });
    tree_container.find('.button-instrument-log-tree-expand-all').on('click', function() {
      $(this).closest('.instrument-log-tree-block').find('> .instrument-log-tree-container > input[type="checkbox"]').each(function(_, checkbox) {
        checkbox.checked = true;
      });
    });
    tree_container.find('.button-instrument-log-tree-collapse-all').on('click', function() {
      $(this).closest('.instrument-log-tree-block').find('> .instrument-log-tree-container > input[type="checkbox"]').each(function(_, checkbox) {
        checkbox.checked = false;
      });
    });
  });
  show_tree_button_author_date.on('click', function() {
    reset_instrument_log_filter_states();
    show_list_button.prop('disabled', false);
    show_tree_button_date_author.prop('disabled', false);
    show_tree_button_author_date.prop('disabled', true);
    $('.button-switch-instrument-log-order, #button-instrument-log-list-filter').prop('disabled', true);
    let log_entries = $('#instrument-log-container > div > .instrument-log-entry');
    $('#button-instrument-log-list-filter').popover('hide');
    log_entries.hide();
    let tree_container = $('#instrument-log-tree');
    if (log_entries.length) {
      tree_container.html(`<div class="instrument-log-tree-container"><div class="instrument-log-tree-block" id="instrument-log-tree-root-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_authors')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_authors')}</button></div></div></div>`);
    } else {
      tree_container.html();
    }
    let containers_by_author = {};
    let i = 0;
    const MONTH_NAMES = window.getTemplateValue('translations.month_names');
    log_entries.each(function(_, element) {
      let log_entry = $(element);
      let author = log_entry.data('instrumentLogUserName');
      let utc_datetime_string = log_entry.data('instrumentLogDatetime');
      let utc_datetime = moment.utc(utc_datetime_string);
      let local_datetime = utc_datetime.local();
      let year = local_datetime.year();
      let month = local_datetime.month();
      let day = local_datetime.date();
      if (!(author in containers_by_author)) {
        let parent_container = tree_container.find('#instrument-log-tree-root-block');
        let container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${author}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${author}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_years')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_years')}</button></div></div></div>`);
        container.appendTo(parent_container);
        sort_tree_container_children(parent_container);
        containers_by_author[author] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(year in containers_by_author[author][1])) {
        let parent_container = containers_by_author[author][0];
        let container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${year}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${year}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_months')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_months')}</button></div></div></div>`);
        container.appendTo(parent_container);
        sort_tree_container_children(parent_container);
        containers_by_author[author][1][year] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(month in containers_by_author[author][1][year][1])) {
        let parent_container = containers_by_author[author][1][year][0];
        let container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${month}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${MONTH_NAMES[month]}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_days')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_days')}</button></div></div></div>`);
        container.appendTo(parent_container);
        sort_tree_container_children(parent_container);
        containers_by_author[author][1][year][1][month] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(day in containers_by_author[author][1][year][1][month][1])) {
        let parent_container = containers_by_author[author][1][year][1][month][0];
        let container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${day}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${day}</label></h3><div class="instrument-log-tree-block"></div></div>`);
        container.appendTo(parent_container);
        sort_tree_container_children(parent_container);
        containers_by_author[author][1][year][1][month][1][day] = [container.find('.instrument-log-tree-block'), {}];
      }
      let log_entry_clone = $(log_entry).clone();
      log_entry_clone.show();
      log_entry_clone.appendTo(containers_by_author[author][1][year][1][month][1][day][0]);
    });
    tree_container.find('.button-instrument-log-tree-expand-all').on('click', function() {
      $(this).closest('.instrument-log-tree-block').find('> .instrument-log-tree-container > input[type="checkbox"]').each(function(_, checkbox) {
        checkbox.checked = true;
      });
    });
    tree_container.find('.button-instrument-log-tree-collapse-all').on('click', function() {
      $(this).closest('.instrument-log-tree-block').find('> .instrument-log-tree-container > input[type="checkbox"]').each(function(_, checkbox) {
        checkbox.checked = false;
      });
    });
  });

  $('.log_entry_date_picker').each(function() {
    var datetimepicker = $(this);
    var textbox = datetimepicker.find('input[type="text"]');
    var checkbox = datetimepicker.parent().find('input[type="checkbox"]');
    if (textbox.val()) {
      checkbox.prop('checked', true);
      textbox.prop('disabled', false);
    }
    datetimepicker.datetimepicker({
      format: window.getTemplateValue('event_utc_datetime.format_moment'),
      showClear: true,
      showClose: true,
      showTodayButton: true,
      timeZone: window.getTemplateValue('current_user.timezone')
    });
    checkbox.on('change', function() {
      var checked = checkbox.prop('checked');
      textbox.prop('disabled', !checked);
      if (checked) {
        datetimepicker.data("DateTimePicker").show();
      } else {
        datetimepicker.data("DateTimePicker").hide();
        textbox.val('');
      }
    });
    datetimepicker.on('dp.change', function() {
      if (textbox.val() === "") {
        checkbox.prop('checked', false);
        textbox.prop('disabled', true);
        datetimepicker.data("DateTimePicker").hide();
      }
    });
    textbox.on('change', function() {
      if (textbox.val() === "") {
        checkbox.prop('checked', false);
        textbox.prop('disabled', true);
        datetimepicker.data("DateTimePicker").hide();
      }
    });
  });

  if (window.getTemplateValue('log_entry_text_missing')) {
    $('#newLogEntryModal').modal({'show': true});
  }

  $('.button-show-instrument-log-list').prop('disabled', true);
});
