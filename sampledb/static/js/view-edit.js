// Enable to control that only one element can be edited in time
var selected_element;
var form_changed = false;

function send_data(elem, act_vals) {
    // Read out all form 'key - value' pairs out of the 'form-horizontal' element in the actual document
    let data_list = $($(".form-horizontal")[0]).serializeArray();

    // Search for 'key - value' pairs in the given list and the list that has been read out of the actual document to check if there are different entries
    let found = false;
    if (data_list.length != act_vals.length) {
        found = true;
    } else {
        for (let i = 0; i < data_list.length; i++) {
            if (data_list[i]["name"] != act_vals[i]["name"] || data_list[i]["value"] != act_vals[i]["value"]) {
                found = true;
                break;
            }
        }
    }
    if (!found) {
        return;
    } else {
        // Actual form changed
        form_changed = true;
    }

    // Create new string which contains the 'key - value' pairs
    let data_string = "";

    for (let i = 0; i < data_list.length; i++) {
        let name = data_list[i]["name"].replaceAll(/\s/g);
        let value = (name.endsWith("__units")) ? data_list[i]["value"].replaceAll(/\s/g, "") : data_list[i]["value"];
        data_string += name + "=" + value + "&";
    }
    data_string += "action_submit="
    data_string = encodeURI(data_string);

    // Create new HTTP-Request to POST the data to SampleDB
    let xml_request = new XMLHttpRequest();

    // Add listener to request to being able to react on the finish of the POST
    xml_request.addEventListener("load", function () {
        // Read out the replied html
        let res_html = ($.parseHTML(xml_request.responseText));
        for (let i = 0; i < res_html.length; i++) {
            if ($(res_html[i]).attr("id") == "main") {
                let main_html = $(res_html[i])
                // Check if the 'edit-website' has been replied to check if an error occurred
                if (main_html.find(".form-horizontal[method=post]").length > 0) {
                    // Message user using alert div
                    $(selected_element).find(".alert-upload-failed").each(function () {
                        $(this).css("display", "block");
                    });
                    $(selected_element).addClass("alert alert-danger");
                } else {
                    // Reload website to show that the change has been successful and to being able to edit the new object
                    window.location.reload();
                }
            }
        }
    });

    // Open request
    xml_request.open("POST", window.location.href.split("?")[0] + "?mode=edit");

    // Set headers
    xml_request.setRequestHeader("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8");
    xml_request.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

    // Send request
    xml_request.send(data_string);
}

function setup(elem) {
    // Save actual value
    let act_vals = $($(".form-horizontal")[0]).serializeArray();
    // Make all form elements visible
    $(elem).find(".form-switch").each(function () {
        $(this).css("display", "block");
    });
    // Hide view elements
    $(elem).find(".view-switch").each(function () {
        $(this).css("display", "none")
    });
    // If clicked outside the focussed element
    $(document).click(function (event) {
        if (!elem.contains(event.target)) {
            // Hide all form elements
            $(elem).find(".form-switch").each(function () {
                $(this).css("display", "none");
            });
            // Show all view elements
            $(elem).find(".view-switch").each(function () {
                $(this).css("display", "");
            });
            // Send actualized data
            send_data(elem, act_vals);
            event.stopPropagation();
        }
    });
    // If presses enter
    $(elem).find(":input").each(function () {
        this.addEventListener("keyup", function (event) {
            if (event.keyCode == 13) {
                // Hide all form elements
                $(elem).find(".form-switch").each(function () {
                    $(this).css("display", "none");
                });
                // Show all view elements
                $(elem).find(".view-switch").each(function () {
                    $(this).css("display", "");
                });
                // Send actualized data
                send_data(elem, act_vals);
                a = elem;
                event.stopPropagation();
            }
        })
    });
}

function setLstnr() {
    // Setup every 'form-area' to listen for a double click
    $(".form-area").each(function () {
        $(this).dblclick(function () {
            // If no other form changed before or this is the actual element
            if(!form_changed || this == selected_element) {
                selected_element = this;
                setup(this);
            }
        });
    });
}

$(document).ready(function () {
    setLstnr();
});