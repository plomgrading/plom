/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2024-2025 Andrew Rechnitze
    Copyright (C) 2024-2025 Bryan Tanady
    Copyright (C) 2025-2026 Colin B. Macdonald
    Copyright (C) 2025-2026 Aidan Murphy
*/

/**
 * This javascript routine draw a series of coloured rectangles on top
 * of a list of html canvas/image pairs.
 *
 * The caller must provide a <script> block with id 'rectangle-regions-data',
 * which should be a list of dicts, the format is which TODO.
 */

/**
 * Draws a list of rectangles on a Canvas.
 * @param {Array} list_of_rects - An array of 4-arrays.
 * @param {object} canvas - An HTML Canvas to draw on.
 */
function drawLabeledRectangles(list_of_rects, canvas) {
  const lw = 4; // rectangle border linewidth
  // sequence from GNU Octave's default ("help lines")
  const colours = ['#0072BD', '#D95319', '#EDB120', '#7E2F8E', '#77AC30', '#4DBEEE', '#A2142F'];
  var ci = 0;
  var ctx = canvas.getContext('2d');
  for (let r of Object.values(list_of_rects)) {
    var colour = colours[ci];
    ci = (ci + 1) % colours.length;
    // text with white border draw *before* the rectangle
    ctx.font = '30px Arial';
    ctx.fillStyle = colour;
    ctx.strokeStyle = '#ffffffcc';
    ctx.lineWidth = 1.5 * lw;
    ctx.lineJoin = 'round';
    var tx = r[0] * canvas.width + lw / 2 + 10;
    var ty = (r[1] + 0.5 * r[3]) * canvas.height + 10;
    ctx.strokeText('Q', tx, ty);

    // now the rectangle
    ctx.beginPath();
    ctx.lineWidth = lw;
    ctx.fillStyle = colour + '30';
    ctx.strokeStyle = colour + '99';
    ctx.rect(r[0] * canvas.width + lw / 2, r[1] * canvas.height + lw / 2, r[2] * canvas.width - lw, r[3] * canvas.height - lw);
    ctx.fill();
    ctx.stroke();

    // and the coloured text itself
    ctx.fillStyle = colour;
    ctx.fillText('Q', tx, ty);
  }
}

/** Make the canvas match the reference image, and draw the rectangles, labels etc. */
function drawTheStuff() {
  const data = JSON.parse(document.getElementById('rectangle-regions-data').textContent);
  for (let row of data) {
    if (row.has_regions) {
      // console.log(row);
      // these ids must match what is written in the HTML (TODO: store in data?)
      var image = document.getElementById('reference_image_pg' + String(row.page));
      var canvas = document.getElementById('canvas_pg' + String(row.page));
      _initCanvas(canvas, image);
      drawLabeledRectangles(row.page_region_rects, canvas);
    }
  }
}

/**
 * Initialise a Canvas to a particular image.
 * @param {object} canvas - An HTML Canvas element.
 * @param {object} image - An HTML Image element.
 */
function _initCanvas(canvas, image) {
  // make canvas same as image, which may have changed size and position
  canvas.height = image.height;
  canvas.width = image.width;
  canvas.style.top = image.offsetTop + 'px'; ;
  canvas.style.left = image.offsetLeft + 'px';
}

/** Call various initialisers. */
function init() {
  // console.log('regions: init');
  drawTheStuff();
}

window.addEventListener('load', init);
window.addEventListener('resize', drawTheStuff);
