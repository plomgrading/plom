/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2026 Aidan Murphy
*/

/* eslint-disable no-unused-vars */

// Strongly coupled with SpecCreator/gui_spec_builder.html,
// check there for WET stuff.

let numberOfPagesSpan = document.getElementById('numberOfPages');
const numberOfPages = parseInt(numberOfPagesSpan.dataset.numberOfPages);

// Stuff to interact with the "spec"; soaking WET right now with the server.
// Ideally the spec validation code could be broken down to allow partial
// submission of some elements while keeping the rest incomplete.
var statefulSpec = {
  name: '',
  longName: '',
  numberOfVersions: 1,
  numberOfPages: numberOfPages,
  numberOfQuestions: 0,
  totalMarks: 0,
  idPage: null,
  doNotMarkPages: [],
  question: [],
  allowSharedPages: false,
};
const questionTemplate = {
  // this isn't in the spec, it's only used locally
  // we must remove it before uploading to server.
  qidx: 1,

  pages: [],
  mark: -1,
  // this will depend on the number of versions, so set dynamically
  select: [],
  label: null,
  bonus: false,
};
var selectedPages = new Set();

/**
 * Get the global "spec" and return it as a JSON string.
 * @returns {string} - A string containing the spec in JSON.
 */
function getSpecJson() {
  let spec = structuredClone(statefulSpec);
  // as above, don't include the qidx in the final submission
  spec.question.forEach((q) => {
    delete q.qidx;
  });
  return JSON.stringify(spec);
}

/**
 * Parse existing questions, and return an unused Question index.
 * @returns {number} - An integer which isn't yet used as a question index.
 */
function getNextAvailableQidx() {
  let qidxArray = statefulSpec.question.map(q => q.qidx).sort((a, b) => a - b);
  if (qidxArray.length === 0)
    return 1;
  return qidxArray.at(-1) + 1;
}

/**
 * Add a question to the spec, but first check if there's one with a similar label.
 * @param {string} label - The label for the new question.
 */
function createQuestion(label) {
  const q = statefulSpec.question.find(q => q.label === label);
  if (q) {
    alert('A question using that label already exists');
    return;
  }
  var newQuestion = structuredClone(questionTemplate);
  // eslint-disable-next-line no-useless-assignment
  newQuestion.select = [...Array(statefulSpec.numberOfVersions).keys()].map(x => ++x);
  newQuestion.qidx = getNextAvailableQidx();
  newQuestion.label = label ? label : `Q${newQuestion.qidx}`;
  statefulSpec.question.push(newQuestion);
  refreshQuestionLists();
  return newQuestion;
}

/**
 * Remove a question from the spec.
 * @param {number} qidx - The question index of the question to remove.
 */
function removeQuestion(qidx) {
  statefulSpec.question = statefulSpec.question.filter(
    questionObj => questionObj.qidx !== qidx,
  );
  refreshQuestionLists();
  return;
}

/**
 * Check the spec's ID pages, and update html elements accordingly.
 */
function refreshIdPageLists() {
  refreshIdPageSummary();
  refreshPageAssignments();
}

/**
 * Update The Id Page summary html element according to the spec.
 */
function refreshIdPageSummary() {
  const container = document.getElementById('idPageCard');
  var pagesText = `<span class="text-muted fst-italic">none</span>`;
  if (statefulSpec.idPage !== null)
    pagesText = statefulSpec.idPage;
  container.innerHTML = `
                        <div class="card my-1">
                            <div class="card-header d-flex justify-content-between align-items-center py-1">
                                <strong>ID</strong>
                            </div>
                            <div class="card-body p-2 small">
                                <div class="mb-1">
                                    <span class="text-muted">Page:</span> ${pagesText}
                                </div>
                            </div>
                        </div>`;
}

//
/**
 * Check the spec's DNM pages, and update html elements accordingly.
 */
function refreshDnmPageLists() {
  refreshDnmPageSummary();
  refreshPageAssignments();
}
/**
 * Update The DNM Page summary html element according to the spec.
 */
