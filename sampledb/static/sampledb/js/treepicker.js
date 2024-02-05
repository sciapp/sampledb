'use strict';
/* eslint-env jquery */

$(function () {
  function updateCollapseExpandStatus (option) {
    const classes = option.attr('class').split(/\s+/);
    for (let i = 0; i < classes.length; i++) {
      if (classes[i].startsWith('option-group-') && classes[i].endsWith('-closed')) {
        option.closest('li').hide();
        return;
      }
    }
    option.closest('li').show();
  }

  function collapseExpandMenu (event) {
    const option = $(event.currentTarget).parent();
    const ul = option.closest('ul');
    const classes = option.attr('class').split(/\s+/);
    let optionGroupID = null;
    for (let i = 0; i < classes.length; i++) {
      if (classes[i].startsWith('option-group-') && classes[i].endsWith('-header')) {
        optionGroupID = classes[i].substring('option-group-'.length, classes[i].length - '-header'.length);
      }
    }
    if (optionGroupID === null) {
      return;
    }
    const duplicateOptions = ul.find('span.option-group-' + optionGroupID + '-header');
    duplicateOptions.toggleClass('closed');
    const childOptions = ul.find('span.option-group-' + optionGroupID + '-member');
    if (option.hasClass('closed')) {
      childOptions.addClass('option-group-' + optionGroupID + '-closed');
    } else {
      childOptions.removeClass('option-group-' + optionGroupID + '-closed');
    }
    childOptions.each(function (_, element) {
      updateCollapseExpandStatus($(element));
    });
    ul.find('.active').removeClass('active');
    event.stopPropagation();
    event.preventDefault();
    const treepicker = ul.closest('.treepicker.bootstrap-select');
    if (window.treepicker_change && window.treepicker_change.time >= Date.now() - 10 && window.treepicker_change.target === treepicker[0]) {
      treepicker.find('.selectpicker').selectpicker('val', window.treepicker_change.previousValue);
    }
  }

  function expandAll (selectpicker) {
    selectpicker.find('ul.dropdown-menu li > a > span > span').each(function (_, element) {
      const option = $(element);
      option.removeClass('closed');
      const classes = option.attr('class').split(/\s+/);
      for (let i = 0; i < classes.length; i++) {
        if (classes[i].startsWith('option-group-') && classes[i].endsWith('-closed')) {
          option.removeClass(classes[i]);
        }
      }
      option.closest('li').show();
    });
  }

  function collapseAll (selectpicker) {
    selectpicker.find('ul.dropdown-menu li > a > span > span').each(function (_, element) {
      const option = $(element);
      const classes = option.attr('class').split(/\s+/);
      for (let i = 0; i < classes.length; i++) {
        if (classes[i].startsWith('option-group-') && classes[i].endsWith('-header')) {
          option.addClass('closed');
        }
        if (classes[i].startsWith('option-group-') && classes[i].endsWith('-member')) {
          const optionGroupID = classes[i].substring('option-group-'.length, classes[i].length - '-member'.length);
          option.addClass('option-group-' + optionGroupID + '-closed');
          option.closest('li').hide();
        }
      }
    });
  }

  function updateAll (selectpicker) {
    selectpicker.find('ul.dropdown-menu li > a > span > span').each(function (_, element) {
      updateCollapseExpandStatus($(element));
    });
  }

  $(document).on('click', '.treepicker.bootstrap-select .selectpicker-collapsible-menu', collapseExpandMenu);
  $(document).on('mouseup', '.treepicker.bootstrap-select .disabled .selectpicker-collapsible-menu', collapseExpandMenu);
  $(document).on('show.bs.select', function () {
    $(this).find('.treepicker.bootstrap-select').each(function (_, element) {
      const selectpicker = $(element);
      updateAll(selectpicker);
      selectpicker.find('.bs-searchbox input[type="search"]').on('input', function (event) {
        expandAll($(this).closest('.treepicker.bootstrap-select'));
        if ($(this).val()) {
          selectpicker.find('li').addClass('searching');
        } else {
          selectpicker.find('li').removeClass('searching');
        }
      });
      if (selectpicker.find('.treepicker-actions').length === 0) {
        const collapseAllText = window.getTemplateValue('translations.treepicker_collapse_all_text');
        const expandAllText = window.getTemplateValue('translations.treepicker_expand_all_text');
        const treepickerActions = $('<div class="treepicker-actions"><button type="button" class="btn btn-default btn-xs treepicker-collapse-all">' + collapseAllText + '</button> <button type="button" class="btn btn-default btn-xs treepicker-expand-all">' + expandAllText + '</button></div>');
        treepickerActions.insertAfter(selectpicker.find('.bs-searchbox'));
        treepickerActions.find('.treepicker-collapse-all').on('click', function (event) {
          const selectpicker = $(this).closest('.treepicker.bootstrap-select');
          collapseAll(selectpicker);
          event.stopPropagation();
        });
        treepickerActions.find('.treepicker-expand-all').on('click', function (event) {
          const selectpicker = $(this).closest('.treepicker.bootstrap-select');
          expandAll(selectpicker);
          event.stopPropagation();
        });
      }
    });
  });
  $('.treepicker.bootstrap-select').on('changed.bs.select', function (e, clickedIndex, isSelected, previousValue) {
    if (clickedIndex !== null && isSelected !== null) {
      window.treepicker_change = {
        time: Date.now(),
        previousValue,
        target: e.currentTarget
      };
    } else {
      window.treepicker_change = null;
    }
  });
});
