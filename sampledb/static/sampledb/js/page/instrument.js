'use strict';
/* eslint-env jquery */
/* globals InscrybMDE, moment */

import {
  setupImageDragAndDrop
} from '../markdown_image_upload.js';

$(function () {
  window.categoriesShown = window.getTemplateValue('categories_shown');
  window.filterDate = null;
  window.filterUser = null;
  window.editLogEntryContentMDE = null;
});
function setupInstrumentLogFilterStates () {
  for (const categoryID in window.categoriesShown) {
    $(`#instrument_log_filter_${categoryID}`).prop('checked', window.categoriesShown[categoryID]);
  }
  $('#instrument_log_filter_none').prop('checked', window.categoriesShown.none);
  $('#instrument_log_counter').html($('.instrument-log-entry:not(:hidden)').length.toString() + ' / ' + $('.instrument-log-entry').length.toString());
  $('.input-group.date').each(function () {
    const datetimepicker = $(this).datetimepicker({
      date: window.filterDate,
      locale: window.getTemplateValue('language.lang_code'),
      format: 'YYYY-MM',
      showClear: true,
      showClose: true,
      maxDate: moment(new Date()),
      timeZone: window.getTemplateValue('current_user.timezone')
    });
    datetimepicker.on('dp.change', function () {
      updateInstrumentLogFilterStates();
    });
    $('#input-instrument-log-filter-date').on('click', function () {
      datetimepicker.data('DateTimePicker').toggle();
    });
  });
  const selectpicker = $('#input-instrument-log-filter-user');
  selectpicker.selectpicker('val', window.filterUser);
  selectpicker.on('changed.bs.select', function () {
    updateInstrumentLogFilterStates();
  });
}

function updateInstrumentLogFilterStates () {
  const filterDate = $('#input-instrument-log-filter-date').val();
  if (filterDate === '') {
    window.filterDate = null;
  } else {
    window.filterDate = filterDate;
  }
  const filterUser = $('#input-instrument-log-filter-user').val();
  if (filterUser === '') {
    window.filterUser = null;
  } else {
    window.filterUser = filterUser;
  }
  $('.instrument-log-entry').hide();
  for (const categoryID in window.categoriesShown) {
    window.categoriesShown[categoryID] = $(`#instrument_log_filter_${categoryID}`).prop('checked');
    if (window.categoriesShown[categoryID]) {
      let filterSelector = `div[data-instrument-log-category-${categoryID}="yes"]`;
      if (filterDate !== '') {
        filterSelector = filterSelector + '[data-instrument-log-date=' + filterDate + ']';
      }
      if (filterUser !== '') {
        filterSelector = filterSelector + '[data-instrument-log-user-id=' + filterUser + ']';
      }
      $(filterSelector).show();
    }
  }
  $('#instrument_log_counter').html($('.instrument-log-entry:not(:hidden)').length.toString() + ' / ' + $('.instrument-log-entry').length.toString());
}

function resetInstrumentLogFilterStates () {
  for (const categoryID in window.categoriesShown) {
    window.categoriesShown[categoryID] = true;
  }
  window.filterUser = null;
  window.filterDate = null;
  const numEntries = $('#instrument-log-container > div > .instrument-log-entry').length;
  $('#instrument_log_counter').html(numEntries.toString() + ' / ' + numEntries.toString());
}

