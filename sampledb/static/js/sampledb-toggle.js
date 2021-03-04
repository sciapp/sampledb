function sdbtoggle(id) {
    plot_div = '#plotly_plot_div_'+id;
    toggle_link = '#plotly_info_link_'+id;
    $( plot_div ).toggle();
    content = $( toggle_link ).html();
    if ($( plot_div ).is(":hidden")) {
        $( toggle_link ).html(content.replace("hide", "show"));
    }
    else {
        $( toggle_link ).html(content.replace("show", "hide"));
    }
}