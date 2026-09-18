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
 * which should be a list of dicts, each of which must have keys
 * 'has_regions' (bool), 'ref_image_html_id' (str), 'canvas_html_id' (str),
 * 'question_regions' (list of dicts, each with `rect` and `qlabel` at least).
 * The HTML/js safety of qlabel is ensured if you use json_script.
 * See question_regions.py: get_region_info_per_page() which generates this.
 */

/**
 * Draws a list of rectangles on a Canvas.
 * @param {Array} blocks - An array of dicts, each dict has
 *                         question_label_str, and rect fields.
 * @param {object} canvas - An HTML Canvas to draw on.
 */
function drawLabeledRectangles(blocks, canvas) {
  const lw = 4; // rectangle border linewidth
  // sequence from GNU Octave's default ("help lines") + one more teal
  const colours = [
    '#0072BD',
    '#D95319',
    '#EDB120',
    '#7E2F8E',
    '#77AC30',
    '#4DBEEE',
    '#A2142F',
    '#007760',
  ];
  var ctx = canvas.getContext('2d');
  for (let i = 0; i < blocks.length; i++) {
    var r = blocks[i].rect;
    var label = blocks[i].qlabel;
    var colour = colours[blocks[i].qidx % colours.length];
    // text with white border draw *before* the rectangle
    ctx.font = '30px Arial';
    ctx.fillStyle = colour;
    ctx.strokeStyle = '#ffffffaa';
    ctx.lineWidth = 1.5 * lw;
    ctx.lineJoin = 'round';
    var tx = r[0] * canvas.width + lw / 2 + 10;
    var ty = (r[1] + r[3]) * 0.5 * canvas.height + 10;
    ctx.strokeText(label, tx, ty);

    // now the rectangle
    ctx.beginPath();
    ctx.lineWidth = lw;
    ctx.fillStyle = colour + '1b';
    ctx.strokeStyle = colour + '99';
    ctx.rect(
      r[0] * canvas.width + lw / 2,
      r[1] * canvas.height + lw / 2,
      (r[2] - r[0]) * canvas.width - lw,
      (r[3] - r[1]) * canvas.height - lw,
    );
    ctx.fill();
    ctx.stroke();

    // and the coloured text itself
    ctx.fillStyle = colour;
    ctx.fillText(label, tx, ty);
  }
}

/** Make the canvas match the reference image, and draw the rectangles, labels etc. */
function drawTheStuff() {
  const data = JSON.parse(document.getElementById('rectangle-regions-data').textContent);
  for (let row of data) {
    if (row.has_regions) {
      // console.log(row);
      var image = document.getElementById(row.ref_image_html_id);
      var canvas = document.getElementById(row.canvas_html_id);
      _initCanvas(canvas, image);
      drawLabeledRectangles(row.question_regions, canvas);
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
