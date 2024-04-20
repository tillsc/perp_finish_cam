import { LitElement, html } from '../lit.js';

import componentCss from './styles.js';

class PerpFinishcamBrowserElement extends LitElement {
    static properties = {
        href: { type: String },
        selectedSessionKey: { type: String },

        // Internal properties
        _error: { type: String, state: true },
        _sessions: { type: Object, state: true }
    };

    static styles = componentCss;

    buildUri(relativePath) {
        if (!this.baseUrl) {
            this.baseURL = new URL(this.href, window.location.href);
            if (!this.baseURL.pathname.endsWith('/')) {
                this.baseURL.pathname = this.baseURL.pathname + '/';
            }
        }
        return new URL(relativePath, this.baseURL).href
    }

    connectedCallback() {
        super.connectedCallback();

        this.fetchSessions();
    }

    async fetchSessions() {
        const uri = this.buildUri('index.json');
        const response = await fetch(uri);
        if (response.ok) {
            const json = await response.json();
            this._sessions = json;
        }
        else {
            this._error = `Could not fetch sessions with uri ${uri}:\n${response.status} ${response.statusText}`;
        }
    }

    loaded() {
        return this._sessions;
    }

    sessionKeys() {
        return Object.keys(this._sessions).sort().reverse()
    }

    sessionData(sessionKey) {
        return this._sessions[sessionKey];
    }

    render() {
        if (this._error) {
            return html`<pre class="alert alert-danger" role="alert">Error: ${this._error}</pre>`
        }
        else if (this.selectedSessionKey) {
            return html`<perp-finishcam-measuring href="${this.buildUri(this.selectedSessionKey)}"></perp-finishcam-measuring>`;
        }
        else if (this.loaded()) {
           return this.renderWorkspace();
        }
        else {
            return html`<div class="alert alert-primary" role="alert">Loading...</div>`
        }
    }

    renderWorkspace() {
        return html`<table class="session-list">
            ${this.sessionKeys().map(sessionKey => {
                return this.renderSessionLine(sessionKey)
            })}
        </table>`
    }

    renderSessionLine(sessionKey) {
        const data = this.sessionData(sessionKey);
        const timeStart = new Date((data['time_start'] || 0) * 1000);
        const imageCount = data['last_index'] || 0;
        const timeSpan = data['time_span'] || 10;
        const timeEnd = new Date(timeStart.valueOf() + (timeSpan * (imageCount + 1) * 1000));
        const isLive = timeEnd.valueOf() > ((new Date()).valueOf() - 20_000);
        return html`<tr @click="${_e => this.selectedSessionKey = sessionKey}">
            <td>${timeStart.toLocaleDateString()}</td>
            <td>${timeStart.toLocaleTimeString()}</td>
            <td>${timeEnd.toLocaleTimeString()}</td>
            <td>${imageCount}</td>
            <td>${isLive ? 'Live!' : ''}</td>
        <tr>`
    }
}

customElements.define("perp-finishcam-browser", PerpFinishcamBrowserElement);