const fileInput = document.querySelector('#pdf_file');
const fileLabel = document.querySelector('#file-label');
const uploadForm = document.querySelector('#upload-form');
const generateButton = document.querySelector('#generate-button');

if (fileInput && fileLabel) {
    fileInput.addEventListener('change', () => {
        const file = fileInput.files?.[0];
        if (!file) {
            fileLabel.textContent = 'Klik untuk memilih PDF';
            return;
        }

        const sizeMb = file.size / 1024 / 1024;
        fileLabel.textContent = `${file.name} (${sizeMb.toFixed(1)} MB)`;
    });
}

if (uploadForm && generateButton) {
    uploadForm.addEventListener('submit', () => {
        generateButton.textContent = 'Memproses dan merapikan soal...';
        generateButton.disabled = true;
    });
}
