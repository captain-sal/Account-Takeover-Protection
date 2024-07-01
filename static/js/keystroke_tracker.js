class KeystrokeTracker {
    constructor() {
        this.socket = new WebSocket("ws://" + window.location.host + "/ws");
        this.keystrokeData = {};
        this.lastReleaseTime = 0;
        this.statusElement = document.getElementById('status');
        this.isPageVisible = true;

        this.initializeWebSocket();
        this.addEventListeners();
    }

    initializeWebSocket() {
        this.socket.onopen = (e) => {
            this.updateStatus("Connected to server");
        };

        this.socket.onmessage = (event) => {
            this.updateStatus(event.data);
        };

        this.socket.onclose = (event) => {
            this.updateStatus("Disconnected from server");
        };
    }

    addEventListeners() {
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
        document.addEventListener('keyup', this.handleKeyUp.bind(this));
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    }

    handleKeyDown(e) {
        if (!this.isPageVisible) return;

        const pressTime = performance.now();
        const key = e.key;

        if (!this.keystrokeData[key]) {
            this.keystrokeData[key] = {
                key: key,
                pressTime: pressTime,
                holdTime: null,
                releaseTime: null,
                flightTime: pressTime - this.lastReleaseTime
            };
        }
    }

    handleKeyUp(e) {
        if (!this.isPageVisible) return;

        const releaseTime = performance.now();
        const key = e.key;

        if (this.keystrokeData[key]) {
            const keystrokeEvent = this.keystrokeData[key];
            keystrokeEvent.releaseTime = releaseTime;
            keystrokeEvent.holdTime = releaseTime - keystrokeEvent.pressTime;
            this.lastReleaseTime = releaseTime;

            // Send the completed keystroke data
            this.socket.send(JSON.stringify([keystrokeEvent]));

            // Remove the sent data
            delete this.keystrokeData[key];
        }
    }

    handleVisibilityChange() {
        if (document.hidden) {
            this.isPageVisible = false;
            this.socket.send(JSON.stringify([{ event: 'page_hidden', timestamp: performance.now() }]));
        } else {
            this.isPageVisible = true;
            this.socket.send(JSON.stringify([{ event: 'page_visible', timestamp: performance.now() }]));
        }
    }

    updateStatus(message) {
        this.statusElement.innerHTML = message;
    }
}

// Initialize the tracker when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    new KeystrokeTracker();
});