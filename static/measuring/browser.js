import { LitElement, html } from '../lit.js';

import { browserCss } from './styles.js';
import { SessionListService } from './metadata.js';

class PerpFinishcamBrowserElement extends LitElement {
    static properties = {
        href: { type: String },
        selectedSessionKey: { type: String },

        // Internal properties
        _error: { type: String, state: true }
    };

    static styles = browserCss;

    sessionListService = new SessionListService({
        onNewSessionList: () => {
            this._error = undefined;
            this.requestUpdate();
        },
        onError: msg => this._error = msg
    });

    connectedCallback() {
        super.connectedCallback();

        this.sessionListService.start(this.href);
    }


    render() {
        if (this._error) {
            return html`<pre class="alert alert-danger" role="alert">Error: ${this._error}</pre>`
        }
        else if (this.selectedSessionKey) {
            return html`
            <div @click=${() => this.selectedSessionKey = null}>Close</div>
            <perp-fc-measuring href="${this.sessionListService.buildUri(this.selectedSessionKey)}">
            <slot></slot>
            </perp-fc-measuring>
            `;
        }
        else if (this.sessionListService.loaded(this.href)) {
           return this.renderWorkspace();
        }
        else {
            return html`<div class="alert alert-primary" role="alert">Loading...</div>`
        }
    }

    renderWorkspace() {
        return html`<table class="session-list">
            ${this.sessionListService.sessionKeys().map(sessionKey => {
                return this.renderSessionLine(sessionKey)
            })}
        </table>`
    }

    renderSessionLine(sessionKey) {
        const data = this.sessionListService.sessionData(sessionKey);
        const timeStart = new Date((data['time_start'] || 0) * 1000);
        const imageCount = data['last_index'] || 0;
        const timeSpan = data['time_span'] || 10;
        const timeEnd = new Date(timeStart.valueOf() + (timeSpan * (imageCount + 1) * 1000));
        const isLive = timeEnd.valueOf() > ((new Date()).valueOf() - 20_000);
        return html`<tr @click="${_e => this.selectedSessionKey = sessionKey}">
            <td>${timeStart.toLocaleDateString()}</td>
            <td>${timeStart.toLocaleTimeString()}</td>
            <td>${timeEnd.toLocaleTimeString()}</td>
            <td>${imageCount + 1}</td>
            <td>${isLive ? 'Live!' : ''}</td>
        <tr>`
    }
}

customElements.define("perp-fc-browser", PerpFinishcamBrowserElement);