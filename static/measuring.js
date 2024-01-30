import {LitElement, html, css} from './lit.js';
import './live.js';

class PerpFinishcamMeasuringElement extends LitElement {
    static properties = {
        href: { type: String },
        metadata: { tpye: Object },
        error: { type: String },
        x: { type: Number }
      };

      static styles = css`
        :host {
            display: block;
            background-color: lightgray;
        }

        .wrapper {
            display: flex;
            flex-direction: column;
            height: 100%;
            align-items: stretch;
        }

        .images {
            cursor: crosshair;
            overflow-x: scroll;
            overflow-y: hidden;
            flex: 1;
            display: flex;
            gap: 1rem;
            justify-content: start;
        }

        .images img {
        }

        .hud {
            padding: 1rem;
            background-color: #888888;
            height: 200px;
            overflow: scroll;
        }
        `;

    connectedCallback() {
        super.connectedCallback();
        this.fetchMetadata();  
    }
    
    buildUri(relativePath) {
        const base = new URL(this.href, window.location.href);
        if (!base.pathname.endsWith('/')) {
            base.pathname = base.pathname + '/';
        }
        return new URL(relativePath, base).href
    }

    fetchAgainAt(date, offset = 500) {
        let t = date - new Date();
        t = Math.max(t, 0);
        console.log("fetch next time in", t);
        this.requestUpdateTimeout = setTimeout(() => this.requestUpdate(), t);
        this.fetchAgainTimeout = setTimeout(() => this.fetchMetadata(), t + offset);
    }

    async fetchMetadata() {
        const uri = this.buildUri('./index.json');
        const response = await fetch(uri);
        if (response.ok) {
            const newMetadata =  await response.json();
            if (!this.metadata || this.metadata.last_index != newMetadata.last_index) {
                this.error = undefined;
                this.metadata = newMetadata;
                this.requestUpdate();
            }
            if (this.isLive()) {
              this.fetchAgainAt(this.expectedNext());
            }
        }
        else {
            this.fatalError(`Failed to fetch JSON metadata from "${uri}"`);
            this.fetchAgainAt(new Date());
        }     
    }

    fatalError(msg) {
        this.error = msg;
    }

    timeStart(index=0) {
        if (this.metadata && this.metadata.time_start && this.metadata.time_span) {
            const ts = this.metadata.time_start + (this.metadata.time_span * index);
            return new Date(ts * 1000);
        }
    }

    timeEnd() {
        return this.timeStart(this.imageCount());
    }

    expectedNext() {
        let expectedNext = this.timeEnd();
        if (expectedNext && this.metadata.time_span) {
          expectedNext.setSeconds(expectedNext.getSeconds() + this.metadata.time_span);
        }
        else {
            expectedNext = new Date();
        }
        return expectedNext;
    }
    
    isLive() {
        return (this.expectedNext() - new Date() > -1000);
    }

    render() {
        if (this.error) {
            return html`<div class="alert alert-danger" role="alert">Error: ${this.error}</div>`
        }
        if (this.metadata) {
            return this.renderWorkspace()
        }
        else {
            return html`<div class="alert alert-primary" role="alert">Loading...</div>`
        }
    }

    imageCount() {
        if (this.metadata && this.metadata.last_index !== undefined && this.metadata.last_index != null) {
            return this.metadata.last_index + 1;
        }
        else {
            return 0;
        }
    }

    _handleMouseover(event) {
        if (event.target?.timeStart) {
          this.x = new Date(event.target.timeStart.getTime() + (1000 * this.metadata.time_span * (event.offsetX - 1) / event.target.width));
          this.mouseX = event.offsetX;
          this.mousePerc = this.mouseX / event.target.width;
        }
        else if (this.x) {
            this.x = null;
        }
    }

    _zpad(value, digits = 2) {
        return value.toString().padStart(digits, '0')
    }

    _formatTime(date) {
        if (date) {
            return `${this._zpad(date.getHours())}:${this._zpad(date.getMinutes())}:${this._zpad(date.getSeconds())}.${this._zpad(Math.round(date.getMilliseconds() / 10))}`
        }
    }

    renderWorkspace() {
        return html`
        <div class="wrapper">
          <div class="images" @mouseover="${this._handleMouseover}" @click="${this._handleMouseover}">
            ${[...Array(this.imageCount()).keys()].map(index => this.renderImg(index))}
            ${this.renderLive()}
          </div>
          <div class="hud">
          <dl>
            <dt>X:</dt><dd>${this._formatTime(this.x)}</dd>
            <dt>Start:</dt><dd>${this._formatTime(this.timeStart())}</dd>
            <dt>End:</dt><dd>${this._formatTime(this.timeEnd())}</dd>
            <dt>Next in:</dt><dd>${this.expectedNext()} ${this.isLive() ? " (Live!)" : ""}</dd>
          </dl>
          <code>${JSON.stringify(this.metadata)}</code>
          </hud>
        </div>
        `
    }

    renderImg(index) {
        return html`<img src="${this.buildUri(`img${index}.webp`)}" .timeStart=${this.timeStart(index)}>`;
    }

    renderLive() {
        if (this.isLive()) {
            let liveIndex = this.imageCount();
            const dummyImg = '';
            if (this.expectedNext() < new Date()) {
              this.renderImg(liveIndex);
              liveIndex++;
            }
            return html`${dummyImg}<perp-finishcam-live .timeStart=${this.timeStart(liveIndex)}></perp-finishcam-live>`;
        }
    }
}

customElements.define("perp-finishcam-measuring", PerpFinishcamMeasuringElement);