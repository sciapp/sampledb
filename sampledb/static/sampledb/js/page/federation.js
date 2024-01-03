if (window.getTemplateValue('show_add_form')) {
  $(document).ready(function () {
    var add_modal = $('#addComponentModal');
    add_modal.removeClass('fade');
    add_modal.modal('show');
    add_modal.addClass('fade');
  });
}
if (window.getTemplateValue('federation_uuid') === null) {
  $('span.copy-uuid').on('click', function () {
    var button = $(this);
    navigator.clipboard.writeText(button.attr('data-uuid')).then(
      () => {
        var wrapper = button.parent();
        button.tooltip('hide');
        wrapper.tooltip('show');
        setTimeout(function () {
          wrapper.tooltip('hide');
        }, 500);
      }
    );
  });
}
$(function() {
  let address_input = $('#addComponentAddress');
  let uuid_input = $('#addComponentUUID');
  let name_input = $('#addComponentName');
  let address_group = address_input.closest('.form-group');
  let uuid_group = uuid_input.closest('.form-group');
  let name_group = name_input.closest('.form-group');
  address_input.on('change', function() {
    address_group.removeClass('has-error').removeClass('has-success');
    address_group.find('.help-block').remove();
    let database_url = address_input.val();
    if (database_url) {
      if (!database_url.endsWith('/')) {
        database_url = database_url + '/'
      }
      let status_url = database_url + 'status/';
      $.get(status_url, function(data) {
        address_group.addClass('has-success');
        if (!uuid_input.val() && data.federation_uuid && !name_input.val() && data.name) {
          uuid_input.val(data.federation_uuid);
          name_input.val(data.name);
          uuid_group.removeClass('has-error').addClass('has-success');
          name_group.removeClass('has-error').addClass('has-success');
          uuid_group.find('.help-block').remove();
          name_group.find('.help-block').remove();
        }
      });
    }
  });
  uuid_input.on('change', function() {
    uuid_group.removeClass('has-error').removeClass('has-success');
    uuid_group.find('.help-block').remove();
  });
  name_input.on('change', function() {
    name_group.removeClass('has-error').removeClass('has-success');
    name_group.find('.help-block').remove();
  });
  if (window.getTemplateValue('nodes').length > 0 && window.getTemplateValue('edges').length > 0) {
    // create an array with nodes
    let nodes = new vis.DataSet(
      window.getTemplateValue('nodes')
    );
    // create an array with edges
    let edges = new vis.DataSet(
      window.getTemplateValue('edges')
    );

    // create a network
    let container = document.getElementById("graph");
    let data = {
      nodes: nodes,
      edges: edges
    };
    let options = {
      layout: {
        randomSeed: 9 // prevent the graph from being random
      },
      interaction: {
        zoomView: false,
        dragView: false,
        dragNodes: false,
        selectable: false,
        tooltipDelay: 0
      },
      nodes: {
        shape: 'box',
        color: {
          background: '#ffffff',
          border: '#222222'
        }
      },
      edges: {
        arrowStrikethrough: false,
        arrows: {
          to: {
            scaleFactor: 0.25
          },
          from: {
            scaleFactor: 0.25
          }
        }
      }
    };
    let network = new vis.Network(container, data, options);
  }
});
