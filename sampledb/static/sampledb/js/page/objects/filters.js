'use strict';
/* eslint-env jquery */

$(function () {
  const filterOriginIDsPicker = $('#filter_origin_ids');
  const filterActionTypeIDsPicker = $('#filter_action_type_ids');
  const filterActionIDsPicker = $('#filter_action_ids');
  const filterInstrumentPicker = $('#filter_instrument_ids');
  filterOriginIDsPicker.on('changed.bs.select', function () {
    const selectedSources = filterOriginIDsPicker.val();
    if (selectedSources.length === 0) {
      // enable all options
      filterActionTypeIDsPicker.find('option').prop('disabled', false);
      filterActionIDsPicker.find('option').prop('disabled', false);
      filterInstrumentPicker.find('option').prop('disabled', false);
    } else {
      // disable all options
      filterActionTypeIDsPicker.find('option').prop('disabled', true);
      filterActionIDsPicker.find('option').prop('disabled', true);
      filterInstrumentPicker.find('option').prop('disabled', true);
      // enable local default action types as they might be aliases for other action types
      filterActionTypeIDsPicker.find('option[data-source="local"][value^="-"]').prop('disabled', false);
      // enable options for the selected sources
      for (const source of selectedSources) {
        filterActionTypeIDsPicker.find('option[data-source="' + source + '"]').prop('disabled', false);
        filterActionIDsPicker.find('option[data-source="' + source + '"]').prop('disabled', false);
        filterInstrumentPicker.find('option[data-source="' + source + '"]').prop('disabled', false);
      }
    }
    // refresh to update enabled/disabled options
    filterActionTypeIDsPicker.selectpicker('refresh');
    filterActionIDsPicker.selectpicker('refresh');
    filterInstrumentPicker.selectpicker('refresh');
    // render to update selected options
    filterActionTypeIDsPicker.selectpicker('render');
    filterActionIDsPicker.selectpicker('render');
    filterInstrumentPicker.selectpicker('render');
  });
  $('.selectpicker').each(function (_, element) {
    const selectpicker = $(element);
    selectpicker.selectpicker();
    // ensure options marked as selected will be selected again after page reload
    const selectedOptions = selectpicker.find('option[selected]');
    if (selectedOptions) {
      const selectedOptionValues = [];
      selectedOptions.each(function (_, option) {
        selectedOptionValues.push($(option).val());
      });
      selectpicker.selectpicker('val', selectedOptionValues);
    } else {
      selectpicker.selectpicker('val', null);
    }
  });

  $('#filter_instrument_ids, #filter_action_ids').on('rendered.bs.select', function () {
    const values = $(this).val();
    values.sort();
    const uniqueValues = [];
    for (const value of values) {
      if (uniqueValues.length === 0 || uniqueValues[uniqueValues.length - 1] !== value) {
        uniqueValues.push(value);
      }
    }
    if (values.length === 0) {
      return;
    }
    const selectedOptions = [];
    for (const value of uniqueValues) {
      selectedOptions.push($(this).find(`option[value="${value}"]`).first().text().trim());
    }
    const dropdownLabel = $(this).siblings('.dropdown-toggle').find('.filter-option-inner-inner');
    dropdownLabel.text(selectedOptions.join(', '));
  }).on('changed.bs.select', function (event, clickedIndex, isSelected, previousValue) {
    if (clickedIndex !== null) {
      const currentValue = $(this).val();
      const values = currentValue.concat(previousValue);
      values.sort();
      const uniqueValues = [];
      for (const value of values) {
        if (uniqueValues.length === 0 || uniqueValues[uniqueValues.length - 1] !== value) {
          uniqueValues.push(value);
        }
      }
      for (const value of uniqueValues) {
        const previousNumber = $.grep(previousValue, function (val) {
          return val === value;
        }).length;
        const currentNumber = $.grep(currentValue, function (val) {
          return val === value;
        }).length;
        if (previousNumber !== currentNumber) {
          $(this).find(`option[value="${value}"]`).prop('selected', previousNumber < currentNumber);
        }
      }
      $(this).selectpicker('refresh');
    }
  }).selectpicker('refresh');
});
