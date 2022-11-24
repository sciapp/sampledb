$(function () {
  function updateCollapseExpandStatus(option) {
    let classes = option.attr("class").split(/\s+/);
    for (let i = 0; i < classes.length; i++) {
      if (classes[i].startsWith('option-group-') && classes[i].endsWith('-closed')) {
        option.closest('li').hide();
        return
      }
    }
    option.closest('li').show();
  }

  function collapseExpandMenu(event) {
    let option = $(this).parent();
    let ul = option.closest("ul");
    let classes = option.attr("class").split(/\s+/);
    let option_group_id = null;
    for (let i = 0; i < classes.length; i++) {
      if (classes[i].startsWith('option-group-') && classes[i].endsWith('-header')) {
        option_group_id = classes[i].substring('option-group-'.length, classes[i].length - '-header'.length);
      }
    }
    if (option_group_id === null) {
      return;
    }
    let duplicate_options = ul.find('span.option-group-' + option_group_id + '-header');
    duplicate_options.toggleClass('closed');
    let child_options = ul.find('span.option-group-' + option_group_id + '-member');
    if (option.hasClass('closed')) {
      child_options.addClass('option-group-' + option_group_id + '-closed');
    } else {
      child_options.removeClass('option-group-' + option_group_id + '-closed');
    }
    child_options.each(function (_, element) {
      updateCollapseExpandStatus($(element));
    });
    ul.find('.active').removeClass('active');
    event.stopPropagation();
    event.preventDefault();
    let treepicker = ul.closest('.treepicker.bootstrap-select');
    if (window.treepicker_change && window.treepicker_change.time >= Date.now() - 10 && window.treepicker_change.target === treepicker[0]) {
      treepicker.find('.selectpicker').selectpicker('val', window.treepicker_change.previousValue);
    }
  }

  function expandAll(selectpicker) {
    selectpicker.find('ul.dropdown-menu li > a > span > span').each(function (_, element) {
      let option = $(element);
      option.removeClass('closed');
      let classes = option.attr("class").split(/\s+/);
      for (let i = 0; i < classes.length; i++) {
        if (classes[i].startsWith('option-group-') && classes[i].endsWith('-closed')) {
          option.removeClass(classes[i]);
        }
      }
      option.closest('li').show();
    });
  }

  function collapseAll(selectpicker) {
    selectpicker.find('ul.dropdown-menu li > a > span > span').each(function (_, element) {
      let option = $(element);
      let classes = option.attr("class").split(/\s+/);
      for (let i = 0; i < classes.length; i++) {
        if (classes[i].startsWith('option-group-') && classes[i].endsWith('-header')) {
          option.addClass('closed');
        }
        if (classes[i].startsWith('option-group-') && classes[i].endsWith('-member')) {
          let option_group_id = classes[i].substring('option-group-'.length, classes[i].length - '-member'.length);
          option.addClass('option-group-' + option_group_id + '-closed');
          option.closest('li').hide();
        }
      }
    });
  }

  function updateAll(selectpicker) {
    selectpicker.find('ul.dropdown-menu li > a > span > span').each(function (_, element) {
      updateCollapseExpandStatus($(element));
    });
  }

  $(document).on("click", ".treepicker.bootstrap-select .selectpicker-collapsible-menu", collapseExpandMenu);
  $(document).on("mouseup", ".treepicker.bootstrap-select .disabled .selectpicker-collapsible-menu", collapseExpandMenu);
  $(document).on("show.bs.select", function () {
    $(this).find('.treepicker.bootstrap-select').each(function (_, element) {
      let selectpicker = $(element);
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
        let collapse_all_text = window.treepicker_collapse_all_text;
        let expand_all_text = window.treepicker_expand_all_text;
        let treepicker_actions = $('<div class="treepicker-actions"><button type="button" class="btn btn-default btn-xs treepicker-collapse-all">' + collapse_all_text + '</button> <button type="button" class="btn btn-default btn-xs treepicker-expand-all">' + expand_all_text + '</button></div>');
        treepicker_actions.insertAfter(selectpicker.find('.bs-searchbox'));
        treepicker_actions.find('.treepicker-collapse-all').on('click', function(event) {
          let selectpicker = $(this).closest('.treepicker.bootstrap-select');
          collapseAll(selectpicker);
          event.stopPropagation();
        });
        treepicker_actions.find('.treepicker-expand-all').on('click', function(event) {
          let selectpicker = $(this).closest('.treepicker.bootstrap-select');
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
        previousValue: previousValue,
        target: e.currentTarget
      };
    } else {
      window.treepicker_change = null;
    }
  });
});