function refreshDnmPageSummary() {
  const container = document.getElementById('dnmPageCard');
  var pagesText = `<span class="text-muted fst-italic">none</span>`;
  if (statefulSpec.doNotMarkPages.length !== 0)
    pagesText = statefulSpec.doNotMarkPages.join(', ');
  container.innerHTML = `
                        <div class="card my-1">
                            <div class="card-header d-flex justify-content-between align-items-center py-1">
                                <strong>DNM</strong>
                            </div>
                            <div class="card-body p-2 small">
                                <div class="mb-1">
                                    <span class="text-muted">Pages:</span> ${pagesText}
                                </div>
                            </div>
                        </div>`;
}

/**
 *  Check the spec's questions, and update html elements accordingly.
 */
function refreshQuestionLists() {
  refreshPageAssignments();
  refreshQuestionSummary();
  refreshQuestionDropdown();
  updateTotalMarks();
  updateNumberOfQuestions();
  return;
}
/**
 * Update The Question summary html elements according to the spec.
 */
function refreshQuestionSummary() {
  const container = document.getElementById('questionSummary');
  let questionCardElems = [];

  if (statefulSpec.question.length === 0) {
    container.innerHTML = `<p class="text-muted small">No questions yet.</p>`;
    return;
  }

  statefulSpec.question.forEach((q) => {
    const pagesText = q.pages.length
      ? q.pages.map(p => `p.${p}`).join(', ')
      : `<span class="text-muted fst-italic">none</span>`;

    // Build version checkboxes
    let versionsHtml = '';
    for (let v = 1; v <= statefulSpec.numberOfVersions; v++) {
      const checked = q.select.includes(v) ? 'checked' : '';
      versionsHtml += `
                                <div class="form-check form-check-inline">
                                    <input class="form-check-input"
                                           type="checkbox"
                                           id="q_${q.qidx}_v${v}"
                                           ${checked}
                                           onchange="setQuestionVersions(${q.qidx}, ${v}, this.checked)">
                                    <label class="form-check-label" for="q_${q.qidx}_v${v}">${v}</label>
                                </div>`;
    }

    const card = document.createElement('div');
    card.className = 'card my-1';
    card.innerHTML = `
                            <div class="card-header d-flex justify-content-between align-items-center py-1">
                                <strong>
                                    <input id="label_${q.qidx}" type="text" class="form-control form-control-sm d-inline-block ms-1" style="width: 5rem;" value="${escapeHtml(q.label)}" placeholder="" onchange="setQuestionLabel(${q.qidx}, this.value)">
                                </strong>
                                <button class="btn btn-sm btn-outline-danger py-0" onclick="removeQuestion(${q.qidx})">
                                    &times; Remove
                                </button>
                            </div>
                            <div class="card-body p-2 small">
                                <!-- for debugging
                                <div class="mb-1">
                                    <label class="text-muted" for="mark_${q.qidx}">DEBUG Qidx:</label>
                                    <input id="idx_${q.qidx}" type="number" min="0" class="form-control form-control-sm d-inline-block ms-1" style="width: 5rem;" value="${q.qidx}" placeholder="?" disabled>
                                </div>
                                -->
                                <div class="mb-1">
                                    <span class="text-muted">Pages:</span> ${pagesText}
                                </div>
                                <div class="mb-1">
                                    <label class="text-muted" for="mark_${q.qidx}">Marks:</label>
                                    <input id="mark_${q.qidx}" type="number" min="0" class="form-control form-control-sm d-inline-block ms-1" style="width: 5rem;" value="${q.mark ?? ''}" placeholder="?" onchange="setQuestionMarks(${q.qidx}, this.value)">
                                    <label class="text-muted" for="bonus_${q.qidx}">Bonus:</label>
                                    <input id="bonus_${q.qidx}" type="checkbox" class="form-check-input" ${q.bonus ? 'checked' : ''} oninput="setQuestionBonus(${q.qidx}, this.checked)">
                                </div>
                                ${statefulSpec.numberOfVersions > 1
                                  ? `
                                <div>
                                    <span class="text-muted">Select from versions:</span>
                                    ${versionsHtml}
                                </div>`
                                  : ''}
                            </div>`;
    questionCardElems.push(card);
  });
  // do this last so prior errors don't remove everything
  container.innerHTML = '';
  questionCardElems.forEach((elem) => {
    container.appendChild(elem);
  });
}
/**
 * Update the dropdown for the "assign page to <question>" button.
 */
