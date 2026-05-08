/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2023 Brennen Chiu
    Copyright (C) 2024 Aden Chan
    Copyright (C) 2024 Bryan Tanady
    Copyright (C) 2025-2026 Aidan Murphy
    Copyright (C) 2025 Colin B. Macdonald
*/

const firstWordList = ['adorable', 'adventurous', 'aggressive', 'agreeable', 'alert', 'alive', 'amused', 'angry', 'annoyed', 'anxious', 'attractive', 'average', 'bad', 'beautiful', 'better', 'bewildered', 'blue', 'blushing', 'bored', 'brainy', 'brave', 'breakable', 'bright', 'busy', 'calm', 'careful', 'cautious', 'charming', 'cheerful', 'clean', 'clear', 'clever', 'cloudy', 'clumsy', 'colourful', 'combative', 'comfortable', 'concerned', 'confused', 'cooperative', 'crazy', 'curious', 'cute', 'dangerous', 'delightful', 'determined', 'different', 'distinct', 'dizzy', 'eager', 'easy', 'elated', 'elegant', 'energetic', 'enthusiastic', 'excited', 'expensive', 'exuberant', 'fair', 'faithful', 'famous', 'fancy', 'fantastic', 'fine', 'friendly', 'funny', 'gentle', 'gifted', 'glamorous', 'gleaming', 'glorious', 'good', 'gorgeous', 'handsome', 'happy', 'healthy', 'helpful', 'hilarious', 'hungry', 'important', 'innocent', 'jolly', 'kind', 'light', 'lively', 'lovely', 'lucky', 'magnificent', 'misty', 'muddy', 'mushy', 'mysterious', 'naughty', 'nice', 'oldfashioned', 'outstanding', 'perfect', 'powerful', 'precious', 'real', 'relieved', 'rich', 'shiny', 'smiling', 'sparkling', 'successful', 'super', 'thoughtful', 'wandering', 'young'];
const secondWordList = ['actor', 'actress', 'advertisement', 'airport', 'animal', 'answer', 'apple', 'balloon', 'banana', 'battery', 'bears', 'bird', 'bison', 'breakfast', 'camera', 'candle', 'car', 'cartoon', 'cat', 'chicken', 'computer', 'deer', 'dog', 'dolphin', 'eagle', 'fire', 'fish', 'food', 'ghost', 'gold', 'gorilla', 'grass', 'guitar', 'hamburger', 'helicopter', 'horse', 'ice', 'jackal', 'jelly', 'juice', 'kangaroo', 'king', 'lawyer', 'lion', 'lizard', 'llama', 'lobster', 'machine', 'magician', 'monkey', 'mosquito', 'panda', 'parrot', 'pig', 'pizza', 'planet', 'pony', 'potato', 'queen', 'rabbit', 'rainbow', 'shark', 'snake', 'tiger', 'tomato', 'train', 'truck', 'turkey', 'whale', 'wolf'];

// toggle password visibility
/* *********************************************************** */
window.toggleVisibility = function (passwordInputId) {
  let passwordInput = document.getElementById(passwordInputId);
  const newType = passwordInput.getAttribute('type') == 'password' ? 'text' : 'password';
  passwordInput.setAttribute('type', newType);
};
/* *********************************************************** */

// generate a random username
/* *********************************************************** */
window.insertRandomUsername = function (textInputId) {
  const firstUserWord = firstWordList[Math.floor(Math.random() * firstWordList.length)].split(' ').join('');
  const secondUserWord = secondWordList[Math.floor(Math.random() * secondWordList.length)].split(' ').join('');
  const randomNumAsString = (Math.floor(Math.random() * 10) + 1).toString();
  let textInput = document.getElementById(textInputId);
  textInput.value = firstUserWord + secondUserWord + randomNumAsString;
};
/* *********************************************************** */

// copy password reset link
/* *********************************************************** */
// Call this function on a button with the intended content
// in the "data-copyText" attribute.
// For example:
// <button id="myElementId"
//         data-copyText="https://www.examplewebsite.com/"
//         onclick="copyToClipboard(this)">
//     Copy Link
// </button>
window.copyToClipboard = function (buttonElement) {
  const copyText = buttonElement.dataset.copytext;
  navigator.clipboard.writeText(copyText);

  buttonElement.disabled = true;
  let tickIcon = document.createElement('i');
  tickIcon.className = 'bi bi-check';
  buttonElement.insertAdjacentElement('afterend', tickIcon);

  setTimeout(() => {
    buttonElement.disabled = false;
    tickIcon.remove();
  }, 500);
};
/* *********************************************************** */