$(function () {
  setupInstrumentLogFilterStates();
  $('[data-toggle="popover"]').popover();

  function updateNewLogEntryMarkdown () {
    if ($('#input-content-is-markdown').prop('checked')) {
      window.new_log_entry = new InscrybMDE({
        element: $('#textarea-log-entry-text')[0],
        indentWithTabs: false,
        spellChecker: false,
        status: false,
        hideIcons: ['guide', 'fullscreen', 'side-by-side', 'quote'],
        showIcons: ['code', 'table'],
        minHeight: '100px',
        autoDownloadFontAwesome: false
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

  const editLogEntryModal = $('#editLogEntryModal');
  editLogEntryModal.on('show.bs.modal', function (event) {
    if (!event || !event.relatedTarget) {
      return;
    }
    const logEntryInfo = $(event.relatedTarget).data('json-log-entry-info');
    editLogEntryModal.find('#input-edit-log-entry-id').val(logEntryInfo.id);
    editLogEntryModal.find('#input-edit-content-is-markdown').prop('checked', logEntryInfo.contentIsMarkdown);
    editLogEntryModal.find('#textarea-edit-log-entry-text').val(logEntryInfo.content);
    updateEditLogEntryMarkdown();
    editLogEntryModal.find('#textarea-edit-log-entry-text').val(logEntryInfo.content);
    editLogEntryModal.find('#input-edit-has-event-datetime').prop('checked', logEntryInfo.hasEventDatetime);
    editLogEntryModal.find('#textarea-edit-log-entry-event_utc_datetime').val(logEntryInfo.hasEventDatetime ? logEntryInfo.eventDatetime : '').prop('disabled', !logEntryInfo.hasEventDatetime);
    editLogEntryModal.find('#select-edit-categories').selectpicker('val', logEntryInfo.categoryIds);
    const newObjectAttachmentSelectpicker = editLogEntryModal.find('#select-edit-new-object-attachments');
    newObjectAttachmentSelectpicker.find('option').each(function () {
      const option = $(this);
      option.prop('disabled', logEntryInfo.existingAttachedObjectIds.includes(+(option.val())));
    });
    newObjectAttachmentSelectpicker.selectpicker('refresh');
    if (logEntryInfo.existingObjectAttachments.length === 0 && logEntryInfo.existingFileAttachments.length === 0) {
      $('#hr-edit-hide-attachments').hide().nextAll().hide();
    } else {
      $('#hr-edit-hide-attachments').show().nextAll().show();
    }
    const existingObjectAttachmentsSelectpicker = editLogEntryModal.find('#select-edit-existing-object-attachments');
    existingObjectAttachmentsSelectpicker.empty();
    for (const objectAttachment of logEntryInfo.existingObjectAttachments) {
      const option = $(`<option value="${objectAttachment.id}"></option>`);
      option.text(objectAttachment.label);
      existingObjectAttachmentsSelectpicker.prepend(option);
    }
    if (logEntryInfo.existingObjectAttachments.length === 0) {
      existingObjectAttachmentsSelectpicker.closest('.form-group').hide();
    }
    existingObjectAttachmentsSelectpicker.selectpicker('refresh');
    const existingFileAttachmentsSelectpicker = editLogEntryModal.find('#select-edit-existing-file-attachments');
    existingFileAttachmentsSelectpicker.empty();
    for (const fileAttachment of logEntryInfo.existingFileAttachments) {
      const option = $(`<option value="${fileAttachment.id}"></option>`);
      option.text(fileAttachment.label);
      existingFileAttachmentsSelectpicker.prepend(option);
    }
    if (logEntryInfo.existingFileAttachments.length === 0) {
      existingFileAttachmentsSelectpicker.closest('.form-group').hide();
    }
    existingFileAttachmentsSelectpicker.selectpicker('refresh');
  });

  function editLogEntryFileChangeHandler () {
    const files = $('#input-edit-file-upload').get(0).files;
    if (files.length === 0) {
      $('#input-file-text').val('');
    } else if (files.length === 1) {
      $('#input-edit-file-text').val(files[0].name);
    } else {
      $('#input-edit-file-text').val(files.length + ' ' + window.getTemplateValue('translations.files_selected'));
    }
  }
  $('#input-edit-file-upload').on('change', editLogEntryFileChangeHandler);

  function editLogEntryFileDropHandler (e) {
    e.preventDefault();
    $('#input-edit-file-upload')[0].files = e.dataTransfer.files;
    editLogEntryFileChangeHandler();
  }
  function editLogEntryFileDragOverHandler (e) {
    e.preventDefault();
  }
  const uploadArea = $('#edit-upload-area');
  if (uploadArea.length > 0) {
    uploadArea[0].ondrop = editLogEntryFileDropHandler;
    uploadArea[0].ondragover = editLogEntryFileDragOverHandler;
  }

  function updateEditLogEntryMarkdown () {
    if (editLogEntryModal.find('#input-edit-content-is-markdown').prop('checked')) {
      if (window.editLogEntryContentMDE) {
        window.editLogEntryContentMDE.toTextArea();
      }
      window.editLogEntryContentMDE = new InscrybMDE({
        element: editLogEntryModal.find('#textarea-edit-log-entry-text')[0],
        indentWithTabs: false,
        spellChecker: false,
        status: false,
        hideIcons: ['guide', 'fullscreen', 'side-by-side', 'quote'],
        showIcons: ['code', 'table'],
        minHeight: '100px',
        autoDownloadFontAwesome: false
      });
      setupImageDragAndDrop(window.editLogEntryContentMDE);
    } else {
      if (window.editLogEntryContentMDE) {
        window.editLogEntryContentMDE.toTextArea();
        window.editLogEntryContentMDE = null;
      }
    }
  }
  editLogEntryModal.find('#input-edit-content-is-markdown').change(updateEditLogEntryMarkdown);
  editLogEntryModal.on('shown.bs.modal', updateEditLogEntryMarkdown);

  function changeHandler () {
    const files = $('#input-file-upload').get(0).files;
    if (files.length === 0) {
      $('#input-file-text').val('');
    } else if (files.length === 1) {
      $('#input-file-text').val(files[0].name);
    } else {
      $('#input-file-text').val(files.length + ' ' + window.getTemplateValue('translations.files_selected'));
    }
  }
  if (window.getTemplateValue('can_create_instrument_log_entries')) {
    $('#input-file-upload').on('change', changeHandler);
    const dropHandler = function (e) {
      e.preventDefault();
      $('#input-file-upload')[0].files = e.dataTransfer.files;
      changeHandler();
    };
    const dragOverHandler = function (e) {
      e.preventDefault();
    };
    const uploadArea = $('#upload-area')[0];
    uploadArea.ondrop = dropHandler;
    uploadArea.ondragover = dragOverHandler;
  }

  function applySortOrder (logOrderButton, attribute) {
    const logOrderButtonIndicator = logOrderButton.find('i');
    if (logOrderButtonIndicator.css('visibility') === 'hidden') {
      $('.button-switch-instrument-log-order i').css('visibility', 'hidden');
      logOrderButtonIndicator.css('visibility', 'visible');
    } else {
      logOrderButtonIndicator.toggleClass('fa-sort-asc').toggleClass('fa-sort-desc');
    }

    const ascending = (logOrderButton.find('i.fa-sort-asc').length !== 0);

    const container = $('#instrument-log-container');
    container.children().sort(function (a, b) {
      const aDatetime = $(a).find('.instrument-log-entry').data('instrumentLog' + attribute);
      const bDatetime = $(b).find('.instrument-log-entry').data('instrumentLog' + attribute);
      if (ascending) {
        return aDatetime > bDatetime;
      } else {
        return aDatetime < bDatetime;
      }
    }).appendTo(container);

    const form = $('#form-instrument-log-order');
    form.find('input[type="checkbox"]').prop('checked', ascending);
    form.find('input[type="text"]').val(attribute.toLowerCase());
    $.ajax({
      type: 'POST',
      url: window.getTemplateValue('set_instrument_log_order_url'),
      data: form.serialize()
    });
  }
  const logOrderButtonDate = $('#button-switch-instrument-log-order-date');
  logOrderButtonDate.on('click', function () {
    applySortOrder(logOrderButtonDate, 'Datetime');
  });
  const logOrderButtonUserName = $('#button-switch-instrument-log-order-user-name');
  logOrderButtonUserName.on('click', function () {
    applySortOrder(logOrderButtonUserName, 'UserName');
  });

  const showListButton = $('.button-show-instrument-log-list');
  const showTreeButtonDateAuthor = $('.button-show-instrument-log-tree-date-author');
  const showTreeButtonAuthorDate = $('.button-show-instrument-log-tree-author-date');
  showListButton.on('click', function () {
    resetInstrumentLogFilterStates();
    showListButton.prop('disabled', true);
    showTreeButtonDateAuthor.prop('disabled', false);
    showTreeButtonAuthorDate.prop('disabled', false);
    $('.button-switch-instrument-log-order, #button-instrument-log-list-filter').prop('disabled', false);
    $('#instrument-log-tree').html('');
    $('.instrument-log-entry').show();
  });
  function sortTreeContainerChildren (container) {
    container.children('.instrument-log-tree-container').sort(function (a, b) {
      const aValue = $(a).data('instrumentLogTreeSortValue');
      const bValue = $(b).data('instrumentLogTreeSortValue');
      const aNumber = Number.parseInt(aValue);
      const bNumber = Number.parseInt(bValue);
      if (Number.isNaN(aNumber) || Number.isNaN(bNumber)) {
        return aValue > bValue;
      } else {
        return aNumber > bNumber;
      }
    }).appendTo(container);
  }
  showTreeButtonDateAuthor.on('click', function () {
    resetInstrumentLogFilterStates();
    showListButton.prop('disabled', false);
    showTreeButtonDateAuthor.prop('disabled', true);
    showTreeButtonAuthorDate.prop('disabled', false);
    $('.button-switch-instrument-log-order, #button-instrument-log-list-filter').prop('disabled', true);
    const logEntries = $('#instrument-log-container > div > .instrument-log-entry');
    $('#button-instrument-log-list-filter').popover('hide');
    logEntries.hide();
    const treeContainer = $('#instrument-log-tree');
    if (logEntries.length) {
      treeContainer.html(`<div class="instrument-log-tree-container"><div class="instrument-log-tree-block" id="instrument-log-tree-root-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_years')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_years')}</button></div></div></div>`);
    } else {
      treeContainer.html('');
    }
    const containersByDate = {};
    let i = 0;
    const MONTH_NAMES = window.getTemplateValue('translations.month_names');
    logEntries.each(function (_, element) {
      const logEntry = $(element);
      const author = logEntry.data('instrumentLogUserName');
      const utcDatetimeString = logEntry.data('instrumentLogDatetime');
      const utcDatetime = moment.utc(utcDatetimeString);
      const localDatetime = utcDatetime.local();
      const year = localDatetime.year();
      const month = localDatetime.month();
      const day = localDatetime.date();
      if (!(year in containersByDate)) {
        const parentContainer = treeContainer.find('#instrument-log-tree-root-block');
        const container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${year}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${year}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_months')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_months')}</button></div></div></div>`);
        container.appendTo(parentContainer);
        sortTreeContainerChildren(parentContainer);
        containersByDate[year] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(month in containersByDate[year][1])) {
        const parentContainer = containersByDate[year][0];
        const container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${month}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${MONTH_NAMES[month]}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_days')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_days')}</button></div></div></div>`);
        container.appendTo(parentContainer);
        sortTreeContainerChildren(parentContainer);
        containersByDate[year][1][month] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(day in containersByDate[year][1][month][1])) {
        const parentContainer = containersByDate[year][1][month][0];
        const container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${day}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${day}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_authors')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_authors')}</button></div></div></div>`);
        container.appendTo(parentContainer);
        sortTreeContainerChildren(parentContainer);
        containersByDate[year][1][month][1][day] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(author in containersByDate[year][1][month][1][day][1])) {
        const parentContainer = containersByDate[year][1][month][1][day][0];
        const container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${author}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${author}</label></h3><div class="instrument-log-tree-block"></div></div>`);
        container.appendTo(parentContainer);
        sortTreeContainerChildren(parentContainer);
        containersByDate[year][1][month][1][day][1][author] = [container.find('.instrument-log-tree-block'), {}];
      }
      const logEntryClone = $(logEntry).clone();
      logEntryClone.show();
      logEntryClone.appendTo(containersByDate[year][1][month][1][day][1][author][0]);
    });
    treeContainer.find('.button-instrument-log-tree-expand-all').on('click', function () {
      $(this).closest('.instrument-log-tree-block').find('> .instrument-log-tree-container > input[type="checkbox"]').each(function (_, checkbox) {
        checkbox.checked = true;
      });
    });
    treeContainer.find('.button-instrument-log-tree-collapse-all').on('click', function () {
      $(this).closest('.instrument-log-tree-block').find('> .instrument-log-tree-container > input[type="checkbox"]').each(function (_, checkbox) {
        checkbox.checked = false;
      });
    });
  });
  showTreeButtonAuthorDate.on('click', function () {
    resetInstrumentLogFilterStates();
    showListButton.prop('disabled', false);
    showTreeButtonDateAuthor.prop('disabled', false);
    showTreeButtonAuthorDate.prop('disabled', true);
    $('.button-switch-instrument-log-order, #button-instrument-log-list-filter').prop('disabled', true);
    const logEntries = $('#instrument-log-container > div > .instrument-log-entry');
    $('#button-instrument-log-list-filter').popover('hide');
    logEntries.hide();
    const treeContainer = $('#instrument-log-tree');
    if (logEntries.length) {
      treeContainer.html(`<div class="instrument-log-tree-container"><div class="instrument-log-tree-block" id="instrument-log-tree-root-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_authors')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_authors')}</button></div></div></div>`);
    } else {
      treeContainer.html();
    }
    const containersByAuthor = {};
    let i = 0;
    const MONTH_NAMES = window.getTemplateValue('translations.month_names');
    logEntries.each(function (_, element) {
      const logEntry = $(element);
      const author = logEntry.data('instrumentLogUserName');
      const utcDatetimeString = logEntry.data('instrumentLogDatetime');
      const utcDatetime = moment.utc(utcDatetimeString);
      const localDatetime = utcDatetime.local();
      const year = localDatetime.year();
      const month = localDatetime.month();
      const day = localDatetime.date();
      if (!(author in containersByAuthor)) {
        const parentContainer = treeContainer.find('#instrument-log-tree-root-block');
        const container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${author}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${author}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_years')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_years')}</button></div></div></div>`);
        container.appendTo(parentContainer);
        sortTreeContainerChildren(parentContainer);
        containersByAuthor[author] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(year in containersByAuthor[author][1])) {
        const parentContainer = containersByAuthor[author][0];
        const container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${year}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${year}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_months')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_months')}</button></div></div></div>`);
        container.appendTo(parentContainer);
        sortTreeContainerChildren(parentContainer);
        containersByAuthor[author][1][year] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(month in containersByAuthor[author][1][year][1])) {
        const parentContainer = containersByAuthor[author][1][year][0];
        const container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${month}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${MONTH_NAMES[month]}</label></h3><div class="instrument-log-tree-block"><div><button type="button" class="btn btn-default btn-xs button-instrument-log-tree-expand-all">${window.getTemplateValue('translations.expand_all_days')}</button> <button type="button" class="btn btn-default btn-xs button-instrument-log-tree-collapse-all">${window.getTemplateValue('translations.collapse_all_days')}</button></div></div></div>`);
        container.appendTo(parentContainer);
        sortTreeContainerChildren(parentContainer);
        containersByAuthor[author][1][year][1][month] = [container.find('.instrument-log-tree-block'), {}];
      }
      if (!(day in containersByAuthor[author][1][year][1][month][1])) {
        const parentContainer = containersByAuthor[author][1][year][1][month][0];
        const container = $(`<div class="instrument-log-tree-container" data-instrument-log-tree-sort-value="${day}"><input type="checkbox" id="instrument-log-tree-toggle-${++i}"/><h3><label for="instrument-log-tree-toggle-${i}"><i class="fa fa-fw fa-plus-square"></i> ${day}</label></h3><div class="instrument-log-tree-block"></div></div>`);
        container.appendTo(parentContainer);
        sortTreeContainerChildren(parentContainer);
        containersByAuthor[author][1][year][1][month][1][day] = [container.find('.instrument-log-tree-block'), {}];
      }
      const logEntryClone = $(logEntry).clone();
      logEntryClone.show();
      logEntryClone.appendTo(containersByAuthor[author][1][year][1][month][1][day][0]);
    });
    treeContainer.find('.button-instrument-log-tree-expand-all').on('click', function () {
      $(this).closest('.instrument-log-tree-block').find('> .instrument-log-tree-container > input[type="checkbox"]').each(function (_, checkbox) {
        checkbox.checked = true;
      });
    });
    treeContainer.find('.button-instrument-log-tree-collapse-all').on('click', function () {
      $(this).closest('.instrument-log-tree-block').find('> .instrument-log-tree-container > input[type="checkbox"]').each(function (_, checkbox) {
        checkbox.checked = false;
      });
    });
  });

  $('.log_entry_date_picker').each(function () {
    const datetimepicker = $(this);
    const textbox = datetimepicker.find('input[type="text"]');
    const checkbox = datetimepicker.parent().find('input[type="checkbox"]');
    if (textbox.val()) {
      checkbox.prop('checked', true);
      textbox.prop('disabled', false);
    }
    const now = new Date();
    const minDate = new Date();
    minDate.setFullYear(now.getFullYear() - 999);
    const maxDate = new Date();
    maxDate.setFullYear(now.getFullYear() + 999);
    datetimepicker.datetimepicker({
      format: window.getTemplateValue('event_utc_datetime.format_moment'),
      showClear: true,
      showClose: true,
      showTodayButton: true,
      timeZone: window.getTemplateValue('current_user.timezone'),
      minDate,
      maxDate
    });
    checkbox.on('change', function () {
      const checked = checkbox.prop('checked');
      textbox.prop('disabled', !checked);
      if (checked) {
        datetimepicker.data('DateTimePicker').show();
      } else {
        datetimepicker.data('DateTimePicker').hide();
        textbox.val('');
      }
    });
    datetimepicker.on('dp.change', function () {
      if (textbox.val() === '') {
        checkbox.prop('checked', false);
        textbox.prop('disabled', true);
        datetimepicker.data('DateTimePicker').hide();
      }
    });
    textbox.on('change', function () {
      if (textbox.val() === '') {
        checkbox.prop('checked', false);
        textbox.prop('disabled', true);
        datetimepicker.data('DateTimePicker').hide();
      }
    });
  });

  if (window.getTemplateValue('log_entry_text_missing')) {
    $('#newLogEntryModal').modal({ show: true });
  }

  $('.button-show-instrument-log-list').prop('disabled', true);

  $('#button-instrument-log-list-filter').on('inserted.bs.popover', function () {
    setupInstrumentLogFilterStates();
    for (const categoryID in window.categoriesShown) {
      document.getElementById(`instrument_log_filter_${categoryID}`).addEventListener('click', function () {
        updateInstrumentLogFilterStates();
      });
    }
  });
});