function refreshQuestionDropdown() {
  let questionOptionElems = [];
  // question dropdown node
  let container = document.getElementById('questionAssignmentSelector');
  let defaultOption = document.createElement('option');
  defaultOption.disabled = true;
  defaultOption.hidden = true;
  defaultOption.selected = true;
  questionOptionElems.push(defaultOption);

  statefulSpec.question.forEach((questionObj) => {
    let dropdownOption = document.createElement('option');
    dropdownOption.value = questionObj.qidx;
    dropdownOption.innerText = questionObj.label;
    questionOptionElems.push(dropdownOption);
  });

  // do this last, so prior failures don't remove everything
  container.innerHTML = '';
  questionOptionElems.forEach((elem) => {
    container.appendChild(elem);
  });
}

/**
 * Unselect all selected pages.
 */
function clearAllSelectedPages() {
  // get elements with IDs = "page...Checkbox"
  var pageCheckboxes = document.querySelectorAll('[id ^= "page"][id $= "Checkbox"]');
  pageCheckboxes.forEach((checkbox) => {
    // replace all alphabet chars with ""
    let pageNumString = checkbox.id.replace(RegExp('[a-zA-Z]*'), '');
    let pageNumInt = parseInt(pageNumString);
    checkbox.checked = false;
    updateSelectedPages(pageNumInt, checkbox.checked);
  });
}

/**
 * Update the array of selected pages.
 * @param {number} pageIndex - The page whose selection "status" should be updated.
 * @param {boolean} checked - - whether the page is selected.
 */
function updateSelectedPages(pageIndex, checked) {
  if (checked) {
    selectedPages.add(pageIndex);
  }
  else {
    selectedPages.delete(pageIndex);
  }

  // convert to array, sort, then back to set
  const sortedPagesArray = [...selectedPages].sort((a, b) => a - b);
  selectedPages = new Set(sortedPagesArray);

  // update html elems using sorted array
  let span = document.getElementById('selectedPagesDisplay');
  span.innerText = sortedPagesArray.join(', ');
}

/**
 * Update the spec's "numberOfQuestions" property value.
 * There is no input, the update is based on the "question"
 * property array in the spec.
 */
function updateNumberOfQuestions() {
  statefulSpec.numberOfQuestions = statefulSpec.question.length;
  let container = document.getElementById('numberOfQuestions');
  container.innerText = statefulSpec.numberOfQuestions;
}

/**
 * Set the spec's "longName" property value.
 * @param {string} longName - The new value.
 */
function setLongName(longName) {
  statefulSpec.longName = longName;
}

/**
 * Set the spec's "shortName" property value.
 * @param {string} shortName - The new value.
 */
function setShortName(shortName) {
  statefulSpec.name = shortName;
}

/**
 * Set the spec's "allowSharedPages" property value.
 * @param {boolean} allowed - The new value.
 */
function setAllowSharedPages(allowed) {
  statefulSpec.allowSharedPages = allowed;
}

/**
 * Update the spec's "totalMarks" property value.
 * There is no input, the update is based on the "question"
 * property array in the spec.
 */
function updateTotalMarks() {
  let totalMarks = statefulSpec.question.reduce((sum, q) => {
    return sum + q.mark;
  }, 0);
  statefulSpec.totalMarks = totalMarks;
  let container = document.getElementById('totalMarks');
  container.innerText = statefulSpec.totalMarks;
}

