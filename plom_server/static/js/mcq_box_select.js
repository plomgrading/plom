/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2026 Deep Shah
*/

/* global
    bottom_right_coord,
    top_left_coord,
    effective_image_width,
    effective_image_height,
    canvas,
    mcq_box_detection_url
*/

(function () {
  const optionLabels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const overlay = document.getElementById('mcq_box_overlay');
  const controls = document.getElementById('mcq_controls');
  const detectButton = document.getElementById('mcq_detect_boxes');
  const addButton = document.getElementById('mcq_add_box');
  const removeButton = document.getElementById('mcq_remove_box');
  const clearButton = document.getElementById('mcq_clear_boxes');
  const autoLabelButton = document.getElementById('mcq_auto_label_boxes');
  const activeLabelSelect = document.getElementById('mcq_active_label');
  const optionCountContainer = document.getElementById('mcq_option_count');
  const optionCountInput = document.getElementById('mcq_num_options');
  const questionTypeInput = document.getElementById('question_type');
  const statusElement = document.getElementById('mcq_detection_status');
  const hiddenInput = document.getElementById('mcq_boxes');

  if (
    !overlay
    || !controls
    || !detectButton
    || !autoLabelButton
    || !activeLabelSelect
    || !optionCountContainer
    || !questionTypeInput
    || !hiddenInput
  ) {
    return;
  }

  let mcqBoxes = [];
  let activeBoxIndex = -1;
  let dragState = null;

  function clamp(value, low, high) {
    return Math.min(Math.max(value, low), high);
  }

  function roundCoord(value) {
    return Number(value.toFixed(6));
  }

  function getReferenceSize() {
    return {
      width: bottom_right_coord[0] - top_left_coord[0],
      height: bottom_right_coord[1] - top_left_coord[1],
    };
  }

  function canvasDeltaToPlom(dx, dy) {
    const referenceSize = getReferenceSize();
    return {
      dx: (dx * effective_image_width / canvas.width) / referenceSize.width,
      dy: (dy * effective_image_height / canvas.height) / referenceSize.height,
    };
  }

  function plomBoxToCanvasBox(box) {
    const referenceSize = getReferenceSize();
    const absLeft = top_left_coord[0] + box.left * referenceSize.width;
    const absTop = top_left_coord[1] + box.top * referenceSize.height;
    const absRight = top_left_coord[0] + box.right * referenceSize.width;
    const absBottom = top_left_coord[1] + box.bottom * referenceSize.height;
    return {
      left: absLeft * canvas.width / effective_image_width,
      top: absTop * canvas.height / effective_image_height,
      width: (absRight - absLeft) * canvas.width / effective_image_width,
      height: (absBottom - absTop) * canvas.height / effective_image_height,
    };
  }

  function getSelectedRect() {
    const selected = {
      left: parseFloat(document.getElementById('plom_left').value),
      top: parseFloat(document.getElementById('plom_top').value),
      right: parseFloat(document.getElementById('plom_right').value),
      bottom: parseFloat(document.getElementById('plom_bottom').value),
    };
    if (
      !Number.isFinite(selected.left)
      || !Number.isFinite(selected.top)
      || !Number.isFinite(selected.right)
      || !Number.isFinite(selected.bottom)
    ) {
      return null;
    }
    const selectedRect = {
      left: Math.min(selected.left, selected.right),
      top: Math.min(selected.top, selected.bottom),
      right: Math.max(selected.left, selected.right),
      bottom: Math.max(selected.top, selected.bottom),
    };
    if (
      selectedRect.right <= selectedRect.left
      || selectedRect.bottom <= selectedRect.top
    ) {
      return null;
    }
    return selectedRect;
  }

  function getNumOptions() {
    return clamp(parseInt(optionCountInput.value, 10) || 1, 1, optionLabels.length);
  }

  function getAllowedLabels() {
    return optionLabels.slice(0, getNumOptions()).split('');
  }

  function getLabelRank(label) {
    const rank = optionLabels.indexOf(label);
    return rank >= 0 ? rank : optionLabels.length;
  }

  function isMCQMode() {
    return questionTypeInput.value === 'MCQ';
  }

  function setStatus(message, isError) {
    statusElement.textContent = message;
    statusElement.classList.toggle('text-danger', Boolean(isError));
    statusElement.classList.toggle('text-muted', !isError);
  }

  function selectedRectContainsBox(selectedRect, box) {
    const tolerance = 0.000001;
    return (
      box.left >= selectedRect.left - tolerance
      && box.top >= selectedRect.top - tolerance
      && box.right <= selectedRect.right + tolerance
      && box.bottom <= selectedRect.bottom + tolerance
    );
  }

  function getBoxesOutsideSelectedRect(selectedRect) {
    return mcqBoxes.filter(box => !selectedRectContainsBox(selectedRect, box));
  }

  function boxOutsideMessage(boxes) {
    const labels = boxes.map(box => box.label).join(', ');
    const plural = boxes.length === 1 ? '' : 'es';
    return `Option box${plural} ${labels} must stay inside the selected rectangle.`;
  }

  function clampBoxToSelectedRect(box, selectedRect) {
    const selectedWidth = selectedRect.right - selectedRect.left;
    const selectedHeight = selectedRect.bottom - selectedRect.top;
    const width = Math.min(box.right - box.left, selectedWidth);
    const height = Math.min(box.bottom - box.top, selectedHeight);
    const left = clamp(box.left, selectedRect.left, selectedRect.right - width);
    const top = clamp(box.top, selectedRect.top, selectedRect.bottom - height);
    return {
      ...box,
      left,
      top,
      right: left + width,
      bottom: top + height,
    };
  }

  function validateBoxesInsideSelectedRect() {
    if (!isMCQMode() || mcqBoxes.length === 0) {
      return true;
    }
    const selectedRect = getSelectedRect();
    if (!selectedRect) {
      setStatus('Select a rectangle before submitting MCQ boxes.', true);
      return false;
    }
    const outsideBoxes = getBoxesOutsideSelectedRect(selectedRect);
    if (outsideBoxes.length > 0) {
      setStatus(boxOutsideMessage(outsideBoxes), true);
      return false;
    }
    return true;
  }

  function validateBoxLabels() {
    if (!isMCQMode() || mcqBoxes.length === 0) {
      return true;
    }
    const allowedLabels = new Set(getAllowedLabels());
    const seenLabels = new Set();
    for (const box of mcqBoxes) {
      if (!allowedLabels.has(box.label)) {
        setStatus(
          `Option box ${box.label} is not valid for ${getNumOptions()} options.`,
          true,
        );
        return false;
      }
      if (seenLabels.has(box.label)) {
        setStatus(`Option label ${box.label} is used more than once.`, true);
        return false;
      }
      seenLabels.add(box.label);
    }
    return true;
  }

  function syncOverlayToCanvas() {
    overlay.style.left = canvas.style.left;
    overlay.style.top = canvas.style.top;
    overlay.style.width = `${canvas.width}px`;
    overlay.style.height = `${canvas.height}px`;
  }

  function serialiseBox(box) {
    return {
      label: box.label,
      left: roundCoord(box.left),
      top: roundCoord(box.top),
      right: roundCoord(box.right),
      bottom: roundCoord(box.bottom),
    };
  }

  function getBoxesForSubmission() {
    return [...mcqBoxes].sort((a, b) => {
      const labelOrder = getLabelRank(a.label) - getLabelRank(b.label);
      if (labelOrder !== 0) {
        return labelOrder;
      }
      if (a.top === b.top) {
        return a.left - b.left;
      }
      return a.top - b.top;
    });
  }

  function updateHiddenInput() {
    if (!isMCQMode()) {
      hiddenInput.value = '[]';
      return;
    }
    hiddenInput.value = JSON.stringify({
      question_type: questionTypeInput.value,
      num_options: getNumOptions(),
      boxes: getBoxesForSubmission().map(serialiseBox),
    });
  }

  function sortBoxesInReadingOrder(boxes) {
    const sortedByTop = [...boxes].sort((a, b) => {
      if (a.top === b.top) {
        return a.left - b.left;
      }
      return a.top - b.top;
    });
    if (sortedByTop.length === 0) {
      return [];
    }

    const heights = sortedByTop
      .map(box => box.bottom - box.top)
      .sort((a, b) => a - b);
    const medianHeight = heights[Math.floor(heights.length / 2)];
    const rowThreshold = Math.max(medianHeight * 0.75, 0.01);
    const rows = [];

    sortedByTop.forEach((box) => {
      const centerY = (box.top + box.bottom) / 2;
      let row = rows.find(candidate => (
        Math.abs(centerY - candidate.centerY) <= rowThreshold
      ));
      if (!row) {
        row = { centerY, boxes: [] };
        rows.push(row);
      }
      row.boxes.push(box);
      row.centerY = row.boxes.reduce(
        (total, rowBox) => total + (rowBox.top + rowBox.bottom) / 2,
        0,
      ) / row.boxes.length;
    });

    return rows
      .sort((a, b) => a.centerY - b.centerY)
      .flatMap(row => row.boxes.sort((a, b) => a.left - b.left));
  }

  function autoLabelBoxes() {
    const activeBox = activeBoxIndex >= 0 ? mcqBoxes[activeBoxIndex] : null;
    mcqBoxes = sortBoxesInReadingOrder(mcqBoxes);
    mcqBoxes.forEach((box, index) => {
      box.label = optionLabels[index] || '?';
    });
    activeBoxIndex = activeBox ? mcqBoxes.indexOf(activeBox) : activeBoxIndex;
  }

  function getFirstUnusedLabel() {
    const usedLabels = new Set(mcqBoxes.map(box => box.label));
    return getAllowedLabels().find(label => !usedLabels.has(label)) || '?';
  }

  function updateActiveLabelSelect() {
    const activeBox = activeBoxIndex >= 0 ? mcqBoxes[activeBoxIndex] : null;
    activeLabelSelect.replaceChildren();

    const emptyOption = new Option('Select', '');
    activeLabelSelect.appendChild(emptyOption);
    getAllowedLabels().forEach((label) => {
      activeLabelSelect.appendChild(new Option(label, label));
    });

    activeLabelSelect.disabled = !isMCQMode() || !activeBox;
    activeLabelSelect.value = activeBox && getAllowedLabels().includes(activeBox.label)
      ? activeBox.label
      : '';
  }

  function setActiveBox(index) {
    activeBoxIndex = index >= 0 && index < mcqBoxes.length ? index : -1;
    updateActiveLabelSelect();
  }

  function setActiveBoxLabel(label) {
    if (activeBoxIndex < 0 || activeBoxIndex >= mcqBoxes.length || !label) {
      return;
    }
    const activeBox = mcqBoxes[activeBoxIndex];
    const previousLabel = activeBox.label;
    const otherIndex = mcqBoxes.findIndex(
      (box, index) => index !== activeBoxIndex && box.label === label,
    );
    activeBox.label = label;
    if (otherIndex >= 0 && previousLabel !== '?') {
      mcqBoxes[otherIndex].label = previousLabel;
    }
    renderBoxes();
  }

  function renderBoxes() {
    syncOverlayToCanvas();
    overlay.replaceChildren();
    if (!isMCQMode()) {
      updateHiddenInput();
      return;
    }
    mcqBoxes.forEach((box, index) => {
      const canvasBox = plomBoxToCanvasBox(box);
      const boxElement = document.createElement('div');
      boxElement.className = 'mcq-option-box';
      if (index === activeBoxIndex) {
        boxElement.classList.add('active');
      }
      boxElement.dataset.index = index;
      boxElement.style.left = `${canvasBox.left}px`;
      boxElement.style.top = `${canvasBox.top}px`;
      boxElement.style.width = `${canvasBox.width}px`;
      boxElement.style.height = `${canvasBox.height}px`;
      boxElement.title = `Option ${box.label}`;

      const labelElement = document.createElement('span');
      labelElement.className = 'mcq-option-label';
      labelElement.textContent = box.label;
      boxElement.appendChild(labelElement);

      const resizeElement = document.createElement('span');
      resizeElement.className = 'mcq-option-resize';
      resizeElement.dataset.resize = 'true';
      boxElement.appendChild(resizeElement);

      boxElement.addEventListener('pointerdown', startDraggingBox);
      overlay.appendChild(boxElement);
    });
    updateActiveLabelSelect();
    updateHiddenInput();
  }

  function startDraggingBox(event) {
    const boxElement = event.currentTarget;
    setActiveBox(parseInt(boxElement.dataset.index, 10));
    event.preventDefault();
    event.stopPropagation();
    const selectedRect = getSelectedRect();
    if (!selectedRect) {
      setStatus('Select a rectangle before moving option boxes.', true);
      return;
    }
    mcqBoxes[activeBoxIndex] = clampBoxToSelectedRect(
      mcqBoxes[activeBoxIndex],
      selectedRect,
    );
    dragState = {
      mode: event.target.dataset.resize === 'true' ? 'resize' : 'move',
      startX: event.clientX,
      startY: event.clientY,
      original: { ...mcqBoxes[activeBoxIndex] },
      selectedRect,
    };
    renderBoxes();
  }

  function moveActiveBox(event) {
    if (!dragState || activeBoxIndex < 0) {
      return;
    }

    const delta = canvasDeltaToPlom(
      event.clientX - dragState.startX,
      event.clientY - dragState.startY,
    );
    const original = dragState.original;
    const minDelta = canvasDeltaToPlom(12, 12);
    const box = mcqBoxes[activeBoxIndex];
    const selectedRect = dragState.selectedRect;

    if (dragState.mode === 'resize') {
      const maxWidth = selectedRect.right - original.left;
      const maxHeight = selectedRect.bottom - original.top;
      const minWidth = Math.min(minDelta.dx, maxWidth);
      const minHeight = Math.min(minDelta.dy, maxHeight);
      box.right = clamp(
        original.right + delta.dx,
        original.left + minWidth,
        selectedRect.right,
      );
      box.bottom = clamp(
        original.bottom + delta.dy,
        original.top + minHeight,
        selectedRect.bottom,
      );
    }
    else {
      const width = original.right - original.left;
      const height = original.bottom - original.top;
      box.left = clamp(
        original.left + delta.dx,
        selectedRect.left,
        selectedRect.right - width,
      );
      box.top = clamp(
        original.top + delta.dy,
        selectedRect.top,
        selectedRect.bottom - height,
      );
      box.right = box.left + width;
      box.bottom = box.top + height;
    }

    event.preventDefault();
    renderBoxes();
  }

  function finishDraggingBox() {
    if (!dragState) {
      return;
    }
    dragState = null;
    setActiveBox(
      mcqBoxes.length > 0 ? Math.min(activeBoxIndex, mcqBoxes.length - 1) : -1,
    );
    renderBoxes();
  }

  function normaliseDetectedBox(box, selectedRect) {
    return clampBoxToSelectedRect({
      label: box.label,
      left: clamp(box.plom.left, 0, 1),
      top: clamp(box.plom.top, 0, 1),
      right: clamp(box.plom.right, 0, 1),
      bottom: clamp(box.plom.bottom, 0, 1),
    }, selectedRect);
  }

  function detectBoxes() {
    if (!isMCQMode()) {
      return;
    }
    const selectedRect = getSelectedRect();
    if (!selectedRect) {
      setStatus('Select a rectangle before detecting boxes.', true);
      return;
    }

    const params = new URLSearchParams({
      left: selectedRect.left,
      top: selectedRect.top,
      right: selectedRect.right,
      bottom: selectedRect.bottom,
      num_options: getNumOptions(),
    });

    setStatus('Detecting boxes...', false);
    fetch(`${mcq_box_detection_url}?${params.toString()}`, {
      headers: { Accept: 'application/json' },
    })
      .then((response) => {
        if (!response.ok) {
          return response.text().then((text) => {
            throw new Error(text || response.statusText);
          });
        }
        return response.json();
      })
      .then((data) => {
        if (data.error) {
          throw new Error(data.error);
        }
        mcqBoxes = data.boxes.map(box => normaliseDetectedBox(box, selectedRect));
        setActiveBox(mcqBoxes.length > 0 ? 0 : -1);
        autoLabelBoxes();
        renderBoxes();
        if (mcqBoxes.length === getNumOptions()) {
          setStatus(`Detected ${mcqBoxes.length} boxes.`, false);
        }
        else {
          setStatus(`Detected ${mcqBoxes.length} of ${getNumOptions()} boxes.`, false);
        }
      })
      .catch((error) => {
        setStatus(error.message || 'Could not detect boxes.', true);
      });
  }

  function getDefaultBoxSize(selectedRect) {
    if (mcqBoxes.length > 0) {
      const widths = mcqBoxes
        .map(box => box.right - box.left)
        .sort((a, b) => a - b);
      const heights = mcqBoxes
        .map(box => box.bottom - box.top)
        .sort((a, b) => a - b);
      const middle = Math.floor(mcqBoxes.length / 2);
      return {
        width: widths[middle],
        height: heights[middle],
      };
    }
    const selectedHeight = selectedRect.bottom - selectedRect.top;
    const selectedWidth = selectedRect.right - selectedRect.left;
    const size = Math.min(selectedHeight * 0.35, selectedWidth * 0.12);
    return { width: size, height: size };
  }

  function addBox() {
    if (!isMCQMode()) {
      return;
    }
    const selectedRect = getSelectedRect();
    if (!selectedRect) {
      setStatus('Select a rectangle before adding a box.', true);
      return;
    }
    if (mcqBoxes.length >= getNumOptions()) {
      setStatus('Increase the option count before adding another box.', true);
      return;
    }
    const size = getDefaultBoxSize(selectedRect);
    const boxWidth = Math.min(size.width, selectedRect.right - selectedRect.left);
    const boxHeight = Math.min(size.height, selectedRect.bottom - selectedRect.top);
    const optionSlot = Math.min(mcqBoxes.length + 1, getNumOptions());
    const slotGap = (selectedRect.right - selectedRect.left) / (getNumOptions() + 1);
    const centerX = selectedRect.left + slotGap * optionSlot;
    const centerY = selectedRect.top + (selectedRect.bottom - selectedRect.top) / 2;
    const left = clamp(
      centerX - boxWidth / 2,
      selectedRect.left,
      selectedRect.right - boxWidth,
    );
    const top = clamp(
      centerY - boxHeight / 2,
      selectedRect.top,
      selectedRect.bottom - boxHeight,
    );
    mcqBoxes.push({
      label: getFirstUnusedLabel(),
      left,
      top,
      right: left + boxWidth,
      bottom: top + boxHeight,
    });
    setActiveBox(mcqBoxes.length - 1);
    renderBoxes();
    setStatus(`${mcqBoxes.length} boxes selected.`, false);
  }

  function removeActiveBox() {
    if (activeBoxIndex < 0 || activeBoxIndex >= mcqBoxes.length) {
      return;
    }
    mcqBoxes.splice(activeBoxIndex, 1);
    setActiveBox(mcqBoxes.length > 0 ? 0 : -1);
    renderBoxes();
    setStatus(`${mcqBoxes.length} boxes selected.`, false);
  }

  function clearBoxes() {
    mcqBoxes = [];
    setActiveBox(-1);
    renderBoxes();
    setStatus('No boxes selected.', false);
  }

  function updateMCQMode() {
    const enabled = isMCQMode();
    controls.classList.toggle('d-none', !enabled);
    optionCountContainer.classList.toggle('d-none', !enabled);
    overlay.classList.toggle('d-none', !enabled);
    if (!enabled) {
      mcqBoxes = [];
      setActiveBox(-1);
      setStatus('', false);
    }
    renderBoxes();
  }

  detectButton.addEventListener('click', detectBoxes);
  addButton.addEventListener('click', addBox);
  removeButton.addEventListener('click', removeActiveBox);
  clearButton.addEventListener('click', clearBoxes);
  autoLabelButton.addEventListener('click', () => {
    autoLabelBoxes();
    renderBoxes();
    setStatus(`${mcqBoxes.length} boxes labelled in reading order.`, false);
  });
  activeLabelSelect.addEventListener('change', () => {
    setActiveBoxLabel(activeLabelSelect.value);
  });
  optionCountInput.addEventListener('change', () => {
    updateActiveLabelSelect();
    updateHiddenInput();
  });
  questionTypeInput.addEventListener('change', updateMCQMode);
  document.addEventListener('pointermove', moveActiveBox);
  document.addEventListener('pointerup', finishDraggingBox);
  window.addEventListener('resize', renderBoxes);
  window.addEventListener('load', updateMCQMode);
  hiddenInput.form.addEventListener('submit', (event) => {
    if (!validateBoxesInsideSelectedRect()) {
      event.preventDefault();
      return;
    }
    if (!validateBoxLabels()) {
      event.preventDefault();
      return;
    }
    updateHiddenInput();
  });
  updateMCQMode();
})();
