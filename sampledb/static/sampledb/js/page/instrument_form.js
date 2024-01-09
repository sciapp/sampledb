'use strict';
/* eslint-env jquery */

import {
  updateTranslationJSON,
  setTranslationHandler,
  updateTranslationLanguages,
  updateMarkdownField
} from '../sampledb-internationalization.js';

window.mdeFields = {
  descriptions: [],
  short_descriptions: [],
  notes: []
};
window.new_category_counter = -1;
$(function () {
  window.translations = window.getTemplateValue('translations');
  window.categories = window.getTemplateValue('categories');

  window.languages = window.getTemplateValue('language_info.languages');
  function updateCategoryJSON () {
    $('#input-categories').val(JSON.stringify(window.categories));
  }

  updateCategoryJSON();
  updateTranslationJSON();
  function updateEventHandler () {
    $('[data-category-id][data-category-id!=""]').each(function () {
      $(this).find('input').on('change', function () {
        const categoryElement = $(this).closest('[data-category-id]');
        const categoryID = categoryElement.attr('data-category-id');
        const categoryTitle = categoryElement.find('input[type="text"]').val().trim();
        if (categoryTitle === '') {
          categoryElement.parent().addClass('has-error').find('.help-block').html(window.getTemplateValue('translations.enter_category_title'));
        } else if (categoryTitle.length > 100) {
          categoryElement.parent().addClass('has-error').find('.help-block').html(window.getTemplateValue('translations.enter_shorter_category_title'));
        } else {
          categoryElement.parent().removeClass('has-error').find('.help-block').html('');
        }
        window.categories.forEach(function (category) {
          if (category.id === categoryID) {
            category.title = categoryTitle;
          }
        });
        updateCategoryJSON();
      }).change();
      $(this).find('select').on('change', function () {
        const categoryElement = $(this).closest('[data-category-id]');
        const categoryID = categoryElement.attr('data-category-id');
        const categoryTheme = categoryElement.find('option:selected').val();
        window.categories.forEach(function (category) {
          if (category.id === categoryID) {
            category.theme = categoryTheme;
          }
        });
        updateCategoryJSON();
      });
      $(this).find('.button-delete-category').on('click', function () {
        const categoryElement = $(this).closest('[data-category-id]');
        const categoryID = categoryElement.attr('data-category-id');
        categoryElement.parent().remove();
        window.categories = window.categories.filter(function (category) {
          return category.id !== categoryID;
        });
        updateCategoryJSON();
      });
    });
  }
  $('#button-instrument-log-new-category').on('click', function () {
    $($('#instrument-log-category-template').html()).insertBefore($(this).parent());
    $(this).parent().prev('.form-group').find('.input-group').attr('data-category-id', window.new_category_counter);
    window.categories.push({
      id: window.new_category_counter.toString(),
      title: '',
      theme: window.getTemplateValue('default_theme_name')
    });
    window.new_category_counter -= 1;
    $('[data-category-id][data-category-id!=""] select').addClass('selectpicker');
    $('.selectpicker').selectpicker();
    updateEventHandler();
    updateCategoryJSON();
  });

  if (window.getTemplateValue('is_create_form')) {
    $('.form-group[data-name="input-names"] .selectpicker, .form-group[data-name="input-descriptions"] .selectpicker, .form-group[data-name="input-short-descriptions"] .selectpicker, .form-group[data-name="input-notes"] .selectpicker').each(function () {
      $(this).selectpicker('val', ['' + window.getTemplateValue('language_info.english_id')]);
    });
  }

  $('#select-language-name').on('change', function () {
    updateTranslationLanguages(this, 'name-template', 'input-name-', ['name', 'description', 'short_description', 'notes']);
  }).change();

  $('#select-language-description').on('change', function () {
    updateTranslationLanguages(this, 'description-template', 'input-description-', ['name', 'description', 'short_description', 'notes']);
    updateDescriptionMarkdown();
  }).change();

  $('#select-language-short-description').on('change', function () {
    updateTranslationLanguages(this, 'short-description-template', 'input-short-description-', ['name', 'description', 'short_description', 'notes']);
    updateShortDescriptionMarkdown();
  }).change();

  $('#select-language-notes').on('change', function () {
    updateTranslationLanguages(this, 'notes-template', 'input-notes-', ['name', 'description', 'short_description', 'notes']);
    updateNotesMarkdown();
  }).change();

  $('.form-group[data-name="input-names"] [data-language-id], .form-group[data-name="input-descriptions"] [data-language-id], .form-group[data-name="input-short-descriptions"] [data-language-id], .form-group[data-name="input-notes"] [data-language-id]').each(function () {
    setTranslationHandler(this);
  });
  updateEventHandler();

  $('form').on('submit', function () {
    $('input').change();
    $('textarea').change();
    updateTranslationJSON();
    return $(this).find('.has-error').length === $(this).find('.has-error-static').length;
  });

  function updateDescriptionMarkdown () {
    updateMarkdownField('input-markdown', 'descriptions', 'input-descriptions', '300px');
  }

  $('#input-markdown').change(updateDescriptionMarkdown);
  updateDescriptionMarkdown();

  function updateShortDescriptionMarkdown () {
    updateMarkdownField('input-short-description-is-markdown', 'short_descriptions', 'input-short-descriptions', '100px');
  }
  $('#input-short-description-is-markdown').change(updateShortDescriptionMarkdown);
  updateShortDescriptionMarkdown();

  function updateNotesMarkdown () {
    updateMarkdownField('input-notes-is-markdown', 'notes', 'input-notes', '300px');
  }
  $('#input-notes-is-markdown').change(updateNotesMarkdown);
  updateNotesMarkdown();
});
