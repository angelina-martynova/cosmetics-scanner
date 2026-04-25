// scans.js — Skipley Scan History

class ScansManager {
    constructor() {
        this.currentPage = 1;
        this.perPage = 10;
        this.totalPages = 1;
        this.selectedScans = new Set();
        this.allScansSelected = false;
        this.filters = { risk: '', method: '' };
        this.currentDetailScan = null;
    }

    init() {
        this.bindEvents();
        this.bindFilterEvents();
        this.loadScans();
        this.checkAuthStatus();
    }

    bindEvents() {
        var self = this;
        var closeBtn = document.getElementById('closeDetailsBtn');
        if (closeBtn) closeBtn.addEventListener('click', function() { self.closeScanDetails(); });

        var selectAllBtn = document.getElementById('selectAllBtn');
        if (selectAllBtn) selectAllBtn.addEventListener('click', function() { self.toggleSelectAll(); });

        var deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
        if (deleteSelectedBtn) deleteSelectedBtn.addEventListener('click', function() { self.deleteSelectedScans(); });

        var exportBtn = document.getElementById('exportScanBtn');
        if (exportBtn) exportBtn.addEventListener('click', function() {
            if (self.currentDetailScan) self.exportSingleScanToTxt(self.currentDetailScan.id);
        });
    }

