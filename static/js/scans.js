// Управление историей сканирований

class ScansManager {
    constructor() {
        this.currentPage = 1;
        this.perPage = 10;
        this.totalPages = 1;
        this.selectedScans = new Set();
        this.allScansSelected = false;
        this.filters = {
            type: '',
            method: ''
        };
    }

    init() {
        this.bindEvents();
        this.bindFilterEvents();
        this.loadScans();
        this.checkAuthStatus();
    }

    // Привязка всех событий
    bindEvents() {
        // Кнопка "Закрити" в модальном окне
        const closeDetailsBtn = document.getElementById('closeDetailsBtn');
        if (closeDetailsBtn) {
            closeDetailsBtn.addEventListener('click', () => this.closeScanDetails());
        }

        // Кнопка "Обрати всі"
        const selectAllBtn = document.getElementById('selectAllBtn');
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => this.toggleSelectAll());
        }

        // Кнопка "Видалити обрані"
        const deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
        if (deleteSelectedBtn) {
            deleteSelectedBtn.addEventListener('click', () => this.deleteSelectedScans());
        }
    }

    // Привязка событий фильтров
    bindFilterEvents() {
        const filterType = document.getElementById('filterType');
        const filterMethod = document.getElementById('filterMethod');

        if (filterType) {
            filterType.addEventListener('change', (e) => {
                this.filters.type = e.target.value;
                this.currentPage = 1;
                this.loadScans();
            });
        }

        if (filterMethod) {
            filterMethod.addEventListener('change', (e) => {
                this.filters.method = e.target.value;
                this.currentPage = 1;
                this.loadScans();
            });
        }
    }

    // Загрузка списка сканирований
    async loadScans(page = 1) {
        this.currentPage = page;
        this.showLoadingState();
        
        try {
            const response = await fetch('/api/scans');
            
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/login';
                    return;
                }
                throw new Error('Помилка завантаження сканувань');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Фильтруем сканы на клиенте если нужно
                let filteredScans = data.scans;
                
                if (this.filters.type) {
                    filteredScans = filteredScans.filter(scan => scan.input_type === this.filters.type);
                }
                
                if (this.filters.method) {
                    filteredScans = filteredScans.filter(scan => scan.input_method === this.filters.method);
                }
                
                // Пагинация на клиенте
                const startIndex = (page - 1) * this.perPage;
                const endIndex = startIndex + this.perPage;
                const paginatedScans = filteredScans.slice(startIndex, endIndex);
                this.totalPages = Math.ceil(filteredScans.length / this.perPage);
                
                this.displayScans(paginatedScans);
                this.updatePagination(filteredScans.length);
                this.updateUI();
            } else {
                throw new Error(data.message);
            }
            
        } catch (error) {
            this.showError(error.message);
        }
    }

    // Отображение списка сканирований
    displayScans(scans) {
        const scansList = document.getElementById('scansList');
        const emptyState = document.getElementById('emptyState');
        const loadingState = document.getElementById('loadingState');
        
        loadingState.classList.add('hidden');
        
        if (scans.length === 0) {
            scansList.innerHTML = '';
            emptyState.classList.remove('hidden');
            this.updateEmptyStateText();
            return;
        }
        
        emptyState.classList.add('hidden');
        scansList.innerHTML = scans.map(scan => this.createScanCard(scan)).join('');
        
        // Добавляем обработчики событий для кликов по карточкам и кнопкам
        this.bindScanCardEvents();
    }

    // Создание карточки сканирования
    createScanCard(scan) {
        const date = new Date(scan.created_at).toLocaleString('uk-UA');
        const methodIcon = this.getMethodIcon(scan.input_method);
        const riskLevel = scan.safety_status || this.calculateRiskLevel(scan.ingredients || []);
        
        return `
            <div class="scan-card" data-scan-id="${scan.id}">
                <div class="scan-card-header">
                    <div class="scan-method">
                        <span class="method-icon">${methodIcon}</span>
                        <span class="method-text">${this.getMethodText(scan.input_method)}</span>
                        <span class="scan-type-badge">${this.getTypeText(scan.input_type)}</span>
                    </div>
                    <div class="scan-actions">
                        <input type="checkbox" class="scan-checkbox" data-scan-id="${scan.id}" onclick="event.stopPropagation(); scansManager.handleCheckboxClick(${scan.id})">
                        <button class="icon-btn delete" data-scan-id="${scan.id}" title="Видалити">
                            <img src="/static/images/delete.svg" alt="Видалити" width="16" height="16">
                        </button>
                    </div>
                </div>
                
                <div class="scan-card-content">
                    <div class="scan-preview">
                        ${scan.original_text ? this.truncateText(scan.original_text, 100) : 'Текст не знайдено'}
                    </div>
                    
                    <div class="scan-stats">
                        <span class="risk-badge risk-${riskLevel}">
                            ${this.getRiskText(riskLevel)}
                        </span>
                        <span class="ingredients-count">
                            ${scan.ingredients_count || 0} інгредієнтів
                        </span>
                    </div>
                </div>
                
                <div class="scan-card-footer">
                    <span class="scan-date">${date}</span>
                </div>
            </div>
        `;
    }

    // Привязка событий к карточкам сканирования
    bindScanCardEvents() {
        const scanCards = document.querySelectorAll('.scan-card');
        
        scanCards.forEach(card => {
            // Клик по всей карточке для просмотра деталей
            card.addEventListener('click', (e) => {
                // Проверяем, не кликнули ли по чекбоксу или кнопке удаления
                if (!e.target.closest('.scan-checkbox') && 
                    !e.target.closest('.icon-btn.delete') && 
                    e.target.className !== 'icon-btn delete') {
                    
                    const scanId = parseInt(card.dataset.scanId);
                    this.viewScanDetails(scanId);
                }
            });
            
            // Обработчик для кнопки удаления
            const deleteBtn = card.querySelector('.icon-btn.delete');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation(); // Останавливаем всплытие события
                    const scanId = parseInt(deleteBtn.dataset.scanId);
                    this.deleteScan(scanId);
                });
            }
        });
    }

    // Обработчик клика по чекбоксу
    handleCheckboxClick(scanId) {
        this.toggleScanSelection(scanId);
    }

    // Просмотр деталей сканирования
    async viewScanDetails(scanId) {
        try {
            const response = await fetch(`/api/scans/${scanId}`);
            
            if (!response.ok) {
                throw new Error('Помилка завантаження деталей');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showScanDetails(data.scan);
            } else {
                throw new Error(data.message);
            }
            
        } catch (error) {
            this.showError(error.message);
        }
    }
    
    // Показ деталей сканирования в модальном окне
    showScanDetails(scan) {
        const modal = document.getElementById('scanDetailsModal');
        const content = document.getElementById('scanDetailsContent');
        const date = new Date(scan.created_at).toLocaleString('uk-UA');
        const riskLevel = scan.safety_status || this.calculateRiskLevel(scan.ingredients_detailed || scan.ingredients || []);
        
        // Определяем длину текста и списка ингредиентов
        const isLongText = scan.original_text && scan.original_text.length > 500;
        const isLongList = (scan.ingredients_detailed && scan.ingredients_detailed.length > 15) || 
                        (scan.ingredients && scan.ingredients.length > 15);
        const ingredients = scan.ingredients_detailed || scan.ingredients || [];
        
        content.innerHTML = `
            <div class="scan-details">
                <div class="detail-row">
                    <strong>Тип введення:</strong>
                    <span>${this.getTypeText(scan.input_type)}</span>
                </div>
                <div class="detail-row">
                    <strong>Метод введення:</strong>
                    <span>${this.getMethodText(scan.input_method)}</span>
                </div>
                <div class="detail-row">
                    <strong>Дата сканування:</strong>
                    <span>${date}</span>
                </div>
                <div class="detail-row">
                    <strong>Рівень ризику:</strong>
                    <span class="risk-badge risk-${riskLevel}">${this.getRiskText(riskLevel)}</span>
                </div>
                
                <div class="detail-section">
                    <h4>Оригінальний текст:</h4>
                    <div class="original-text ${isLongText ? 'long-text' : ''}">
                        ${scan.original_text || 'Текст не знайдено'}
                    </div>
                    ${isLongText ? `<button class="show-more-btn" onclick="this.previousElementSibling.classList.toggle('long-text'); this.textContent = this.previousElementSibling.classList.contains('long-text') ? 'Показати більше' : 'Показати менше';">Показати більше</button>` : ''}
                </div>
                
                <div class="detail-section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
                        <h4 style="margin: 0;">Знайдені інгредієнти (${ingredients.length}):</h4>
                        <div style="display: flex; gap: 10px;">
                            <button onclick="scansManager.exportSingleScanToTxt(${scan.id})" class="export-pdf-btn" title="Експортувати в TXT">
                                TXT
                            </button>
                            <button onclick="scansManager.exportSingleScanToPdf(${scan.id})" class="export-pdf-btn" title="Експортувати в PDF">
                                PDF
                            </button>
                        </div>
                    </div>
                    <div class="ingredients-list ${isLongList ? 'long-list' : ''}">
                        ${ingredients.length > 0 
                            ? ingredients.map(ing => `
                                <div class="ingredient-item ${ing.risk_level || 'safe'}">
                                    <strong>${ing.name || 'Невідомий інгредієнт'}</strong>
                                    ${ing.description ? `<br><small>${ing.description}</small>` : ''}
                                    ${ing.risk_level ? `<br><small>Рівень ризику: ${this.getRiskText(ing.risk_level)}</small>` : ''}
                                </div>
                            `).join('')
                            : '<p>Не знайдено небезпечних інгредієнтів</p>'
                        }
                    </div>
                    ${isLongList ? `<button class="show-more-btn" onclick="this.previousElementSibling.classList.toggle('long-list'); this.textContent = this.previousElementSibling.classList.contains('long-list') ? 'Показати більше' : 'Показати менше';">Показати більше</button>` : ''}
                </div>
            </div>
        `;
        
        modal.classList.remove('hidden');
    }

    // Экспорт одного сканирования в PDF
    exportSingleScanToPdf(scanId) {
        try {
            this.showMessage('Створення PDF...', 'success');
            
            // Проверьте этот URL
            const url = `/api/scans/${scanId}/export/pdf`;
            console.log('Opening PDF URL:', url); // Добавьте эту строку для отладки
            window.open(url, '_blank');
            
        } catch (error) {
            console.error('Помилка при експорті в PDF:', error);
            this.showMessage(`Помилка: ${error.message}`, 'error');
        }
    }
    
    exportSingleScanToTxt(scanId) {
    try {
        this.showMessage('Створення TXT...', 'success');
        const url = `/api/scans/${scanId}/export/txt`;
        window.open(url, '_blank');
    } catch (error) {
        console.error('Помилка при експорті в TXT:', error);
        this.showMessage(`Помилка: ${error.message}`, 'error');
    }
    }
    
    // Удаление сканирования
    async deleteScan(scanId) {
        if (!confirm('Ви впевнені, що хочете видалити це сканування?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/scans/${scanId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showMessage(data.message, 'success');
                this.loadScans(this.currentPage);
                this.selectedScans.delete(scanId);
                this.updateBulkActions();
            } else {
                throw new Error(data.message);
            }
            
        } catch (error) {
            this.showError(error.message);
        }
    }

    // Массовое удаление сканирований
    async deleteSelectedScans() {
        const selectedIds = Array.from(this.selectedScans);
        
        if (selectedIds.length === 0) {
            this.showMessage('Оберіть сканування для видалення', 'error');
            return;
        }
        
        if (!confirm(`Ви впевнені, що хочете видалити ${selectedIds.length} сканувань?`)) {
            return;
        }
        
        try {
            const response = await fetch('/api/scans/bulk-delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    scan_ids: selectedIds
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showMessage(data.message, 'success');
                this.loadScans(this.currentPage);
                this.selectedScans.clear();
                this.allScansSelected = false;
                this.updateBulkActions();
            } else {
                throw new Error(data.message);
            }
            
        } catch (error) {
            this.showError(error.message);
        }
    }

    // Управление выделением
    toggleScanSelection(scanId) {
        const checkbox = document.querySelector(`.scan-checkbox[data-scan-id="${scanId}"]`);
        
        if (checkbox) {
            if (checkbox.checked) {
                this.selectedScans.add(scanId);
            } else {
                this.selectedScans.delete(scanId);
                this.allScansSelected = false;
            }
        }
        
        this.updateBulkActions();
    }

    toggleSelectAll() {
        const checkboxes = document.querySelectorAll('.scan-checkbox');
        
        if (this.allScansSelected) {
            // Снимаем выделение
            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
                const scanId = parseInt(checkbox.dataset.scanId);
                this.selectedScans.delete(scanId);
            });
            this.allScansSelected = false;
        } else {
            // Выделяем все
            checkboxes.forEach(checkbox => {
                const scanId = parseInt(checkbox.dataset.scanId);
                checkbox.checked = true;
                this.selectedScans.add(scanId);
            });
            this.allScansSelected = true;
        }
        
        this.updateBulkActions();
    }

    updateBulkActions() {
        const deleteBtn = document.getElementById('deleteSelectedBtn');
        const selectAllBtn = document.getElementById('selectAllBtn');
        
        if (deleteBtn) {
            deleteBtn.disabled = this.selectedScans.size === 0;
            deleteBtn.textContent = this.selectedScans.size > 0 
                ? `Видалити обрані (${this.selectedScans.size})` 
                : 'Видалити обрані';
        }
        if (selectAllBtn) {
            selectAllBtn.textContent = this.allScansSelected ? 'Зняти виділення' : 'Обрати всі';
        }
    }

    // Вспомогательные методы
    getMethodIcon(method) {
        const icons = {
            'text': `<img src="/static/images/scan_verification.svg" alt="Ручний ввід" width="24" height="24">`,
            'device': `<img src="/static/images/scan_devices.svg" alt="З пристрою" width="24" height="24">`,
            'camera': `<img src="/static/images/scan_eye.svg" alt="Камера" width="24" height="24">`
        };
        return icons[method] || `<img src="/static/images/default_icon.svg" alt="Іконка" width="24" height="24">`;
    }

    getMethodText(method) {
        const texts = {
            'text': 'Ручний ввід',
            'device': 'З пристрою',
            'camera': 'Камера'
        };
        return texts[method] || 'Невідомий метод';
    }

    getTypeText(type) {
        const texts = {
            'manual': 'Текст',
            'camera': 'Фото'
        };
        return texts[type] || 'Невідомий тип';
    }

    calculateRiskLevel(ingredients) {
        if (!ingredients || ingredients.length === 0) return 'safe';
        
        const riskLevels = ingredients.map(ing => {
            if (typeof ing === 'object') {
                return ing.risk_level || 'safe';
            }
            return 'safe';
        });
        
        if (riskLevels.includes('high') || riskLevels.includes('danger')) return 'high';
        if (riskLevels.includes('medium') || riskLevels.includes('warning')) return 'medium';
        if (riskLevels.includes('low')) return 'low';
        return 'safe';
    }

    getRiskText(riskLevel) {
        const texts = {
            'high': 'Високий ризик',
            'danger': 'Високий ризик',
            'medium': 'Середній ризик',
            'warning': 'Середній ризик',
            'low': 'Низький ризик',
            'safe': 'Безпечно',
        };
        return texts[riskLevel] || 'Невідомо';
    }

    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    // Обновление текста пустого состояния в зависимости от фильтров
    updateEmptyStateText() {
        const emptyState = document.getElementById('emptyState');
        const emptyTitle = emptyState.querySelector('h3');
        const emptyText = emptyState.querySelector('p');
        
        if (this.filters.type || this.filters.method) {
            let filterText = '';
            
            if (this.filters.type && this.filters.method) {
                filterText = `за типом "${this.getTypeText(this.filters.type)}" та методом "${this.getMethodText(this.filters.method)}"`;
            } else if (this.filters.type) {
                filterText = `за типом "${this.getTypeText(this.filters.type)}"`;
            } else if (this.filters.method) {
                filterText = `за методом "${this.getMethodText(this.filters.method)}"`;
            }
            
            emptyTitle.textContent = 'Сканування не знайдено';
            emptyText.textContent = `Не знайдено сканувань ${filterText}. Спробуйте змінити критерії пошуку.`;
        } else {
            emptyTitle.textContent = 'Немає сканувань';
            emptyText.textContent = 'Тут будуть зберігатися всі ваші сканування косметики';
        }
    }

    // Пагинация
    updatePagination(totalItems) {
        const pagination = document.getElementById('pagination');
        const totalPages = Math.ceil(totalItems / this.perPage);
        
        if (totalPages <= 1) {
            pagination.classList.add('hidden');
            return;
        }
        
        pagination.classList.remove('hidden');
        
        let paginationHTML = '';
        
        if (this.currentPage > 1) {
            paginationHTML += `<button onclick="scansManager.loadScans(${this.currentPage - 1})">← Попередня</button>`;
        }
        
        for (let i = 1; i <= totalPages; i++) {
            if (i === this.currentPage) {
                paginationHTML += `<span class="current-page">${i}</span>`;
            } else {
                paginationHTML += `<button onclick="scansManager.loadScans(${i})">${i}</button>`;
            }
        }
        
        if (this.currentPage < totalPages) {
            paginationHTML += `<button onclick="scansManager.loadScans(${this.currentPage + 1})">Наступна →</button>`;
        }
        
        pagination.innerHTML = paginationHTML;
    }

    // UI состояния
    showLoadingState() {
        document.getElementById('scansList').innerHTML = '';
        document.getElementById('emptyState').classList.add('hidden');
        document.getElementById('pagination').classList.add('hidden');
        document.getElementById('loadingState').classList.remove('hidden');
    }

    showError(message) {
        this.showMessage(message, 'error');
        document.getElementById('loadingState').classList.add('hidden');
    }

    showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 5px;
            color: white;
            font-weight: bold;
            z-index: 1000;
            opacity: 0;
            animation: fadeInOut 5s;
        `;
        
        if (type === 'success') {
            messageDiv.style.backgroundColor = '#4CAF50';
        } else if (type === 'error') {
            messageDiv.style.backgroundColor = '#f44336';
        } else {
            messageDiv.style.backgroundColor = '#2196F3';
        }
        
        // Добавляем анимацию в стили если ее нет
        if (!document.querySelector('#message-animation')) {
            const style = document.createElement('style');
            style.id = 'message-animation';
            style.textContent = `
                @keyframes fadeInOut {
                    0% { opacity: 0; transform: translateY(-20px); }
                    10% { opacity: 1; transform: translateY(0); }
                    90% { opacity: 1; transform: translateY(0); }
                    100% { opacity: 0; transform: translateY(-20px); }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(messageDiv);
        setTimeout(() => messageDiv.remove(), 5000);
    }

    closeScanDetails() {
        document.getElementById('scanDetailsModal').classList.add('hidden');
    }

    // Проверка авторизации
    async checkAuthStatus() {
        try {
            const response = await fetch('/api/status');
            
            if (!response.ok) {
                window.location.href = '/login';
                return;
            }
            
            const data = await response.json();
            
            if (data.status === 'authenticated') {
                const userEmailElement = document.getElementById('userEmail');
                if (userEmailElement) {
                    userEmailElement.textContent = data.user.email;
                }
            }
            
        } catch (error) {
            console.error('Auth error:', error);
        }
    }

    updateUI() {
        // Дополнительные обновления UI при необходимости
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    window.scansManager = new ScansManager();
    window.scansManager.init();
});