/**
 * Set the spec's "numberOfVersions" property value.
 * @param {number} numVersions - The new value.
 */
function setNumberOfVersions(numVersions) {
  statefulSpec.numberOfVersions = parseInt(numVersions);
  updateQuestionVersions();
  // question properties depend on number of exam versions
  refreshQuestionLists();
}

/**
 * Update the 'select' attribute in each spec question.
 * This is relevant, for example, when the number of versions
 * decreases, and some elements in 'select' are no longer editable
 * but still need to be deleted for serverside validation.
 */
function updateQuestionVersions() {
  let numVersions = statefulSpec.numberOfVersions;
  statefulSpec.question.forEach((q) => {
    // in this case checkboxes are hidden, so we need to manually correct
    if (numVersions == 1) {
      q.select = [1];
    }
    else {
      q.select = q.select.filter(v => v <= numVersions);
    }
  });
}

/**
 * Add or remove a version for a given question.
 * @param {number} qidx - The index for the given question.
 * @param {number} version - The version.
 * @param {boolean} checked - If true, add this version to the question,
 *   otherwise remove the version.
 */
function setQuestionVersions(qidx, version, checked) {
  const q = statefulSpec.question.find(q => q.qidx === qidx);
  if (!q)
    return;
  if (checked) {
    if (!q.select.includes(version)) q.select.push(version);
  }
  else {
    q.select = q.select.filter(v => v !== version);
  }
  refreshQuestionLists();
}

/**
 * Set the number of marks for a given question.
 * @param {number} qidx - The index for the question.
 * @param {number} mark - The marks for that question.
 */
function setQuestionMarks(qidx, mark) {
  const q = statefulSpec.question.find(q => q.qidx === qidx);
  if (!q || mark < 0)
    return;
  q.mark = parseInt(mark);
  refreshQuestionLists();
}

/**
 * Change whether a question is a "bonus" question.
 * @param {number} qidx - The index for the question.
 * @param {boolean} bonus - Whether the question should be a bonus.
 */
function setQuestionBonus(qidx, bonus) {
  const q = statefulSpec.question.find(q => q.qidx === qidx);
  if (!q)
    return;
  q.bonus = bonus;
  refreshQuestionLists();
}

/**
 * Assign the provided pages to a particular question.
 * @param {number} qidx - Which question to assign the pages to.
 * @param {number[]} pageArray - An array of pages to assign.
 */
function insertQuestionPages(qidx, pageArray) {
  const q = statefulSpec.question.find(q => q.qidx === qidx);
  if (!q || !pageArray)
    return;
  var pageSet = new Set(q.pages);
  pageArray.forEach(page => pageSet.add(page));
  q.pages = [...pageSet].sort((a, b) => a - b);

  refreshQuestionLists();
}

/**
 * Create a new question, and assign the provided pages to it.
 * @param {number[]} pageArray - An array of pages to assign.
 */
function insertPagesIntoNewQuestion(pageArray) {
  const newQidx = createQuestion().qidx;
  insertQuestionPages(newQidx, pageArray);
}

/**
 * Set the label for a particular question.
 * @param {number} qidx - The question's index.
 * @param {string} label - The new label for the question.
 */
function setQuestionLabel(qidx, label) {
  const q = statefulSpec.question.find(q => q.qidx === qidx);
  if (!q || !label)
    return;
  q.label = label;
  refreshQuestionLists();
}

/**
 * Assign the given pages as DNM pages.
 * @param {number[]} pageArray - The pages to assign.
 */
function insertDnmPages(pageArray) {
  var pageSet = new Set(statefulSpec.doNotMarkPages);
  pageArray.forEach(page => pageSet.add(page));
  statefulSpec.doNotMarkPages = [...pageSet].sort((a, b) => a - b);
  refreshDnmPageLists();
}

/**
 * Assign the given pages as ID pages.
 * @param {number[]} pageArray - The pages to assign.
 */
