/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2024-2025 Andrew Rechnitze
    Copyright (C) 2024-2025 Bryan Tanady
    Copyright (C) 2025-2026 Colin B. Macdonald
    Copyright (C) 2025-2026 Aidan Murphy
*/

/** This is a toolkit to display rectangles in js. Alone, it doesn't do anything. */

/**
 * Draws a list of rectangles on a Canvas.
 * @param {Array} blocks - An array of dicts, each dict has
 *                         question_label_str, and rect fields.
 * @param {object} canvas - An HTML Canvas to draw on.
 */
export function drawLabeledRectangles(blocks, canvas) {
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
  const ctx = canvas.getContext('2d');
  for (let i = 0; i < blocks.length; i++) {
    const r = blocks[i].rect;
    const label = blocks[i].qlabel;
    const colour = colours[blocks[i].qidx % colours.length];
    // text with white border draw *before* the rectangle
    ctx.font = '30px Arial';
    ctx.fillStyle = colour;
    ctx.strokeStyle = '#ffffffaa';
    ctx.lineWidth = 1.5 * lw;
    ctx.setLineDash([]);
    ctx.lineJoin = 'round';
    const tx = r[0] * canvas.width + lw / 2 + 10;
    const ty = (r[1] + r[3]) * 0.5 * canvas.height + 10;
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