    bindFilterEvents() {
        var self = this;
        // Pill button filters
        document.querySelectorAll('.pill-btn[data-filter]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var filterType = btn.getAttribute('data-filter');
                var value = btn.getAttribute('data-value');

                self.filters[filterType] = value;
                self.currentPage = 1;

                // Update active state for the group
                document.querySelectorAll('.pill-btn[data-filter="' + filterType + '"]').forEach(function(b) {
                    b.classList.remove('active');
                });
                btn.classList.add('active');

                // Show/hide clear button
                var clearBtn = document.getElementById('filterClear');
                if (clearBtn) {
                    if (self.filters.risk || self.filters.method) {
                        clearBtn.classList.remove('hidden');
                    } else {
                        clearBtn.classList.add('hidden');
                    }
                }

                self.loadScans();
            });
        });

        var clearBtn = document.getElementById('filterClear');
        if (clearBtn) {
            clearBtn.addEventListener('click', function() {
                self.filters.risk = '';
                self.filters.method = '';
                self.currentPage = 1;
                document.querySelectorAll('.pill-btn[data-filter]').forEach(function(b) {
                    b.classList.remove('active');
                });
                document.querySelectorAll('.pill-btn[data-value=""]').forEach(function(b) {
                    b.classList.add('active');
                });
                clearBtn.classList.add('hidden');
                self.loadScans();
            });
        }
    }

    async loadScans(page) {
        if (page === undefined) page = 1;
        this.currentPage = page;
        this.showLoadingState();

        try {
            var response = await fetch('/api/scans');
            if (!response.ok) {
                if (response.status === 401) { window.location.href = '/login'; return; }
                throw new Error('Помилка завантаження сканувань');
            }

            var data = await response.json();
            if (data.status === 'success') {
                var filteredScans = data.scans;

                // Filter by risk
                if (this.filters.risk) {
                    var riskFilter = this.filters.risk;
                    var self = this;
                    filteredScans = filteredScans.filter(function(scan) {
                        var rl = scan.safety_status || self.calculateRiskLevel(scan.ingredients || []);
                        return rl === riskFilter;
                    });
                }

                // Filter by method
                if (this.filters.method) {
                    var methodFilter = this.filters.method;
                    filteredScans = filteredScans.filter(function(scan) {
                        return scan.input_method === methodFilter;
                    });
                }

                var startIndex = (page - 1) * this.perPage;
                var paginatedScans = filteredScans.slice(startIndex, startIndex + this.perPage);
                this.totalPages = Math.ceil(filteredScans.length / this.perPage);

                this.displayScans(paginatedScans);
                this.updatePagination(filteredScans.length);
                this.updateScansCount(filteredScans.length);
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    displayScans(scans) {
        var scansList = document.getElementById('scansList');
        var emptyState = document.getElementById('emptyState');
        var loadingState = document.getElementById('loadingState');

        loadingState.classList.add('hidden');

        if (scans.length === 0) {
            scansList.innerHTML = '';
            emptyState.classList.remove('hidden');
            this.updateEmptyStateText();
            return;
        }

        emptyState.classList.add('hidden');
        var self = this;
        scansList.innerHTML = scans.map(function(scan) { return self.createScanCard(scan); }).join('');
        this.bindScanCardEvents();
    }

    createScanCard(scan) {
        var date = new Date(scan.created_at).toLocaleString('uk-UA');
        var riskLevel = scan.safety_status || this.calculateRiskLevel(scan.ingredients || []);
        var methodIconSvg = this.getMethodSvg(scan.input_method);
        var methodText = this.getMethodText(scan.input_method);
        var preview = scan.original_text ? this.truncateText(scan.original_text, 100) : 'Текст не знайдено';

        return '<div class="scan-card" data-scan-id="' + scan.id + '">' +
            '<button class="scan-card-delete" data-scan-id="' + scan.id + '" title="Видалити" onclick="event.stopPropagation(); scansManager.deleteScan(' + scan.id + ')">' +
                '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>' +
            '</button>' +
            '<div class="scan-card-method">' +
                '<div class="scan-method-icon">' + methodIconSvg + '</div>' +
                '<div>' +
                    '<div class="scan-method-name">' + methodText + '</div>' +
                    '<div class="scan-method-date">' + date + '</div>' +
                '</div>' +
            '</div>' +
            '<p class="scan-preview-text">' + preview + '</p>' +
            '<div class="scan-stats">' +
                '<span class="risk-badge risk-sm risk-' + riskLevel + '"><span class="dot"></span>' + this.getRiskText(riskLevel) + '</span>' +
                '<span class="scan-ingredients-count">' + (scan.ingredients_count || 0) + ' інгредієнтів</span>' +
            '</div>' +
            '<div class="scan-card-footer" style="display:flex;align-items:center;gap:8px">' +
                '<input type="checkbox" class="scan-checkbox" data-scan-id="' + scan.id + '" onclick="event.stopPropagation(); scansManager.handleCheckboxClick(' + scan.id + ')">' +
                '<span class="scan-product">' + (this.getTypeText(scan.input_type) || '') + '</span>' +
            '</div>' +
        '</div>';
    }

    getMethodSvg(method) {
        var icons = {
            'text': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/></svg>',
            'device': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
            'camera': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2m10 0h2a2 2 0 0 1 2 2v2m0 10v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><rect x="7" y="7" width="10" height="10" rx="1.5"/></svg>'
        };
        return icons[method] || icons['text'];
    }

    bindScanCardEvents() {
        var self = this;
        document.querySelectorAll('.scan-card').forEach(function(card) {
            card.addEventListener('click', function(e) {
                if (!e.target.closest('.scan-checkbox') && !e.target.closest('.scan-card-delete')) {
                    var scanId = parseInt(card.dataset.scanId);
                    self.viewScanDetails(scanId);
                }
            });
        });
    }

    handleCheckboxClick(scanId) {
        this.toggleScanSelection(scanId);
    }

    async viewScanDetails(scanId) {
        try {
            var response = await fetch('/api/scans/' + scanId);
            if (!response.ok) throw new Error('Помилка завантаження деталей');
            var data = await response.json();
            if (data.status === 'success') {
                this.showScanDetails(data.scan);
            } else { throw new Error(data.message); }
        } catch (error) {
            this.showError(error.message);
        }
    }

    showScanDetails(scan) {
        this.currentDetailScan = scan;
        var modal = document.getElementById('scanDetailsModal');
        var content = document.getElementById('scanDetailsContent');
        var meta = document.getElementById('detailMeta');
        var date = new Date(scan.created_at).toLocaleString('uk-UA');

        if (meta) meta.textContent = this.getMethodText(scan.input_method) + ' · ' + date;

        var ingredients = scan.ingredients_detailed || scan.ingredients || [];

        // Risk counts
        var counts = {};
        ingredients.forEach(function(ing) {
            var lvl = ing.risk_level || 'safe';
            counts[lvl] = (counts[lvl] || 0) + 1;
        });

        var html = '';

        // Summary badges
        html += '<div class="risk-counts" style="margin-bottom:20px">';
        for (var lvl in counts) {
            html += '<span class="risk-badge risk-' + lvl + '"><span class="dot"></span>' + counts[lvl] + ' ' + lvl + '</span>';
        }
        html += '</div>';

        // Ingredients
        html += '<p class="detail-section-label">Інгредієнти</p>';
        html += '<div class="detail-ingredients">';
        if (ingredients.length > 0) {
            ingredients.forEach(function(ing) {
                var riskClass = 'risk-' + (ing.risk_level || 'safe');
                html += '<div class="detail-ingredient">';
                html += '<div style="flex:1"><div class="name">' + (ing.name || 'Невідомий') + '</div>';
                if (ing.description) html += '<div class="desc">' + ing.description + '</div>';
                html += '</div>';
                html += '<span class="risk-badge risk-sm ' + riskClass + '"><span class="dot"></span>' + (ing.risk_level || 'safe') + '</span>';
                html += '</div>';
            });
        } else {
            html += '<div style="padding:16px;text-align:center;color:var(--txt-3)">Не знайдено інгредієнтів</div>';
        }
        html += '</div>';

        // Original text
        if (scan.original_text) {
            html += '<p class="detail-section-label">Розпізнаний текст</p>';
            html += '<div class="original-text">' + scan.original_text + '</div>';
        }

        content.innerHTML = html;
        modal.classList.remove('hidden');
    }

    exportSingleScanToPdf(scanId) {
        try {
            this.showMessage('Створення PDF...', 'success');
            window.open('/api/scans/' + scanId + '/export/pdf', '_blank');
        } catch (error) {
            this.showMessage('Помилка: ' + error.message, 'error');
        }
    }

    exportSingleScanToTxt(scanId) {
        try {
            this.showMessage('Створення TXT...', 'success');
            window.open('/api/scans/' + scanId + '/export/txt', '_blank');
        } catch (error) {
            this.showMessage('Помилка: ' + error.message, 'error');
        }
    }

    async deleteScan(scanId) {
        if (!confirm('Ви впевнені, що хочете видалити це сканування?')) return;
        try {
            var response = await fetch('/api/scans/' + scanId, { method: 'DELETE' });
            var data = await response.json();
            if (data.status === 'success') {
                this.showMessage(data.message, 'success');
                this.loadScans(this.currentPage);
                this.selectedScans.delete(scanId);
                this.updateBulkActions();
            } else { throw new Error(data.message); }
        } catch (error) {
            this.showError(error.message);
        }
    }

    async deleteSelectedScans() {
        var selectedIds = Array.from(this.selectedScans);
        if (selectedIds.length === 0) { this.showMessage('Оберіть сканування', 'error'); return; }
        if (!confirm('Видалити ' + selectedIds.length + ' сканувань?')) return;

        try {
            var response = await fetch('/api/scans/bulk-delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scan_ids: selectedIds })
            });
            var data = await response.json();
            if (data.status === 'success') {
                this.showMessage(data.message, 'success');
                this.loadScans(this.currentPage);
                this.selectedScans.clear();
                this.allScansSelected = false;
                this.updateBulkActions();
            } else { throw new Error(data.message); }
        } catch (error) {
            this.showError(error.message);
        }
    }

    toggleScanSelection(scanId) {
        var checkbox = document.querySelector('.scan-checkbox[data-scan-id="' + scanId + '"]');
        if (checkbox) {
            if (checkbox.checked) { this.selectedScans.add(scanId); }
            else { this.selectedScans.delete(scanId); this.allScansSelected = false; }
        }
        this.updateBulkActions();
    }

    toggleSelectAll() {
        var self = this;
        var checkboxes = document.querySelectorAll('.scan-checkbox');
        if (this.allScansSelected) {
            checkboxes.forEach(function(cb) {
                cb.checked = false;
                self.selectedScans.delete(parseInt(cb.dataset.scanId));
            });
            this.allScansSelected = false;
        } else {
            checkboxes.forEach(function(cb) {
                cb.checked = true;
                self.selectedScans.add(parseInt(cb.dataset.scanId));
            });
            this.allScansSelected = true;
        }
        this.updateBulkActions();
    }

    updateBulkActions() {
        var deleteBtn = document.getElementById('deleteSelectedBtn');
        var selectAllBtn = document.getElementById('selectAllBtn');
        if (deleteBtn) {
            deleteBtn.disabled = this.selectedScans.size === 0;
            deleteBtn.textContent = this.selectedScans.size > 0
                ? 'Видалити обрані (' + this.selectedScans.size + ')' : 'Видалити обрані';
        }
        if (selectAllBtn) {
            selectAllBtn.textContent = this.allScansSelected ? 'Зняти виділення' : 'Обрати всі';
        }
    }

    // Helpers
    getMethodText(method) {
        return { 'text': 'Вручну', 'device': 'З пристрою', 'camera': 'Камера' }[method] || 'Невідомий';
    }

    getTypeText(type) {
        return { 'manual': 'Текст', 'camera': 'Фото' }[type] || '';
    }

    calculateRiskLevel(ingredients) {
        if (!ingredients || ingredients.length === 0) return 'safe';
        var levels = ingredients.map(function(ing) {
            return (typeof ing === 'object') ? (ing.risk_level || 'safe') : 'safe';
        });
        if (levels.indexOf('high') !== -1 || levels.indexOf('danger') !== -1) return 'high';
        if (levels.indexOf('medium') !== -1 || levels.indexOf('warning') !== -1) return 'medium';
        if (levels.indexOf('low') !== -1) return 'low';
        return 'safe';
    }

    getRiskText(riskLevel) {
        return { 'high': 'Високий', 'danger': 'Високий', 'medium': 'Середній',
                 'warning': 'Середній', 'low': 'Низький', 'safe': 'Безпечно' }[riskLevel] || 'Невідомо';
    }

    truncateText(text, maxLength) {
        if (!text) return '';
        return text.length <= maxLength ? text : text.substring(0, maxLength) + '...';
    }

    updateEmptyStateText() {
        var emptyState = document.getElementById('emptyState');
        var emptyTitle = emptyState.querySelector('h3');
        var emptyText = emptyState.querySelector('p');
        if (this.filters.risk || this.filters.method) {
            emptyTitle.textContent = 'Немає сканувань за фільтром';
            emptyText.textContent = 'Спробуйте змінити критерії пошуку.';
        } else {
            emptyTitle.textContent = 'Немає сканувань';
            emptyText.textContent = 'Тут будуть зберігатися всі ваші сканування косметики';
        }
    }

    updateScansCount(total) {
        var el = document.getElementById('scansCount');
        if (el) el.textContent = total + ' результат' + (total !== 1 ? 'ів' : '');
    }

    updatePagination(totalItems) {
        var pagination = document.getElementById('pagination');
        var totalPages = Math.ceil(totalItems / this.perPage);

        if (totalPages <= 1) { pagination.classList.add('hidden'); return; }
        pagination.classList.remove('hidden');

        var html = '';
        for (var i = 1; i <= totalPages; i++) {
            if (i === this.currentPage) {
                html += '<span class="page-current">' + i + '</span>';
            } else {
                html += '<button onclick="scansManager.loadScans(' + i + ')">' + i + '</button>';
            }
        }
        pagination.innerHTML = html;
    }

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
        var messageDiv = document.createElement('div');
        messageDiv.className = 'message ' + type;
        messageDiv.textContent = message;
        document.body.appendChild(messageDiv);
        setTimeout(function() { if (messageDiv.parentNode) messageDiv.remove(); }, 5000);
    }

    closeScanDetails() {
        document.getElementById('scanDetailsModal').classList.add('hidden');
        this.currentDetailScan = null;
    }

    async checkAuthStatus() {
        try {
            var response = await fetch('/api/status');
            if (!response.ok) { window.location.href = '/login'; return; }
            var data = await response.json();
            if (data.status === 'authenticated') {
                var el = document.getElementById('userEmail');
                if (el) el.textContent = data.user.email;
            }
        } catch (error) { console.error('Auth error:', error); }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    window.scansManager = new ScansManager();
    window.scansManager.init();
});