function insertIdPages(pageArray) {
  if (pageArray.length !== 1) {
    alert('Only one question at a time');
    return;
  }
  statefulSpec.idPage = pageArray[0];
  refreshIdPageLists();
}

/**
 * Assign the "selectedPages".
 * @param {string} type - One of "dnm", "id", "question".
 * @param {number} qidx - If type is "question" assign to this question.
 */
function assignSelectedPages(type, qidx = null) {
  let selectedPagesArray = [...selectedPages];
  switch (type) {
    case 'dnm':
      insertDnmPages(selectedPagesArray);
      break;
    case 'id':
      insertIdPages(selectedPagesArray);
      break;
    case 'question':
      if (!qidx)
        alert('must select a question');
      insertQuestionPages(qidx, selectedPagesArray);
      break;
    case 'newQuestion':
      insertPagesIntoNewQuestion(selectedPagesArray);
      break;
  }
  clearAllSelectedPages();
}

/** Unassign the "selectedPages" from any grouping they are currently in. */
function unassignSelectedPages() {
  let selectedPagesArray = [...selectedPages];
  unassignDnmPages(selectedPagesArray);
  unassignIdPages(selectedPagesArray);
  unassignQuestionPages(selectedPagesArray);
  clearAllSelectedPages();
}

/**
 * Remove the provided pages from the DNM pages in the spec.
 * @param {number[]} pageArray - The pages to assign.
 */
function unassignDnmPages(pageArray) {
  statefulSpec.doNotMarkPages = statefulSpec.doNotMarkPages.filter(
    page => !(pageArray.includes(page)),
  );
  refreshDnmPageLists();
}
/**
 * Remove the provided pages from the ID pages in the spec.
 * @param {number[]} pageArray - The pages to assign.
 */
function unassignIdPages(pageArray) {
  if (pageArray.includes(statefulSpec.idPage))
    statefulSpec.idPage = null;
  refreshIdPageLists();
}
/**
 * Remove the provided pages from any questions in the spec.
 * @param {number[]} pageArray - The pages to assign.
 */
function unassignQuestionPages(pageArray) {
  statefulSpec.question.forEach((q) => {
    q.pages = q.pages.filter(
      page => !(pageArray.includes(page)),
    );
  });
  refreshQuestionLists();
}

/** Update the details on each HTML page card specifying where it's assigned. */
function refreshPageAssignments() {
  let pageMap = new Map();

  // initialise map with empty sets
  for (let i = 1; i <= statefulSpec.numberOfPages + 1; i++) {
    pageMap.set(i, new Set());
  }

  // DNM pages
  for (let pageNum of statefulSpec.doNotMarkPages) {
    pageMap.get(pageNum).add('DNM');
  }
  // ID page
  if (statefulSpec.idPage) {
    pageMap.get(statefulSpec.idPage).add('ID');
  }
  // Question pages
  statefulSpec.question.forEach((q) => {
    for (let pageNum of q.pages) {
      pageMap.get(pageNum).add(q.label);
    }
  });

  // Use map to update page elements
  for (let i = 1; i <= statefulSpec.numberOfPages; i++) {
    let pageAssignmentsContainer = document.getElementById(`page${i}Assignments`);
    let pageAssignmentsString = [...pageMap.get(i)].join(', ');
    pageAssignmentsContainer.innerText = pageAssignmentsString;
  }
}

/**
 * Represent a string in html. Escapes a few things like "<".
 * @param {string} str - The string to represent.
 * @returns {string} - A string that's safe to use in html.
 */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/**
 * Represent a string in html attributes.
 * @param {string} str - The string to represent.
 * @returns {string} - A string that's safe to use in html attributes.
 */
function escapeAttr(str) {
  // Safe for use inside onclick='...' single-quoted attribute values
  return String(str).replace(/'/g, '\\\'');
}

// refresh html on load
refreshQuestionLists();
refreshDnmPageLists();
refreshIdPageLists();
