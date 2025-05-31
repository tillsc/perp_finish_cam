import { LitElement, html, ref, createRef } from '../lit.js';

import { measuringCss } from './styles.js';
import { SessionMetadataService } from './metadata.js';
import './canvas.js';

import {addSeconds, formatTime, timeDifferenceInMilliseconds, timeDifference, parseTime} from '../time.js';

import '../live.js';

class PerpFinishcamMeasuringElement extends LitElement {
    static properties = {
        href: {type: String},
        startTime: {type: String, attribute: 'start-time'},
        expectedAt: {type: String, attribute: 'expected-at'},
        instanceId: {type: String, attribute: 'instance-id'},
    
        // Internal properties
        _error: {type: String, state: true},

        _autoplay: {type: Boolean},
        _lanes: {type: Array, state: true},
        _laneHeightPercentages: {type: Array, state: true},
        _activeLane: {type: Object, state: true},
        _resizingLaneIndex: {type: Number, state: true},

        _currentScale: {type: Number, state: true},
        _currentOffsetLeft: {type: Number, state: true},

        _x: {type: Number, state: true}
    };

    static styles = measuringCss;

    canvasRef = createRef();
    imagesRef = createRef();
    sessionMetadataService = new SessionMetadataService({
        onNewImage: () => {
            this._error = undefined;
            this.requestUpdate();
        },
        onLoaded: () => this._initLanes(this.sessionMetadataService.timeStart()),
        onError: (msg) => this._error = msg
    });

    connectedCallback() {
        super.connectedCallback();

        this.sessionMetadataService.start(this.href);
        this.live = 
        new ResizeObserver(() => this._afterRender(true))
          .observe(this);
    }

    _initLanes(baseDate) {
        const slot = this.querySelector('slot');
        if (!slot) {
            return;
        }
        this._lanes = [];
        [...slot.assignedElements()].forEach((element, index) => {
            const base = {index, ref: createRef()}
            if (element instanceof HTMLLabelElement) {
                const input = element.querySelector('input');
                let time;
                if (input && input.value) {
                    time = parseTime(input.value, baseDate);
                }
                this._lanes.push({text: element.innerText, input, time, ...base});
            } else {
                this._lanes.push({text: "Lane ${index + 1}", ...base});
            }
        });
        this._initLaneHeightPercentages();
    }

    _loadLocalStorageConfig() {
        let stored = localStorage.getItem("perpFreezingCamConfig") || '{}';
        if (stored) {
            try {
                stored = JSON.parse(stored);
            }
            catch (SyntaxError) {
                stored = {};
            }
        }
        return stored || {};
    }

    _getConfig() {
        return this._loadLocalStorageConfig()[this.instanceId] || {};
    }

    _saveConfig(config) {
        let data = this._loadLocalStorageConfig();
        data[this.instanceId] = config;
        localStorage.setItem("perpFreezingCamConfig", JSON.stringify(data));
    }

    _dispatchLaneHeightsChange() {
        const event = new CustomEvent('laneheightschange', {
            detail: {
                laneHeights: this._laneHeightPercentages
            },
            bubbles: true,
            composed: true
        });
        this.dispatchEvent(event);
    }

    _initLaneHeightPercentages() {
        const outerMetadataLaneHeights = this.getRootNode()?.host?.closest('perp-fc-browser')?.getMetadataLaneHeights() || [];
        const storedPercentages = this._getConfig()['laneHeightPercentages'] || [];
        this._laneHeightPercentages = this._lanes.map(lane => {
            return outerMetadataLaneHeights[lane.index] ||
                storedPercentages[lane.index] ||
                100/this._lanes.length;
        });
        const correctionFactor = 100.0 / this._laneHeightPercentages.reduce((sum, lh) => sum + lh);
        this._laneHeightPercentages = this._laneHeightPercentages.map(lh => lh * correctionFactor);
        this._dispatchLaneHeightsChange();
    }

    _saveLaneHeightPercentages() {
        let config = this._getConfig();
        config['laneHeightPercentages'] = this._laneHeightPercentages;
        this._saveConfig(config);
    }

    render() {
        if (this._error) {
            return html`<div class="alert alert-danger" role="alert">Error: ${this._error}</div>`
        } else if (this.sessionMetadataService.loaded()) {
            this.updateComplete.then(() => this._afterRender(false));
            return this.renderWorkspace()
        } else {
            return html`<div class="alert alert-primary" role="alert">Loading...</div>`
        }
    }

