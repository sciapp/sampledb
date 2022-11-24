window.objectpicker_datasets = {};

$(function() {
  function idsToArray(ids) {
    if (typeof ids === 'string') {
      ids = ids.split(",").filter(function(id) {
        return id !== "";
      });
      ids = $.map(ids, function(id){
         return +id;
      });
    } else if (Array.isArray(ids)) {
      ids = ids.filter(function(id) {
        return id !== "";
      });
      ids = $.map(ids, function(id){
         return +id;
      });
    } else if (typeof ids === 'undefined') {
      ids = [];
    } else {
      ids = [ids];
    }
    return ids;
  }

  var to_load = $('[data-sampledb-default-selected], [data-sampledb-remove]');
  if (to_load.length > 0) {
    to_load.prop('disabled', 'true');
    var perm_lowest = 4;
    let action_ids_helper = {};
    to_load.each(function () {
      let $x = $(this);
      if ($x.prop("tagName") === 'SELECT') {
        $x.selectpicker('refresh');
      }
      let perm = $x.data('sampledbRequiredPerm') || 1;
      perm_lowest = perm_lowest < perm ? perm_lowest : perm;
      let valid_action_ids = idsToArray($x.data('sampledbValidActionIds'));
      if (valid_action_ids.length > 0) {
        for (let i = 0; i < valid_action_ids.length; i++) {
            action_ids_helper[valid_action_ids[i]] = true;
        }
      } else {
        action_ids_helper[-1] = true;
      }

      $($x.data('sampledbStartEnable')).prop('disabled', false);
      $($x.data('sampledbStartDisable')).prop('disabled', true);
      $($x.data('sampledbStartShow')).show();
      $($x.data('sampledbStartHide')).hide();
    });

    let action_ids = [];
    for (let action_id in action_ids_helper) {
        action_ids.push(Number.parseInt(action_id));
    }
    var data = {
      'required_perm': perm_lowest,
      'action_ids': JSON.stringify(action_ids)
    };

    $.get({
      'url': window.application_root_path + 'objects/referencable',
      'data': data,
      'json': true
    }, function (data) {
      var referencable_objects = data.referencable_objects;
      to_load.each(function (x) {
        var $x = $(this);
        let is_selectpicker = ($x.prop("tagName") === 'SELECT');
        var action_ids = idsToArray($x.data('sampledbValidActionIds'));
        var required_perm = $x.data('sampledbRequiredPerm') || 1;
        var remove_ids = idsToArray($x.data('sampledbRemove'));
        var to_add = referencable_objects
          .filter(function (el) {
            return el.max_permission >= required_perm && $.inArray(el.id, remove_ids) === -1;
          }).filter(function (el) {
            return action_ids.length === 0 || $.inArray(el.action_id, action_ids) !== -1;
          });
        if (is_selectpicker) {
          $x.find('option[value != ""]').remove();
          $x.append(
            to_add.map(function (el) {
              var data_tokens = "";
              if (el.tags.length) {
                data_tokens = 'data-tokens="';
                for (var i = 0; i < el.tags.length; i++) {
                  data_tokens += '#' + el.tags[i] + ' ';
                }
                data_tokens += el.text + '"';
              }
              var is_fed = ' ';
              if (el.is_fed) {
                is_fed = ' data-icon="fa fa-share-alt" ';
              }
              return '<option' + is_fed + 'value="' + el.id + '" '+ data_tokens + ' data-action-id="' + el.action_id + '">' + el.text + '</option>';
            }).join(""));
        } else {
          $x.typeahead("destroy");
          let bloodhound = new Bloodhound({
            datumTokenizer: function (item) {
              let tokens = new Set([]);
              Bloodhound.tokenizers.whitespace(item.unescaped_text).forEach(function(token) {
                tokens.add(token);
                // search by substrings (except for ID)
                if (token !== '(#' + item.id + ')') {
                  for (let i = 1; i < token.length - 1; i++) {
                    tokens.add(token.substring(i, token.length));
                  }
                }
              });
              // search by ID
              tokens.add('#' + item.id);
              tokens.add('' + item.id);
              // search tags
              tokens.add.apply(tokens, item.tags);
              return Array.from(tokens);
            },
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            local: to_add,
            identify: function(item) { return item.unescaped_text; },
          });
          function source(q, sync) {
            function syncWrap(results) {
              $x.num_results = results.length;
              if (!$x.prop('required')) {
                // add placeholder for not selecting an object
                results.unshift({
                  text: null,
                  is_fed: false
                });
              }
              sync(results);
            }
            if (q === '') {
              syncWrap(bloodhound.all()); // This is the only change needed to get 'ALL' items as the defaults
            } else {
              bloodhound.search(q, syncWrap);
            }
          }
          let dataset = {
            name: 'object_picker',
            source: source,
            limit: ((window.object_picker_limit === null || window.object_picker_limit < 1) ? 'Infinity' : window.object_picker_limit + (!$x.prop('required') ? 1 : 0)),
            display: function (item) {
              return item.unescaped_text;
            },
            templates: {
              suggestion: function(data) {
                if (data.text === null) {
                  return '<div>—</div>';
                }
                if (data.is_fed) {
                  return '<div><i class="fa fa-share-alt fa-fw" style="margin-left: -1.43571429em; margin-right:0.15em;"></i>' + data.text + '</div>';
                } else {
                  return '<div>' + data.text + '</div>';
                }
              },
              header: function (context) {
                let num_results_total = $x.num_results;
                let num_results_shown = context.suggestions.length;
                let query = $x.typeahead('val');
                if (!$x.prop('required')) {
                  // the placeholder for not selecting an object does not count
                  num_results_shown -= 1;
                }
                let header_text_template = "";
                if (num_results_shown === 0) {
                  if (query === "") {
                    header_text_template = window.object_picker_no_results_text_template_no_query;
                  } else {
                    header_text_template = window.object_picker_no_results_text_template;
                  }
                } else if (num_results_shown === num_results_total) {
                  if (query === "") {
                    header_text_template = window.object_picker_all_results_text_template_no_query;
                  } else {
                    header_text_template = window.object_picker_all_results_text_template;
                  }
                } else {
                  if (query === "") {
                    header_text_template = window.object_picker_some_results_text_template_no_query;
                  } else {
                    header_text_template = window.object_picker_some_results_text_template;
                  }
                }
                let header_text = header_text_template.replace('PLACEHOLDER1', num_results_shown).replace('PLACEHOLDER2', num_results_total)
                let header = $('<div class="tt-header">' + header_text + '</div>');
                header.find('.query-container').text(query);
                return header;
              },
              empty: function (context) {
                let query = $x.typeahead('val');
                let empty_text_template = "";
                if (query === "") {
                  empty_text_template = window.object_picker_no_results_text_template_no_query;
                } else {
                  empty_text_template = window.object_picker_no_results_text_template;
                }
                let empty_text = empty_text_template;
                let empty = $('<div class="tt-header">' + empty_text + '</div>');
                empty.find('.query-container').text(query);
                return empty;
              }
            }
          }
          window.objectpicker_datasets[$x.closest('.objectpicker-container').find('input[type=hidden]')[0].name] = dataset;
          $x.typeahead(
            {
              hint: true,
              highlight: true,
              minLength: 0
            },
            dataset
          );
          function change_handler() {
            $x.blur();
            let field = $(this);
            let text = $(this).typeahead('val');
            let is_valid = false;
            let object_id = null;
            if (text) {
              for (let i = 0; i < to_add.length && !is_valid; i++) {
                if (to_add[i].unescaped_text === text) {
                  object_id = to_add[i].id;
                  is_valid = true;
                }
              }
            } else if (!field.prop('required')) {
              is_valid = true;
              object_id = '';
            }
            let form_group = field.closest('.form-group')
            if (is_valid) {
              this.setCustomValidity('');
              form_group.removeClass('has-error');
              form_group.find('.help-block').text('');
              field.closest('.objectpicker-container').find('input[type="hidden"]').val(object_id);
            } else {
              this.setCustomValidity(window.object_picker_select_text);
              form_group.addClass('has-error');
              form_group.find('.help-block').text('').first().text(window.object_picker_select_text);
              field.closest('.objectpicker-container').find('input[type="hidden"]').val('');
            }
          }
          $x.on('typeahead:selected', change_handler);
          $x.on('change', change_handler);
        }

        $x.prop("disabled", false);

        $($x.data('sampledbStopEnable')).prop('disabled', false);
        $($x.data('sampledbStopDisable')).prop('disabled', true);
        $($x.data('sampledbStopShow')).show();
        $($x.data('sampledbStopHide')).hide();
        if (to_add.length !== 0) {
          $($x.data('sampledbNonemptyEnable')).prop('disabled', false);
          $($x.data('sampledbNonemptyDisable')).prop('disabled', true);
          $($x.data('sampledbNonemptyShow')).show();
          $($x.data('sampledbNonemptyHide')).hide();
        } else {
          $($x.data('sampledbEmptyEnable')).prop('disabled', false);
          $($x.data('sampledbEmptyDisable')).prop('disabled', true);
          $($x.data('sampledbEmptyShow')).show();
          $($x.data('sampledbEmptyHide')).hide();
        }

        $x.selectpicker('refresh');
        var data = $x.data('sampledbDefaultSelected');
        if (typeof(data) !== 'undefined' && data !== 'None') {
          if (is_selectpicker) {
            $x.selectpicker('val', data);
          } else {
            for (let i = 0; i < to_add.length; i++) {
              if (to_add[i].id === data) {
                $x.typeahead('val', to_add[i].unescaped_text);
                break;
              }
            }
          }
        } else {
          if (is_selectpicker) {
            $x.selectpicker('val', null);
          } else {
            $x.typeahead('val', '');
          }
        }
      });
    });
  }
});

function objectpicker_show_all(button, event) {
  let objectpicker_container = $(button).closest('.objectpicker-container');
  let objectpicker = objectpicker_container.find('.typeahead.tt-input');
  let name = objectpicker_container.find('input[type=hidden]')[0].name;
  let dataset = window.objectpicker_datasets[name];
  dataset["limit"] = 'Infinity';
  objectpicker.typeahead('destroy');
  objectpicker.typeahead(
    {
      hint: true,
      highlight: true,
      minLength: 0
    },
    dataset
  );
  objectpicker.focus();
  event.preventDefault();
  event.stopPropagation();
}

function objectpicker_clear(button, event) {
  let objectpicker_container = $(button).closest('.objectpicker-container');
  let objectpicker = objectpicker_container.find('.typeahead.tt-input');
  objectpicker.typeahead('val', '');
  event.preventDefault();
  event.stopPropagation();
}
