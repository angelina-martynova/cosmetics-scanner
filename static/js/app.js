// app.js — Skipley

class CosmeticsScanner {
    constructor() {
        this.currentUser = null;
        this.currentScan = null;
    }

    init() {
        this.checkAuthStatus();
    }

    checkAuthStatus() {
        fetch('/api/status')
            .then(function(response) {
                if (!response.ok) throw new Error('Not authenticated');
                return response.json();
            })
            .then(function(data) {
                if (data.status === 'authenticated') {
                    this.currentUser = data.user;
                    // Show scans link in sidebar
                    var scansLink = document.getElementById('sidebarScansLink');
                    if (scansLink) scansLink.style.display = 'flex';
                    // Show logged-in sidebar state
                    var loggedOut = document.getElementById('sidebarAuthLoggedOut');
                    var loggedIn = document.getElementById('sidebarAuthLoggedIn');
                    if (loggedOut) loggedOut.style.display = 'none';
                    if (loggedIn) loggedIn.style.display = 'block';
                }
            }.bind(this))
            .catch(function() {
                this.currentUser = null;
            }.bind(this));
    }

    showMessage(message, type) {
        if (typeof showMessage === 'function') {
            showMessage(message, type);
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    window.app = new CosmeticsScanner();
    window.app.init();
    console.log('CosmeticsScanner ініціалізовано');
});