    renderWorkspace() {
        let lastTime;
        return html`
            <div class="wrapper" @mousemove="${this}" @mouseup="${this}" @mousedown="${this}" @mouseleave="${this}"
                 style="--perp-fc-image-scale: ${this._currentScale}; --perp-fc-offset-left: ${this._currentOffsetLeft}px; 
                 --perp-fc-image-ratio: ${this.sessionMetadataService.imageWidth() / this.sessionMetadataService.imageHeight()};
                 --perp-fc-lanes-grid-template-rows: ${this._laneHeightPercentages?.map(perc => `${perc}%`)?.join(' ')};">
                <div class="images-outer">
                    <div class="images" ${ref(this.imagesRef)} @scroll="${this}">
                        ${[...Array(this.sessionMetadataService.imageCount()).keys()].map(index => html`
                            <img src="${this.sessionMetadataService.buildUri(`img${index}.webp`)}" 
                                 .timeStart="${this.sessionMetadataService.timeStart(index)}">
                        `)}
                        ${this.sessionMetadataService.isLive() ? html`
                            <perp-fc-live 
                              href="${this.href}"
                              .timeStart=${this.sessionMetadataService.timeStart(this.sessionMetadataService.imageCount())} 
                              for-index="${this.sessionMetadataService.imageCount()}"></perp-fc-live>` : ''}
                        <div class="times">
                            ${this._lanes?.map(lane => html`
                                <div class="time ${lane.time ? 'has-time' : ''} ${lane === this._activeLane ? 'active' : ''}" 
                                     style="--perp-fc-time-x: ${lane.time ? timeDifferenceInMilliseconds(lane.time, this.sessionMetadataService.timeStart())/1000 * this.sessionMetadataService.pxPerSecond() : 0}px"
                                     data-lane-index="${lane.index}">
                                    ${lane.time ? formatTime(lane.time) : ''}<br>
                                    ${this._relativeTime(lane.time)}
                                </div>`)}
                        </div>
                    </div>
                    
                    <div class="lanes">
                        ${this._lanes?.map(lane => html`
                            <div class="lane ${lane.time ? 'has-time' : ''} ${lane === this._activeLane ? 'active' : ''} ${(this._resizingLaneIndex === lane.index || this._resizingLaneIndex === lane.index - 1) ? 'resizing' : ''}" 
                                 ${ref(lane.ref)} data-lane-index="${lane.index}"
                                 title="${lane.time ? formatTime(lane.time) : ''}">
                                ${lane.text}
                            </div>`)}
                    </div>
                    
                    <perp-fc-measuring-canvas ${ref(this.canvasRef)}></perp-fc-measuring-canvas>
                </div>
                
                <div class="hud">
                    ${this.renderControls()}
                    <div class="time">Time: ${formatTime(this._x)} ${this.startTime ? html`<br>${formatTime(timeDifference(this._x, new Date(this.startTime)), true)}` : ''}</div>
                    <div class="lane">Lane: ${this._activeLane?.text}</div>
                    <div class="ranks">${this._lanesWithTimes().map((l) => {
                        const res = html`<div title="${formatTime(timeDifference(l.time, new Date(this.startTime)), true)}">
                                ${l.text}<br>
                                ${lastTime ? '+' + formatTime(timeDifference(l.time, lastTime), true) : formatTime(timeDifference(l.time, new Date(this.startTime)), true)}
                                <button title="Delete" @click="${() => {
                                        this._stopTime(undefined, l);
                                        this.requestUpdate(); 
                                    }}">🗑</button>
                            </div>`;
                        lastTime = l.time;
                        return res;
                    })}</div>
                </div>
            </div>
        `;
    }

    renderControls() {
        const playPause = this.sessionMetadataService.isLive() ? 
            html`<button @click="${() => this._autoplay = !this._autoplay}">
                ${this._autoplay ? '⏸' : '▶'}</button>` : '';
        
        const jumpToMostRelevant = this.sessionMetadataService.expectedAt ? 
            html`<button @click="${() => this.scrollToTime(parseTime(this.expectedAt, this.sessionMetadataService.timeStart()))}}">
                ⏲</button>` : '';
        return html`<div class="buttons">
                        <button @click="${() => { this._autoplay = false; this.scrollTo(0); }}">⏮</button>
                        ${playPause}
                        ${jumpToMostRelevant}
                        <button @click="${() => { this._autoplay = false; this.scrollToRight(); }}">⏭</button>
                    </div>`;
    }

    _lanesWithTimes() {
        return (this._lanes || [])
          .filter((l) => !!l.time)
          .sort((l1, l2) => l1.time - l2.time);
    }

    _relativeTime(date) {
        if (date && this.startTime) {
            return formatTime(timeDifference(date, new Date(this.startTime)), true);
        }
    }

    _afterRender(forceBoundingBoxes) {
        if (!this.boundingBox || forceBoundingBoxes) {
            this.boundingBox = this.getBoundingClientRect();
        }
        if (!this.boundingBoxFirstImage || forceBoundingBoxes) {
            this.boundingBoxFirstImage = this.imagesRef?.value?.firstElementChild?.getBoundingClientRect();
            if (this.boundingBoxFirstImage) {
                this._currentScale = this.boundingBoxFirstImage.width / this.sessionMetadataService.imageWidth();
                this._currentOffsetLeft = this.boundingBoxFirstImage.left;
            }
        }
        if (!this.alreadyScrolledRight) {
            this.alreadyScrolledRight = true;
            setTimeout(() => {
                const firstTime = this._lanesWithTimes()[0]?.time;
                if (firstTime) {
                    this.scrollToTime(firstTime);
                }
                else if (this.expectedAt) {
                    this.scrollToTime(parseTime(this.expectedAt, this.sessionMetadataService.timeStart()));
                }
                else if (this.sessionMetadataService.isLive()) {
                    this._autoplay = true;
                    this.scrollToRight();
                }
            }, 500);
        } 
        else {
            if (this._autoplay && this.sessionMetadataService.isLive()) {
                this.scrollToRight();
            }
        }
    }

    scrollTo(left) {
        if (left !== undefined) {
            this.imagesRef.value.scrollTo({
                left: left,
                behavior: 'smooth'
            });
        }
    }

    scrollToTime(time) {
        this.scrollTo(timeDifferenceInMilliseconds(time, this.sessionMetadataService.timeStart())/1000 * this.sessionMetadataService.pxPerSecond() * this._currentScale)
    }

    scrollToRight() {
        this.scrollTo(this.imagesRef?.value?.scrollWidth);
    }

    handleEvent(event) {
        switch (event.type) {
            case 'scroll':
                this._afterRender(true);
                break;
            case 'mousedown':
                if (event.target.classList.contains('lane')) {
                    if (event.offsetY > event.target.getBoundingClientRect().height - 3) {
                        const laneIndex = parseInt(event.target.getAttribute('data-lane-index'));
                        if (laneIndex >= 0 && laneIndex <= this._lanes.length - 1) {
                            this._resizingLaneIndex = laneIndex;
                        }
                    }
                }
                else {
                    this._handleMouseMove(event);
                    if (this._x && this._activeLane) {
                        this._autoplay = false;
                        this._stopTime(this._x, this._activeLane);
                        this.requestUpdate();
                    }
                }
                event.preventDefault();
                break;
            case 'mouseup':
                if (this._resizingLaneIndex === undefined && event.target.classList.contains('lane')) {
                    const laneIndex = parseInt(event.target.getAttribute('data-lane-index'));
                    const lane = this._lanes[laneIndex];
                    if (lane?.time) {
                        this._autoplay = false;
                        this.scrollToTime(addSeconds(lane.time, -1));
                    }
                }
                // Intentional! no break;
            case 'mouseleave':
                if (this._resizingLaneIndex !== undefined) {
                    this._resizingLaneIndex = undefined;
                    this._saveLaneHeightPercentages();
                    this._dispatchLaneHeightsChange();
                }
                this._handleMouseMove(event);
                event.preventDefault();
                break;
            case 'mousemove':
                this._handleMouseMove(event);
                if (this._resizingLaneIndex !== undefined) {
                    this._handleLaneResize(event);
                }
                else {
                    if (!event.target.classList.contains('lane') && event.buttons == 1 && this._x && this._activeLane) {
                        this._stopTime(this._x, this._activeLane);
                        this.requestUpdate();
                    }
                }
                event.preventDefault();
                break;
        }
    }

    _stopTime(x, activeLane) {
        activeLane.time = x;
        if (activeLane.input) {
            activeLane.input.value = x ? formatTime(x) : '';
        }
    }

    _handleLaneResize(event) {
        if (this._resizingLaneIndex !== undefined) {
            const resizingLane1 = this._lanes[this._resizingLaneIndex];
            const resizingLane2 = this._lanes[this._resizingLaneIndex + 1];
            const bbLane1 = resizingLane1.ref.value.getBoundingClientRect();
            const bbLane2 = resizingLane2.ref.value.getBoundingClientRect();
            const relY = event.clientY - bbLane1.y;
            const totalHeight = bbLane1.height + bbLane2.height;
            const totalPercentage = this._laneHeightPercentages[this._resizingLaneIndex] + this._laneHeightPercentages[this._resizingLaneIndex + 1];

            this._laneHeightPercentages[this._resizingLaneIndex] = Math.max(Math.min(totalPercentage * relY / totalHeight, totalPercentage - 2), 2);
            this._laneHeightPercentages[this._resizingLaneIndex + 1] = totalPercentage - this._laneHeightPercentages[this._resizingLaneIndex];
            this.requestUpdate();
        }
    }
    _handleMouseMove(event) {
        const canvas = this.canvasRef.value;
        if (canvas) {
            const canvasBounds = canvas.getBoundingClientRect();
            canvas.drawLiveCrosshair(event.clientX - canvasBounds.left, event.clientY - canvasBounds.top, this._activeLane?.time ? '#c33' : '#000');
        }
        
        if (this.boundingBoxFirstImage) {
          this._x = this.sessionMetadataService.timeStart((event.pageX - this.boundingBoxFirstImage.left) / this.boundingBoxFirstImage.width);
        }

        if (event.buttons == 0) { // Switch active lane only when no buttons are pressed
            this._activeLane = this._lanes?.find(l => {
                const r = l.ref?.value.getBoundingClientRect();
                return r && r.top <= event.clientY && r.bottom >= event.clientY;
            });
        }
    }

}

customElements.define("perp-fc-measuring", PerpFinishcamMeasuringElement);