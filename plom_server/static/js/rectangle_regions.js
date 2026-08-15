/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2024-2025 Andrew Rechnitze
    Copyright (C) 2024-2025 Bryan Tanady
    Copyright (C) 2025-2026 Colin B. Macdonald
    Copyright (C) 2025-2026 Aidan Murphy
*/

// TODO: remove?
/* eslint-disable no-unused-vars */

var image = document.getElementById('reference_image');
var canvas = document.getElementById('canvas');

// these must be initialised in the template
// eslint-disable-next-line no-unassigned-vars
var list_of_rects;

var list_of_labels_html;

/**
 * Draws a list of rectangles.
 * @param {Array} list_of_rects - An array of 4-arrays.
 */
function drawRects(list_of_rects) {
  const lw = 4; // rectangle border linewidth
  // sequence from GNU Octave's default ("help lines")
  const colours = ['#0072BD', '#D95319', '#EDB120', '#7E2F8E', '#77AC30', '#4DBEEE', '#A2142F'];
  var ci = 0;
  var ctx = canvas.getContext('2d');
  for (let r of Object.values(list_of_rects)) {
    ctx.beginPath();
    ctx.lineWidth = lw;
    ctx.fillStyle = colours[ci] + '30';
    ctx.strokeStyle = colours[ci] + '99';
    ci = (ci + 1) % colours.length;
    ctx.rect(r[0] * canvas.width + lw / 2, r[1] * canvas.height + lw / 2, r[2] * canvas.width - lw, r[3] * canvas.height - lw);
    ctx.fill();
    ctx.stroke();
  }
}

/** Make the canvas match the reference image, and redraw the rectangles. */
function repositionCanvas() {
  _initCanvas();
  drawRects(list_of_rects);
}

/** Initialise the Canvas. */
function _initCanvas() {
  // make canvas same as image, which may have changed size and position
  canvas.height = image.height;
  canvas.width = image.width;
  canvas.style.top = image.offsetTop + 'px'; ;
  canvas.style.left = image.offsetLeft + 'px';
}

/** Call various initialisers. */
function init() {
  _initCanvas();
  // console.log('regions: init');
  // console.log(list_of_rects);
  drawRects(list_of_rects);
}

window.addEventListener('load', init);
window.addEventListener('resize', repositionCanvas);
