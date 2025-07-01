'use strict';
/* eslint-env jquery */
/* globals Plotly */

window.all_timeseries_data = [];

/**
 * Set up timeseries charts, tables and buttons.
 * @param container a DOM element
 */
function setUpTimeseries (container) {
  $(container).find('.timeseries-container').each(function (index, element) {
    const timeseriesData = JSON.parse($(element).find('script[type="application/json"]')[0].textContent);
    window.all_timeseries_data.push({
      id: $(element).data('sampledbTimeseriesId'),
      title: $(element).data('sampledbTimeseriesTitle'),
      data: timeseriesData
    });
    $(element).find('.timeseries-chart-button').on('click', function () {
      const currentID = $(this).closest('.timeseries-container').data('sampledbTimeseriesId');
      const chartModal = $('#timeseriesChartModal');
      const chartModalBody = chartModal.find('.modal-body');
      const chartModalTitle = chartModal.find('.modal-title');
      if (window.all_timeseries_data.length === 1) {
        chartModalTitle.show();
        chartModal.find('.timeseries-picker-wrapper').hide();
      } else {
        chartModalTitle.hide();
        chartModal.find('.timeseries-picker-wrapper').show();
      }
      chartModalTitle.text(timeseriesData.title);
      const chartSelectpicker = chartModal.find('.modal-header select.selectpicker');
      chartSelectpicker.html('');
      const titles = [];
      let hasDuplicates = false;
      for (let i = 0; i < window.all_timeseries_data.length; i++) {
        const ts = window.all_timeseries_data[i];
        if (titles.includes(ts.title)) {
          hasDuplicates = true;
        } else {
          titles.push(ts.title);
        }
      }
      for (let i = 0; i < window.all_timeseries_data.length; i++) {
        const ts = window.all_timeseries_data[i];
        let name = ts.title;
        if (hasDuplicates) {
          name += ' (' + ts.id.replaceAll('__', ' ➜ ') + ')';
        }
        const option = $('<option></option>');
        option.attr('value', ts.id);
        option.text(name);
        chartSelectpicker.append(option);
      }
      chartSelectpicker.selectpicker('refresh');
      chartSelectpicker.selectpicker('val', currentID);
      chartSelectpicker.on('changed.bs.select', function () {
        const timeseriesIDs = chartSelectpicker.val();
        const titles = [];
        let hasDuplicates = false;
        let relativeTickSuffix = null;
        let absoluteTickSuffix = null;
        for (let i = 0; i < window.all_timeseries_data.length; i++) {
          const ts = window.all_timeseries_data[i];
          if (timeseriesIDs.includes(ts.id)) {
            if (titles.includes(ts.title)) {
              hasDuplicates = true;
            } else {
              titles.push(ts.title);
            }
            if (ts.data.relative_times.length > 0) {
              if (relativeTickSuffix === null) {
                relativeTickSuffix = ts.data.units;
              } else if (relativeTickSuffix !== ts.data.units) {
                relativeTickSuffix = '';
              }
            } else {
              if (absoluteTickSuffix === null) {
                absoluteTickSuffix = ts.data.units;
              } else if (absoluteTickSuffix !== ts.data.units) {
                absoluteTickSuffix = '';
              }
            }
          }
        }
        const chartData = [];
        let relative = false;
        let absolute = false;
        for (let i = 0; i < window.all_timeseries_data.length; i++) {
          const ts = window.all_timeseries_data[i];
          if (timeseriesIDs.includes(ts.id)) {
            let name = ts.title;
            if (hasDuplicates) {
              name += ' (' + ts.id.replaceAll('__', ' ➜ ') + ')';
            }
            if (ts.data.relative_times.length > 0) {
              relative = true;
              if (relativeTickSuffix === '' && ts.data.units.trim().length > 0) {
                name += ' [' + ts.data.units.trim() + ']';
              }
              chartData.push({
                x: ts.data.relative_times,
                y: ts.data.magnitudes,
                type: 'scatter',
                name
              });
            } else {
              absolute = true;
              if (absoluteTickSuffix === '' && ts.data.units.trim().length > 0) {
                name += ' [' + ts.data.units.trim() + ']';
              }
              chartData.push({
                x: ts.data.times_strings,
                y: ts.data.magnitudes,
                xaxis: 'x2',
                yaxis: 'y2',
                type: 'scatter',
                name
              });
            }
          }
        }
        if (chartData.length > 0) {
          const chartLayout = {
            margin: {
              l: 50,
              r: 50,
              b: 50,
              t: 50,
              pad: 4
            },
            width: 868,
            legend: {
              orientation: 'h'
            }
          };
          if (relative && absolute) {
            chartLayout.grid = {
              rows: 2,
              columns: 1,
              pattern: 'independent'
            };
            chartLayout.height = 668;
          }
          if (relative) {
            chartLayout.xaxis = {
              ticksuffix: 's'
            };
            chartLayout.yaxis = {
              ticksuffix: relativeTickSuffix
            };
          }
          if (absolute) {
            chartLayout.xaxis2 = {
              ticksuffix: ''
            };
            chartLayout.yaxis2 = {
              ticksuffix: absoluteTickSuffix
            };
          }
          chartModalBody.html('<div></div>');
          Plotly.newPlot(chartModalBody.children()[0], chartData, chartLayout);
        } else {
          chartModalBody.html('<p class="text-center text-muted"></p>');
          chartModalBody.children().text(window.getTemplateValue('translations.select_timeseries'));
        }
      }).trigger('changed.bs.select');
      chartModal.modal();
    });
    $(element).find('.timeseries-table-button').on('click', function () {
      const tableModal = $('#timeseriesTableModal');
      tableModal.find('.modal-title').text(timeseriesData.title);
      const table = tableModal.find('table');
      const tbody = table.find('tbody');
      tbody.html('');
      for (let i = 0; i < timeseriesData.times_strings.length; i++) {
        const tr = $('<tr/>').appendTo(tbody);
        tr.append('<td>' + timeseriesData.times_strings[i] + '</td>');
        tr.append('<td>' + timeseriesData.magnitude_strings[i] + timeseriesData.units + '</td>');
      }
      tableModal.modal();
    });
  });
}

$(function () {
  setUpTimeseries(document);
  window.setUpFunctions.push(setUpTimeseries);
});
