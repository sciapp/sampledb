function sdbtoggle(id) {
    var plot_div = $('#plotly_plot_div_'  +id);
    var toggle_link = $('#plotly_info_link_' + id);
    plot_div.toggle();
    if (plot_div.is(":hidden")) {
        toggle_link.text(toggle_link.data('showText'));
    } else {
        toggle_link.text(toggle_link.data('hideText'));
    }
}
