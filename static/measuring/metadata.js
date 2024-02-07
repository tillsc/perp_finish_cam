export default class MetadataService {
    constructor(options) {
        this._options = { 
            fetchAgainDelay: 500, 
            ...options
        };
    }

    start(url) {
        this.url = url;
        this._fetchMetadata();
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

    isLive() {
        return (this.expectedNext() - new Date() > this._options.fetchAgainDelay * 2);
    }

    loaded() {
        return !!this._metadata;
    }

    _fetchAgainAt(date) {
        let t = date - new Date();
        t = Math.max(t, 0);
        console.log("fetch next time in", t, `+${this._options.fetchAgainDelay} ms`);
        this.fetchAgainTimeout = setTimeout(() => this._fetchMetadata(), t + this._options.fetchAgainDelay);
    }

    async _fetchMetadata() {
        const response = await fetch(this.url);
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

    _error(msg) {
        if (this._options.onError) {
            this._options.onError(msg);
        }
    }

    _newImage(newIndex) {
        if (this._options.onNewImage) {
            this._options.onNewImage(newIndex);
        }
    }

}