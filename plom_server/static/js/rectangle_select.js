/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2024-2025 Andrew Rechnitze
    Copyright (C) 2024-2025 Bryan Tanady
    Copyright (C) 2025-2026 Colin B. Macdonald
    Copyright (C) 2025-2026 Aidan Murphy
*/

/**
 * This javascript module allows the user to select a box on-top
 * of an image.
 *
 * The html template must have a canvas element with id `canvas`
 * and an img element with id `reference_image`.
 *
 * It must define some variables using Django's `json_script` filter:
 * `top_left_ref_coord`, `bottom_right_ref_coord`.
 * Optionally, there can also be `initial_rectangle` or `initial_rectangle_01_coords`
 * which specify the initial selection, either in QR or [0, 1]-based coordinates.
 * Optionally, there can be a `regions_data` id element from `json_script`
 * containing info about a labelled region.
 *
 * Original event code based on
 * https://medium.com/variance-digital/interactive-rectangular-selection-on-a-responsive-image-761ebe24280.
 */

const image = document.getElementById('reference_image');
const canvas = document.getElementById('canvas');

// These are input elements that any page using this javascript must provide
const h_th_left = document.getElementById('thb_left');
const h_th_top = document.getElementById('thb_top');
const h_th_right = document.getElementById('thb_right');
const h_th_bottom = document.getElementById('thb_bottom');
const h_plom_tl_x = document.getElementById('plom_left');
const h_plom_tl_y = document.getElementById('plom_top');
const h_plom_br_x = document.getElementById('plom_right');
const h_plom_br_y = document.getElementById('plom_bottom');

const handleRadius = 10;

// represents the corners of the interactive rectangle in the canvas
// unit coordinate system (which is dependent on the current layout)
let rect = { left: 50, top: 50, width: 150, height: 100 };

// global variables used in mouse movement deltas
let startX, startY;
let dragWholeRect = false;
let dragTL = false, dragBL = false, dragTR = false, dragBR = false;

import { drawLabeledRectangles } from './rectangle_tools.js';

/**
 * Set the initial rectangle from an array in the QR coordinate system.
 * @param {Array} initial_rect - 4 numbers in the "QR"-based coordinate system.
 */
function set_initial_rectangle_from_qr_coord(initial_rect) {
  const top_left_coord = JSON.parse(document.getElementById('top_left_ref_coord').textContent);
  const bottom_right_coord = JSON.parse(document.getElementById('bottom_right_ref_coord').textContent);
  const w = bottom_right_coord[0] - top_left_coord[0];
  const h = bottom_right_coord[1] - top_left_coord[1];
  const left = initial_rect[0] * w + top_left_coord[0];
  const right = initial_rect[2] * w + top_left_coord[0];
  const top = initial_rect[1] * h + top_left_coord[1];
  const bottom = initial_rect[3] * h + top_left_coord[1];
  const ratio_w = canvas.width / image.naturalWidth;
  const ratio_h = canvas.height / image.naturalHeight;
  rect.width = (right - left) * ratio_w;
  rect.height = (bottom - top) * ratio_h;
  rect.left = left * ratio_w;
  rect.top = top * ratio_h;
}

/**
 * Set the initial rectangle from an array in [0, 1] coordinate system.
 * @param {Array} initial_rect - 4 numbers in a normalized [0, 1] coordinate system.
 */
function set_initial_rectangle_from_01_coord(initial_rect) {
  const w = canvas.width;
  const h = canvas.height;
  const left = initial_rect[0] * w;
  const right = initial_rect[2] * w;
  const top = initial_rect[1] * h;
  const bottom = initial_rect[3] * h;
  rect.width = right - left;
  rect.height = bottom - top;
  rect.left = left;
  rect.top = top;
}

/** Update input elements on an associated HTML page with rectangle corner values. */
function updateHiddenInputs() {
  // image.naturalWidth is number of pixels, vs image.width which depends on size on page
  const inverse_ratio_w = image.naturalWidth / canvas.width;
  const inverse_ratio_h = image.naturalHeight / canvas.height;
  h_th_left.value = Math.round(rect.left * inverse_ratio_w);
  h_th_top.value = Math.round(rect.top * inverse_ratio_h);
  h_th_right.value = Math.round((rect.left + rect.width) * inverse_ratio_w);
  h_th_bottom.value = Math.round((rect.top + rect.height) * inverse_ratio_h);

  const top_left_coord = JSON.parse(document.getElementById('top_left_ref_coord').textContent);
  const bottom_right_coord = JSON.parse(document.getElementById('bottom_right_ref_coord').textContent);

  const w = bottom_right_coord[0] - top_left_coord[0];
  const h = bottom_right_coord[1] - top_left_coord[1];

  h_plom_tl_x.value = (h_th_left.value - top_left_coord[0]) / w;
  h_plom_tl_y.value = (h_th_top.value - top_left_coord[1]) / h;
  h_plom_br_x.value = (h_th_right.value - top_left_coord[0]) / w;
  h_plom_br_y.value = (h_th_bottom.value - top_left_coord[1]) / h;
}

