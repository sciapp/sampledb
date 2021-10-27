$(function() {
  var to_load = $('[data-sampledb-default-selected], [data-sampledb-remove]');
  if (to_load.length > 0) {
    to_load.prop('disabled', 'true').selectpicker('refresh');
    var perm_lowest = 4;
    to_load.each(function (x) {
      var $x = $(this);
      var perm = $x.data('sampledbRequiredPerm') || 1;
      perm_lowest = perm_lowest < perm ? perm_lowest : perm;

      $($x.data('sampledbStartEnable')).prop('disabled', false);
      $($x.data('sampledbStartDisable')).prop('disabled', true);
      $($x.data('sampledbStartShow')).show();
      $($x.data('sampledbStartHide')).hide();
    });
    var data = {
      'required_perm': perm_lowest
    };

    $.get({
      'url': window.application_root_path + 'objects/referencable',
      'data': data,
      'json': true
    }, function (data) {
      var referencable_objects = data.referencable_objects;
      to_load.each(function (x) {
        var $x = $(this);
        var action_ids = $x.data('sampledbValidActionIds');
        if (typeof action_ids === 'string') {
          action_ids = action_ids.split(",").filter(function(action_id) {
            return action_id !== "";
          });
          action_ids = $.map(action_ids, function(action_id){
             return +action_id;
          });
        } else if (Array.isArray(action_ids)) {
          action_ids = action_ids.filter(function(action_id) {
            return action_id !== "";
          });
          action_ids = $.map(action_ids, function(action_id){
             return +action_id;
          });
        } else if (typeof action_ids === 'undefined') {
          action_ids = [];
        } else {
          action_ids = [action_ids];
        }
        var required_perm = $x.data('sampledbRequiredPerm') || 1;
        var remove_ids = $x.data('sampledbRemove');
        if (typeof remove_ids === 'string') {
          remove_ids = $.map(remove_ids.split(","), function(id){
             return +id;
          });
        } else if (Array.isArray(remove_ids)) {
          remove_ids = remove_ids.filter(function(id) {
            return id !== "";
          });
          remove_ids = $.map(remove_ids, function(id){
             return +id;
          });
        } else if (typeof remove_ids === 'undefined') {
          remove_ids = [];
        } else {
          remove_ids = [remove_ids];
        }

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

        $x.selectpicker('refresh').prop("disabled", false).selectpicker('refresh');

        function refreshIfSame (x2) {
          if (x2 === x)
            $x.selectpicker('refresh');
        }

        $($x.data('sampledbStopEnable')).prop('disabled', false).each(refreshIfSame);
        $($x.data('sampledbStopDisable')).prop('disabled', true).each(refreshIfSame);
        $($x.data('sampledbStopShow')).show();
        $($x.data('sampledbStopHide')).hide();
        if (to_add.length != 0) {
          $($x.data('sampledbNonemptyEnable')).prop('disabled', false).each(refreshIfSame);
          $($x.data('sampledbNonemptyDisable')).prop('disabled', true).each(refreshIfSame);
          $($x.data('sampledbNonemptyShow')).show();
          $($x.data('sampledbNonemptyHide')).hide();
        } else {
          $($x.data('sampledbEmptyEnable')).prop('disabled', false).each(refreshIfSame);
          $($x.data('sampledbEmptyDisable')).prop('disabled', true).each(refreshIfSame);
          $($x.data('sampledbEmptyShow')).show();
          $($x.data('sampledbEmptyHide')).hide();
        }

        var data = $x.data('sampledbDefaultSelected');
        if (data !== 'None') {
          $x.selectpicker('val', data);
          $x.selectpicker('refresh');
        }
      });
    });
  }
});
