/***
 * This function uses the JSON-String which is given to her by an 'onClick-Function' to put the plots of the given data to the 'div ' on the object-page.
 *
 * The function makes it possible to get more information about the plot data or to hide
 * @param data_json
 * @param div_data_hash
 * @param layout_json
 */
function plotlyPlot(data_json, div_data_hash, layout_json="") {
    var plot_div = $('#plotly_plot_div_'+ div_data_hash);
    var plot_info_link = $('#plot_info_link_' + div_data_hash);
    if(/display:none/.test(String(plot_div.attr('style')))) {
        plot_div.attr('style', 'height:40vh')
        plot_info_link.html('less info')
        if(plot_info_link.attr("isPlotted") != "true") {
            plot(data_json, 'plotly_plot_div_' + div_data_hash, layout_json);
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
 * @param data_json
 * @param div_id
 * @param layout_json
 */
function plot(data_json, div_id, layout_json) {
    var json_string_key_list = Object.keys(data_json);
    Plotly.newPlot(div_id, {data: []});
    var layout = {layout: {barmode: 'stack'}};
    if(String(layout_json) != "") {
        layout = layout_json;
        layout = JSON.parse(JSON.stringify(layout));
    }
    for(var i in json_string_key_list) {
        var json_data = data_json[json_string_key_list[i]]
        Plotly.plot(div_id, {data: [data_json[json_string_key_list[i]]], layout: layout });
    }
}

function hash(json_string) {

}