/**
 * Draws a circle.
 * @param {object} ctx - Context for drawing operations.
 * @param {number} x - X coordinate of circle's centre.
 * @param {number} y - Y coordinate of circle's centre.
 * @param {number} radius - Circle's radius.
 */
function drawCircle(ctx, x, y, radius) {
  ctx.fillStyle = '#008080';
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, 2 * Math.PI);
  ctx.fill();
}

/**
 * Draw circles on the corners of the rectangle.
 * @param {object} ctx - Context for drawing operations.
 * @param {object} rect - Dict specifying the rectangle.
 */
function drawHandles(ctx, rect) {
  drawCircle(ctx, rect.left, rect.top, handleRadius);
  drawCircle(ctx, rect.left + rect.width, rect.top, handleRadius);
  drawCircle(ctx, rect.left + rect.width, rect.top + rect.height, handleRadius);
  drawCircle(ctx, rect.left, rect.top + rect.height, handleRadius);
}

/** Draw a box for Plom's QR coordinate system. */
function drawQRCoordBox() {
  const ctx = canvas.getContext('2d');
  const ratio_w = canvas.width / image.naturalWidth;
  const ratio_h = canvas.height / image.naturalHeight;

  const top_left_coord = JSON.parse(document.getElementById('top_left_ref_coord').textContent);
  const bottom_right_coord = JSON.parse(document.getElementById('bottom_right_ref_coord').textContent);

  ctx.strokeStyle = '#ff8000';
  ctx.setLineDash([2, 4]);
  ctx.fillStyle = '#ff8000';
  ctx.beginPath();
  ctx.lineWidth = '2';
  ctx.rect(top_left_coord[0] * ratio_w, top_left_coord[1] * ratio_h, (bottom_right_coord[0] - top_left_coord[0]) * ratio_w, (bottom_right_coord[1] - top_left_coord[1]) * ratio_h);
  ctx.stroke();
}

/** Draw the selection rectangle. */
function drawSelectionRect() {
  let ctx = canvas.getContext('2d');
  ctx.beginPath();
  ctx.lineWidth = '2';
  ctx.fillStyle = '#00808050';
  ctx.strokeStyle = '#008080';
  ctx.rect(rect.left, rect.top, rect.width, rect.height);
  ctx.fill();
  ctx.stroke();
  drawHandles(ctx, rect);
}

/** Draw all the bits and pieces. */
function drawStuff() {
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  drawQRCoordBox();

  let regions = [];
  let elm = document.getElementById('regions_data');
  if (elm) {
    regions = JSON.parse(elm.textContent);
  }
  drawLabeledRectangles(regions, canvas);

  drawSelectionRect();

  updateHiddenInputs();
}

/** Sets global vars when the mouse button is lifted. */
function mouseUp() {
  dragTL = dragTR = dragBL = dragBR = false;
  dragWholeRect = false;
}

// mousedown connected functions -- START
/**
 * Check if a certain coordinate is in a given rectangle.
 * @param {number} x - The X coord.
 * @param {number} y - The Y coord.
 * @param {object} r - The rectangle to check.
 * @returns {boolean} - `true` if the coords are in the rectangle.
 */
function checkInRect(x, y, r) {
  return (x > r.left && x < (r.width + r.left)) && (y > r.top && y < (r.top + r.height));
}

/**
 * Are the given numbers close enough for Plom's liking?
 * @param {number} p1 - A number, in local canvas coord sys.
 * @param {number} p2 - A number, in local canvas coord sys.
 * @returns {boolean} - `true` if the points are close enough.
 */
function checkCloseEnough(p1, p2) {
  return Math.abs(p1 - p2) < handleRadius;
}

/**
 * Get the position of the user's mouse, relative to the rectangle.
 * @param {HTMLCanvasElement} canvas
 * @param {Event} evt
 * @returns {{x: number, y: number}} - A point object indicating where the cursor is.
 */
function getMousePos(canvas, evt) {
  var clx, cly;
  if (evt.type == 'touchstart' || evt.type == 'touchmove') {
    clx = evt.touches[0].clientX;
    cly = evt.touches[0].clientY;
  }
  else {
    clx = evt.clientX;
    cly = evt.clientY;
  }
  const boundingRect = canvas.getBoundingClientRect();
  return {
    x: clx - boundingRect.left,
    y: cly - boundingRect.top,
  };
}

/**
 * Resize rectangle, or drag it, depending on the mouse position. It's
 * assumed that this function is attached to an event listener on a Canvas object.
 * @param {Event} e
 */
function mouseDown(e) {
  // we assume `this` is a Canvas object.
  let pos = getMousePos(this, e);
  let mouseX = pos.x;
  let mouseY = pos.y;
  // 1. top left
  if (checkCloseEnough(mouseX, rect.left) && checkCloseEnough(mouseY, rect.top)) {
    dragTL = true;
  }
  // 2. top right
  else if (checkCloseEnough(mouseX, rect.left + rect.width) && checkCloseEnough(mouseY, rect.top)) {
    dragTR = true;
  }
  // 3. bottom left
  else if (checkCloseEnough(mouseX, rect.left) && checkCloseEnough(mouseY, rect.top + rect.height)) {
    dragBL = true;
  }
  // 4. bottom right
  else if (checkCloseEnough(mouseX, rect.left + rect.width) && checkCloseEnough(mouseY, rect.top + rect.height)) {
    dragBR = true;
  }
  // 5. inside movable rectangle
  else if (checkInRect(mouseX, mouseY, rect)) {
    dragWholeRect = true;
    startX = mouseX;
    startY = mouseY;
  }
  else {
    // handle not resizing
  }
  drawStuff();
}
// mousedown connected functions -- END

