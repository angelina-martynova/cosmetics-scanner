// Обработка выбора текстового файла
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('file', file);

        fetch('/api/upload_text_file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                app.showMessage('Файл успешно загружен и проанализирован');
            } else {
                app.showMessage('Ошибка: ' + data.message, 'error');
            }
        })
        .catch(error => {
            app.showMessage('Ошибка при загрузке файла: ' + error, 'error');
        });
    }
}
