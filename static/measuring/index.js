import { LitElement, html, ref, createRef } from '../lit.js';

import componentCss from './styles.js';
import MetadataService from './metadata.js';
import './canvas.js';

import { formatTime, addSeconds } from '../time.js';

import '../live.js';

class PerpFinishcamMeasuringElement extends LitElement {
    static properties = {
        href: { type: String },

        // Internal properties
        _error: { type: String, state: true },
        _x: { type: Number, state: true }
    };

    static styles = componentCss;

    canvasRef = createRef();
    metadataService = new MetadataService({
        onNewImage: () => {
            this._error = undefined;
            this.requestUpdate();
        },
        onError: (msg) => this._error = msg
    });

    connectedCallback() {
        super.connectedCallback();

        this.baseURL = new URL(this.href, window.location.href);
        if (!this.baseURL.pathname.endsWith('/')) {
            this.baseURL.pathname = this.baseURL.pathname + '/';
        }

        this.metadataService.start(this.buildUri('index.json'));
    }

    buildUri(relativePath) {
        return new URL(relativePath, this.baseURL).href
    }

    render() {
        if (this._error) {
            return html`<div class="alert alert-danger" role="alert">Error: ${this._error}</div>`
        }
        else if (this.metadataService.loaded()) {
            return this.renderWorkspace()
        }
        else {
            return html`<div class="alert alert-primary" role="alert">Loading...</div>`
        }
    }

    renderWorkspace() {
        return html`
        <div class="wrapper">
          <div class="images-outer">
            <perp-finishcam-measuring-canvas ${ref(this.canvasRef)}></perp-finishcam-measuring-canvas>
            <div class="images" @mousemove="${this._handleMousemove}">
              ${[...Array(this.metadataService.imageCount()).keys()].map(index => this.renderImg(index))}
              ${this.renderLive()}
            </div>
          </div>
          <div class="hud">
          <dl>
            <dt>X:</dt><dd>${formatTime(this._x)}</dd>
            <dt>Start:</dt><dd>${formatTime(this.metadataService.timeStart())}</dd>
            <dt>End:</dt><dd>${formatTime(this.metadataService.timeEnd())}</dd>
            <dt>Next in:</dt><dd>${this.metadataService.expectedNext()} ${this.metadataService.isLive() ? " (Live!)" : ""}</dd>
          </dl>
          <code>${JSON.stringify(this.metadataService._metadata)}</code>
          </hud>
        </div>
        `
    }

    renderImg(index) {
        return html`<img src="${this.buildUri(`img${index}.webp`)}" .timeStart=${this.metadataService.timeStart(index)}>`;
    }

    renderLive() {
        if (this.metadataService.isLive()) {
            return html`<perp-finishcam-live cut .timeStart=${this.metadataService.timeStart(this.metadataService.imageCount())} for-index="${this.metadataService.imageCount()}"></perp-finishcam-live>`;
        }
    }

    _handleMousemove(event) {
        this.canvasRef.value?.drawLiveCrosshair(event.pageX, event.pageY);
        
        if (event.target?.timeStart) {
            this._x = addSeconds(event.target.timeStart, this.metadataService.timeSpan() * (event.offsetX - 1) / event.target.width);
            this.mouseX = event.offsetX;
            this.mousePerc = this.mouseX / event.target.width;
        }
        else if (this._x) {
            this._x = null;
        }
    }
}

customElements.define("perp-finishcam-measuring", PerpFinishcamMeasuringElement);