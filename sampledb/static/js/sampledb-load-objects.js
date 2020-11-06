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
        var valid = $x.data('sampledbValidActionIds');
        var required_perm = $x.data('sampledbRequiredPerm') || 1;
        var remove_id = $x.data('sampledbRemove');

        var to_add = referencable_objects
          .filter(function (el) {
            return el.max_permission >= required_perm && el.id != remove_id;
          }).filter(function (el) {
            return !valid || valid.includes(el.action_id);
          });
        $x.append(
          to_add.map(function (el) {
              return '<option value="' + el.id + '">' + el.text + '</option>';
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
        if (data !== 'None')
          $x.selectpicker('val', data);
      });
    });
  }
});
