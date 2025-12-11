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
            let url = `/api/scans?page=${page}&per_page=${this.perPage}`;
            
            if (this.filters.type) {
                url += `&type=${encodeURIComponent(this.filters.type)}`;
            }
            if (this.filters.method) {
                url += `&method=${encodeURIComponent(this.filters.method)}`;
            }
            
            const response = await fetch(url);
            
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/login';
                    return;
                }
                throw new Error('Помилка завантаження сканувань');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.displayScans(data.scans);
                this.updatePagination(data);
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
        const riskLevel = this.calculateRiskLevel(scan.ingredients_detected);
        
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
                            ${scan.ingredients_detected ? scan.ingredients_detected.length : 0} інгредієнтів
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
        const riskLevel = this.calculateRiskLevel(scan.ingredients_detected);
        
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
                    <div class="original-text">${scan.original_text || 'Текст не знайдено'}</div>
                </div>
                
                <div class="detail-section">
                    <h4>Знайдені інгредієнти (${scan.ingredients_detected ? scan.ingredients_detected.length : 0}):</h4>
                    <div class="ingredients-list">
                        ${scan.ingredients_detected && scan.ingredients_detected.length > 0 
                            ? scan.ingredients_detected.map(ing => `
                                <div class="ingredient-item ${ing.risk_level || 'safe'}">
                                    <strong>${ing.name}</strong>
                                    ${ing.description ? `<br><small>${ing.description}</small>` : ''}
                                </div>
                            `).join('')
                            : '<p>Не знайдено небезпечних інгредієнтів</p>'
                        }
                    </div>
                </div>
            </div>
        `;
        
        modal.classList.remove('hidden');
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
        
        const riskLevels = ingredients.map(ing => ing.risk_level);
        
        if (riskLevels.includes('high')) return 'high';
        if (riskLevels.includes('medium')) return 'medium';
        if (riskLevels.includes('low')) return 'low';
        return 'safe';
    }

    getRiskText(riskLevel) {
        const texts = {
            'high': 'Високий ризик',
            'medium': 'Середній ризик',
            'low': 'Низький ризик',
            'safe': 'Безпечно'
        };
        return texts[riskLevel] || 'Невідомо';
    }

    truncateText(text, maxLength) {
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
    updatePagination(data) {
        const pagination = document.getElementById('pagination');
        
        if (data.pages <= 1) {
            pagination.classList.add('hidden');
            return;
        }
        
        pagination.classList.remove('hidden');
        
        let paginationHTML = '';
        
        if (data.current_page > 1) {
            paginationHTML += `<button onclick="scansManager.loadScans(${data.current_page - 1})">← Попередня</button>`;
        }
        
        for (let i = 1; i <= data.pages; i++) {
            if (i === data.current_page) {
                paginationHTML += `<span class="current-page">${i}</span>`;
            } else {
                paginationHTML += `<button onclick="scansManager.loadScans(${i})">${i}</button>`;
            }
        }
        
        if (data.current_page < data.pages) {
            paginationHTML += `<button onclick="scansManager.loadScans(${data.current_page + 1})">Наступна →</button>`;
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
                document.getElementById('userEmail').textContent = data.user.email;
            }
            
        } catch (error) {
            window.location.href = '/login';
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