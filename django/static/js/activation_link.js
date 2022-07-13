let copiedLink = document.getElementById("link").textContent.trim();

function copyToClipboard() {
    let copyBtn = document.getElementById("copy");
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(copiedLink);
    });
}

document.addEventListener('DOMContentLoaded', copyToClipboard);