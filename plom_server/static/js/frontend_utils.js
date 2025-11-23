/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2023 Brennen Chiu
    Copyright (C) 2024 Aden Chan
    Copyright (C) 2024 Bryan Tanady
    Copyright (C) 2025 Aidan Murphy
*/

const firstWordList = ['adorable', 'adventurous', 'aggressive', 'agreeable', 'alert', 'alive', 'amused', 'angry', 'annoyed', 'anxious', 'attractive', 'average', 'bad', 'beautiful', 'better', 'bewildered', 'blue', 'blushing', 'bored', 'brainy', 'brave', 'breakable', 'bright', 'busy', 'calm', 'careful', 'cautious', 'charming', 'cheerful', 'clean', 'clear', 'clever', 'cloudy', 'clumsy', 'colourful', 'combative', 'comfortable', 'concerned', 'confused', 'cooperative', 'crazy', 'curious', 'cute', 'dangerous', 'delightful', 'determined', 'different', 'distinct', 'dizzy', 'eager', 'easy', 'elated', 'elegant', 'energetic', 'enthusiastic', 'excited', 'expensive', 'exuberant', 'fair', 'faithful', 'famous', 'fancy', 'fantastic', 'fine', 'friendly', 'funny', 'gentle', 'gifted', 'glamorous', 'gleaming', 'glorious', 'good', 'gorgeous', 'handsome', 'happy', 'healthy', 'helpful', 'hilarious', 'hungry', 'important', 'innocent', 'jolly', 'kind', 'light', 'lively', 'lovely', 'lucky', 'magnificent', 'misty', 'muddy', 'mushy', 'mysterious', 'naughty', 'nice', 'oldfashioned', 'outstanding', 'perfect', 'powerful', 'precious', 'real', 'relieved', 'rich', 'shiny', 'smiling', 'sparkling', 'successful', 'super', 'thoughtful', 'wandering', 'xenogeneic', 'young'];
const secondWordList = ['actor', 'actress', 'advertisement', 'airport', 'animal', 'answer', 'apple', 'ballon', 'banana', 'battery', 'bears', 'bird', 'bison', 'boy', 'breakfast', 'camera', 'candle', 'car', 'cartoon', 'cat', 'chicken', 'computer', 'deer', 'dog', 'dolphin', 'eagle', 'fire', 'fish', 'food', 'ghost', 'gold', 'gorilla', 'grass', 'guitar', 'hamburger', 'helicopter', 'horse', 'ice', 'jackal', 'jelly', 'juice', 'kangaroo', 'king', 'lawyer', 'lion', 'lizard', 'llamas', 'lobster', 'machine', 'magician', 'monkey', 'mosquitose', 'panda', 'parrot', 'pig', 'pizza', 'planet', 'pony', 'potato', 'queen', 'rabbit', 'rainbow', 'shark', 'snake', 'software', 'tiger', 'tomato', 'train', 'truck', 'turkey', 'whale', 'whale', 'wolf'];
let generateUsernameBtn = document.getElementById('generate-username');
let copyBtn = document.getElementById('copy-btn');

let togglePassword = document.getElementById('togglePassword');
let newPassword1 = document.getElementById('id_new_password1');
let newPassword2 = document.getElementById('id_new_password2');

// login.html
let showPassword = document.getElementById('check-password');

function generateRandomUsername() {
  generateUsernameBtn.addEventListener('click', () => {
    let firstUserWord = firstWordList[Math.floor(Math.random() * firstWordList.length)].split(' ').join('');
    let secondUserWord = secondWordList[Math.floor(Math.random() * secondWordList.length)].split(' ').join('');
    let randomNumAsString = (Math.floor(Math.random() * 10) + 1).toString();
    document.getElementById('id_username').value = firstUserWord + secondUserWord + randomNumAsString;
  });
}

function copyToClipboard() {
  const passwordResetLink = copyBtn.getAttribute('data-passwordResetLink');
  copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(passwordResetLink);
  });
}

function viewPassword() {
  togglePassword.addEventListener('click', () => {
    const type = newPassword1.getAttribute('type') === 'password' ? 'text' : 'password';
    const classAttribute = togglePassword.getAttribute('class') === 'bi-eye' ? 'bi-eye-slash' : 'bi-eye';
    newPassword1.setAttribute('type', type);
    newPassword2.setAttribute('type', type);
    togglePassword.setAttribute('class', classAttribute);
  });
}

// login.html
function showLoginPassword() {
  let loginPasswordInput = document.getElementById('typePasswordX');
  showPassword.addEventListener('click', () => {
    const passwordType = loginPasswordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    loginPasswordInput.setAttribute('type', passwordType);
  });
}

document.addEventListener('DOMContentLoaded', generateRandomUsername);
document.addEventListener('DOMContentLoaded', copyToClipboard);
document.addEventListener('DOMContentLoaded', viewPassword);
document.addEventListener('DOMContentLoaded', showLoginPassword);
