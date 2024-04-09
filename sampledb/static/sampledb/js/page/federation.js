'use strict';
/* eslint-env jquery */
/* globals vis */

if (window.getTemplateValue('show_add_form')) {
  $(document).ready(function () {
    const addModal = $('#addComponentModal');
    addModal.removeClass('fade');
    addModal.modal('show');
    addModal.addClass('fade');
  });
}
if (window.getTemplateValue('federation_uuid')) {
  $('span.copy-uuid').on('click', function () {
    const button = $(this);
    navigator.clipboard.writeText(button.attr('data-uuid')).then(
      () => {
        const wrapper = button.parent();
        button.tooltip('hide');
        wrapper.tooltip('show');
        setTimeout(function () {
          wrapper.tooltip('hide');
        }, 500);
      }
    );
  });
}
$(function () {
  const addressInput = $('#addComponentAddress');
  const uuidInput = $('#addComponentUUID');
  const nameInput = $('#addComponentName');
  const addressGroup = addressInput.closest('.form-group');
  const uuidGroup = uuidInput.closest('.form-group');
  const nameGroup = nameInput.closest('.form-group');
  addressInput.on('change', function () {
    addressGroup.removeClass('has-error').removeClass('has-success');
    addressGroup.find('.help-block').remove();
    let databaseURL = addressInput.val();
    if (databaseURL) {
      if (!databaseURL.endsWith('/')) {
        databaseURL = databaseURL + '/';
      }
      const statusURL = databaseURL + 'status/';
      $.get(statusURL, function (data) {
        addressGroup.addClass('has-success');
        if (!uuidInput.val() && data.federation_uuid && !nameInput.val() && data.name) {
          uuidInput.val(data.federation_uuid);
          nameInput.val(data.name);
          uuidGroup.removeClass('has-error').addClass('has-success');
          nameGroup.removeClass('has-error').addClass('has-success');
          uuidGroup.find('.help-block').remove();
          nameGroup.find('.help-block').remove();
        }
      });
    }
  });
  uuidInput.on('change', function () {
    uuidGroup.removeClass('has-error').removeClass('has-success');
    uuidGroup.find('.help-block').remove();
  });
  nameInput.on('change', function () {
    nameGroup.removeClass('has-error').removeClass('has-success');
    nameGroup.find('.help-block').remove();
  });
  if (window.getTemplateValue('nodes').length > 0 && window.getTemplateValue('edges').length > 0) {
    // create an array with nodes
    const nodes = new vis.DataSet(
      window.getTemplateValue('nodes')
    );
    // create an array with edges
    const edges = new vis.DataSet(
      window.getTemplateValue('edges')
    );

    // create a network
    const container = document.getElementById('graph');
    const data = {
      nodes,
      edges
    };
    const options = {
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
    window.network = new vis.Network(container, data, options);
  }
});
