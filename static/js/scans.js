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

    normalizeRiskLevel(level) {
        if (!level) return 'safe';
        var l = level.toLowerCase().trim();
        if (l === 'danger') return 'high';
        if (l === 'warning') return 'medium';
        if (l === 'low_warning') return 'low';
        if (['safe', 'low', 'medium', 'high', 'unknown'].indexOf(l) !== -1) return l;
        return 'safe';
    }

    init() {
        this.bindEvents();
        this.bindFilterEvents();
        this.loadScans();
        this.checkAuthStatus();
        window.addEventListener('languageChanged', () => { this.rerender(); });
    }

    rerender() {
        if (this.currentDetailScan) {
            this.showScanDetails(this.currentDetailScan);
        }
        this.loadScans(this.currentPage);
    }

    bindEvents() {
        var self = this;
        var closeBtn = document.getElementById('closeDetailsBtn');
        if (closeBtn) closeBtn.addEventListener('click', function() { self.closeScanDetails(); });

        var selectAllBtn = document.getElementById('selectAllBtn');
        if (selectAllBtn) selectAllBtn.addEventListener('click', function() { self.toggleSelectAll(); });

        var deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
        if (deleteSelectedBtn) deleteSelectedBtn.addEventListener('click', function() { self.deleteSelectedScans(); });

        var exportSelectedBtn = document.getElementById('exportSelectedBtn');
        if (exportSelectedBtn) exportSelectedBtn.addEventListener('click', function() { self.exportSelectedScans(); });

        // Обработчик закрытия модального окна деталей
        var scanDetailsModal = document.getElementById('scanDetailsModal');
        if (scanDetailsModal) {
            scanDetailsModal.addEventListener('click', function(e) {
                if (e.target === scanDetailsModal) self.closeScanDetails();
            });
        }

        // Safety legend modal
        var safetyInfoBtn = document.getElementById('safetyInfoBtn');
        var safetyLegendModal = document.getElementById('safetyLegendModal');
        var closeSafetyLegend = document.getElementById('closeSafetyLegend');
        if (safetyInfoBtn && safetyLegendModal) {
            safetyInfoBtn.addEventListener('click', function() {
                safetyLegendModal.classList.remove('hidden');
            });
            if (closeSafetyLegend) {
                closeSafetyLegend.addEventListener('click', function() {
                    safetyLegendModal.classList.add('hidden');
                });
            }
            safetyLegendModal.addEventListener('click', function(e) {
                if (e.target === safetyLegendModal) safetyLegendModal.classList.add('hidden');
            });
        }
    }

    bindFilterEvents() {
        var self = this;
        document.querySelectorAll('.pill-btn[data-filter]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var filterType = btn.getAttribute('data-filter');
                var value = btn.getAttribute('data-value');

                self.filters[filterType] = value;
                self.currentPage = 1;

                document.querySelectorAll('.pill-btn[data-filter="' + filterType + '"]').forEach(function(b) {
                    b.classList.remove('active');
                });
                btn.classList.add('active');

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
                throw new Error(window.i18n('serverError'));
            }

            var data = await response.json();
            if (data.status === 'success') {
                var filteredScans = data.scans;

                if (this.filters.risk) {
                    var riskFilter = this.filters.risk;
                    filteredScans = filteredScans.filter(function(scan) {
                        var rl = scansManager.normalizeRiskLevel(scan.safety_status || scansManager.calculateRiskLevel(scan.ingredients || []));
                        return rl === riskFilter;
                    });
                }

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
        var date = new Date(scan.created_at).toLocaleString(window.getCurrentLang() === 'en' ? 'en-US' : 'uk-UA');
        var riskLevel = this.normalizeRiskLevel(scan.safety_status || this.calculateRiskLevel(scan.ingredients || []));
        var methodIconSvg = this.getMethodSvg(scan.input_method);
        var methodText = this.getMethodText(scan.input_method);
        var preview = scan.original_text ? this.truncateText(scan.original_text, 100) : '';

        return '<div class="scan-card" data-scan-id="' + scan.id + '">' +
            '<div class="scan-card-method">' +
                '<div class="scan-method-icon">' + methodIconSvg + '</div>' +
                '<div>' +
                    '<div class="scan-method-name">' + methodText + '</div>' +
                    '<div class="scan-method-date">' + date + '</div>' +
                '</div>' +
            '</div>' +
            '<p class="scan-preview-text">' + preview + '</p>' +
            // Совмещённая строка: статистика слева, кнопки справа
            '<div class="scan-stats" style="display:flex; align-items:center; justify-content:space-between;">' +
                '<div style="display:flex; align-items:center; gap:8px;">' +
                    '<span class="risk-badge risk-sm risk-' + riskLevel + '"><span class="dot"></span>' + this.getRiskText(riskLevel) + '</span>' +
                    '<span class="scan-ingredients-count">' + window.i18n('ingredientsFound', (scan.ingredients_count || 0)) + '</span>' +
                '</div>' +
                '<div style="display:flex; align-items:center; gap:6px;">' +
                    '<input type="checkbox" class="scan-checkbox" data-scan-id="' + scan.id + '" onclick="event.stopPropagation(); scansManager.handleCheckboxClick(' + scan.id + ')">' +
                    '<button class="btn-icon" title="' + window.i18n('exportScan') + '" onclick="event.stopPropagation(); scansManager.exportSingleScanToPdf(' + scan.id + ')" style="padding:4px;">' +
                        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
                    '</button>' +
                    '<button class="btn-icon" title="' + window.i18n('deleteBtn') + '" onclick="event.stopPropagation(); scansManager.deleteScan(' + scan.id + ')" style="padding:4px;">' +
                        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>' +
                    '</button>' +
                '</div>' +
            '</div>' +
        '</div>';
    }

    getMethodSvg(method) {
        var icons = {
            'text': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/></svg>',
            'device': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
            'gallery': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
            'camera': '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2m10 0h2a2 2 0 0 1 2 2v2m0 10v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><rect x="7" y="7" width="10" height="10" rx="1.5"/></svg>'
        };
        return icons[method] || icons['text'];
    }

    bindScanCardEvents() {
        var self = this;
        document.querySelectorAll('.scan-card').forEach(function(card) {
            card.addEventListener('click', function(e) {
                // Не открываем детали, если кликнули по кнопкам или чекбоксу
                if (e.target.closest('.scan-checkbox') || e.target.closest('button')) return;
                var scanId = parseInt(card.dataset.scanId);
                self.viewScanDetails(scanId);
            });
        });
    }

    handleCheckboxClick(scanId) {
        this.toggleScanSelection(scanId);
    }

    async viewScanDetails(scanId) {
        try {
            var response = await fetch('/api/scans/' + scanId);
            if (!response.ok) throw new Error(window.i18n('serverError'));
            var data = await response.json();
            if (data.status === 'success') {
                this.currentDetailScan = data.scan;
                this.showScanDetails(data.scan);
            } else { throw new Error(data.message); }
        } catch (error) {
            this.showError(error.message);
        }
    }

    showScanDetails(scan) {
        var modal = document.getElementById('scanDetailsModal');
        var content = document.getElementById('scanDetailsContent');
        var meta = document.getElementById('detailMeta');
        var date = new Date(scan.created_at).toLocaleString(window.getCurrentLang() === 'en' ? 'en-US' : 'uk-UA');

        if (meta) meta.textContent = this.getMethodText(scan.input_method) + ' · ' + date;

        var ingredients = scan.ingredients_detailed || scan.ingredients || [];
        var self = this;

        var counts = {};
        ingredients.forEach(function(ing) {
            var lvl = self.normalizeRiskLevel(ing.risk_level);
            counts[lvl] = (counts[lvl] || 0) + 1;
        });

        var html = '';

        html += '<div class="risk-counts" style="margin-bottom:20px">';
        for (var lvl in counts) {
            var riskLabel = window.i18n('risk_' + lvl) || lvl;
            html += '<span class="risk-badge risk-' + lvl + '"><span class="dot"></span>' + counts[lvl] + ' ' + riskLabel + '</span>';
        }
        html += '</div>';

        var isEn = window.getCurrentLang() === 'en';

        html += '<p class="detail-section-label">' + window.i18n('ingredients') + '</p>';
        html += '<div class="detail-ingredients">';
        if (ingredients.length > 0) {
            ingredients.forEach(function(ing) {
                var normalizedRisk = self.normalizeRiskLevel(ing.risk_level);
                var riskClass = 'risk-' + normalizedRisk;
                var riskLabel = window.i18n('risk_' + normalizedRisk) || normalizedRisk;
                var desc = isEn ? (ing.description_en || ing.description) : ing.description;
                html += '<div class="detail-ingredient">';
                html += '<div style="flex:1"><div class="name">' + (ing.name || window.i18n('unknown')) + '</div>';
                if (desc) html += '<div class="desc">' + desc + '</div>';
                html += '</div>';
                html += '<span class="risk-badge risk-sm ' + riskClass + '"><span class="dot"></span>' + riskLabel + '</span>';
                html += '</div>';
            });
        } else {
            html += '<div style="padding:16px;text-align:center;color:var(--txt-3)">' + window.i18n('scanNotFound') + '</div>';
        }
        html += '</div>';

        if (scan.original_text) {
            html += '<p class="detail-section-label">' + window.i18n('recognizedText') + '</p>';
            html += '<div class="original-text">' + scan.original_text + '</div>';
        }

        content.innerHTML = html;
        modal.classList.remove('hidden');
    }

    exportSingleScanToPdf(scanId) {
        window.open('/api/scans/' + scanId + '/export/pdf?lang=' + window.getCurrentLang(), '_blank');
        this.clearSelection();
    }

    exportSelectedScans() {
        var selectedIds = Array.from(this.selectedScans);
        if (selectedIds.length === 0) {
            alert(window.i18n('pleaseSelectForExport') || 'Оберіть сканування для експорту');
            return;
        }
        var url = '/api/scans/export-multiple/zip?ids=' + selectedIds.join(',') + '&lang=' + window.getCurrentLang();
        window.open(url, '_blank');
        this.clearSelection();
    }

    async deleteScan(scanId) {
        if (!confirm(window.i18n('deleteConfirm'))) return;
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
        if (selectedIds.length === 0) {
            this.showMessage(window.i18n('pleaseSelect'), 'error');
            return;
        }
        if (!confirm(window.i18n('deleteSelectedConfirm', selectedIds.length))) return;

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
        var checkboxes = document.querySelectorAll('.scan-checkbox');
        if (this.allScansSelected) {
            checkboxes.forEach(cb => {
                cb.checked = false;
                this.selectedScans.delete(parseInt(cb.dataset.scanId));
            });
            this.allScansSelected = false;
        } else {
            checkboxes.forEach(cb => {
                cb.checked = true;
                this.selectedScans.add(parseInt(cb.dataset.scanId));
            });
            this.allScansSelected = true;
        }
        this.updateBulkActions();
    }

    clearSelection() {
        // Снимаем все галочки
        document.querySelectorAll('.scan-checkbox').forEach(cb => {
            cb.checked = false;
        });
        this.selectedScans.clear();
        this.allScansSelected = false;
        this.updateBulkActions();
    }

    updateBulkActions() {
        var deleteBtn = document.getElementById('deleteSelectedBtn');
        var exportBtn = document.getElementById('exportSelectedBtn');
        var selectAllBtn = document.getElementById('selectAllBtn');
        var count = this.selectedScans.size;

        if (deleteBtn) {
            deleteBtn.disabled = count === 0;
            deleteBtn.textContent = count > 0
                ? window.i18n('deleteSelectedBtn', count)
                : window.i18n('deleteSelected');
        }
        if (exportBtn) {
            exportBtn.disabled = count === 0;
            exportBtn.textContent = count > 0
                ? window.i18n('exportSelectedBtn', count)
                : window.i18n('exportSelected');
        }
        if (selectAllBtn) {
            selectAllBtn.textContent = this.allScansSelected
                ? window.i18n('deselectAll')
                : window.i18n('selectAll');
        }
    }

    getMethodText(method) {
        return window.i18n('method_' + method) || window.i18n('method_unknown');
    }

    getTypeText(type) {
        return window.i18n('type_' + type) || '';
    }

    calculateRiskLevel(ingredients) {
        if (!ingredients || ingredients.length === 0) return 'safe';
        var self = this;
        var levels = ingredients.map(function(ing) {
            return (typeof ing === 'object') ? self.normalizeRiskLevel(ing.risk_level) : 'safe';
        });
        if (levels.indexOf('high') !== -1) return 'high';
        if (levels.indexOf('medium') !== -1) return 'medium';
        if (levels.indexOf('low') !== -1) return 'low';
        return 'safe';
    }

    getRiskText(riskLevel) {
        return window.i18n('risk_' + riskLevel) || riskLevel;
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
            emptyTitle.textContent = window.i18n('noScansFilter');
            emptyText.textContent = window.i18n('changeFilter');
        } else {
            emptyTitle.textContent = window.i18n('noScansTitle');
            emptyText.textContent = window.i18n('noScansDesc');
        }
    }

    updateScansCount(total) {
        var el = document.getElementById('scansCount');
        if (el) el.textContent = window.i18n('scansResult', total);
    }

        updatePagination(totalItems) {
        var pagination = document.getElementById('pagination');
        var totalPages = Math.ceil(totalItems / this.perPage);

        if (totalPages <= 1) {
            pagination.classList.add('hidden');
            return;
        }
        pagination.classList.remove('hidden');

        var current = this.currentPage;
        var pages = [];

        // Всегда добавляем первую страницу
        pages.push(1);

        // Определяем промежуточные страницы без дублирования
        if (totalPages > 2) {
            var rangeStart = Math.max(2, current - 1);
            var rangeEnd = Math.min(totalPages - 1, current + 1);

            if (rangeStart > 2) {
                pages.push('...');
            } else if (rangeStart === 2) {
                pages.push(2);
            }

            // Добавляем страницы от rangeStart+1 до rangeEnd (избегаем повторов 2)
            for (var i = Math.max(rangeStart + 1, 3); i <= rangeEnd; i++) {
                pages.push(i);
            }

            if (rangeEnd < totalPages - 1) {
                pages.push('...');
            }
        }

        // Добавляем последнюю страницу, если она ещё не добавлена
        if (totalPages > 1 && pages[pages.length - 1] !== totalPages) {
            pages.push(totalPages);
        }

        // Строим HTML
        var html = '';
        // Кнопка «Предыдущая»
        if (current > 1) {
            html += '<button onclick="scansManager.loadScans(' + (current - 1) + ')" title="' + window.i18n('prevPage') + '">‹</button>';
        } else {
            html += '<button disabled>‹</button>';
        }

        for (var idx = 0; idx < pages.length; idx++) {
            var page = pages[idx];
            if (page === '...') {
                html += '<span class="page-ellipsis">…</span>';
            } else if (page === current) {
                html += '<span class="page-current">' + page + '</span>';
            } else {
                html += '<button onclick="scansManager.loadScans(' + page + ')">' + page + '</button>';
            }
        }

        // Кнопка «Следующая»
        if (current < totalPages) {
            html += '<button onclick="scansManager.loadScans(' + (current + 1) + ')" title="' + window.i18n('nextPage') + '">›</button>';
        } else {
            html += '<button disabled>›</button>';
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
        // Отключены глобально через CSS
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