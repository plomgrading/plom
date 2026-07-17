/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2025-2026 Aidan Murphy
    Copyright (C) 2025 Colin B. Macdonald
*/

/* This script adds listeners for htmx responseError and sendError events
 and displays event text in a sticky div at the top of the screen.
 You must have bootstrap loaded to use this.
*/

/** Listens for htmx responses with 400 and 500 code errors. */
document.body.addEventListener('htmx:responseError', (event) => {
  // there's probably more debug info in this event that might be helpful
  const response_payload = event.detail.xhr.response;
  displayDismissableAlert(response_payload, 'alert-danger');
});

/** Listens for htmx requests that can't reach the server. */
document.body.addEventListener('htmx:sendError', (event) => {
  const target_url = event.detail.xhr.responseURL;
  const alert_text = `Unsuccessful htmx request addressed to ${target_url}.<br /><b>The server couldn't be reached</b>.`;
  displayDismissableAlert(alert_text, 'alert-secondary');
});

/**
 * Display a dismissable alert on screen using bootstrap.
 * @param {string} html_content - An html string to display in the alert.
 * @param {string} alert_type - A bootstrap class for the alert style. It
 *   should be something like "primary", "secondary", "danger" etc.
 */
function displayDismissableAlert(html_content, alert_type = 'alert-danger') {
  const outer_div = document.createElement('div');
  outer_div.className = `alert ${alert_type} alert-dismissible fade show m-1 p-1 shadow`;
  outer_div.role = 'alert';
  outer_div.innerHTML = html_content;

  const close_button = document.createElement('button');
  close_button.className = 'btn-close p-1 m-1';
  close_button.setAttribute('data-bs-dismiss', 'alert');

  outer_div.appendChild(close_button);

  getOrCreateStickyDiv().prepend(outer_div);
}

/**
 * Fetch a sticky div (or create one if it doesn't exist).
 * @param {HTMLElement} div_id - The id of the stickydiv to fetch/create.
 * @returns {HTMLElement} - A sticky div.
 */
function getOrCreateStickyDiv(div_id = 'plomHtmxErrorHandler') {
  var sticky_div = document.getElementById(div_id);
  if (sticky_div !== null)
    return sticky_div;

  sticky_div = document.createElement('div');
  sticky_div.className = 'fixed-top w-50 mx-auto';
  sticky_div.id = div_id;
  document.body.prepend(sticky_div);
  return sticky_div;
}
