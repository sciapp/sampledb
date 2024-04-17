
    window.object_location_translations = {
       en: ''
    };
    $(function () {
      window.languages = window.getTemplateValue('languages');

      if (!window.getTemplateValue('is_archived') && window.getTemplateValue('labels_enabled')) {
        $('#form-generate-labels').on('submit', validateLabelsForm);
        $('#objectLabelModal input[type="radio"]').on('change', updateLabelsForm);
        $('#objectLabelModal input[name="add-label-number"]').on('change', updateQRCodeLabelsCheckbox);
        if (window.getTemplateValue('label_paper_formats').length > 0) {
          $('#objectLabelModal select[name="qr-code-paper-dimension-template"]').on('change', updateQRCodeLabelPaperDimensionSettings);
        }
      }

      function updateObjectLocationTranslationJSON() {
        var translation_json = JSON.stringify(window.object_location_translations);
        $('#input-object_location-translations').val(translation_json);
      }

      $('form#assign-location-form').on('submit', function(){
        resp = $('.selectpicker#input-responsible-user').val();
        locat = $('.selectpicker#input-location').val()
        if (resp === '-1' && locat === '-1'){
          $('#object_location-help-block').html(window.getTemplateValue('translations.select_responsible_user_or_location'));
        } else {
          $('#object_location-help-block').html('')
        }
        return (resp !== '-1' || locat !== '-1')
      });

      $('#select-language-object_location').on('change', function () {
        var existing_languages = []
        $.each(window.object_location_translations, function (key, value) {
          existing_languages.push(key)
        })
        let selected = ["en"];
        let input_descriptions = $('[data-name="input-descriptions"]')
        selected = selected.concat($(this).val())
        let remove_languages = existing_languages.filter(n => !selected.includes(n))
        let add_languages = selected.filter(n => !existing_languages.includes(n))
        for (const del_language of remove_languages) {
          let temp = $('#input-group-object_location-' + del_language)
          $.each(window.object_location_translations, function (key, value) {
            if (key === del_language)
              delete window.object_location_translations[key];
          });
          $(temp).remove();
          updateObjectLocationTranslationJSON();
        }
        for (const new_language of selected) {
          if (!$('#input-group-object_location-' + new_language).length) {
            $($('#object_location-template').html()).insertAfter(input_descriptions.children().last());
            let temp = input_descriptions.children().last();
            let lang_name = window.languages.find(lang => lang.lang_code === new_language).name
            $(temp).children().first().attr('id', 'textarea-object_location' + new_language.toString())

            $(temp).attr('id', 'input-group-object_location-' + new_language)
            $(temp).attr('data-name', 'input-group-object_location')
            $(temp).children('.input-group-addon[data-name="language"]').text(lang_name)
            $(temp).attr('data-language', new_language);

            $(temp).change(function () {
              var language = $(this).attr('data-language');
              var translation_text = $(this).find('textarea').val();
              window.object_location_translations[language] = translation_text;
              updateObjectLocationTranslationJSON();
            });
            $(temp).find('textarea').change();
          }
          if (add_languages.includes(new_language)) {
            window.object_location_translations[new_language] = '';
          }
          updateObjectLocationTranslationJSON();
        }
      });

      $('#input-group-object_location-en').change(function(){
        var language = $(this).attr('data-language');
        var translation_text = $(this).find('textarea').val();
        window.object_location_translations[language] = translation_text;
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
      if (!window.getTemplateValue('is_archived') && window.getTemplateValue('user_may_comments')) {
        var comment_form = $('#new-comment-form');
        var comment_textarea = comment_form.find('textarea');
        comment_textarea.on('input change propertychange', function () {
          comment_textarea.closest('.form-group').removeClass('has-error');
        });
        comment_form.on('submit', function () {
          if (comment_textarea.val() === "") {
            comment_textarea.closest('.form-group').addClass('has-error');
            comment_textarea.focus();
            return false;
          }
          return true;
        });
      }
      $(function () {
        $('[data-toggle="popover"]').popover()
      });
      if (window.getTemplateValue('has_object_log_entries')) {
        const activity_log_filter_type_dict = window.getTemplateValue('activity_log_filter_type_dict');
        window.activity_log_apply_filters = function() {
          window.activity_log_apply_filter("versions");
          window.activity_log_apply_filter("measurements");
          window.activity_log_apply_filter("comments");
          window.activity_log_apply_filter("files");
          window.activity_log_apply_filter("locations");
          window.activity_log_apply_filter("references");
          window.activity_log_apply_filter("other");
          const activity_log = $('#activity_log_table > tbody');
          const show_all = $('#activity_log_show_all_toggle').prop('checked');
          const visible_activity_log_entries = activity_log.find('tr:visible');
          $('#activity_log_counter').html('' + visible_activity_log_entries.length + '&thinsp;/&thinsp;' + activity_log.find('tr').length);
          if (!show_all && visible_activity_log_entries.length > 15) {
            visible_activity_log_entries.slice(15).css({display: 'none'});
            $('#activity_log_show_all_wrapper').show();
          } else {
            $('#activity_log_show_all_wrapper').hide();
          }
        }
        window.activity_log_apply_filter = function (category) {
          const type_list = activity_log_filter_type_dict[category];
          const activity_log = $('#activity_log_table > tbody');
          type_list.forEach(function (activity_log_type) {
            const activity_log_rows = activity_log.find('tr[data-activity-log-type=' + activity_log_type + ']');
            if (window.activity_log_toggle.current_state[category]) {
              activity_log_rows.css({display: 'table-row'});
            } else {
              activity_log_rows.css({display: 'none'});
            }
          });
        };
        window.activity_log_toggle = function (should_show, category) {
          window.activity_log_toggle.current_state[category] = should_show;
          Cookies.set('SAMPLEDB_ACTIVITY_LOG_FILTER_STATE', JSON.stringify(window.activity_log_toggle.current_state), {sameSite: 'Lax'});
        };
        window.activity_log_toggle.current_state = {};
        let activity_log_filter_state;
        try {
          activity_log_filter_state = JSON.parse(Cookies.get('SAMPLEDB_ACTIVITY_LOG_FILTER_STATE'));
        } catch(e) {
            // ignore invalid cookies
        }
        if (activity_log_filter_state === undefined) {
          activity_log_filter_state = {
            "versions": true,
            "measurements": true,
            "comments": true,
            "files": true,
            "locations": true,
            "references": true,
            "other": true
          };
          Cookies.set('SAMPLEDB_ACTIVITY_LOG_FILTER_STATE', JSON.stringify(activity_log_filter_state), {sameSite: 'Lax'});
        }
        $('#activity_log_show_all_toggle').on('change', function() {
          window.activity_log_apply_filters();
        });
        window.activity_log_toggle(activity_log_filter_state['versions'], "versions");
        window.activity_log_toggle(activity_log_filter_state['measurements'], "measurements");
        window.activity_log_toggle(activity_log_filter_state['comments'], "comments");
        window.activity_log_toggle(activity_log_filter_state['files'], "files");
        window.activity_log_toggle(activity_log_filter_state['locations'], "locations");
        window.activity_log_toggle(activity_log_filter_state['references'], "references");
        window.activity_log_toggle(activity_log_filter_state['other'], "other");
        window.activity_log_apply_filters();

        $('#activity_log_counter').closest('button').on('inserted.bs.popover', function () {
          for (const filterType of ['versions', 'measurements', 'comments', 'files', 'locations', 'references', 'other']) {
            const filterToggle = $(`#activity_log_filter_${filterType}`);
            filterToggle.prop('checked', window.activity_log_toggle.current_state[filterType]);
            filterToggle.on('click', function () {
              activity_log_toggle($(this).prop('checked'), filterType);
              activity_log_apply_filters();
            });
          }
        });
      }
      if (!window.getTemplateValue('is_archived')) {
        if (window.getTemplateValue('files_enabled')) {
          window.file_table_toggle = function (should_show, category) {
            var file_table = $('#file_table').find('> tbody');
            var file_table_rows = file_table.find('tr[data-file-type=' + category + ']');
            if (should_show) {
              file_table_rows.css({display: 'table-row'});
            } else {
              file_table_rows.css({display: 'none'});
            }
            $('#file_table_counter').html('' + file_table.find('tr:visible').length + '&thinsp;/&thinsp;' + file_table.find('tr').length);
            window.file_table_toggle.current_state[category] = should_show;
            Cookies.set('SAMPLEDB_FILE_TABLE_FILTER_STATE', JSON.stringify(window.file_table_toggle.current_state), {sameSite: 'Lax'});
          };
          window.file_table_toggle.current_state = {};
          let file_table_filter_state;
          try {
            file_table_filter_state = JSON.parse(Cookies.get('SAMPLEDB_FILE_TABLE_FILTER_STATE'));
          }catch (e) {
            // ignore invalid cookies
          }
          if (file_table_filter_state === undefined) {
            file_table_filter_state = {
              "notebooks": true,
              "other": true
            };
            Cookies.set('SAMPLEDB_FILE_TABLE_FILTER_STATE', JSON.stringify(file_table_filter_state), {sameSite: 'Lax'});
          }
          window.file_table_toggle(file_table_filter_state['notebooks'], "notebooks");
          window.file_table_toggle(file_table_filter_state['other'], "other");
          window.update_file_table_filter_states = function () {
            if (window.file_table_toggle.current_state['notebooks']) {
              $('#file_table_filter_notebooks').attr('checked', 'checked');
            }
            if (window.file_table_toggle.current_state['other']) {
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
        if (window.getTemplateValue('files_enabled')) {
          function changeHandler() {
            var files = $('#input-file-upload').get(0).files;
            if (files.length === 0) {
              $('#input-file-text').val("");
              $('#button-upload-files').addClass('disabled');
              $('#button-upload-files').prop('disabled', true);
            } else if (files.length === 1) {
              $('#input-file-text').val(files[0].name);
              $('#button-upload-files').removeClass('disabled');
              $('#button-upload-files').prop('disabled', false);
            } else {
              $('#input-file-text').val(files.length + " " + window.getTemplateValue('translations.files_selected'));
              $('#button-upload-files').removeClass('disabled');
              $('#button-upload-files').prop('disabled', false);
            }
            $('#input-file-names-hidden').val("");
            $('#input-file-source-hidden').val("local");
          }
          if (window.getTemplateValue('user_may_upload_files')) {
            $('#input-file-upload').on('change', changeHandler);
            function dropHandler(e) {
              e.preventDefault();
              $('#input-file-upload')[0].files = e.dataTransfer.files;
              changeHandler();
            }
            function dragOverHandler(e) {
              e.preventDefault();
            }
            var upload_area = $('#upload-area')[0];
            upload_area.ondrop = dropHandler;
            upload_area.ondragover = dragOverHandler;
          }
        }
      }

      if (window.getTemplateValue('files_enabled')) {
        $('.button-file-info').on('click', function () {
          var file_id = $(this).attr('data-file_id');
          $('#fileInfoModal-' + file_id).modal('show');
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
        var file_id = window.getTemplateValue('edit_external_link_file');
        if (file_id >= 0) {
          $('.file-info-edit-mode').show();
          $('.file-info-view-mode').hide();
          $('#fileInfoModal-' + file_id).modal('show');
          $('#file-url-error-' + file_id + ' > span:first-of-type').text(window.getTemplateValue('external_link_error'));
          $('#file-url-error-' + file_id).show();
        }
      }
      if (window.getTemplateValue('has_related_objects_tree')) {
        $('input[name^=data_export_object_]').prop("checked", false);
        $('input.data_export_object').prop("checked", false);
        $(`input.data_export_object_${window.getTemplateValue('object_id')}`).prop("checked", true);
      }
        function updateDataExportLink() {
          var format = ".pdf";
          var selected_format_option = $('#select-export-format > option:selected');
          if (selected_format_option) {
            format = selected_format_option.val();
          }
          $('#pdf–export-sections').toggleClass('disabled', format !== '.pdf');
          $('#pdf–export-sections select[name="language"]').attr('disabled', format !== '.pdf').selectpicker('refresh');
          var pdf_export_sections = $('#pdf–export-sections input');
          var enabled_sections = [];
          pdf_export_sections.each(function (_, input) {
            if (!$(input).hasClass('disabled')) {
              input.disabled = (format !== '.pdf');
              if (input.checked) {
                enabled_sections.push(input.name);
              }
            }
          });
          var pdf_export_language = $('#pdf–export-sections select[name="language"]').selectpicker('val');
          var object_ids_to_export = [];
          if (window.getTemplateValue('has_related_objects_tree')) {
            $('input[name^=data_export_object_]').each(function () {
              if ($(this).prop('checked')) {
                object_ids_to_export.push(parseInt($(this).attr('data-object-id'), 10));
              }
            });
          } else {
            object_ids_to_export.push(window.getTemplateValue('object_id'));
          }
          var export_link = $('#button-related-objects-export-data');
          if (object_ids_to_export.length > 0) {
            export_link.attr('href', window.getTemplateValue('export_data_url') + "?format=" + format + "&object_ids=" + encodeURIComponent(JSON.stringify(object_ids_to_export)) + "&sections=" + encodeURIComponent(JSON.stringify(enabled_sections)) + "&language=" + encodeURIComponent(pdf_export_language));
            export_link.removeClass("disabled");
          } else {
            export_link.attr('href', "#");
            export_link.addClass("disabled");
          }
        }

        $('#pdf–export-sections input').on('change', function () {
          updateDataExportLink();
        });
        $('#pdf–export-sections select[name="language"]').on('change', function () {
          updateDataExportLink();
        });
        $('input[name^=data_export_object_]').on('change', function () {
          $('input.' + this.name + ':not([name=' + this.name + '])').prop("checked", $(this).prop("checked"));
          updateDataExportLink();
        });
        $('#button-related-objects-select-all').on('click', function () {
          $('#dataExportModal .related-objects-tree-toggle').prop("checked", true);
          $('input.data_export_object').prop("checked", true);
          updateDataExportLink();
        });
        $('#button-related-objects-deselect-all').on('click', function () {
          $('input.data_export_object').prop("checked", false);
          updateDataExportLink();
        });
        $('#select-export-format').on('change', function () {
          updateDataExportLink();
        });
        updateDataExportLink();

      if (!window.getTemplateValue('is_archived') && window.getTemplateValue('show_download_service')) {
        $('#button-modal-files-select-all').on('click', function () {
          $('input[name^=data_download_service_checked_]').prop("checked", true);
        });
        $('#button-modal-files-deselect-all').on('click', function () {
          $('input[name^=data_download_service_checked_]').prop("checked", false);
        });
        $('#button-modal-files-download-zip').on('click', function () {
          let file_ids = [];
          $('input[name^=data_download_service_checked_]').each(function () {
            if ($(this).prop('checked')) {
              file_ids.push(parseInt($(this).attr('data-object-id')));
            }
          });
          let params = '?file_ids=' + file_ids.join('&file_ids=')
          let ifrm = document.getElementById('download_frame');
          ifrm.src = window.getTemplateValue('download_service_url') + params;
        });
      }

      $('span.copy-external-link').on('click', function () {
        var button = $(this);
        navigator.clipboard.writeText(button.attr('data-url')).then(
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
    });
    if (!window.getTemplateValue('is_archived') && window.getTemplateValue('labels_enabled')) {
    function validateLabelsForm() {
      const PAGE_SIZES = window.getTemplateValue("page_sizes")
      const LABEL_PAPER_FORMATS = window.getTemplateValue("label_paper_formats");
      var labels_form = $('#form-generate-labels');
      var is_valid = true;
      labels_form.find('.has-error').removeClass('has-error');
      labels_form.find('.has-success').removeClass('has-success');
      labels_form.find('.help-block').text("");
      if (labels_form.find('input[name="mode"][value="fixed-width"]').is(':checked')) {
        var paper_format = labels_form.find('select[name="width-paper-format"] > option:checked').val();
        if (!PAGE_SIZES.hasOwnProperty(paper_format)) {
          var paper_format_group = labels_form.find('select[name="width-paper-format"]').closest('.form-group');
          paper_format_group.addClass('has-error');
          paper_format_group.find('.help-block').text(window.getTemplateValue('translations.select_a_paper_format'));
          is_valid = false;
        } else {
          labels_form.find('select[name="width-paper-format"]').closest('.form-group').addClass('has-success');
          var maximum_width = Math.floor(PAGE_SIZES[paper_format][0] - 2 * window.getTemplateValue('horizontal_label_margin'));
          var maximum_height = Math.floor(PAGE_SIZES[paper_format][1] - 2 * window.getTemplateValue('vertical_label_margin'));
          var minimum_width = 20;
          if (labels_form.find('input[name="side-by-side"]').is(':checked')) {
            minimum_width = 40;
          }
          var input_width = $('#input-width');
          var input_width_group = input_width.closest('.form-group');
          var input_width_help = input_width_group.find('.help-block');
          var label_width = +input_width.val();
          if (!isNaN(label_width) && label_width >= minimum_width && label_width <= maximum_width) {
            input_width_group.addClass('has-success');
            input_width_help.text("");
            input_width.val(label_width);
          } else {
            input_width_group.addClass('has-error');
            input_width_help.text(window.getTemplateValue('translations.enter_a_number_between_minimum_and_maximum').replace("{minimum}", minimum_width.toString()).replace("{maximum}", maximum_width.toString()));
            input_width.closest('.form-group').addClass('has-error');
            is_valid = false;
          }
          var input_minimum_height = $('#input-minimum-height');
          var input_minimum_height_group = input_minimum_height.closest('.form-group');
          var input_minimum_height_help = input_minimum_height_group.find('.help-block');
          var label_minimum_height = +input_minimum_height.val();
          if (!isNaN(label_minimum_height) && label_minimum_height >= 0 && label_minimum_height <= maximum_height) {
            input_minimum_height_group.addClass('has-success');
            input_minimum_height.val(label_minimum_height);
          } else {
            input_minimum_height_group.addClass('has-error');
            input_minimum_height_help.text(window.getTemplateValue('translations.enter_a_number_between_minimum_and_maximum').replace("{minimum}", "0").replace("{maximum}", maximum_height.toString()));
            is_valid = false;
          }
        }
      }
      if (labels_form.find('input[name="mode"][value="minimum-height"]').is(':checked')) {
        var paper_format = labels_form.find('select[name="height-paper-format"] > option:checked').val();
        if (!PAGE_SIZES.hasOwnProperty(paper_format)) {
          var paper_format_group = labels_form.find('select[name="height-paper-format"]').closest('.form-group');
          paper_format_group.addClass('has-error');
          paper_format_group.find('.help-block').text(window.getTemplateValue('translations.select_a_paper_format'));
          is_valid = false;
        } else {
          labels_form.find('select[name="height-paper-format"]').closest('.form-group').addClass('has-success');
          var maximum_width = Math.floor(PAGE_SIZES[paper_format][0] - 2 * window.getTemplateValue('horizontal_label_margin'));
          var input_minimum_width = $('#input-minimum-width');
          var input_minimum_width_group = input_minimum_width.closest('.form-group');
          var input_minimum_width_help = input_minimum_width_group.find('.help-block');
          var label_minimum_width = +input_minimum_width.val();
          if (!isNaN(label_minimum_width) && label_minimum_width >= 0 && label_minimum_width <= maximum_width) {
            input_minimum_width_group.addClass('has-success');
            input_minimum_width.val(label_minimum_width);
          } else {
            input_minimum_width_group.addClass('has-error');
            input_minimum_width_help.text(window.getTemplateValue('translations.enter_a_number_between_minimum_and_maximum').replace("{minimum}", "0").replace("{maximum}", maximum_width.toString()));
            is_valid = false;
          }
        }
      }
      if (labels_form.find('input[name="mode"][value="mixed"]').is(':checked')) {
        var paper_format = labels_form.find('select[name="mixed-paper-format"] > option:checked').val();
        if (!PAGE_SIZES.hasOwnProperty(paper_format)) {
         var paper_format_group = labels_form.find('select[name="mixed-paper-format"]').closest('.form-group');
         paper_format_group.addClass('has-error');
         paper_format_group.find('.help-block').text(window.getTemplateValue('translations.select_a_paper_format'));
         is_valid = false;
        } else {
         labels_form.find('select[name="mixed-paper-format"]').closest('.form-group').addClass('has-success');
        }
      }

      if (labels_form.find('input[name="mode"][value="qr-code-width"]').is(":checked")) {
        var input_qr_code_width = labels_form.find('input[name="qr-code-width"]');
        var input_qr_code_width_group = labels_form.find('input[name="qr-code-width"]').closest('.form-group');
        var input_qr_code_number = labels_form.find('input[name="qr-code-number"]');
        var input_qr_code_number_group = labels_form.find('input[name="qr-code-number"]').closest('.form-group');
        var input_qr_code_label_dimension_template_group = labels_form.find('select[name="qr-code-paper-dimension-template"]').closest('.form-group');
        var input_qr_code_content = labels_form.find('input[name="qr-code-content"]:checked');
        var input_qr_code_content_group = labels_form.find('input[name="qr-code-content"]:checked').closest('.form-group');

        var paper_format = labels_form.find('select[name="qr-code-paper-format"] > option:checked').val();
        var selected_label_dimension = labels_form.find('select[name="qr-code-paper-dimension-template"] > option:checked').val();
        var qr_code_width = input_qr_code_width.val();
        var qr_code_number = input_qr_code_number.val();
        var qr_code_content = input_qr_code_content.val();

        if (LABEL_PAPER_FORMATS.length > 0) {
            if (Number(selected_label_dimension) < LABEL_PAPER_FORMATS.length || selected_label_dimension === "default") {
              input_qr_code_label_dimension_template_group.addClass('has-success');
            } else {
              input_qr_code_label_dimension_template_group.addClass('has-error');
              input_qr_code_label_dimension_template_group.find('.help-block').text(window.getTemplateValue('translations.select_an_existing_label_paper_format'));
              is_valid = false;
            }
        }

        if (LABEL_PAPER_FORMATS.length === 0 || selected_label_dimension === "default") {
            if(!PAGE_SIZES.hasOwnProperty(paper_format)) {
              var paper_format_group = labels_form.find('select[name="qr-code-paper-format"]').closest('.form-group');
              paper_format_group.addClass('has-error');
              paper_format_group.find('.help-block').text(window.getTemplateValue('translations.select_a_paper_format'));
              is_valid = false;
            } else {
              labels_form.find('select[name="qr-code-paper-format"]').closest('.form-group').addClass('has-success');
            }

            if(!isNaN(qr_code_width) && qr_code_width >= 4 && qr_code_width <= 150) {
              input_qr_code_width_group.addClass('has-success');
            } else {
              input_qr_code_width_group.addClass('has-error');
              input_qr_code_width_group.find('.help-block').text(window.getTemplateValue('translations.enter_a_number_between_minimum_and_maximum').replace("{minimum}", "4").replace("{maximum}", "150"));
              is_valid = false;
            }
        }

        if(!isNaN(qr_code_number) && qr_code_number >= 1 && qr_code_number <= 1000) {
          input_qr_code_number_group.addClass('has-success');
        } else {
          input_qr_code_number_group.addClass('has-error');
          input_qr_code_number_group.find('.help-block').text(window.getTemplateValue('translations.enter_a_number_between_minimum_and_maximum').replace("{minimum}", "1").replace("{maximum}", "1000"));
          is_valid = false;
        }

        if(qr_code_content  === 'object-url' || qr_code_content === 'object-id') {
          input_qr_code_width_group.addClass('has-success');
        } else {
          input_qr_code_width_group.addClass('has-error');
          input_qr_code_width_group.find('.help-block').text(window.getTemplateValue('translations.select_qr_code_data'));
          is_valid = false;
        }
      }

      if (labels_form.find('input[name="mode"]:checked').length == 0) {
        labels_form.find('input[name="mode"]').closest('.radio').addClass('has-error');
        is_valid = false;
      }
      return is_valid;
    }
    function updateLabelsForm() {
      var labels_form = $('#form-generate-labels');
      labels_form.find('.has-error').removeClass('has-error');
      labels_form.find('.has-success').removeClass('has-success');
      labels_form.find('.help-block').text("");
      var is_mixed = labels_form.find('input[name="mode"][value="mixed"]').is(':checked');
      labels_form.find('select[name="mixed-paper-format"]').prop('disabled', !is_mixed).selectpicker('refresh');
      var is_fixed_width = labels_form.find('input[name="mode"][value="fixed-width"]').is(':checked');
      labels_form.find('input[name="side-by-side"]').prop('disabled', !is_fixed_width);
      labels_form.find('input[name="centered"]').prop('disabled', !is_fixed_width);
      labels_form.find('input[name="label-width"]').prop('disabled', !is_fixed_width);
      labels_form.find('input[name="label-minimum-height"]').prop('disabled', !is_fixed_width);
      labels_form.find('select[name="width-paper-format"]').prop('disabled', !is_fixed_width).selectpicker('refresh');
      var is_minimum_height = labels_form.find('input[name="mode"][value="minimum-height"]').is(':checked');
      labels_form.find('input[name="include-qrcode"]').prop('disabled', !is_minimum_height);
      labels_form.find('input[name="label-minimum-width"]').prop('disabled', !is_minimum_height);
      labels_form.find('select[name="height-paper-format"]').prop('disabled', !is_minimum_height).selectpicker('refresh');
      var is_qr_code = labels_form.find('input[name="mode"][value="qr-code-width"]').is(":checked");
      var show_label_number = labels_form.find('input[name="show-label-number"]').is(":checked");
      labels_form.find('select[name="qr-code-paper-format"]').prop('disabled', !is_qr_code).selectpicker('refresh');
      labels_form.find('input[name="qr-code-width"]').prop('disabled', !is_qr_code);
      labels_form.find('input[name="qr-code-number"]').prop('disabled', !is_qr_code);
      labels_form.find('select[name="qr-code-paper-dimension-template"]').prop('disabled', !is_qr_code).selectpicker('refresh');
      labels_form.find('input[name="qr-code-content"]').prop('disabled', !is_qr_code);
      labels_form.find('input[name="show-id-on-label"]').prop('disabled', !is_qr_code);
      labels_form.find('input[name="add-label-number"]').prop('disabled', !is_qr_code);
      updateQRCodeLabelsCheckbox();
    }
    updateLabelsForm();

    function updateQRCodeLabelsCheckbox() {
      var labels_form = $('#form-generate-labels');
      var is_qr_code = labels_form.find('input[name="mode"][value="qr-code-width"]').is(":checked");
      var show_label_number = labels_form.find('input[name="add-label-number"]').is(":checked");
      labels_form.find('input[name="add-maximum-label-number"]').prop('disabled', !is_qr_code || !show_label_number);
    }

    if (window.getTemplateValue('label_paper_formats').length > 0) {
    function updateQRCodeLabelPaperDimensionSettings() {
      const form = $("#form-generate-labels");
      $('.defined-by-label-paper').toggle(form.find('select[name="qr-code-paper-dimension-template"]').val() === 'default');
    }
    updateQRCodeLabelPaperDimensionSettings();
    }

  }
   $( document ).ready(function() {
      $('.modal-body table.diff').each(function(_, table) {
        let skipped_rows = 0;
        $(table).find('tr').each(function(index, row) {
          if ($(row).find('.diff_header').text() === '>>') {
            skipped_rows += 1;
            $(row).addClass('noborder');
          }
          if ((index - skipped_rows) % 2 === 1) {
            $(row).addClass('striped');
          }
        });
      });
    });