'use strict';
/* eslint-env jquery */

import {
  setupImageDragAndDrop
} from './markdown_image_upload.js';

import {
  initMarkdownField
} from './sampledb-internationalization.js';

import {
  applySchemaConditions
} from './conditional_wrapper.js';

import {
  addActionFilterButton
} from './object_form/object-reference.js';

window.mdeFields = [];

// Enable to control that only one element can be edited in time
let selectedElement = null;
let formChanged = false;

// Recognize if error occurred to avoid missing a change in datetime-objects
let formErrorEdit = false;
// Log if the user is editing an entry in the moment
let isEditing = false;

/**
 * Stop editing the field and send the edited data, if any.
 * @param initialFormData the form data before editing
 * @param editedFormData the form data after editing
 */
function stopEditing (initialFormData, editedFormData) {
  // Set the cursor style to 'wait' to indicate the website is loading
  document.body.style.cursor = 'wait';

  // Determine edited fields and properties
  const previousData = {};
  for (const field of initialFormData) {
    previousData[field.name] = field.value;
  }
  const newData = {};
  for (const field of editedFormData) {
    newData[field.name] = field.value;
  }
  const editedFields = [];
  for (const field of initialFormData) {
    if (!Object.prototype.hasOwnProperty.call(newData, field.name) || (newData[field.name] !== field.value)) {
      editedFields.push(field.name);
    }
  }
  for (const field of editedFormData) {
    if (!Object.prototype.hasOwnProperty.call(previousData, field.name)) {
      editedFields.push(field.name);
    }
  }
  const editedPropertyIDPrefixes = [];
  for (const fieldName of editedFields) {
    const propertyIDPrefix = fieldName.split('__').slice(0, -1).join('__') + '_';
    if (!editedPropertyIDPrefixes.includes(propertyIDPrefix)) {
      editedPropertyIDPrefixes.push(propertyIDPrefix);
    }
  }
  formChanged = editedPropertyIDPrefixes.length > 0;

  if (!formChanged) {
    isEditing = false;
    document.body.style.cursor = 'default';
    return;
  }
  sendData(editedFormData, editedPropertyIDPrefixes);
}

/**
 * Send the edited data to SampleDB.
 * @param editedFormData the form data after editing
 * @param editedPropertyIDPrefixes the ID prefixes of all edited fields
 */
function sendData (editedFormData, editedPropertyIDPrefixes) {
  const data = {
    action_submit: 'inline_edit'
  };
  for (const field of editedFormData) {
    const key = field.name;
    let value = field.value;
    if (key.endsWith('__units')) {
      value = value.replaceAll(/\s/g, '');
    }
    data[key] = value;
  }

  // POST the data to SampleDB
  $.post(window.location.href.split('?')[0] + '?mode=edit', data, function () {
    // Reload website to show that the change has been successful and to being able to edit the new object
    window.location.reload();
  }).fail(function (response) {
    formErrorEdit = true;
    document.body.style.cursor = 'default';
    isEditing = false;
    let errors = {};
    let hasUnexpectedErrors = false;
    try {
      errors = JSON.parse(response.responseText).errors;
    } catch (e) {
      // SampleDB did not return the expected JSON response containing errors
      hasUnexpectedErrors = true;
    }
    const errorFields = Object.keys(errors);
    if (errorFields.length === 0) {
      // something broke without reporting errors
      hasUnexpectedErrors = true;
    }
    for (let i = 0; i < errorFields.length && !hasUnexpectedErrors; i++) {
      const fieldName = errorFields[i];
      const propertyIDPrefix = fieldName.split('__').slice(0, -1).join('__') + '_';
      if (!editedPropertyIDPrefixes.includes(propertyIDPrefix)) {
        hasUnexpectedErrors = true;
        break;
      }
    }
    if (hasUnexpectedErrors) {
      // show generic error, independent of the changed field
      $('#inline-edit-alert').show();
    } else {
      // display error messages for changed field
      let errorMessages = Object.values(errors);
      // remove duplicate error messages
      const seen = {};
      errorMessages = errorMessages.filter(function (item) {
        return Object.prototype.hasOwnProperty.call(seen, item) ? false : (seen[item] = true);
      });
      $(selectedElement).find('.alert-upload-failed').text(errorMessages.join(' ')).show();
      $(selectedElement).addClass('alert alert-danger');
    }
  });
}

/**
 * Set up a form area for editing instead of viewing its content.
 * @param formArea a form area jQuery element
 */
function startEditing (formArea) {
  const form = $('.form-horizontal').first();
  // Save form data before editing
  const initialFormData = form.serializeArray();
  // Make all form elements visible
  formArea.find('.form-switch').show();
  // Hide view elements
  formArea.find('.view-switch').hide();
  // Set up markdown fields in the form area
  formArea.find('textarea[data-markdown-textarea="true"]').each(function (_, e) {
    if ($(this).attr('markdown-editor-initialized') !== 'true') {
      $(this).attr('markdown-editor-initialized', 'true');
      setupImageDragAndDrop(initMarkdownField(this, '100px'));
    }
  });
  // Focus the element to being able to directly start typing
  const focusableElements = formArea.find('input[type=text], input[type=textarea], textarea[display!=none]');
  if (focusableElements.length > 0) {
    focusableElements[0].focus();
  }

  function eventFunction (event) {
    // If active element lost focus or user pressed enter
    if (((event.type === 'click' && !formArea[0].contains(event.target) && (event.target.parentElement === null || !event.target.parentElement.classList.contains('tag')))) || ((event.type === 'keyup' && event.keyCode === 13) && !event.target.classList.contains('tt-input'))) {
      event.stopPropagation();
      if (document.activeElement.type !== 'textarea') {
        // Hide all form elements
        formArea.find('.form-switch').hide();
        // Show all view elements
        formArea.find('.view-switch').each(function () {
          $(this).css('display', '');
        });
        // Get form data after editing.
        const editedFormData = form.serializeArray();
        // Send actualized data
        stopEditing(initialFormData, editedFormData);
        // Remove event listener to avoid multiple reactions
        document.removeEventListener('click', eventFunction);
        document.removeEventListener('keyup', eventFunction);
      }
    }
  }

  // If clicked outside the focussed element
  document.addEventListener('click', eventFunction);
  // If the user presses enter
  document.addEventListener('keyup', eventFunction);
}

$(document).ready(function () {
  // Prevent submitting form via browser
  $('#data-form').submit(function (event) {
    event.preventDefault();
  });
  // Set event handlers for form areas
  $('.form-area').each(function () {
    const formArea = $(this);
    function onStartEditing () {
      // If no other form changed before or this is the actual element
      if (!isEditing && (!formChanged || formArea[0] === selectedElement)) {
        isEditing = true;
        selectedElement = formArea[0];
        startEditing(formArea);
      }
    }
    // Start editing on doubleclick on a form area...
    formArea.dblclick(onStartEditing);
    // ... or on click on the edit helper of a form area
    formArea.find('.edit-helper').on('click', onStartEditing);
    // Show edit helper on mouseover
    formArea.mouseover(function () {
      if (!formErrorEdit || formArea[0] === selectedElement) {
        $(this).find('.edit-helper').each(function () {
          $(this).css('visibility', 'visible');
        });
      }
    });
    formArea.mouseout(function () {
      $(this).find('.edit-helper').each(function () {
        $(this).css('visibility', 'hidden');
      });
    });
  });

  $.each(window.conditionalWrapperScripts, function () {
    this();
  });

  $('div.objectpicker').each(function () {
    addActionFilterButton($(this));
  });

  applySchemaConditions(document);
});
