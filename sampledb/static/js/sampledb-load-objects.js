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
    to_load.prop('disabled', 'true').selectpicker('refresh');
    var perm_lowest = 4;
    let action_ids_helper = {};
    to_load.each(function (x) {
      let $x = $(this);
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
        var action_ids = idsToArray($x.data('sampledbValidActionIds'));
        var required_perm = $x.data('sampledbRequiredPerm') || 1;
        var remove_ids = idsToArray($x.data('sampledbRemove'));
        var to_add = referencable_objects
          .filter(function (el) {
            return el.max_permission >= required_perm && $.inArray(el.id, remove_ids) === -1;
          }).filter(function (el) {
            return action_ids.length === 0 || $.inArray(el.action_id, action_ids) !== -1;
          });
        $x.find( 'option[value != ""]' ).remove();
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
              return '<option value="' + el.id + '" '+ data_tokens + ' data-action-id="' + el.action_id + '">' + el.text + '</option>';
            }).join(""));

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
          $x.selectpicker('val', data);
        } else {
          $x.selectpicker('val', null);
        }
      });
    });
  }
});
