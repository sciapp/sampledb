window.all_timeseries_data = [];
$(function() {
  $('.timeseries-container').each(function(index, element) {
    let timeseries_data = JSON.parse($(element).find('script[type="application/json"]')[0].textContent);
    window.all_timeseries_data.push({
      id: $(element).data('sampledbTimeseriesId'),
      title: $(element).data('sampledbTimeseriesTitle'),
      data: timeseries_data
    });
    $(element).find('.timeseries-chart-button').on('click', function() {
      let current_id = $(this).closest('.timeseries-container').data('sampledbTimeseriesId');
      let chart_modal = $('#timeseriesChartModal');
      let chart_modal_body = chart_modal.find('.modal-body');
      let chart_modal_title = chart_modal.find('.modal-title');
      if (window.all_timeseries_data.length === 1) {
        chart_modal_title.show();
        chart_modal.find('.timeseries-picker-wrapper').hide();
      } else {
        chart_modal_title.hide();
        chart_modal.find('.timeseries-picker-wrapper').show();
      }
      chart_modal_title.text(timeseries_data.title);
      let chart_selectpicker = chart_modal.find('.modal-header select.selectpicker');
      chart_selectpicker.html('');
      let titles = [];
      let has_duplicates = false;
      for (let i = 0; i < window.all_timeseries_data.length; i++) {
        let ts = window.all_timeseries_data[i];
        if (titles.includes(ts.title)) {
          has_duplicates = true;
        } else {
          titles.push(ts.title);
        }
      }
      for (let i = 0; i < window.all_timeseries_data.length; i++) {
        let ts = window.all_timeseries_data[i];
        let name = ts.title;
        if (has_duplicates) {
          name +=' (' + ts.id.replaceAll('__', ' ➜ ') + ')';
        }
        let option = $('<option></option>');
        option.attr('value', ts.id);
        option.text(name);
        chart_selectpicker.append(option);
      }
      chart_selectpicker.selectpicker('refresh');
      chart_selectpicker.selectpicker('val', current_id);
      chart_selectpicker.on('changed.bs.select', function() {
        let timeseries_ids = chart_selectpicker.val();
        let titles = [];
        let has_duplicates = false;
        let rel_tick_suffix = null;
        let abs_tick_suffix = null;
        for (let i = 0; i < window.all_timeseries_data.length; i++) {
          let ts = window.all_timeseries_data[i];
          if (timeseries_ids.includes(ts.id)) {
            if (titles.includes(ts.title)) {
              has_duplicates = true;
            } else {
              titles.push(ts.title);
            }
            if (ts.data.relative_times.length > 0) {
              if (rel_tick_suffix === null) {
                rel_tick_suffix = ts.data.units;
              } else if (rel_tick_suffix !== ts.data.units) {
                rel_tick_suffix = '';
              }
            } else {
              if (abs_tick_suffix === null) {
                abs_tick_suffix = ts.data.units;
              } else if (abs_tick_suffix !== ts.data.units) {
                abs_tick_suffix = '';
              }
            }
          }
        }
        let chart_data = [];
        let relative = false;
        let absolute = false;
        for(let i = 0; i < window.all_timeseries_data.length; i++) {
          let ts = window.all_timeseries_data[i];
          if (timeseries_ids.includes(ts.id)){
            let name = ts.title;
            if (has_duplicates) {
              name += ' (' + ts.id.replaceAll('__', ' ➜ ') + ')';
            }
            if (ts.data.relative_times.length > 0) {
              relative = true;
              if (rel_tick_suffix === '' && ts.data.units.trim().length > 0) {
                name += ' [' + ts.data.units.trim() + ']';
              }
              chart_data.push({
                x: ts.data.relative_times,
                y: ts.data.magnitudes,
                type: 'scatter',
                name: name
              });
            } else {
              absolute = true;
              if (abs_tick_suffix === '' && ts.data.units.trim().length > 0) {
                name += ' [' + ts.data.units.trim() + ']';
              }
              chart_data.push({
                x: ts.data.times_strings,
                y: ts.data.magnitudes,
                xaxis: 'x2',
                yaxis: 'y2',
                type: 'scatter',
                name: name
              });
            }
          }
        }
        if (chart_data.length > 0) {
          let chart_layout = {
            margin: {
              l: 50,
              r: 50,
              b: 50,
              t: 50,
              pad: 4
            },
            width: 868,
            legend: {
              orientation: "h"
            },
          };
          if (relative && absolute) {
            chart_layout.grid = {
              rows: 2,
              columns: 1,
              pattern: 'independent'
            }
            chart_layout.height = 668;
          }
          if (relative) {
            chart_layout.xaxis = {
              ticksuffix: 's'
            };
            chart_layout.yaxis = {
              ticksuffix: rel_tick_suffix
            };
          }
          if (absolute) {
            chart_layout.xaxis2 = {
              ticksuffix: ''
            };
            chart_layout.yaxis2 = {
              ticksuffix: abs_tick_suffix
            };
          }
          chart_modal_body.html('<div></div>');
          Plotly.newPlot(chart_modal_body.children()[0], chart_data, chart_layout);
        } else {
          chart_modal_body.html('<p class="text-center text-muted"></p>');
          chart_modal_body.children().text(window.select_timeseries_text);
        }
      }).trigger('changed.bs.select');
      chart_modal.modal();
    });
    $(element).find('.timeseries-table-button').on('click', function() {
      let table_modal = $('#timeseriesTableModal');
      table_modal.find('.modal-title').text(timeseries_data.title);
      let table = table_modal.find('table');
      let tbody = table.find('tbody');
      tbody.html('');
      for (let i = 0; i < timeseries_data.times_strings.length; i++) {
          let tr = $('<tr/>').appendTo(tbody);
          tr.append('<td>' + timeseries_data.times_strings[i] + '</td>');
          tr.append('<td>' + timeseries_data.magnitude_strings[i] + timeseries_data.units + '</td>');
      }
      table_modal.modal();
    });
  });
});
