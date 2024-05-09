class MetadataServiceBase {
    constructor(options) {
        this._options = { 
            ...this.getDefaultOptions(),
            ...options
        };
    }

    buildUri(relativePath) {
        if (!this.baseUrl) {
            this.baseURL = new URL(this.baseHref, window.location.href);
            if (!this.baseURL.pathname.endsWith('/')) {
                this.baseURL.pathname = this.baseURL.pathname + '/';
            }
        }
        return new URL(relativePath, this.baseURL).href
    }

    start(baseHref) {
        this.baseHref = baseHref;
        this._fetch();
    }

    loaded() {
        return false;
    }

    _error(msg) {
        if (this._options.onError) {
            this._options.onError(msg);
        }
    }

    getDefaultOptions() { 
        return {};
    }
}

export class SessionListService extends MetadataServiceBase {
    async _fetch() {
        const uri = this.buildUri('index.json');
        this.lastResponse = await fetch(uri);
        if (this.lastResponse.ok) {
            const json = await this.lastResponse.json();
            this._sessions = json;
            this._newSessionList();
        }
        else {
            this._error = `Could not fetch sessions with uri ${uri}:\n${this.lastResponse.status} ${this.lastResponse.statusText}`;
        }
        setTimeout(() => this._fetch(), 10_000);
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

    _newSessionList() {
        if (this._options.onNewSessionList) {
            this._options.onNewSessionList();
        }
    }
}

export class SessionMetadataService extends MetadataServiceBase {

    getDefaultOptions() {
        return { fetchAgainDelay: 500, liveDetectionOffset: 2000, ...super.getDefaultOptions() };
    }

    timeStart(index = 0) {
        if (this._metadata && this._metadata.time_start && this._metadata.time_span) {
            const ts = this._metadata.time_start + (this._metadata.time_span * index);
            return new Date(ts * 1000);
        }
    }

    timeEnd() {
        return this.timeStart(this.imageCount());
    }

    timeSpan() {
        return this._metadata?.time_span;
    }

    pxPerSecond() {
        return this._metadata?.px_per_second;
    }

    expectedNext() {
        let expectedNext = this.timeEnd();
        if (expectedNext && this._metadata.time_span) {
            expectedNext.setSeconds(expectedNext.getSeconds() + this._metadata.time_span);
        }
        else {
            expectedNext = new Date();
        }
        return expectedNext;
    }

    imageCount() {
        if (this._metadata && this._metadata.last_index !== undefined && this._metadata.last_index != null) {
            return this._metadata.last_index + 1;
        }
        else {
            return 0;
        }
    }

    imageWidth() {
        if (this._metadata && this._metadata.px_per_second && this._metadata.time_span) {
            return this._metadata.px_per_second * this._metadata.time_span;
        }
        else {
            return 0;
        }
    }

    imageHeight() {
        return this._metadata && this._metadata.height || 0;
    }

    isLive() {
        return (this.expectedNext() - new Date() + this._options.liveDetectionOffset > 0);
    }

    loaded() {
        return !!this._metadata;
    }

    _fetchAgainAt(date) {
        const t = Math.max(date - new Date(), 0);
        this.fetchAgainTimeout = setTimeout(() => this._fetch(), t + this._options.fetchAgainDelay);
    }

    async _fetch() {
        const response = await fetch(this.buildUri('index.json'));
        if (response.ok) {
            const newMetadata = await response.json();
            if (!this._metadata || this._metadata.last_index != newMetadata.last_index) {
                this._metadata = newMetadata;
                this._newImage(newMetadata.last_index);
            }
            if (this.isLive()) {
                this._fetchAgainAt(this.expectedNext());
            }
        }
        else {
            this._error(`Failed to fetch JSON metadata from "${this.url}"`);
            this._fetchAgainAt(new Date());
        }
    }

    _newImage(newIndex) {
        if (this._options.onNewImage) {
            this._options.onNewImage(newIndex);
        }
    }

}