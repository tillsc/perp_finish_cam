import {addSeconds} from './time.js'

class PerpFinishcamLiveElement extends HTMLElement {

    static observedAttributes = ['for-index', 'cut'];

    constructor() {
        super();
        this.objectURLHistory = [];
        this.timeStartHistory = [];
        this.currentIndex = -1;
        this.timeDelta = 0; //ms difference between date of metadata retrival and timeStart+timeSpan in metadata
    }

    connectedCallback() {
        this.parseAttributes();
        this.timeStartHistory[this.currentIndex] = this.timeStart;

        const loc = window.location;
        const wsUri = (loc.protocol === "https:" ? "wss" : "ws") + "://" + loc.host + "/ws/live";
        this.webservice = new WebSocket(wsUri, ['live-image', 'metadata']);
        this.webservice.binaryType = "arraybuffer";
        this.webservice.onmessage = event => this.handleMessage(event.data);
    }

    attributeChangedCallback(name, _oldValue, newValue) {
        this.parseAttributes();
        this.render();
      }

    parseAttributes() {
        this.forIndex = parseInt(this.getAttribute('for-index'));
        this.cutImage = this.hasAttribute('cut');
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
            this.currentSession = metadata.session_name;
            const now = new Date();
            this.currentIndex = metadata.index;
            const timeStart = new Date(metadata.time_start * 1000);
            this.timeStartHistory[this.currentIndex] = timeStart;
            this.timeDelta = now.getTime() - timeStart.getTime();
            this.timeSpan = metadata.time_span;
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
            if (this.objectURLHistory[index]) {
              img.src = this.objectURLHistory[index];
            }
            else {  
              img.src = this.currentSession ? `/data/${this.currentSession}/img${index}.webp` : '#';
            }
            img.style.objectFit = 'cover';
            img.style.objectPosition = 'top left';
            img.style.height = img.naturalHeight + 'px';
            if (this.cutImage && index == to) {
                const now = new Date();
                const progress = (now.getTime() - this.timeStartHistory[this.currentIndex].getTime()) / (this.timeSpan * 1000.0);
                img.style.width = Math.round(progress * img.naturalWidth) + 'px';
            }
            else {
                img.style.width = 'auto';
            }
            img.timeStart = this.timeStartHistory[index];
        }
        for (let index = (to - from + 1); index < imgs.length; index++) {
          imgs[index].remove();  
        }
    }

}

customElements.define("perp-finishcam-live", PerpFinishcamLiveElement);