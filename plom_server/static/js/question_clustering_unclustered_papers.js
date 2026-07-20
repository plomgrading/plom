/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2026 Deep Shah
*/

// Page-specific behavior for QuestionClustering/unclustered_papers.html.
// The template supplies data-* hooks, form fields, and image fallback calls used here.
(function () {
  document.addEventListener('DOMContentLoaded', initUnclusteredDropTargets);

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

  // Dragging an unchecked card moves just that card.  Dragging a checked card
  // moves the current checked selection as one batch.
  function getCardsForDrag(card) {
    const checkbox = card.querySelector('input[name="paper_nums"]');
    if (!checkbox?.checked) return [card];

    return getSelectedUnclusteredCards();
  }

  function getSelectedUnclusteredCards() {
    return Array.from(
      document.querySelectorAll('[data-unclustered-grid] input[name="paper_nums"]:checked'),
    )
      .map(input => input.closest('.unclustered-paper-card'))
      .filter(Boolean);
  }

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

  function buildFormData(baseFields) {
    const formData = new FormData();
    Object.entries(baseFields).forEach(([key, value]) => formData.append(key, value));
    return formData;
  }

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

  // Group selected server-rendered suggestions by target cluster.  The assignments are awaited
  // sequentially so count badges, removed cards, and previews reflect each
  // completed server mutation before the next one starts.
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

  function clearSuggestions() {
    resetSuggestionsPanel();
  }

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

  function showSuggestionStatus(message, tone = 'info') {
    const panel = document.querySelector('[data-suggestions-panel]');
    const status = document.querySelector('[data-suggestions-status]');
    if (!status) return;

    status.textContent = message;
    status.className = `alert alert-${tone} py-2 mb-2`;
    status.classList.toggle('d-none', !message);
    if (message) panel?.classList.remove('d-none');
  }

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

  // Shared mutating assignment path for drag/drop and suggestion application.
  // It posts selected paper numbers, then updates the visible cards and counts
  // from the JSON response after the server accepts the change.
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

  window.imgError = function (image) {
    const span = document.createElement('span');
    span.classList.add('alert', 'alert-warning', 'mx-2', 'py-0');
    span.innerText = 'Could not extract rectangle.';
    image.parentNode.insertBefore(span, image);
    image.remove();
  };
})();
