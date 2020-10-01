$(function() {
  var to_load = $('[data-sampledb-default-selected]');
  if (to_load.length > 0) {
    to_load.prop('disabled', 'true').selectpicker('refresh');
    $.get({
      'url': '/objects/referencable',
      'json': true
    }, function (data) {
      var referencable_objects = data.referencable_objects;
      to_load.each(function (x) {
        var $x = $(this);
        var valid = $x.data('sampledbValidActionIds');

        $x.append(referencable_objects.filter(el => !valid || valid.includes(el.action_id)).map((el) => '<option value="' + el.id + '">' + el.text + '</option>').join(""));
      })

      to_load.selectpicker('refresh').prop("disabled", false).selectpicker('refresh');

      // Try to set the selected value if one is set
      to_load.each(function(x) {
        var $t = $(this);
        var data = $t.data('sampledbDefaultSelected');
        if (data !== 'None')
          $t.selectpicker('val', data);
      });
    });
  }
});
