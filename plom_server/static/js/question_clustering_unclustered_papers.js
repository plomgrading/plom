/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2026 Deep Shah
*/

// Page-specific behavior for QuestionClustering/unclustered_papers.html.
// The template supplies data-* hooks, form fields, and image fallback calls used here.
(function () {
  document.addEventListener('DOMContentLoaded', initUnclusteredDropTargets);

  /** Initialise functions for drag/drop targets. */
  function initUnclusteredDropTargets() {
    const form = document.querySelector('[data-unclustered-form]');
    const sourceGrid = document.querySelector('[data-unclustered-grid]');
    if (!form || !sourceGrid) return;

    const assignUrl = form.getAttribute('action');
    const selectAllCheckbox = document.querySelector('[data-select-all-unclustered]');
    const baseFields = {
      question_idx: form.querySelector('input[name="question_idx"]').value,
      version: form.querySelector('input[name="version"]').value,
      page_num: form.querySelector('input[name="page_num"]').value,
      next: form.querySelector('input[name="next"]').value,
    };

    let draggedCards = [];

    // Checkbox state drives both normal bulk form submission and bulk dragging.
    sourceGrid.querySelectorAll('.unclustered-paper-card').forEach((card) => {
      card.querySelector('input[name="paper_nums"]')?.addEventListener('change', () => {
        updateSelectedDragCue();
      });

      // Native drag/drop is not a form submit; keep the selected cards in memory
      // until a cluster target receives the drop and can post the assignment.
      card.addEventListener('dragstart', (event) => {
        draggedCards = getCardsForDrag(card);
        draggedCards.forEach(item => item.classList.add('is-bulk-dragged'));
        updateDragCount(draggedCards.length, true);
        document.body.classList.add('dragging-unclustered');
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData(
          'text/plain',
          draggedCards.map(item => item.dataset.paperNumber).join(','),
        );
      });

      card.addEventListener('dragend', () => {
        draggedCards.forEach(item => item.classList.remove('is-bulk-dragged'));
        document.body.classList.remove('dragging-unclustered');
        document.querySelectorAll('.cluster-drop-target.drop-target-hover').forEach((target) => {
          target.classList.remove('drop-target-hover');
        });
        draggedCards = [];
        updateSelectedDragCue();
      });
    });

    selectAllCheckbox?.addEventListener('change', () => {
      const checked = selectAllCheckbox.checked;
      sourceGrid.querySelectorAll('input[name="paper_nums"]').forEach((checkbox) => {
        checkbox.checked = checked;
      });
      updateSelectedDragCue();
    });

    updateSelectedDragCue();

    // Dropping onto a cluster is the mutating action.  The DOM is updated only
    // after the server confirms the assignment.
    document.querySelectorAll('[data-cluster-drop-target]').forEach((target) => {
      target.addEventListener('dragover', (event) => {
        if (draggedCards.length === 0) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        target.classList.add('drop-target-hover');
      });

      target.addEventListener('dragleave', (event) => {
        if (!target.contains(event.relatedTarget)) {
          target.classList.remove('drop-target-hover');
        }
      });

      target.addEventListener('drop', (event) => {
        if (draggedCards.length === 0) return;
        event.preventDefault();
        target.classList.remove('drop-target-hover');
        assignDraggedCards({
          assignUrl,
          baseFields,
          cards: draggedCards,
          target,
          targetClusterId: target.dataset.clusterDropTarget,
        });
      });
    });

    // htmx replaces the suggestions panel, so delegate panel button clicks
    // instead of binding listeners to elements that may be swapped out.
    document.addEventListener('click', (event) => {
      if (!(event.target instanceof Element)) return;

      const applyButton = event.target.closest('[data-apply-suggestions]');
      if (applyButton) {
        applySelectedSuggestions({
          assignUrl,
          baseFields,
          button: applyButton,
        });
        return;
      }

      if (event.target.closest('[data-clear-suggestions]')) {
        clearSuggestions();
      }
    });
  }

  /**
   * Dragging an unchecked card moves just that card.  Dragging a checked card
   * moves the current checked selection as one batch.
   * @param {HTMLElement} card - An html element representing an unclustered item.
   * @returns {HTMLElement[]} - An array of the card elements.
   */
  function getCardsForDrag(card) {
    const checkbox = card.querySelector('input[name="paper_nums"]');
    if (!checkbox?.checked) return [card];

    return getSelectedUnclusteredCards();
  }

  /**
   * Return all cards that are "selected" (have checkboxes checked).
   * @returns {HTMLElement[]} - The selected unclustered cards.
   */
  function getSelectedUnclusteredCards() {
    return Array.from(
      document.querySelectorAll('[data-unclustered-grid] input[name="paper_nums"]:checked'),
    )
      .map(input => input.closest('.unclustered-paper-card'))
      .filter(Boolean);
  }

  /** Update visuals and behaviour for draggable elements. */
  function updateSelectedDragCue() {
    const selectedCards = getSelectedUnclusteredCards();
    const allCards = Array.from(document.querySelectorAll('.unclustered-paper-card'));
    allCards.forEach((card) => {
      card.classList.toggle(
        'is-selected-for-drag',
        selectedCards.length > 1 && selectedCards.includes(card),
      );
    });
    updateSelectAllControl(selectedCards.length, allCards.length);
    updateDragCount(selectedCards.length, false);
  }

  /**
   * Change the display showing the total number of cards, and the
   * number of selected cards.
   * @param {number} selectedCount - Number of selected cards.
   * @param {number} totalCount - Total number of cards.
   */
  function updateSelectAllControl(selectedCount, totalCount) {
    const checkbox = document.querySelector('[data-select-all-unclustered]');
    const selectedBadge = document.querySelector('[data-selected-count]');
    if (checkbox) {
      checkbox.checked = totalCount > 0 && selectedCount === totalCount;
      checkbox.indeterminate = selectedCount > 0 && selectedCount < totalCount;
      checkbox.disabled = totalCount === 0;
    }
    if (!selectedBadge) return;

    if (selectedCount > 0) {
      selectedBadge.textContent = `${selectedCount} selected`;
      selectedBadge.classList.remove('d-none');
    }
    else {
      selectedBadge.textContent = '';
      selectedBadge.classList.add('d-none');
    }
  }

  /**
   * Update visuals showing the number of draggable cards, and whether
   * they are being dragged.
   * @param {number} count - Number of draggable cards.
   * @param {boolean} isDragging - Whether cards are currently being dragged.
   */
  function updateDragCount(count, isDragging) {
    const badge = document.querySelector('[data-drag-count]');
    if (!badge) return;

    if (count > 1) {
      badge.textContent = isDragging
        ? `Dragging ${count} selected`
        : `${count} selected for drag`;
      badge.classList.remove('d-none');
    }
    else {
      badge.textContent = '';
      badge.classList.add('d-none');
    }
  }

  /**
   * Convert a javascript object of key value pairs to a FormData object.
   * @param {object} baseFields - An object containing key value pairs.
   * @returns {FormData} - The object's key value pairs as FormData.
   */
  function buildFormData(baseFields) {
    const formData = new FormData();
    Object.entries(baseFields).forEach(([key, value]) => formData.append(key, value));
    return formData;
  }

  /**
   * Retrieve the data from a JSON response.
   * @param {XMLHttpRequest} xhr - The updated xhr received in the response.
   * @param {string} fallbackMessage - Logging message if the updated xhr doesn't contain a msg.
   * @returns {unknown} - The payload from the response.
   */
  function parseJsonResponse(xhr, fallbackMessage) {
    let data;
    try {
      data = JSON.parse(xhr.responseText || '{}');
    }
    catch {
      throw new Error(fallbackMessage);
    }
    if (xhr.status < 200 || xhr.status >= 300 || !data.ok) {
      throw new Error(data.message || fallbackMessage);
    }
    return data;
  }

  /**
   * Send a POST request via htmx.
   * @param {object} root0
   * @param {string} root0.url - The url to POST to.
   * @param {object} root0.values - An object containing key value pairs.
   * @param {HTMLElement} root0.target - The htmx target.
   * @param {string} root0.errorMessage - A fallback error message if the server
   *   doesn't provide one.
   * @returns {unknown} - Data returned in the response.
   */
  function htmxJsonPost({
    url,
    values,
    target,
    errorMessage,
  }) {
    if (!window.htmx) {
      return Promise.reject(new Error('Could not find htmx.'));
    }

    return new Promise((resolve, reject) => {
      window.htmx.ajax('POST', url, {
        source: document.body,
        target: target || document.body,
        values,
        swap: 'none',
        handler: (_elt, responseInfo) => {
          try {
            resolve(parseJsonResponse(responseInfo.xhr, errorMessage));
          }
          catch (error) {
            reject(error);
          }
        },
      }).catch(reject);
    });
  }

  /**
   * Group selected server-rendered suggestions by target cluster.  The assignments are awaited
   * sequentially so count badges, removed cards, and previews reflect each
   * completed server mutation before the next one starts.
   * @param root0
   * @param {string} root0.assignUrl - The URL to eventually post to.
   * @param {object} root0.baseFields - Key value pairs relevant to the eventual POST.
   * @param {HTMLElement} root0.button - The button which triggered this function.
   */
  async function applySelectedSuggestions({
    assignUrl,
    baseFields,
    button,
  }) {
    const suggestionRows = Array.from(
      document.querySelectorAll('[data-suggestion-row]'),
    ).filter(row => row.querySelector('[data-suggestion-selected]')?.checked);

    if (suggestionRows.length === 0) {
      showSuggestionStatus('No selected suggestions.', 'warning');
      return;
    }

    const groups = new Map();
    suggestionRows.forEach((row) => {
      const paperNumber = row.dataset.suggestionRow;
      const card = document.querySelector(`[data-paper-number="${paperNumber}"]`);
      const targetClusterId = row.querySelector('[data-suggestion-cluster]')?.value;
      if (!card || !targetClusterId) {
        row.remove();
        return;
      }

      if (!groups.has(targetClusterId)) {
        groups.set(targetClusterId, []);
      }
      groups.get(targetClusterId).push(card);
    });

    if (button) button.disabled = true;
    showSuggestionStatus('');

    try {
      for (const [targetClusterId, cards] of groups) {
        const target = document.querySelector(
          `[data-cluster-drop-target="${targetClusterId}"]`,
        );
        await assignDraggedCards({
          assignUrl,
          baseFields,
          cards,
          target,
          targetClusterId,
        });
      }
      refreshSuggestionsPanel();
    }
    finally {
      if (button) button.disabled = false;
    }
  }

  /** Remove server provided cluster suggestions from the UI. */
  function clearSuggestions() {
    resetSuggestionsPanel();
  }

  /** Refresh UI elements in the suggestions panel.  */
  function refreshSuggestionsPanel() {
    const panel = document.querySelector('[data-suggestions-panel]');
    const body = document.querySelector('[data-suggestions-body]');
    if (!panel || !body) return;

    const remaining = body.querySelectorAll('[data-suggestion-row]').length;
    if (remaining === 0) {
      resetSuggestionsPanel();
      return;
    }

    panel.classList.remove('d-none');
    document.querySelector('[data-suggestions-table]')?.classList.remove('d-none');
    document.querySelector('[data-suggestions-actions]')?.classList.remove('d-none');
    updateSuggestionsCount(remaining);
  }

  /**
   * Update UI for cluster suggestions status.
   * @param {string} message - A message to show in the UI, it should be plain text.
   * @param {string} tone - A bootstrap colour to apply to the alert (e.g., "primary",
   *   "success", "danger", etc.).
   */
  function showSuggestionStatus(message, tone = 'info') {
    const panel = document.querySelector('[data-suggestions-panel]');
    const status = document.querySelector('[data-suggestions-status]');
    if (!status) return;

    status.textContent = message;
    status.className = `alert alert-${tone} py-2 mb-2`;
    status.classList.toggle('d-none', !message);
    if (message) panel?.classList.remove('d-none');
  }

  /**
   * Remove all cluster suggestions.
   * @param root0
   * @param {boolean} root0.showPanel  - Whether to show the panel.
   */
  function resetSuggestionsPanel({ showPanel = false } = {}) {
    const panel = document.querySelector('[data-suggestions-panel]');
    const body = document.querySelector('[data-suggestions-body]');
    const table = document.querySelector('[data-suggestions-table]');
    const actions = document.querySelector('[data-suggestions-actions]');
    const status = document.querySelector('[data-suggestions-status]');

    if (body) body.replaceChildren();
    table?.classList.add('d-none');
    actions?.classList.add('d-none');
    updateSuggestionsCount(0);
    if (status) {
      status.textContent = '';
      status.className = 'alert alert-info py-2 mb-2 d-none';
    }
    panel?.classList.toggle('d-none', !showPanel);
  }

  /**
   * Change the total count of the suggestions displayed in the UI.
   * @param {number} count - The number of suggestions.
   */
  function updateSuggestionsCount(count) {
    const countBadge = document.querySelector('[data-suggestions-count]');
    if (!countBadge) return;

    if (count > 0) {
      countBadge.textContent = count;
      countBadge.classList.remove('d-none');
    }
    else {
      countBadge.textContent = '';
      countBadge.classList.add('d-none');
    }
  }

  /**
   * Shared mutating assignment path for drag/drop and suggestion application.
   * It posts selected paper numbers, then updates the visible cards and counts
   * from the JSON response after the server accepts the change.
   * @param root0
   * @param {string} root0.assignUrl - The url to eventually POST to.
   * @param {object} root0.baseFields - Key value pairs to include in the eventual POST.
   * @param {HTMLElement[]} root0.cards - The cards to assign.
   * @param {HTMLElement} root0.target - Where to assign the cards.
   * @param {number} root0.targetClusterId - The cluster to assign the cards to.
   */
  async function assignDraggedCards({
    assignUrl,
    baseFields,
    cards,
    target,
    targetClusterId,
  }) {
    const formData = buildFormData(baseFields);
    formData.append('target_cluster_id', targetClusterId);
    cards.forEach(card => formData.append('paper_nums', card.dataset.paperNumber));

    cards.forEach(card => card.classList.add('is-assigning'));
    target?.classList.add('is-assigning');

    try {
      const data = await htmxJsonPost({
        url: assignUrl,
        values: formData,
        target,
        errorMessage: 'Could not assign papers.',
      });

      const targetCount = document.querySelector(
        `[data-cluster-target-count="${targetClusterId}"]`,
      );
      if (targetCount) targetCount.textContent = data.member_count;

      const preview = document.querySelector(
        `[data-cluster-target-preview="${targetClusterId}"]`,
      );
      if (preview && !preview.querySelector('img')) {
        const itemImage = cards[0]?.querySelector('img');
        if (itemImage) {
          const previewImage = itemImage.cloneNode(true);
          previewImage.alt = `cluster ${targetClusterId} preview`;
          preview.replaceChildren(previewImage);
        }
      }

      const unclusteredCount = document.querySelector('[data-unclustered-count]');
      if (unclusteredCount) unclusteredCount.textContent = data.unclustered_count;

      cards.forEach((card) => {
        document.querySelector(
          `[data-suggestion-row="${card.dataset.paperNumber}"]`,
        )?.remove();
        card.remove();
      });
      updateSelectedDragCue();
      refreshSuggestionsPanel();
      if (data.unclustered_count === 0) {
        document.querySelector('[data-unclustered-form]')?.classList.add('d-none');
        document.querySelector('[data-empty-state]')?.classList.remove('d-none');
      }
      if (target) {
        target.classList.remove('assignment-complete');
        void target.offsetWidth;
        target.classList.add('assignment-complete');
      }
    }
    catch (error) {
      cards.forEach(card => card.classList.remove('is-assigning'));
      showSuggestionStatus(error.message, 'danger');
    }
    finally {
      target?.classList.remove('is-assigning');
    }
  }

  /**
   * Custom replacement for img tags if the image can't be displayed. You
   * should use this as the "onerror" attribute of such an img tag.
   * @param {HTMLElement} image - The image element whose image failed to load.
   */
  window.imgError = function (image) {
    const span = document.createElement('span');
    span.classList.add('alert', 'alert-warning', 'mx-2', 'py-0');
    span.innerText = 'Could not extract rectangle.';
    image.parentNode.insertBefore(span, image);
    image.remove();
  };
})();
