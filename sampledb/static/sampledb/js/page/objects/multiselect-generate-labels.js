'use strict';
/* eslint-env jquery */

import './multiselect-base.js';

$(function () {
  window.checkSubmittableImpl = function (submitTooltip, submitButton) {
    const PAGE_SIZES = window.getTemplateValue('page_sizes');

    const labelVariant = $('#select-label-variant').val();
    const form = $('form#generate-labels-form');
    let submittable = true;
    const shortform = {
      'mixed-formats': 'mf',
      'fixed-width': 'fw',
      'minimal-height': 'mh'
    }[labelVariant];

    const paperSizeSelect = $(`#select-${shortform}-paper-size`);
    const labelsPerObjectInput = $(`#input-${shortform}-labels-per-object`);

    form.find('.has-error').removeClass('has-error');
    form.find('.generate-labels-helper').text('');

    const paperFormat = paperSizeSelect.val();
    const maximumWidth = Math.floor(PAGE_SIZES[paperFormat][0] - window.getTemplateValue('horizontal_label_margin') * 2);
    const maximumHeight = Math.floor(PAGE_SIZES[paperFormat][1] - window.getTemplateValue('vertical_label_margin') * 2);

    if (!Object.prototype.hasOwnProperty.call(PAGE_SIZES, paperFormat)) {
      paperSizeSelect.parent().addClass('has-error');
      $(`#input-${shortform}-paper-size-helper`).text(window.getTemplateValue('translations.select_a_paper_format'));
      submittable = false;
    }

    if (isNaN(labelsPerObjectInput.val()) || labelsPerObjectInput.val().trim() === '' || labelsPerObjectInput.val() <= 0) {
      labelsPerObjectInput.parent().addClass('has-error');
      submittable = false;
      $(`#input-${shortform}-labels-per-object-helper`).text(window.getTemplateValue('translations.quantity_must_be_greater_than_0'));
    }

    if (labelVariant === 'fixed-width') {
      const labelWidthInput = $('#input-fw-label-width');
      const minLabelHeightInput = $('#input-fw-label-min-height');
      const labelWidthMin = $(`input[name=${window.getTemplateValue('generate_labels_form.center_qr_ghs.name')}]`).is(':checked') ? 40 : 20;

      if (isNaN(labelWidthInput.val()) || labelWidthInput.val() < labelWidthMin || labelWidthInput.val() > maximumWidth) {
        labelWidthInput.parent().addClass('has-error');
        submittable = false;
        $('#input-fw-label-width-helper').text(window.getTemplateValue('translations.width_must_be_between_min_and_max').replace('{minWidth}', labelWidthMin).replace('{maxWidth}', maximumWidth));
      }

      if (minLabelHeightInput.val().trim() === '' || minLabelHeightInput.val() < 0 || minLabelHeightInput.val() > maximumHeight) {
        minLabelHeightInput.parent().addClass('has-error');
        submittable = false;
        $('#input-fw-min-label-height-helper').text(window.getTemplateValue('translations.minimum_height_must_be_between_0_and_placeholder').replace('{maxHeight}', maximumHeight));
      }
    } else if (labelVariant === 'minimal-height') {
      const labelMinWidthInput = $('#input-mh-min-label-width');

      if (isNaN(labelMinWidthInput.val()) || labelMinWidthInput.val().trim() === '' || labelMinWidthInput.val() < 0) {
        labelMinWidthInput.parent().addClass('has-error');
        submittable = false;
        $('#input-mh-min-label-width-helper').text(window.getTemplateValue('translations.minimum_width_must_be_greater_or_equal_to_0'));
      }
    }

    if (!submittable) {
      submitTooltip.attr('data-original-title', window.getTemplateValue('translations.you_have_unallowed_values_in_red_marked_fields')).tooltip('setContent').tooltip('enable');
      submitButton.prop('disabled', true);
      return false;
    }
    return true;
  };

  $('#select-label-variant').on('change', function () {
    const selectedVariant = $(this).val();
    for (const variant of ['mixed-formats', 'fixed-width', 'minimal-height']) {
      const isSelectedVariant = selectedVariant === variant;
      const form = $(`#form-${variant}`);
      form.find('input').attr('disabled', !isSelectedVariant);
      form.find('.selectpicker').attr('disabled', !isSelectedVariant);
      form.toggleClass('multiselect-form-disabled', !isSelectedVariant);
    }
    $('.selectpicker').selectpicker('refresh');
  });
});
