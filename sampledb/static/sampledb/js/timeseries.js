$(function() {
  $('.timeseries-container').each(function(index, element) {
    let timeseries_data = JSON.parse($(element).find('script[type="application/json"]')[0].textContent);
    $(element).find('.timeseries-chart-button').on('click', function() {
      let chart_data = [
        {
          x: timeseries_data.local_datetimes_strings,
          y: timeseries_data.magnitudes,
          type: 'scatter'
        }
      ];
      let chart_layout = {
          yaxis: {
            ticksuffix: timeseries_data.units
          },
          margin: {
            l: 50,
            r: 50,
            b: 50,
            t: 50,
            pad: 4
          },
          width: 868
      }
      let chart_modal = $('#timeseriesChartModal');
      chart_modal.find('.modal-title').text(timeseries_data.title);
      Plotly.newPlot(chart_modal.find('.modal-body')[0], chart_data, chart_layout);
      chart_modal.modal();
    });
    $(element).find('.timeseries-table-button').on('click', function() {
      let table_modal = $('#timeseriesTableModal');
      table_modal.find('.modal-title').text(timeseries_data.title);
      let table = table_modal.find('table');
      let tbody = table.find('tbody');
      tbody.html('');
      for (let i = 0; i < timeseries_data.local_datetimes_strings.length; i++) {
          let tr = $('<tr/>').appendTo(tbody);
          tr.append('<td>' + timeseries_data.local_datetimes_strings[i] + '</td>');
          tr.append('<td>' + timeseries_data.magnitude_strings[i] + timeseries_data.units + '</td>');
      }
      table_modal.modal();
    });
  });
});
