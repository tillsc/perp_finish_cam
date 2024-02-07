class PerpFinishcamLiveElement extends HTMLElement {

    static observedAttributes = ['for-index'];

    constructor() {
        super();
        this.objectURLHistory = [];
        this.timeStartHistory = [];
        this.currentIndex = -1;
    }

    connectedCallback() {
        this.forIndex = parseInt(this.getAttribute('for-index'));
        this.timeStartHistory[this.currentIndex] = this.timeStart;

        const loc = window.location;
        const wsUri = (loc.protocol === "https:" ? "wss" : "ws") + "://" + loc.host + "/ws/live";
        this.webservice = new WebSocket(wsUri, ['live-image', 'metadata']);
        this.webservice.binaryType = "arraybuffer";
        this.webservice.onmessage = event => this.handleMessage(event.data);
    }

    attributeChangedCallback(name, _oldValue, newValue) {
        if (name == 'for-index') {
            this.forIndex = parseInt(newValue);
            this.render();
        }
      }

    disconnectedCallback() {
        this.objectURLHistory.forEach((historyElement) => {
            if (historyElement) {
                URL.revokeObjectURL(historyElement);
            }
        });
    }

    handleMessage(event_data) {
        const bytes = new Uint8Array(event_data);
        const type = bytes[0];
        if (type == 0) {
            if (this.objectURLHistory[this.currentIndex]) {
                URL.revokeObjectURL(this.objectURLHistory[this.currentIndex]);
            }
            const blob = new Blob([bytes.slice(1)], { type: "image/webp" });
            const objectURL = URL.createObjectURL(blob);
            this.objectURLHistory[this.currentIndex] = objectURL;
        }
        else if (type == 1) {
            const metadata = JSON.parse(new TextDecoder().decode(bytes.slice(1)));
            this.currentIndex = metadata.index;
            this.timeStartHistory[this.currentIndex] = new Date(metadata.time_start * 1000);
        }
        this.render();
    }

    render() {
        let from = this.forIndex;
        const to = this.currentIndex;
        if (isNaN(from) || to == -1) {
            from = to;
        }
        const imgs = [...this.querySelectorAll('img')];
        for (let index = from; index <= to; index++) {
            let img = imgs[index - from];
            if (!img) {
                img = document.createElement('img');
                this.append(img);                
            }
            img.src = this.objectURLHistory[index];
            img.style.height = '100%';
            img.timeStart = this.timeStartHistory[index];
        }
        for (let index = (to - from + 1); index < imgs.length; index++) {
          imgs[index].remove();  
        }
    }

}

customElements.define("perp-finishcam-live", PerpFinishcamLiveElement);