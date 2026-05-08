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

// generate a random username
/* *********************************************************** */
document.addEventListener('DOMContentLoaded', generateRandomUsername);

let generateUsernameBtn = document.getElementById('generate-username');

function generateRandomUsername() {
  generateUsernameBtn.addEventListener('click', () => {
    let firstUserWord = firstWordList[Math.floor(Math.random() * firstWordList.length)].split(' ').join('');
    let secondUserWord = secondWordList[Math.floor(Math.random() * secondWordList.length)].split(' ').join('');
    let randomNumAsString = (Math.floor(Math.random() * 10) + 1).toString();
    document.getElementById('id_username').value = firstUserWord + secondUserWord + randomNumAsString;
  });
}
/* *********************************************************** */

// copy password reset link
/* *********************************************************** */
document.addEventListener('DOMContentLoaded', copyToClipboard);

let copyBtn = document.getElementById('copy-btn');

function copyToClipboard() {
  const passwordResetLink = copyBtn.getAttribute('data-passwordResetLink');
  copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(passwordResetLink);
  });
}
/* *********************************************************** */

// toggle password visibility
/* *********************************************************** */
document.addEventListener('DOMContentLoaded', viewPassword);

let togglePassword = document.getElementById('togglePassword');
let newPassword1 = document.getElementById('id_new_password1');
let newPassword2 = document.getElementById('id_new_password2');

function viewPassword() {
  togglePassword.addEventListener('click', () => {
    const type = newPassword1.getAttribute('type') === 'password' ? 'text' : 'password';
    const classAttribute = togglePassword.getAttribute('class') === 'bi-eye' ? 'bi-eye-slash' : 'bi-eye';
    newPassword1.setAttribute('type', type);
    newPassword2.setAttribute('type', type);
    togglePassword.setAttribute('class', classAttribute);
  });
}
/* *********************************************************** */

// toggle password visibility (again)
/* *********************************************************** */
let showPasswordCheckbox = document.getElementById('showPasswordCheckbox');
let loginPasswordInput = document.getElementById('passwordInput');

showPasswordCheckbox.addEventListener('change', function () {
  const newType = this.checked ? 'text' : 'password';
  loginPasswordInput.setAttribute('type', newType);
});
/* *********************************************************** */