/**
 * What to do when the mouse moves. Again, it's assumed that this is
 * part of an event listener attached to a Canvas object.
 * @param {Event} e
 */
function mouseMove(e) {
  let pos = getMousePos(this, e);
  let mouseX = pos.x;
  let mouseY = pos.y;
  if (dragWholeRect) {
    e.preventDefault();
    e.stopPropagation();
    let dx = mouseX - startX;
    let dy = mouseY - startY;
    if ((rect.left + dx) > 0 && (rect.left + dx + rect.width) < canvas.width) {
      rect.left += dx;
    }
    if ((rect.top + dy) > 0 && (rect.top + dy + rect.height) < canvas.height) {
      rect.top += dy;
    }
    startX = mouseX;
    startY = mouseY;
  }
  else if (dragTL) {
    e.preventDefault();
    e.stopPropagation();
    let newSideX = Math.abs(rect.left + rect.width - mouseX);
    let newSideY = Math.abs(rect.height + rect.top - mouseY);
    if ((newSideX > 20) && (newSideY > 20)) {
      rect.left = rect.left + rect.width - newSideX;
      rect.top = rect.height + rect.top - newSideY;
      rect.width = newSideX;
      rect.height = newSideY;
    }
  }
  else if (dragTR) {
    e.preventDefault();
    e.stopPropagation();
    let newSideX = Math.abs(mouseX - rect.left);
    let newSideY = Math.abs(rect.height + rect.top - mouseY);
    if ((newSideX > 20) && (newSideY > 20)) {
      rect.top = rect.height + rect.top - newSideY;
      rect.width = newSideX;
      rect.height = newSideY;
    }
  }
  else if (dragBL) {
    e.preventDefault();
    e.stopPropagation();
    let newSideX = Math.abs(rect.left + rect.width - mouseX);
    let newSideY = Math.abs(rect.top - mouseY);
    if ((newSideX > 20) && (newSideY > 20)) {
      rect.left = rect.left + rect.width - newSideX;
      rect.width = newSideX;
      rect.height = newSideY;
    }
  }
  else if (dragBR) {
    e.preventDefault();
    e.stopPropagation();
    let newSideX = Math.abs(mouseX - rect.left);
    let newSideY = Math.abs(rect.top - mouseY);
    if ((newSideX > 20) && (newSideY > 20)) {
      rect.width = newSideX;
      rect.height = newSideY;
    }
  }
  drawStuff();
}

/** Make the canvas match the reference image, and update the rectangle. */
function repositionCanvas() {
  const old_canvas_rect_width = canvas.width;
  const old_canvas_rect_height = canvas.height;
  // make canvas same as image, which may have changed size and position
  canvas.height = image.height;
  canvas.width = image.width;
  canvas.style.top = image.offsetTop + 'px'; ;
  canvas.style.left = image.offsetLeft + 'px';
  // compute ratio comparing the NEW canvas rect with the OLD (current)
  const ratio_w = canvas.width / old_canvas_rect_width;
  const ratio_h = canvas.height / old_canvas_rect_height;
  // update rect coordinates
  rect.top = rect.top * ratio_h;
  rect.left = rect.left * ratio_w;
  rect.height = rect.height * ratio_h;
  rect.width = rect.width * ratio_w;
  drawStuff();
}

/** Initialise the Canvas. */
function initCanvas() {
  canvas.height = image.height;
  canvas.width = image.width;
  canvas.style.top = image.offsetTop + 'px';
  canvas.style.left = image.offsetLeft + 'px';
}

/** Call various initialisers, and add event listeners to the canvas. */
function init() {
  initCanvas();
  let elm = document.getElementById('initial_rectangle');
  if (elm) {
    let tmp = JSON.parse(elm.textContent);
    if (tmp.length) {
      set_initial_rectangle_from_qr_coord(tmp);
    }
  }
  let elm2 = document.getElementById('initial_rectangle_01_coords');
  if (elm2) {
    let tmp = JSON.parse(elm2.textContent);
    if (tmp.length) {
      set_initial_rectangle_from_01_coord(tmp);
    }
  }
  canvas.addEventListener('mousedown', mouseDown, false);
  canvas.addEventListener('mouseup', mouseUp, false);
  canvas.addEventListener('mousemove', mouseMove, false);
  canvas.addEventListener('touchstart', mouseDown);
  canvas.addEventListener('touchmove', mouseMove);
  canvas.addEventListener('touchend', mouseUp);
  drawStuff();
}

window.addEventListener('load', init);
window.addEventListener('resize', repositionCanvas);
