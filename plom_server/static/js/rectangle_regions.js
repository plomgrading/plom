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
 * 'question_regions' (list of dicts, each with `rect`, `qidx`, and `qlabel`).
 * The HTML/js safety of qlabel is ensured if you use json_script.
 * See question_regions.py: get_region_info_per_page() which generates this.
 */

import { drawLabeledRectangles } from './rectangle_tools.js';

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
  // setting the width / height wipes the drawing
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
