const fileInput = document.querySelector('#pdf_file');
const fileLabel = document.querySelector('#file-label');
const uploadForm = document.querySelector('#upload-form');
const generateButton = document.querySelector('#generate-button');

if (fileInput && fileLabel) {
    fileInput.addEventListener('change', () => {
        const fileName = fileInput.files?.[0]?.name;
        fileLabel.textContent = fileName || 'Klik untuk memilih PDF';
    });
}

if (uploadForm && generateButton) {
    uploadForm.addEventListener('submit', () => {
        generateButton.textContent = 'Memproses PDF...';
        generateButton.disabled = true;
    });
}
