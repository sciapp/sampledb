function send_data(elem, act_val) {
    let data_list = $($(".form-horizontal")[0]).serializeArray();


    console.log(data_list);
    let found = false;
    if(data_list.length != act_val.length) {
        found = true;
    } else {
        for (let i = 0; i < Math.min(data_list.length, act_val.length); i++) {
            if (data_list[i]["name"] != act_val[i]["name"] || data_list[i]["value"] != act_val[i]["value"]) {
                found = true;
                break;
            }
        }
    }
    if(!found) {
        return;
    }
    let data_string = "";

    for (let i = 0; i < data_list.length; i++) {
        let name = data_list[i]["name"].replaceAll(/\s/g);
        let value = (name.endsWith("__units")) ? data_list[i]["value"].replaceAll(/\s/g, "") : data_list[i]["value"];
        data_string += name + "=" + value + "&";
    }
    data_string += "action_submit="
    data_string = encodeURI(data_string);

    let xml_request = new XMLHttpRequest();

    xml_request.addEventListener("load", function () {
        let res_html = ($.parseHTML(xml_request.responseText));
        for (let i = 0; i < res_html.length; i++) {
            if ($(res_html[i]).attr("id") == "main") {
                let main_html = $(res_html[i])
                if (main_html.find(".form-horizontal[method=post]").length > 0) {
                    $(elem).find(".alert-upload-failed").each(function () {
                        $(this).css("display", "block");
                    });
                    $(elem).addClass("alert alert-danger");
                } else {
                    window.location.reload();
                }
            }
        }
    });

    xml_request.open("POST", window.location.href.split("?")[0] + "?mode=edit");

    xml_request.setRequestHeader("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8");
    xml_request.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

    xml_request.send(data_string);
}

function setup(elem) {
    // Save actual value
    let act_val = $($(".form-horizontal")[0]).serializeArray();
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
            console.log("abc");
            // Hide all form elements
            $(elem).find(".form-switch").each(function () {
                $(this).css("display", "none");
            });
            // Show all view elements
            $(elem).find(".view-switch").each(function () {
                $(this).css("display", "");
            });
            // Send actualized data
            let res = send_data(elem, act_val);
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
                let res = send_data(elem, act_val);
                event.stopPropagation();
            }
        })
    });
}

function setLstnr() {
    $(".form-area").each(function () {
        $(this).dblclick(function () {
            setup(this);
        });
    });
}

$(document).ready(function () {
    setLstnr();
});