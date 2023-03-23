
function toggleShowMore(prefix) {
  let properties = $('.show-more-' + prefix);
  let btn = $('#show-more-' + prefix + '-btn');
  if (properties.hasClass('hidden')) {
    properties.addClass('show').removeClass('hidden');
    btn.text(window.show_less_text);
  } else {
    properties.addClass('hidden').removeClass('show');
    btn.text(window.show_more_text);
  }
}

$( document ).ready(function() {
  $(window.plotly_charts).each(function(index, element) {
    Plotly.newPlot(element[0], element[1]);
  });
});
