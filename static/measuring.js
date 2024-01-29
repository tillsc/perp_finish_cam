import {LitElement, html, css} from './lit.js';
import './live.js';

class PerpFinishcamMeasuringElement extends LitElement {
    static properties = {
        href: { type: String },
        metadata: { tpye: Object },
        error: { type: String }
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

    timeStart() {
        return this.metadata && new Date(this.metadata.time_start * 1000);
    }

    timeEnd() {
        if (this.metadata && this.metadata.time_start && this.metadata.time_span) {
          return new Date((this.metadata.time_start + (this.metadata.time_span * (this.imageCount()))) * 1000);
        }
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

    renderWorkspace() {
        return html`
        <div class="wrapper">
          <div class="images">
            ${[...Array(this.imageCount()).keys()].map(index =>
              html`<img src="${this.buildUri(`img${index}.webp`)}">`
            )}
            ${this.renderLive()}
          </div>
          <div class="hud">
          <dl>
            <dt>Start:</dt><dd>${this.timeStart()}</dd>
            <dt>End:</dt><dd>${this.timeEnd()}</dd>
            <dt>Next in:</dt><dd>${this.expectedNext()} ${this.isLive() ? " (Live!)" : ""}</dd>
          </dl>
          <code>${JSON.stringify(this.metadata)}</code>
          </hud>
        </div>
        `
    }

    renderLive() {
        if (this.isLive()) {
            const dummyImg = (this.expectedNext() < new Date()) ?
              html`<img src="${this.buildUri(`img${this.imageCount()}.webp`)}">` :
              '';
            return html`${dummyImg}<perp-finishcam-live></perp-finishcam-live>`
        }
    }
}

customElements.define("perp-finishcam-measuring", PerpFinishcamMeasuringElement);