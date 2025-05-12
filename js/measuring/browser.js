import { LitElement, html } from '../lit.js';

import { parseTime } from '../time.js';
import { browserCss } from './styles.js';
import { SessionListService } from './metadata.js';

class PerpFinishcamBrowserElement extends LitElement {
    static properties = {
        href: { type: String },
        selectedSessionKey: { type: String },
        startTime: { type: String, attribute: 'start-time' },
        expectedAt: { type: String, attribute: 'expected-at' },

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
        if (this.selectedSessionKey) {
            return html`
                <a href="#" @click=${this}>Back to Session List</a>
                <slot name="metadata" @slotchange="${this}" style="display: none;"></slot>
                <perp-fc-measuring @laneheightschange="${this}"
                                   start-time="${this.startTime}"
                                   expected-at="${this.expectedAt}"
                                   instance-id="${this.getAttribute('id')}"
                                   href="${this.sessionListService.buildUri(this.selectedSessionKey)}">
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
        const startTimeDate = this.startTime ? new Date(this.startTime) : undefined;
        const expectedAtDate = (startTimeDate && this.expectedAt) ? parseTime(this.expectedAt, startTimeDate) : startTimeDate;
        return html`
            ${this._error ? 
              html`<pre class="alert alert-danger" role="alert">Error: ${this._error}</pre>` :
              ''}
            <table class="session-list">
                <tr>
                    <th>Date</th>
                    <th>From</th>
                    <th>To</th>
                    <th>Images</th>
                    <th></th>
                </tr>
                ${this.sessionListService.sessionKeys().map(sessionKey => {
                    return this.renderSessionLine(sessionKey, expectedAtDate)
                })}
            </table>
            <slot name="metadata" @slotchange="${this}" style="display: none;"></slot>
        `
    }

    renderSessionLine(sessionKey, expectedAtDate) {
        const data = this.sessionListService.sessionData(sessionKey);
        const timeStart = new Date((data['time_start'] || 0) * 1000);
        const imageCount = data['last_index'] || 0;
        const timeSpan = data['time_span'] || 10;
        const timeEnd = new Date(timeStart.valueOf() + (timeSpan * (imageCount + 1) * 1000));

        const isLive = timeEnd.valueOf() > ((new Date()).valueOf() - 20_000);
        const isExpected = expectedAtDate && 
            timeStart.valueOf() <= expectedAtDate.valueOf() && 
            (isLive || timeEnd.valueOf() >= expectedAtDate.valueOf());
        
        return html`<tr @click="${this}" data-session-key="${sessionKey}" class="${isExpected ? 'expected' : ''}"> 
            <td>${timeStart.toLocaleDateString()}</td>
            <td>${timeStart.toLocaleTimeString()}</td>
            <td>${timeEnd.toLocaleTimeString()}</td>
            <td>${imageCount !== undefined ? imageCount + 1 : '-'}</td>
            <td>${isLive ? 'Live!' : ''}</td>
        <tr>`
    }

    selectSession(sessionKey) {
        this.selectedSessionKey = sessionKey;
        this._setMetadata('session', this.sessionListService.sessionData(this.selectedSessionKey));
    }

    handleEvent(event) {
        switch (event.type) {
            case "laneheightschange":
                this._setMetadata('lane_heights', event.detail.laneHeights);
                break;
            case "slotchange":
                this._metadataInput = [...event.target.assignedElements()].reduce((res, el) => {
                    return res || el.querySelector('input');
                }, undefined);
                if (this._metadataInput?.value) {
                    try {
                        const data = JSON.parse(this._metadataInput.value);
                        if (data.session_name && this.sessionListService. sessionKeys().includes(data.session_name)) {
                            this.selectedSessionKey = data.session_name;
                        }
                    }
                    catch {
                        console.log("Couldn't parse JSON:", e)
                    }
                }
                break;
            case "click":
                this.selectSession(event.currentTarget.getAttribute('data-session-key'));
                break;
        }
    }

    getMetadataLaneHeights() {
        return this._loadMetadata()['lane_heights'];
    }

    _loadMetadata() {
        let data = {};
        if (this._metadataInput) {
            try {
                data = JSON.parse(this._metadataInput.value || '{}');
            }
            catch (e) {
                console.log("Couldn't parse JSON:", e);
            }
            if (!data['session']) {
                // Legacy support for old data with no key session
                data = { session: data };
            }
        }
        return data;
    }

    _setMetadata(key, value) {
        if (this._metadataInput) {
            let data = this._loadMetadata();
            data[key] = value;
            this._metadataInput.value = JSON.stringify(data);
        }
    }
}

customElements.define("perp-fc-browser", PerpFinishcamBrowserElement);
