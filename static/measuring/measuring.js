import { LitElement, html, ref, createRef } from '../lit.js';

import { measuringCss } from './styles.js';
import { SessionMetadataService } from './metadata.js';
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

    static styles = measuringCss;

    canvasRef = createRef();
    sessionMetadataService = new SessionMetadataService({
        onNewImage: () => {
            this._error = undefined;
            this.requestUpdate();
        },
        onError: (msg) => this._error = msg
    });

    connectedCallback() {
        super.connectedCallback();

        this.sessionMetadataService.start(this.href);
        this.firstTimeLoad = true;
    }


    render() {
        if (this._error) {
            return html`<div class="alert alert-danger" role="alert">Error: ${this._error}</div>`
        }
        else if (this.sessionMetadataService.loaded()) {
            if (this.firstTimeLoad) {
                this.handleFirstTimeLoad();
            }
            return this.renderWorkspace()
        }
        else {
            return html`<div class="alert alert-primary" role="alert">Loading...</div>`
        }
    }

    handleFirstTimeLoad() {
        this.firstTimeLoad = false;
        this.style.setProperty("--image-width", this.sessionMetadataService.imageWidth() + "px");
        if (this.sessionMetadataService.isLive()) {
            this.updateComplete.then(() => {
                setTimeout(() => {
                    const imageContainer = this.shadowRoot.querySelector('.images');
                    imageContainer.scrollLeft = imageContainer.scrollWidth;     
                }, 500);
            });
        }
    }

    renderWorkspace() {
        return html`
        <div class="wrapper">
          <div class="images-outer">
            <perp-finishcam-measuring-canvas ${ref(this.canvasRef)}></perp-finishcam-measuring-canvas>
            <div class="images" @mousemove="${this._handleMousemove}">
              ${[...Array(this.sessionMetadataService.imageCount()).keys()].map(index => this.renderImg(index))}
              ${this.renderLive()}
            </div>
          </div>
          <div class="hud">
          <dl>
            <dt>X:</dt><dd>${formatTime(this._x)}</dd>
            <dt>Start:</dt><dd>${formatTime(this.sessionMetadataService.timeStart())}</dd>
            <dt>End:</dt><dd>${formatTime(this.sessionMetadataService.timeEnd())}</dd>
            <dt>Next in:</dt><dd>${this.sessionMetadataService.expectedNext()} ${this.sessionMetadataService.isLive() ? " (Live!)" : ""}</dd>
          </dl>
          <code>${JSON.stringify(this.sessionMetadataService._metadata)}</code>
          </hud>
        </div>
        `
    }

    renderImg(index) {
        return html`<img src="${this.sessionMetadataService.buildUri(`img${index}.webp`)}" .timeStart="${this.sessionMetadataService.timeStart(index)}">`;
    }

    renderLive() {
        if (this.sessionMetadataService.isLive()) {
            return html`<perp-finishcam-live .timeStart=${this.sessionMetadataService.timeStart(this.sessionMetadataService.imageCount())} for-index="${this.sessionMetadataService.imageCount()}"></perp-finishcam-live>`;
        }
    }

    _handleMousemove(event) {
        this.canvasRef.value?.drawLiveCrosshair(event.pageX - this.offsetLeft, event.pageY - this.offsetTop);
        
        if (event.target?.timeStart) {
            this._x = addSeconds(event.target.timeStart, this.sessionMetadataService.timeSpan() * (event.offsetX - 1) / event.target.width);
            this.mouseX = event.offsetX;
            this.mousePerc = this.mouseX / event.target.width;
        }
        else if (this._x) {
            this._x = null;
        }
    }
}

customElements.define("perp-finishcam-measuring", PerpFinishcamMeasuringElement);