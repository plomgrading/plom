/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2024-2025 Andrew Rechnitze
    Copyright (C) 2024-2025 Bryan Tanady
    Copyright (C) 2025 Colin B. Macdonald
*/

// Code idea copied from
// https://medium.com/variance-digital/interactive-rectangular-selection-on-a-responsive-image-761ebe24280

var image = document.getElementById('reference_image');
var canvas = document.getElementById('canvas');

// These are input elements that any page using this javascript must provide
var h_th_left = document.getElementById('thb_left');
var h_th_top = document.getElementById('thb_top');
var h_th_right = document.getElementById('thb_right');
var h_th_bottom = document.getElementById('thb_bottom');

var h_plom_tl_x = document.getElementById('plom_left');
var h_plom_tl_y = document.getElementById('plom_top');
var h_plom_br_x = document.getElementById('plom_right');
var h_plom_br_y = document.getElementById('plom_bottom');

var handleRadius = 10

var dragTL, dragBL, dragTR, dragBR;
dragTL = dragBL = dragTR = dragBR = false;

var dragWholeRect = false;

var rect = {}
var current_canvas_rect = {}

var mouseX, mouseY
var startX, startY

// the initial rectangle should be given in [0, 1] coords.
var initial_rect = [0.1, 0.1, 0.1 + 0.2, 0.1 + 0.1]
/* exported setInitialIDBoxRectangle */
// above is the correct way, but not working :(
// eslint-disable-next-line no-unused-vars
function setInitialIDBoxRectangle(id_box_rect) {
  initial_rect = id_box_rect;
}

// these must be initialised in the template
var top_left_coord;
var bottom_right_coord;

// some starting values
var th_left = 0;
var th_top = 0;
var th_right = 256;
var th_bottom = 128;

var th_width = th_right - th_left;
var th_height = th_bottom - th_top;

// some starting values
var effective_image_width = 1700;
var effective_image_height = 2200;
// update these values after the image has loaded
image.onload = function() {
  effective_image_width = image.naturalWidth;
  effective_image_height = image.naturalHeight;

  var w = bottom_right_coord[0] - top_left_coord[0];
  var h = bottom_right_coord[1] - top_left_coord[1];

  th_left = initial_rect[0]*w+top_left_coord[0];
  th_right = initial_rect[2]*w+top_left_coord[0];
  th_top = initial_rect[1]*h+top_left_coord[1];
  th_bottom = initial_rect[3]*h+top_left_coord[1];

  th_width = th_right - th_left;
  th_height = th_bottom - th_top;
}

// drawRectInCanvas() connected functions -- START
function updateHiddenInputs() {
  var inverse_ratio_w =  effective_image_width / canvas.width;
  var inverse_ratio_h = effective_image_height / canvas.height ;
  h_th_left.value = Math.round(rect.left * inverse_ratio_w)
  h_th_top.value = Math.round(rect.top * inverse_ratio_h)
  h_th_right.value = Math.round((rect.left + rect.width) * inverse_ratio_w)
  h_th_bottom.value = Math.round((rect.top + rect.height) * inverse_ratio_h)

  var w = bottom_right_coord[0] - top_left_coord[0];
  var h = bottom_right_coord[1] - top_left_coord[1];

  h_plom_tl_x.value = (h_th_left.value - top_left_coord[0])/w;
  h_plom_tl_y.value = (h_th_top.value - top_left_coord[1])/h;
  h_plom_br_x.value = (h_th_right.value - top_left_coord[0])/w;
  h_plom_br_y.value = (h_th_bottom.value - top_left_coord[1])/h;
}

function drawCircle(x, y, radius) {
  var ctx = canvas.getContext("2d");
  ctx.fillStyle = "#008080";
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, 2 * Math.PI);
  ctx.fill();
}

function drawHandles() {
  drawCircle(rect.left, rect.top, handleRadius);
  drawCircle(rect.left + rect.width, rect.top, handleRadius);
  drawCircle(rect.left + rect.width, rect.top + rect.height, handleRadius);
  drawCircle(rect.left, rect.top + rect.height, handleRadius);
}

