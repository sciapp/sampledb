/***
 * This function uses the JSON-String which is given to her by an 'onClick-Function' to put the plots of the given data to the 'div ' on the object-page.
 *
 * The function makes it possible to get more information about the plot data or to hide
 * @param json_string
 */
function plotlyPlot(json_string, div_id) {
    var plot_div = $('#plotly_plot_div_'+div_id);
    var plot_info_link = $('#plot_info_link_' + div_id);
    if(/display:none/.test(plot_div.attr('style'))) {
        plot_div.attr('style', 'height:40vh')
        plot_info_link.html('less info')
        if(plot_info_link.attr("isPlotted") != "true") {
            plot(json_string, 'plotly_plot_div_' + div_id);
            plot_info_link.attr("isPlotted", "true");
        }
    } else {
        plot_div.attr('style', 'display:none');
        plot_info_link.html('more info')
    }

}

/**
 * Help function of plotlyPlot
 * The function gets an JSON-String and plots the different data to a div.
 * The different data for the plots is given as keys in the JSON-String so that it can be chosen.
 * @param json_string
 */
function plot(json_string, div_id) {
    var json_string_key_list = Object.keys(json_string);
    Plotly.newPlot(div_id, {data: []});
    var layout = {layout: {barmode: 'stack'}};
    if(json_string_key_list.includes("layout")) {
        layout = json_string["layout"];
        layout = JSON.parse(JSON.stringify(layout));
    }
    for(var i in json_string_key_list) {
        var json_data = json_string[json_string_key_list[i]]
        Plotly.plot(div_id, {data: [json_string[json_string_key_list[i]]], layout: layout });
    }
}

function hash(json_string) {

}