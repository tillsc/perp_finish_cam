class PerpFinishcamLiveElement extends HTMLElement {

    connectedCallback() {
        this.img = this.querySelector("img");
        if (!this.img) {
            this.img = document.createElement('img');
            this.append(this.img);
        }
        this.img.style.height = '100%';
        this.img.timeStart = this.timeStart;

        const loc = window.location;
        const wsUri = (loc.protocol === "https:" ? "wss" : "ws") + "://" + loc.host + "/ws/live";
        this.webservice = new WebSocket(wsUri, []);
        this.webservice.binaryType = "arraybuffer";
        this.webservice.onmessage = (event) => {
            const dataUri = "data:image/webp;base64," + btoa(String.fromCharCode(...new Uint8Array(event.data)));;
            this.img.src = dataUri;
        };
    }

}

customElements.define("perp-finishcam-live", PerpFinishcamLiveElement);