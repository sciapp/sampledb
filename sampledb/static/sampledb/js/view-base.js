'use strict';
/* eslint-env jquery */
/* globals Cookies */

window.object_location_translations = {
  en: ''
};
$(function () {
  window.languages = window.getTemplateValue('languages');

  function updateObjectLocationTranslationJSON () {
    const translationJson = JSON.stringify(window.object_location_translations);
    $('#input-object_location-translations').val(translationJson);
  }

  $('form#assign-location-form').on('submit', function () {
    const responsibleUserID = $('.selectpicker#input-responsible-user').val();
    const locationID = $('.selectpicker#input-location').val();
    if (responsibleUserID === '-1' && locationID === '-1') {
      $('#object_location-help-block').html(window.getTemplateValue('translations.select_responsible_user_or_location'));
    } else {
      $('#object_location-help-block').html('');
    }
    return (responsibleUserID !== '-1' || locationID !== '-1');
  });

  $('#select-language-object_location').on('change', function () {
    const existingLanguages = [];
    $.each(window.object_location_translations, function (key, value) {
      existingLanguages.push(key);
    });
    let selected = ['en'];
    const inputDescriptions = $('[data-name="input-descriptions"]');
    selected = selected.concat($(this).val());
    const languagesToRemove = existingLanguages.filter(n => !selected.includes(n));
    const languagesToAdd = selected.filter(n => !existingLanguages.includes(n));
    for (const languageToDelete of languagesToRemove) {
      const temp = $('#input-group-object_location-' + languageToDelete);
      $.each(window.object_location_translations, function (key, value) {
        if (key === languageToDelete) { delete window.object_location_translations[key]; }
      });
      $(temp).remove();
      updateObjectLocationTranslationJSON();
    }
    for (const newLanguage of selected) {
      if (!$('#input-group-object_location-' + newLanguage).length) {
        $($('#object_location-template').html()).insertAfter(inputDescriptions.children().last());
        const temp = inputDescriptions.children().last();
        const languageName = window.languages.find(lang => lang.lang_code === newLanguage).name;
        $(temp).children().first().attr('id', 'textarea-object_location' + newLanguage.toString());

        $(temp).attr('id', 'input-group-object_location-' + newLanguage);
        $(temp).attr('data-name', 'input-group-object_location');
        $(temp).children('.input-group-addon[data-name="language"]').text(languageName);
        $(temp).attr('data-language', newLanguage);

        $(temp).change(function () {
          const language = $(this).attr('data-language');
          const translationText = $(this).find('textarea').val();
          window.object_location_translations[language] = translationText;
          updateObjectLocationTranslationJSON();
        });
        $(temp).find('textarea').change();
      }
      if (languagesToAdd.includes(newLanguage)) {
        window.object_location_translations[newLanguage] = '';
      }
      updateObjectLocationTranslationJSON();
    }
  });

  $('#input-group-object_location-en').change(function () {
    const language = $(this).attr('data-language');
    const translationText = $(this).find('textarea').val();
    window.object_location_translations[language] = translationText;
    updateObjectLocationTranslationJSON();
  });
  $('#input-group-object_location-en').change();

  if (window.getTemplateValue('template_mode') === 'view') {
    $('.input-group.date').each(function () {
      $(this).datetimepicker({
        locale: window.getTemplateValue('current_user.language.lang_code'),
        format: 'YYYY-MM-DD HH:mm:ss',
        date: $(this).attr('data-datetime')
      });
    });
  }
  $('.nav-tabs a').click(function (e) {
    e.preventDefault();
    $(this).tab('show');
  });
  if (!window.getTemplateValue('is_archived') && window.getTemplateValue('user_may_comment')) {
    const commentForm = $('#new-comment-form');
    const commentTextarea = commentForm.find('textarea');
    commentTextarea.on('input change propertychange', function () {
      commentTextarea.closest('.form-group').removeClass('has-error');
    });
    commentForm.on('submit', function () {
      if (commentTextarea.val() === '') {
        commentTextarea.closest('.form-group').addClass('has-error');
        commentTextarea.focus();
        return false;
      }
      return true;
    });
  }
  $(function () {
    $('[data-toggle="popover"]').popover();
  });
  if (window.getTemplateValue('has_object_log_entries')) {
    const activityLogFilterTypeDict = window.getTemplateValue('activity_log_filter_type_dict');
    window.activity_log_apply_filters = function () {
      window.activity_log_apply_filter('versions');
      window.activity_log_apply_filter('measurements');
      window.activity_log_apply_filter('comments');
      window.activity_log_apply_filter('files');
      window.activity_log_apply_filter('locations');
      window.activity_log_apply_filter('references');
      window.activity_log_apply_filter('other');
      const activityLog = $('#activity_log_table > tbody');
      const showAll = $('#activity_log_show_all_toggle').prop('checked');
      const visibleActivityLogEntries = activityLog.find('tr:visible');
      $('#activity_log_counter').html('' + visibleActivityLogEntries.length + '&thinsp;/&thinsp;' + activityLog.find('tr').length);
      if (!showAll && visibleActivityLogEntries.length > 15) {
        visibleActivityLogEntries.slice(15).css({ display: 'none' });
        $('#activity_log_show_all_wrapper').show();
      } else {
        $('#activity_log_show_all_wrapper').hide();
      }
    };
    window.activity_log_apply_filter = function (category) {
      const typeList = activityLogFilterTypeDict[category];
      const activityLog = $('#activity_log_table > tbody');
      typeList.forEach(function (activityLogType) {
        const activityLogRows = activityLog.find('tr[data-activity-log-type=' + activityLogType + ']');
        if (window.activity_log_toggle.current_state[category]) {
          activityLogRows.css({ display: 'table-row' });
        } else {
          activityLogRows.css({ display: 'none' });
        }
      });
    };
    window.activity_log_toggle = function (shouldShow, category) {
      window.activity_log_toggle.current_state[category] = shouldShow;
      Cookies.set('SAMPLEDB_ACTIVITY_LOG_FILTER_STATE', JSON.stringify(window.activity_log_toggle.current_state), { sameSite: 'Lax' });
    };
    window.activity_log_toggle.current_state = {};
    let activityLogFilterState;
    try {
      activityLogFilterState = JSON.parse(Cookies.get('SAMPLEDB_ACTIVITY_LOG_FILTER_STATE'));
    } catch (e) {
      // ignore invalid cookies
    }
    if (activityLogFilterState === undefined) {
      activityLogFilterState = {
        versions: true,
        measurements: true,
        comments: true,
        files: true,
        locations: true,
        references: true,
        other: true
      };
      Cookies.set('SAMPLEDB_ACTIVITY_LOG_FILTER_STATE', JSON.stringify(activityLogFilterState), { sameSite: 'Lax' });
    }
    $('#activity_log_show_all_toggle').on('change', function () {
      window.activity_log_apply_filters();
    });
    window.activity_log_toggle(activityLogFilterState.versions, 'versions');
    window.activity_log_toggle(activityLogFilterState.measurements, 'measurements');
    window.activity_log_toggle(activityLogFilterState.comments, 'comments');
    window.activity_log_toggle(activityLogFilterState.files, 'files');
    window.activity_log_toggle(activityLogFilterState.locations, 'locations');
    window.activity_log_toggle(activityLogFilterState.references, 'references');
    window.activity_log_toggle(activityLogFilterState.other, 'other');
    window.activity_log_apply_filters();

    $('#activity_log_counter').closest('button').on('inserted.bs.popover', function () {
      for (const filterType of ['versions', 'measurements', 'comments', 'files', 'locations', 'references', 'other']) {
        const filterToggle = $(`#activity_log_filter_${filterType}`);
        filterToggle.prop('checked', window.activity_log_toggle.current_state[filterType]);
        filterToggle.on('click', function () {
          window.activity_log_toggle($(this).prop('checked'), filterType);
          window.activity_log_apply_filters();
        });
      }
    });
  }
  if (!window.getTemplateValue('is_archived')) {
    if (window.getTemplateValue('files_enabled')) {
      window.file_table_toggle = function (shouldShow, category) {
        const fileTable = $('#file_table').find('> tbody');
        const fileTableRows = fileTable.find('tr[data-file-type=' + category + ']');
        if (shouldShow) {
          fileTableRows.css({ display: 'table-row' });
        } else {
          fileTableRows.css({ display: 'none' });
        }
        $('#file_table_counter').html('' + fileTable.find('tr:visible').length + '&thinsp;/&thinsp;' + fileTable.find('tr').length);
        window.file_table_toggle.current_state[category] = shouldShow;
        Cookies.set('SAMPLEDB_FILE_TABLE_FILTER_STATE', JSON.stringify(window.file_table_toggle.current_state), { sameSite: 'Lax' });
      };
      window.file_table_toggle.current_state = {};
      let fileTableFilterState;
      try {
        fileTableFilterState = JSON.parse(Cookies.get('SAMPLEDB_FILE_TABLE_FILTER_STATE'));
      } catch (e) {
        // ignore invalid cookies
      }
      if (fileTableFilterState === undefined) {
        fileTableFilterState = {
          notebooks: true,
          other: true
        };
        Cookies.set('SAMPLEDB_FILE_TABLE_FILTER_STATE', JSON.stringify(fileTableFilterState), { sameSite: 'Lax' });
      }
      window.file_table_toggle(fileTableFilterState.notebooks, 'notebooks');
      window.file_table_toggle(fileTableFilterState.other, 'other');
      window.update_file_table_filter_states = function () {
        if (window.file_table_toggle.current_state.notebooks) {
          $('#file_table_filter_notebooks').attr('checked', 'checked');
        }
        if (window.file_table_toggle.current_state.other) {
          $('#file_table_filter_other').attr('checked', 'checked');
        }
      };
    }
    $('#button-show-mobile-file-upload-modal').click(function () {
      $('#mobileFileLinkModal').modal('show');
    });
    $('#button-show-object-qrcode-modal').click(function () {
      $('#mobileObjectLinkModal').modal('show');
    });
    $('#button-show-object-label-modal').click(function () {
      $('#objectLabelModal').modal('show');
    });

    $('.button-workflow-view-modal').on('click', function () {
      const workflowView = $(this).attr('data-workflow_view');
      $('#workflowModal-' + workflowView).modal('show');
    });
    if (window.getTemplateValue('files_enabled')) {
      const changeHandler = function () {
        const files = $('#input-file-upload').get(0).files;
        if (files.length === 0) {
          $('#input-file-text').val('');
          $('#button-upload-files').addClass('disabled');
          $('#button-upload-files').prop('disabled', true);
        } else if (files.length === 1) {
          $('#input-file-text').val(files[0].name);
          $('#button-upload-files').removeClass('disabled');
          $('#button-upload-files').prop('disabled', false);
        } else {
          $('#input-file-text').val(files.length + ' ' + window.getTemplateValue('translations.files_selected'));
          $('#button-upload-files').removeClass('disabled');
          $('#button-upload-files').prop('disabled', false);
        }
        $('#input-file-names-hidden').val('');
        $('#input-file-source-hidden').val('local');
      };
      if (window.getTemplateValue('user_may_upload_files')) {
        $('#input-file-upload').on('change', changeHandler);
        const dropHandler = function (e) {
          e.preventDefault();
          $('#input-file-upload')[0].files = e.dataTransfer.files;
          changeHandler();
        };
        const dragOverHandler = function (e) {
          e.preventDefault();
        };
        const uploadArea = $('#upload-area')[0];
        uploadArea.ondrop = dropHandler;
        uploadArea.ondragover = dragOverHandler;
      }
    }
  }

  if (window.getTemplateValue('files_enabled')) {
    $('.button-file-info').on('click', function () {
      const fileID = $(this).attr('data-file_id');
      $('#fileInfoModal-' + fileID).modal('show');
    });
    $('.file-info-hide').hide();
    $('.file-info-edit-mode').hide();
    $('.file-info-view-mode').show();
    $('.file-url-error').hide();
    $('.button-file-info-edit').on('click', function () {
      $('.input-file-info-title', '.input-file-info-url', '.input-file-info-description').each(function () {
        $(this).attr('data-value', $(this).val());
      });
      $('.file-info-edit-mode').show();
      $('.file-info-view-mode').hide();
    });
    $('.button-file-info-cancel').on('click', function () {
      $('.file-info-edit-mode').hide();
      $('.file-info-view-mode').show();
      $('.file-url-error').hide();
      $('.input-file-info-title', '.input-file-info-url', '.input-file-info-description').each(function () {
        $(this).val($(this).attr('data-value'));
      });
    });
    $('.button-file-info-hide-cancel').on('click', function () {
      $('.file-info-main').show();
      $('.file-info-hide').hide();
    });
    $('.button-file-info-hide').on('click', function () {
      $('.file-info-main').hide();
      $('.file-info-hide').show();
    });
    $('.modal-file-info').on('hidden.bs.modal', function (e) {
      $('.file-info-hide').hide();
      $('.file-info-main').show();
    });
    const fileID = window.getTemplateValue('edit_external_link_file');
    if (fileID >= 0) {
      $('.file-info-edit-mode').show();
      $('.file-info-view-mode').hide();
      $('#fileInfoModal-' + fileID).modal('show');
      $('#file-url-error-' + fileID + ' > span:first-of-type').text(window.getTemplateValue('external_link_error'));
      $('#file-url-error-' + fileID).show();
    }
  }
  if (window.getTemplateValue('has_related_objects_tree')) {
    $('input[name^=data_export_object_]').prop('checked', false);
    $('input.data_export_object').prop('checked', false);
    $(`input.data_export_object_${window.getTemplateValue('object_id')}`).prop('checked', true);
  }
  function updateDataExportLink () {
    let format = '.pdf';
    const selectedFormatOption = $('#select-export-format > option:selected');
    if (selectedFormatOption) {
      format = selectedFormatOption.val();
    }
    $('#pdf–export-sections').toggleClass('disabled', format !== '.pdf');
    $('#pdf–export-sections select[name="language"]').attr('disabled', format !== '.pdf').selectpicker('refresh');
    const pdfExportSections = $('#pdf–export-sections input');
    const enabledSections = [];
    pdfExportSections.each(function (_, input) {
      if (!$(input).hasClass('disabled')) {
        input.disabled = (format !== '.pdf');
        if (input.checked) {
          enabledSections.push(input.name);
        }
      }
    });
    const pdfExportLanguage = $('#pdf–export-sections select[name="language"]').selectpicker('val');
    const objectIDsToExport = [];
    if (window.getTemplateValue('has_related_objects_tree')) {
      $('input[name^=data_export_object_]').each(function () {
        if ($(this).prop('checked')) {
          objectIDsToExport.push(parseInt($(this).attr('data-object-id'), 10));
        }
      });
    } else {
      objectIDsToExport.push(window.getTemplateValue('object_id'));
    }
    const exportLink = $('#button-related-objects-export-data');
    if (objectIDsToExport.length > 0) {
      exportLink.attr('href', window.getTemplateValue('export_data_url') + '?format=' + format + '&object_ids=' + encodeURIComponent(JSON.stringify(objectIDsToExport)) + '&sections=' + encodeURIComponent(JSON.stringify(enabledSections)) + '&language=' + encodeURIComponent(pdfExportLanguage));
      exportLink.removeClass('disabled');
    } else {
      exportLink.attr('href', '#');
      exportLink.addClass('disabled');
    }
  }

  $('#pdf–export-sections input').on('change', function () {
    updateDataExportLink();
  });
  $('#pdf–export-sections select[name="language"]').on('change', function () {
    updateDataExportLink();
  });
  $('input[name^=data_export_object_]').on('change', function () {
    $('input.' + this.name + ':not([name=' + this.name + '])').prop('checked', $(this).prop('checked'));
    updateDataExportLink();
  });
  $('#button-related-objects-select-all').on('click', function () {
    const exportModal = $('#dataExportModal');
    for (let toggles = exportModal.find('.related-objects-tree-toggle:not(:checked)'); toggles.length > 0; toggles = exportModal.find('.related-objects-tree-toggle:not(:checked)')) {
      toggles.prop('checked', true);
      toggles.trigger('change');
    }
    exportModal.find('input.data_export_object').prop('checked', true);
    updateDataExportLink();
  });
  $('#button-related-objects-deselect-all').on('click', function () {
    $('input.data_export_object').prop('checked', false);
    updateDataExportLink();
  });
  $('#select-export-format').on('change', function () {
    updateDataExportLink();
  });
  updateDataExportLink();

  if (!window.getTemplateValue('is_archived') && window.getTemplateValue('show_download_service')) {
    $('#button-modal-files-select-all').on('click', function () {
      $('input[name^=data_download_service_checked_]').prop('checked', true);
    });
    $('#button-modal-files-deselect-all').on('click', function () {
      $('input[name^=data_download_service_checked_]').prop('checked', false);
    });
    $('#button-modal-files-download-zip').on('click', function () {
      const fileIDs = [];
      $('input[name^=data_download_service_checked_]').each(function () {
        if ($(this).prop('checked')) {
          fileIDs.push(parseInt($(this).attr('data-object-id')));
        }
      });
      const params = '?file_ids=' + fileIDs.join('&file_ids=');
      const ifrm = document.getElementById('download_frame');
      ifrm.src = window.getTemplateValue('download_service_url') + params;
    });
  }

  $('span.copy-external-link').on('click', function () {
    const button = $(this);
    navigator.clipboard.writeText(button.attr('data-url')).then(
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

  if (!window.getTemplateValue('is_archived') && window.getTemplateValue('has_related_objects_tree')) {
    const relatedObjectEntriesDiv = $('#related-objects-entries');
    const rootObjectIndex = relatedObjectEntriesDiv.data('sampledbRootObjectIndex');
    const relatedObjectEntries = relatedObjectEntriesDiv.find('> span').map(function () {
      return {
        objectIndex: $(this).data('sampledbObjectIndex'),
        referencedObjects: $(this).data('sampledbReferencedObjects'),
        referencingObjects: $(this).data('sampledbReferencingObjects'),
        isLocal: $(this).data('sampledbIsLocal'),
        objectName: $(this).data('sampledbObjectName'),
        objectId: $(this).data('sampledbObjectId'),
        span: $(this)
      };
    });
    relatedObjectEntries.sort(function (a, b) {
      if (a.objectIndex < b.objectIndex) {
        return -1;
      }
      if (b.objectIndex < a.objectIndex) {
        return 1;
      }
      return 0;
    });
    const rootObjectEntry = relatedObjectEntries[rootObjectIndex];
    const buildTreeNode = function (objectEntry, inExportDataModal, existingObjectEntryIndices, relationshipElement) {
      const result = $('<div></div>');
      const isFirstInstanceOfObject = !existingObjectEntryIndices.includes(objectEntry.objectIndex);
      if (isFirstInstanceOfObject) {
        existingObjectEntryIndices.push(objectEntry.objectIndex);

        if (objectEntry.isLocal && (objectEntry.referencedObjects.length > 0 || objectEntry.referencingObjects.length > 0)) {
          const toggle = $(`<input type="checkbox" class="related-objects-tree-toggle" id="related_object_toggle_${inExportDataModal}_${objectEntry.objectId}">`);
          const label = $(`<label for="related_object_toggle_${inExportDataModal}_${objectEntry.objectId}" class="fa fa-fw"></label>`);
          toggle.on('change', function () {
            if ($(this).parent().find('ul').length === 0) {
              const list = $('<ul></ul>');
              $(this).parent().append(list);
              for (const referencedObjectIndex of objectEntry.referencedObjects) {
                const referencedObjectEntry = relatedObjectEntries[referencedObjectIndex];
                const listItem = $('<li></li>');
                const relationshipText = window.getTemplateValue('translations.referenced_relationship_text').replace('OBJECT_NAME_PLACEHOLDER', objectEntry.objectName).replace('OBJECT_ID_PLACEHOLDER', objectEntry.objectId);
                listItem.append(buildTreeNode(referencedObjectEntry, inExportDataModal, existingObjectEntryIndices, $(`<i class="fa fa-fw fa-arrow-left" aria-hidden="true" data-toggle="tooltip" data-placement="right" title="${relationshipText}"></i>`)));
                list.append(listItem);
              }
              for (const referencingObjectIndex of objectEntry.referencingObjects) {
                const referencingObjectEntry = relatedObjectEntries[referencingObjectIndex];
                const listItem = $('<li></li>');
                const relationshipText = window.getTemplateValue('translations.referencing_relationship_text').replace('OBJECT_NAME_PLACEHOLDER', objectEntry.objectName).replace('OBJECT_ID_PLACEHOLDER', objectEntry.objectId);
                listItem.append(buildTreeNode(referencingObjectEntry, inExportDataModal, existingObjectEntryIndices, $(`<i class="fa fa-fw fa-arrow-right" aria-hidden="true" data-toggle="tooltip" data-placement="right" title="${relationshipText}"></i>`)));
                list.append(listItem);
              }
            }
          });
          result.append(toggle);
          result.append(label);
        } else {
          result.append($('<i class="fa fa-fw" aria-hidden="true"></i>'));
        }
      } else {
        result.append($('<i class="fa fa-fw fa-ellipsis-h" aria-hidden="true" style="position: relative; z-index:3; background-color: white;"></i>'));
      }
      if (relationshipElement !== null) {
        result.append(relationshipElement);
      }
      if (inExportDataModal && objectEntry.objectId) {
        const exportToggleTitle = window.getTemplateValue('translations.include_object_in_export').replace('OBJECT_ID_PLACEHOLDER', objectEntry.objectId);
        const exportToggle = $(`<span class="data_export_object_wrapper"><input type="checkbox" title="${exportToggleTitle}" class="data_export_object data_export_object_${objectEntry.objectId}" /><label for="data_export_object_${objectEntry.objectId}" class="fa fa-fw"><span class="sr-only">${exportToggleTitle}</span></label></span>`);
        const exportToggleInput = exportToggle.find('input');

        if (isFirstInstanceOfObject) {
          exportToggleInput.attr('name', `data_export_object_${objectEntry.objectId}`);
          exportToggleInput.attr('id', `data_export_object_${objectEntry.objectId}`);
          exportToggleInput.attr('data-object-id', objectEntry.objectId);
          exportToggleInput.on('change', updateDataExportLink);
        } else {
          exportToggleInput.prop('disabled', true);
        }
        result.append(' ');
        result.append(exportToggle);
      }
      result.append(objectEntry.span.clone());
      return result;
    };
    $('#related_objects ~ div.related-objects').empty().append(buildTreeNode(rootObjectEntry, false, [], null));
    $('#dataExportModal div.related-objects').empty().append(buildTreeNode(rootObjectEntry, true, [], null));
    $(`#related_object_toggle_false_${rootObjectEntry.objectId}`).prop('checked', true).trigger('change');
    $(`#related_object_toggle_true_${rootObjectEntry.objectId}`).prop('checked', true).trigger('change');
    $(`#data_export_object_${rootObjectEntry.objectId}`).prop('checked', true).trigger('change');
  }
});
if (!window.getTemplateValue('is_archived') && window.getTemplateValue('labels_enabled')) {
  const validateLabelsForm = function () {
    const PAGE_SIZES = window.getTemplateValue('page_sizes');
    const LABEL_PAPER_FORMATS = window.getTemplateValue('label_paper_formats');
    const labelsForm = $('#form-generate-labels');
    let isValid = true;
    labelsForm.find('.has-error').removeClass('has-error');
    labelsForm.find('.has-success').removeClass('has-success');
    labelsForm.find('.help-block').text('');
    if (labelsForm.find('input[name="mode"][value="fixed-width"]').is(':checked')) {
      const paperFormat = labelsForm.find('select[name="width-paper-format"] > option:checked').val();
      if (!Object.prototype.hasOwnProperty.call(PAGE_SIZES, paperFormat)) {
        const paperFormatGroup = labelsForm.find('select[name="width-paper-format"]').closest('.form-group');
        paperFormatGroup.addClass('has-error');
        paperFormatGroup.find('.help-block').text(window.getTemplateValue('translations.select_a_paper_format'));
        isValid = false;
      } else {
        labelsForm.find('select[name="width-paper-format"]').closest('.form-group').addClass('has-success');
        const maximumWidth = Math.floor(PAGE_SIZES[paperFormat][0] - 2 * window.getTemplateValue('horizontal_label_margin'));
        const maximumHeight = Math.floor(PAGE_SIZES[paperFormat][1] - 2 * window.getTemplateValue('vertical_label_margin'));
        let minimumWidth = 20;
        if (labelsForm.find('input[name="side-by-side"]').is(':checked')) {
          minimumWidth = 40;
        }
        const inputWidth = $('#input-width');
        const inputWidthGroup = inputWidth.closest('.form-group');
        const inputWidthHelp = inputWidthGroup.find('.help-block');
        const labelWidth = +inputWidth.val();
        if (!isNaN(labelWidth) && labelWidth >= minimumWidth && labelWidth <= maximumWidth) {
          inputWidthGroup.addClass('has-success');
          inputWidthHelp.text('');
          inputWidth.val(labelWidth);
        } else {
          inputWidthGroup.addClass('has-error');
          inputWidthHelp.text(window.getTemplateValue('translations.enter_a_number_between_minimum_and_maximum').replace('{minimum}', minimumWidth.toString()).replace('{maximum}', maximumWidth.toString()));
          inputWidth.closest('.form-group').addClass('has-error');
          isValid = false;
        }
        const inputMinimumHeight = $('#input-minimum-height');
        const inputMinimumHeightGroup = inputMinimumHeight.closest('.form-group');
        const inputMinimumHeightHelp = inputMinimumHeightGroup.find('.help-block');
        const labelMinimumHeight = +inputMinimumHeight.val();
        if (!isNaN(labelMinimumHeight) && labelMinimumHeight >= 0 && labelMinimumHeight <= maximumHeight) {
          inputMinimumHeightGroup.addClass('has-success');
          inputMinimumHeight.val(labelMinimumHeight);
        } else {
          inputMinimumHeightGroup.addClass('has-error');
          inputMinimumHeightHelp.text(window.getTemplateValue('translations.enter_a_number_between_minimum_and_maximum').replace('{minimum}', '0').replace('{maximum}', maximumHeight.toString()));
          isValid = false;
        }
      }
    }
    if (labelsForm.find('input[name="mode"][value="minimum-height"]').is(':checked')) {
      const paperFormat = labelsForm.find('select[name="height-paper-format"] > option:checked').val();
      if (!Object.prototype.hasOwnProperty.call(PAGE_SIZES, paperFormat)) {
        const paperFormatGroup = labelsForm.find('select[name="height-paper-format"]').closest('.form-group');
        paperFormatGroup.addClass('has-error');
        paperFormatGroup.find('.help-block').text(window.getTemplateValue('translations.select_a_paper_format'));
        isValid = false;
      } else {
        labelsForm.find('select[name="height-paper-format"]').closest('.form-group').addClass('has-success');
        const maximumWidth = Math.floor(PAGE_SIZES[paperFormat][0] - 2 * window.getTemplateValue('horizontal_label_margin'));
        const inputMinimumWidth = $('#input-minimum-width');
        const inputMinimumWidthGroup = inputMinimumWidth.closest('.form-group');
        const inputMinimumWidthHelp = inputMinimumWidthGroup.find('.help-block');
        const labelMinimumWidth = +inputMinimumWidth.val();
        if (!isNaN(labelMinimumWidth) && labelMinimumWidth >= 0 && labelMinimumWidth <= maximumWidth) {
          inputMinimumWidthGroup.addClass('has-success');
          inputMinimumWidth.val(labelMinimumWidth);
        } else {
          inputMinimumWidthGroup.addClass('has-error');
          inputMinimumWidthHelp.text(window.getTemplateValue('translations.enter_a_number_between_minimum_and_maximum').replace('{minimum}', '0').replace('{maximum}', maximumWidth.toString()));
          isValid = false;
        }
      }
    }
    if (labelsForm.find('input[name="mode"][value="mixed"]').is(':checked')) {
      const paperFormat = labelsForm.find('select[name="mixed-paper-format"] > option:checked').val();
      if (!Object.prototype.hasOwnProperty.call(PAGE_SIZES, paperFormat)) {
        const paperFormatGroup = labelsForm.find('select[name="mixed-paper-format"]').closest('.form-group');
        paperFormatGroup.addClass('has-error');
        paperFormatGroup.find('.help-block').text(window.getTemplateValue('translations.select_a_paper_format'));
        isValid = false;
      } else {
        labelsForm.find('select[name="mixed-paper-format"]').closest('.form-group').addClass('has-success');
      }
    }

    if (labelsForm.find('input[name="mode"][value="qr-code-width"]').is(':checked')) {
      const inputQRCodeWidth = labelsForm.find('input[name="qr-code-width"]');
      const inputQRCodeWidthGroup = labelsForm.find('input[name="qr-code-width"]').closest('.form-group');
      const inputQRCodeNumber = labelsForm.find('input[name="qr-code-number"]');
      const inputQRCodeNumberGroup = labelsForm.find('input[name="qr-code-number"]').closest('.form-group');
      const inputQRCodeLabelDimensionTemplateGroup = labelsForm.find('select[name="qr-code-paper-dimension-template"]').closest('.form-group');
      const inputQRCodeContent = labelsForm.find('input[name="qr-code-content"]:checked');

      const paperFormat = labelsForm.find('select[name="qr-code-paper-format"] > option:checked').val();
      const selectedLabelDimension = labelsForm.find('select[name="qr-code-paper-dimension-template"] > option:checked').val();
      const qrCodeWidth = inputQRCodeWidth.val();
      const qrCodeNumber = inputQRCodeNumber.val();
      const qrCodeContent = inputQRCodeContent.val();

      if (LABEL_PAPER_FORMATS.length > 0) {
        if (Number(selectedLabelDimension) < LABEL_PAPER_FORMATS.length || selectedLabelDimension === 'default') {
          inputQRCodeLabelDimensionTemplateGroup.addClass('has-success');
        } else {
          inputQRCodeLabelDimensionTemplateGroup.addClass('has-error');
          inputQRCodeLabelDimensionTemplateGroup.find('.help-block').text(window.getTemplateValue('translations.select_an_existing_label_paper_format'));
          isValid = false;
        }
      }

      if (LABEL_PAPER_FORMATS.length === 0 || selectedLabelDimension === 'default') {
        if (!Object.prototype.hasOwnProperty.call(PAGE_SIZES, paperFormat)) {
          const paperFormatGroup = labelsForm.find('select[name="qr-code-paper-format"]').closest('.form-group');
          paperFormatGroup.addClass('has-error');
          paperFormatGroup.find('.help-block').text(window.getTemplateValue('translations.select_a_paper_format'));
          isValid = false;
        } else {
          labelsForm.find('select[name="qr-code-paper-format"]').closest('.form-group').addClass('has-success');
        }

        if (!isNaN(qrCodeWidth) && qrCodeWidth >= 4 && qrCodeWidth <= 150) {
          inputQRCodeWidthGroup.addClass('has-success');
        } else {
          inputQRCodeWidthGroup.addClass('has-error');
          inputQRCodeWidthGroup.find('.help-block').text(window.getTemplateValue('translations.enter_a_number_between_minimum_and_maximum').replace('{minimum}', '4').replace('{maximum}', '150'));
          isValid = false;
        }
      }

      if (!isNaN(qrCodeNumber) && qrCodeNumber >= 1 && qrCodeNumber <= 1000) {
        inputQRCodeNumberGroup.addClass('has-success');
      } else {
        inputQRCodeNumberGroup.addClass('has-error');
        inputQRCodeNumberGroup.find('.help-block').text(window.getTemplateValue('translations.enter_a_number_between_minimum_and_maximum').replace('{minimum}', '1').replace('{maximum}', '1000'));
        isValid = false;
      }

      if (qrCodeContent === 'object-url' || qrCodeContent === 'object-id') {
        inputQRCodeWidthGroup.addClass('has-success');
      } else {
        inputQRCodeWidthGroup.addClass('has-error');
        inputQRCodeWidthGroup.find('.help-block').text(window.getTemplateValue('translations.select_qr_code_data'));
        isValid = false;
      }
    }

    if (labelsForm.find('input[name="mode"]:checked').length === 0) {
      labelsForm.find('input[name="mode"]').closest('.radio').addClass('has-error');
      isValid = false;
    }
    return isValid;
  };

  const updateQRCodeLabelsCheckbox = function () {
    const labelsForm = $('#form-generate-labels');
    const isQRCode = labelsForm.find('input[name="mode"][value="qr-code-width"]').is(':checked');
    const showLabelNumber = labelsForm.find('input[name="add-label-number"]').is(':checked');
    labelsForm.find('input[name="add-maximum-label-number"]').prop('disabled', !isQRCode || !showLabelNumber);
  };
  const updateLabelsForm = function () {
    const labelsForm = $('#form-generate-labels');
    labelsForm.find('.has-error').removeClass('has-error');
    labelsForm.find('.has-success').removeClass('has-success');
    labelsForm.find('.help-block').text('');
    const isMixed = labelsForm.find('input[name="mode"][value="mixed"]').is(':checked');
    labelsForm.find('select[name="mixed-paper-format"]').prop('disabled', !isMixed).selectpicker('refresh');
    const isFixedWidth = labelsForm.find('input[name="mode"][value="fixed-width"]').is(':checked');
    labelsForm.find('input[name="side-by-side"]').prop('disabled', !isFixedWidth);
    labelsForm.find('input[name="centered"]').prop('disabled', !isFixedWidth);
    labelsForm.find('input[name="label-width"]').prop('disabled', !isFixedWidth);
    labelsForm.find('input[name="label-minimum-height"]').prop('disabled', !isFixedWidth);
    labelsForm.find('select[name="width-paper-format"]').prop('disabled', !isFixedWidth).selectpicker('refresh');
    const isMinimumHeight = labelsForm.find('input[name="mode"][value="minimum-height"]').is(':checked');
    labelsForm.find('input[name="include-qrcode"]').prop('disabled', !isMinimumHeight);
    labelsForm.find('input[name="label-minimum-width"]').prop('disabled', !isMinimumHeight);
    labelsForm.find('select[name="height-paper-format"]').prop('disabled', !isMinimumHeight).selectpicker('refresh');
    const isQRCode = labelsForm.find('input[name="mode"][value="qr-code-width"]').is(':checked');
    labelsForm.find('select[name="qr-code-paper-format"]').prop('disabled', !isQRCode).selectpicker('refresh');
    labelsForm.find('input[name="qr-code-width"]').prop('disabled', !isQRCode);
    labelsForm.find('input[name="qr-code-number"]').prop('disabled', !isQRCode);
    labelsForm.find('select[name="qr-code-paper-dimension-template"]').prop('disabled', !isQRCode).selectpicker('refresh');
    labelsForm.find('input[name="qr-code-content"]').prop('disabled', !isQRCode);
    labelsForm.find('input[name="show-id-on-label"]').prop('disabled', !isQRCode);
    labelsForm.find('input[name="add-label-number"]').prop('disabled', !isQRCode);
    updateQRCodeLabelsCheckbox();
  };
  updateLabelsForm();

  $(function () {
    $('#form-generate-labels').on('submit', validateLabelsForm);
    $('#objectLabelModal input[type="radio"]').on('change', updateLabelsForm);
    $('#objectLabelModal input[name="add-label-number"]').on('change', updateQRCodeLabelsCheckbox);
  });

  if (window.getTemplateValue('label_paper_formats').length > 0) {
    const updateQRCodeLabelPaperDimensionSettings = function () {
      const form = $('#form-generate-labels');
      $('.defined-by-label-paper').toggle(form.find('select[name="qr-code-paper-dimension-template"]').val() === 'default');
    };
    updateQRCodeLabelPaperDimensionSettings();
    $(function () {
      $('#objectLabelModal select[name="qr-code-paper-dimension-template"]').on('change', updateQRCodeLabelPaperDimensionSettings);
    });
  }
}
$(document).ready(function () {
  $('.modal-body table.diff').each(function (_, table) {
    let skippedRows = 0;
    $(table).find('tr').each(function (index, row) {
      if ($(row).find('.diff_header').text() === '>>') {
        skippedRows += 1;
        $(row).addClass('noborder');
      }
      if ((index - skippedRows) % 2 === 1) {
        $(row).addClass('striped');
      }
    });
  });
});
