// Enable to control that only one element can be edited in time
var selected_element;
var form_changed = false;

// Recognize if error occurred to avoid missing a change in datetime-objects
var form_error_edit = false;
// Log if the user is editing an entry in the moment
var is_editing = false;


function send_data(elem, act_vals) {
    // Set the cursor style to 'wait' to indicate the website is loading
    document.body.style.cursor = "wait";
    // Read out all form 'key - value' pairs out of the 'form-horizontal' element in the actual document
    let data_list = $($(".form-horizontal")[0]).serializeArray();

    // Determine edited fields and properties
    let previous_data = {};
    for (let i = 0; i < act_vals.length; i++) {
        previous_data[act_vals[i]["name"]] = act_vals[i]["value"];
    }
    let new_data = {};
    for (let i = 0; i < data_list.length; i++) {
        new_data[data_list[i]["name"]] = data_list[i]["value"];
    }
    let edited_fields= [];
    for (let i = 0; i < act_vals.length; i++) {
        let field_name = act_vals[i]["name"];
        if (!new_data.hasOwnProperty(field_name) || (new_data[field_name] !== act_vals[i]["value"])) {
            edited_fields.push(field_name);
        }
    }
    for (let i = 0; i < data_list.length; i++) {
        let field_name = data_list[i]["name"];
        if (!previous_data.hasOwnProperty(field_name)) {
            edited_fields.push(field_name);
        }
    }
    let edited_properties = []
    for (let i = 0; i < edited_fields.length; i++) {
        let field_name = edited_fields[i];
        let property_name = field_name.split('__').slice(0, -1).join('__');
        if (!edited_properties.includes(property_name)) {
            edited_properties.push(property_name);
        }
    }
    form_changed = edited_properties.length > 0;

    if (!form_changed) {
        is_editing = false;
        document.body.style.cursor = "default";
        return;
    }

    let data = {
        "action_submit": "inline_edit"
    }
    for (let i = 0; i < data_list.length; i++) {
        let key = data_list[i]["name"].replaceAll(/\s/g);
        let value = data_list[i]["value"];
        if (key.endsWith("__units")) {
            value = value.replaceAll(/\s/g, "");
        }
        data[key] = value;
    }

    // POST the data to SampleDB
    $.post(window.location.href.split("?")[0] + "?mode=edit", data, function() {
        // Reload website to show that the change has been successful and to being able to edit the new object
        window.location.reload();
    }).fail(function(response) {
        form_error_edit = true;
        document.body.style = "default";
        is_editing = false;
        let errors = {};
        let has_unexpected_errors = false;
        try {
            errors = JSON.parse(response.responseText)['errors'];
        } catch (e) {
            // SampleDB did not return the expected JSON response containing errors
            has_unexpected_errors = true;
        }
        let error_fields = Object.keys(errors);
        if (error_fields.length === 0) {
            // something broke without reporting errors
            has_unexpected_errors = true;
        }
        for (let i = 0; i < error_fields.length && !has_unexpected_errors; i++) {
            let field_name = error_fields[i];
            let property_name = field_name.split('__').slice(0, -1).join('__');
            if (!edited_properties.includes(property_name)) {
                has_unexpected_errors = true;
                break;
            }
        }
        if (has_unexpected_errors) {
            // show generic error, independent of the changed field
            $('#inline-edit-alert').show();
        } else {
            // display error messages for changed field
            let error_messages = Object.values(errors);
            // remove duplicate error messages
            var seen = {};
            error_messages = error_messages.filter(function(item) {
                return seen.hasOwnProperty(item) ? false : (seen[item] = true);
            });
            $(selected_element).find(".alert-upload-failed").text(error_messages.join(' ')).show();
            $(selected_element).addClass("alert alert-danger");
        }
    });
}


function setup_markdown(elem) {
    $(elem).find('textarea[data-markdown-textarea="true"]').each(function (_, e) {
        if ($(this).attr("markdown-editor-initialized") !== "true") {
            $(this).attr("markdown-editor-initialized", "true");
            setupImageDragAndDrop(initMarkdownField(this, '100px'));
        }
    });

}


function setup(elem) {
    // Save actual value
    let act_vals = $($(".form-horizontal")[0]).serializeArray();
    // Make all form elements visible
    $(elem).find(".form-switch").show();
    // Hide view elements
    $(elem).find(".view-switch").hide();
    setup_markdown(elem);
    // Focus the element to being able directly starting typing
    let focusable_elements = $(elem).find("input[type=text], input[type=textarea], textarea[display!=none]");
    if (focusable_elements.length > 0) {
        focusable_elements[0].focus();
    }

    function event_function(event) {
        if ((event.type == "click" && !elem.contains(event.target) && !event.target.parentElement.classList.contains('tag')) || (event.type == "keyup" && event.keyCode == 13) && !event.target.classList.contains('tt-input')) {
            event.stopPropagation();
            if (document.activeElement.type != "textarea") {
                // Hide all form elements
                $(elem).find(".form-switch").hide();
                // Show all view elements
                $(elem).find(".view-switch").each(function () {
                    $(this).css("display", "");
                });
                // Send actualized data
                send_data(elem, act_vals);
                // Remove event listener to avoid multiple reactions
                this.removeEventListener("click", arguments.callee);
                this.removeEventListener("keyup", arguments.callee);
            }
        }
    }

    // If clicked outside the focussed element
    document.addEventListener("click", event_function);
    // If the user presses enter
    document.addEventListener("keyup", event_function);
}


function setLstnr() {
    // Prevent submitting form
    $("#data-form").submit(function(event) {
        event.preventDefault();
    });
    // Setup every 'form-area' to listen for a double click
    $(".form-area").each(function () {
        $(this).dblclick(function () {
            // If no other form changed before or this is the actual element
            if (!is_editing && (!form_changed || this == selected_element)) {
                is_editing = true;
                selected_element = this;
                setup(this);
            }
        });
        // Set an info element on mouseover
        $(this).mouseover(function () {
            if (!form_error_edit || this == selected_element) {
                $(this).find(".edit-helper").each(function () {
                    $(this).css("visibility", "visible");
                })
            }
        })
        $(this).mouseout(function () {
            $(this).find(".edit-helper").each(function () {
                $(this).css("visibility", "hidden");
            })
        })
        // Set on click listener to every 'edit-helper' to being able to edit using it
        let actual_form_area = this;
        $(this).find(".edit-helper").each(function () {
            this.addEventListener("click", function () {
                if(!is_editing && (!form_changed || actual_form_area == selected_element)) {
                    is_editing = true;
                    selected_element = actual_form_area;
                    setup(actual_form_area);
                }
            });
        })
    });
}


$(document).ready(function () {
    setLstnr();
});
