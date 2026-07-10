class KaraokeQueue {
    constructor() {
        this.queue = [];
        this.userNames = new Set();
        this.darkMode = false;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.showDone = false; // Track if done section is expanded

        this.initializeElements();
        this.attachEventListeners();
        this.connectWebSocket();
    }

    initializeElements() {
        this.queueForm = document.getElementById('queueForm');
        this.singerInput = document.getElementById('singerInput');
        this.songInput = document.getElementById('songInput');
        this.queueList = document.getElementById('queueList');
        this.emptyState = document.getElementById('emptyState');
        this.themeToggle = document.getElementById('themeToggle');
    }

    attachEventListeners() {
        this.queueForm.addEventListener('submit', (e) => this.handleAddEntry(e));
        this.themeToggle.addEventListener('click', () => this.toggleTheme());
    }

    async handleAddEntry(e) {
        e.preventDefault();

        const singer = this.singerInput.value.trim();
        const song = this.songInput.value.trim();

        if (!singer || !song) return;

        try {
            const response = await fetch('/queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ singer, song })
            });

            if (response.ok) {
                this.userNames.add(singer);
                this.singerInput.value = '';
                this.songInput.value = '';
                this.singerInput.focus();
            }
        } catch (error) {
            console.error('Error adding entry:', error);
        }
    }

    toggleTheme() {
        this.darkMode = !this.darkMode;
        document.body.classList.toggle('dark-mode');
        this.themeToggle.textContent = this.darkMode ? '☀️' : '🌙';
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'queue_update') {
                this.handleQueueUpdate(data.queue);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.attemptReconnect();
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = 2000 * this.reconnectAttempts;
            console.log(`Attempting to reconnect in ${delay}ms...`);
            setTimeout(() => this.connectWebSocket(), delay);
        }
    }

    handleQueueUpdate(queueData) {
        this.queue = queueData;
        this.renderQueue();
    }

    renderQueue() {
        this.queueList.innerHTML = '';

        if (this.queue.length === 0) {
            this.emptyState.style.display = 'block';
            return;
        }

        this.emptyState.style.display = 'none';

        // Group by status
        const singing = this.queue.filter(e => e.status === 'singing');
        const waiting = this.queue.filter(e => e.status === 'waiting');
        const done = this.queue.filter(e => e.status === 'done');

        // Render singing
        singing.forEach((entry, index) => {
            this.queueList.appendChild(this.createCard(entry, 'singing', true, index === 0 && waiting.length > 0));
        });

        // Render waiting
        waiting.forEach((entry, index) => {
            this.queueList.appendChild(this.createCard(entry, 'waiting', false, index === 0));
        });

        // Render done section (collapsible)
        if (done.length > 0) {
            const doneSection = document.createElement('div');
            doneSection.className = 'done-section';
            
            const doneHeader = document.createElement('div');
            doneHeader.className = 'done-header';
            doneHeader.style.cursor = 'pointer';
            doneHeader.style.padding = '12px';
            doneHeader.style.backgroundColor = '#f0f0f0';
            doneHeader.style.borderTop = '1px solid #ddd';
            doneHeader.style.fontWeight = 'bold';
            doneHeader.textContent = `${this.showDone ? '▼' : '▶'} Done (${done.length})`;
            
            doneHeader.addEventListener('click', () => {
                this.showDone = !this.showDone;
                this.renderQueue();
            });
            
            doneSection.appendChild(doneHeader);
            
            if (this.showDone) {
                done.forEach(entry => {
                    doneSection.appendChild(this.createCard(entry, 'done', false, false));
                });
            }
            
            this.queueList.appendChild(doneSection);
        }
    }

    createCard(entry, status, showNext, isUpNext) {
        const card = document.createElement('div');
        card.className = `queue-card ${status}`;
        card.draggable = status === 'waiting';
        card.dataset.id = entry.id;

        let badgeHTML = '';
        if (status === 'singing') {
            badgeHTML = '<span class="badge singing">NOW SINGING</span>';
        } else if (isUpNext) {
            badgeHTML = '<span class="badge next">Prossimo</span>';
        }

        let controlsHTML = '';
        if (status === 'singing' && showNext) {
            controlsHTML = `
                <div class="queue-card-controls">
                    <button class="btn-next" data-id="${entry.id}">Fatto ▶</button>
                </div>
            `;
        } else if (status === 'waiting') {
            const waitingItems = this.queue.filter(e => e.status === 'waiting');
            const currentPosition = waitingItems.findIndex(e => e.id === entry.id);
            controlsHTML = `
                <div class="queue-card-controls">
                    <label>Position:</label>
                    <input type="number" min="1" max="${waitingItems.length}" value="${currentPosition + 1}" class="position-input" data-id="${entry.id}">
                </div>
            `;
        }

        card.innerHTML = `
            <div class="queue-card-header">
                <div class="queue-card-title">${this.escapeHtml(entry.singer)}</div>
                ${badgeHTML}
            </div>
            <div class="queue-card-song">${this.escapeHtml(entry.song)}</div>
            <div class="queue-card-footer">
                ${controlsHTML}
            </div>
        `;

        // Attach next button listener
        const nextBtn = card.querySelector('.btn-next');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.handleNext());
        }

        // Attach position input listener
        const positionInput = card.querySelector('.position-input');
        if (positionInput) {
            positionInput.addEventListener('change', (e) => this.handlePositionChange(e));
        }

        return card;
    }

    async handleNext() {
        try {
            const response = await fetch('/queue/next', { method: 'POST' });
            if (!response.ok) {
                console.error('Error moving to next singer');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    async handlePositionChange(e) {
        const input = e.target;
        const entryId = parseInt(input.dataset.id);
        const newPosition = parseInt(input.value) - 1; // Convert to 0-based index

        // Validate position
        const waiting = this.queue.filter(e => e.status === 'waiting');
        if (newPosition < 0 || newPosition >= waiting.length) {
            input.value = (waiting.findIndex(e => e.id === entryId) + 1);
            return;
        }

        try {
            const response = await fetch(`/queue/${entryId}/move?new_position=${newPosition}`, {
                method: 'PATCH'
            });

            if (!response.ok) {
                console.error('Error moving entry');
                // Revert to original position on error
                input.value = (waiting.findIndex(e => e.id === entryId) + 1);
            }
        } catch (error) {
            console.error('Error:', error);
            // Revert to original position on error
            input.value = (waiting.findIndex(e => e.id === entryId) + 1);
        }
    }


    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    window.karaokeApp = new KaraokeQueue();
});