function drawPlomBits() {
  // draw plom coordinate system
  var ctx = canvas.getContext("2d");
  var ratio_w = canvas.width / effective_image_width;
  var ratio_h = canvas.height / effective_image_height;
  ctx.strokeStyle = "#ff8000";
  ctx.setLineDash([2,4])
  ctx.fillStyle = "#ff8000";
  for (let v of Object.values(rect)) {
    ctx.beginPath();
    ctx.arc(v[0]*ratio_w,v[1]*ratio_h,8, 0,2*Math.PI);
    ctx.fill();
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.lineWidth = "2";
  ctx.rect(top_left_coord[0]*ratio_w, top_left_coord[1]*ratio_h, (bottom_right_coord[0]-top_left_coord[0])*ratio_w, (bottom_right_coord[1]-top_left_coord[1])*ratio_h);
  ctx.stroke();
}
function drawRectInCanvas() {
  var ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.beginPath();
  ctx.lineWidth = "2";
  ctx.fillStyle = "#00808050";
  ctx.strokeStyle = "#008080";
  ctx.rect(rect.left, rect.top, rect.width, rect.height);
  ctx.fill();
  ctx.stroke();
  drawHandles();
  drawPlomBits();

  updateHiddenInputs()
}
//drawRectInCanvas() connected functions -- END

function mouseUp() {
  dragTL = dragTR = dragBL = dragBR = false;
  dragWholeRect = false;
}

//mousedown connected functions -- START
function checkInRect(x, y, r) {
  return (x>r.left && x<(r.width+r.left)) && (y>r.top && y<(r.top+r.height));
}

function checkCloseEnough(p1, p2) {
  return Math.abs(p1 - p2) < handleRadius;
}

function getMousePos(canvas, evt) {
  var clx, cly
  if (evt.type == "touchstart" || evt.type == "touchmove") {
    clx = evt.touches[0].clientX;
    cly = evt.touches[0].clientY;
  } else {
    clx = evt.clientX;
    cly = evt.clientY;
  }
  var boundingRect = canvas.getBoundingClientRect();
  return {
    x: clx - boundingRect.left,
    y: cly - boundingRect.top
  };
}

function mouseDown(e) {
  var pos = getMousePos(this, e);
  mouseX = pos.x;
  mouseY = pos.y;
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
  drawRectInCanvas();
}
//mousedown connected functions -- END

function mouseMove(e) {
  var pos = getMousePos(this, e);
  mouseX = pos.x;
  mouseY = pos.y;
  if (dragWholeRect) {
      e.preventDefault();
      e.stopPropagation();
      let dx = mouseX - startX;
      let dy = mouseY - startY;
      if ((rect.left+dx)>0 && (rect.left+dx+rect.width)<canvas.width) {
        rect.left += dx;
      }
      if ((rect.top+dy)>0 && (rect.top+dy+rect.height)<canvas.height) {
        rect.top += dy;
      }
      startX = mouseX;
      startY = mouseY;
  } else if (dragTL) {
      e.preventDefault();
      e.stopPropagation();
      let newSideX = Math.abs(rect.left+rect.width - mouseX)
      let newSideY = Math.abs(rect.height + rect.top - mouseY);
      if ( (newSideX>20) && (newSideY>20)) {
        rect.left = rect.left + rect.width - newSideX;
        rect.top = rect.height + rect.top - newSideY;
        rect.width = newSideX; rect.height = newSideY;
      }
  } else if (dragTR) {
      e.preventDefault();
      e.stopPropagation();
      let newSideX = Math.abs(mouseX-rect.left);
      let newSideY = Math.abs(rect.height + rect.top - mouseY);
      if ( (newSideX>20) && (newSideY>20) ) {
          rect.top = rect.height + rect.top - newSideY;
          rect.width = newSideX;
          rect.height = newSideY;
      }
  } else if (dragBL) {
      e.preventDefault();
      e.stopPropagation();
      let newSideX = Math.abs(rect.left+rect.width-mouseX);
      let newSideY = Math.abs(rect.top - mouseY);
      if ( (newSideX>20) && (newSideY>20) ) {
        rect.left = rect.left + rect.width - newSideX;
        rect.width = newSideX; rect.height = newSideY;
      }
  } else if (dragBR) {
      e.preventDefault();
      e.stopPropagation();
      let newSideX = Math.abs(mouseX-rect.left);
      let newSideY = Math.abs(rect.top - mouseY);
      if ( (newSideX>20) && (newSideY>20) ) {
        rect.width = newSideX; rect.height = newSideY;
      }
  }
  drawRectInCanvas();
}

function updateCurrentCanvasRect() {
  current_canvas_rect.height = canvas.height
  current_canvas_rect.width = canvas.width
  current_canvas_rect.top = image.offsetTop
  current_canvas_rect.left = image.offsetLeft
}

function repositionCanvas() {
  //make canvas same as image, which may have changed size and position
  canvas.height = image.height;
  canvas.width = image.width;
  canvas.style.top = image.offsetTop + "px";;
  canvas.style.left = image.offsetLeft + "px";
  //compute ratio comparing the NEW canvas rect with the OLD (current)
  var ratio_w = canvas.width / current_canvas_rect.width;
  var ratio_h = canvas.height / current_canvas_rect.height;
  //update rect coordinates
  rect.top = rect.top * ratio_h;
  rect.left = rect.left * ratio_w;
  rect.height = rect.height * ratio_h;
  rect.width = rect.width * ratio_w;
  updateCurrentCanvasRect();
  drawRectInCanvas();
}

function initCanvas() {
  canvas.height = image.height;
  canvas.width = image.width;
  canvas.style.top = image.offsetTop + "px";;
  canvas.style.left = image.offsetLeft + "px";
  updateCurrentCanvasRect();
}

function initRect() {
  var ratio_w = canvas.width / effective_image_width;
  var ratio_h = canvas.height / effective_image_height;

  rect.height = th_height*ratio_h;
  rect.width = th_width*ratio_w;
  rect.top = th_top*ratio_h;
  rect.left = th_left*ratio_w;
}


function init() {
  canvas.addEventListener('mousedown', mouseDown, false);
  canvas.addEventListener('mouseup', mouseUp, false);
  canvas.addEventListener('mousemove', mouseMove, false);
  canvas.addEventListener('touchstart', mouseDown);
  canvas.addEventListener('touchmove', mouseMove);
  canvas.addEventListener('touchend', mouseUp);
  initCanvas();
  initRect();
  drawRectInCanvas();
}

window.addEventListener('load', init)
window.addEventListener('resize', repositionCanvas)

//
