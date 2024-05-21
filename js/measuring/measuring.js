import { LitElement, html, ref, createRef } from '../lit.js';

import { measuringCss } from './styles.js';
import { SessionMetadataService } from './metadata.js';
import './canvas.js';

import { formatTime, timeDifferenceInMilliseconds, timeDifference } from '../time.js';

import '../live.js';

class PerpFinishcamMeasuringElement extends LitElement {
    static properties = {
        href: {type: String},
        startTime: {type: String, attribute: 'start-time'},

        // Internal properties
        _error: {type: String, state: true},

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
                    time = new Date(`${baseDate.toDateString()} ${input.value}`);
                }
                this._lanes.push({text: element.innerText, input, time, ...base});
            } else {
                this._lanes.push({text: "Lane ${index + 1}", ...base});
            }
        });
        let stored = localStorage.getItem("laneHeightPercentages") || '[]';
        if (stored) {
            try {
                stored = JSON.parse(stored);
            }
            catch (SyntaxError) {
                stored = [];
            }
        }
        this._laneHeightPercentages = this._lanes.map(lane => {
            let v = 100/this._lanes.length;
            if (stored[lane.index]) {
                v = stored[lane.index];
            }
            return v;
        });
        const correctionFactor = 100.0 / this._laneHeightPercentages.reduce((sum, lh) => sum + lh);
        this._laneHeightPercentages = this._laneHeightPercentages.map(lh => lh * correctionFactor);
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
                              .timeStart=${this.sessionMetadataService.timeStart(this.sessionMetadataService.imageCount())} 
                              for-itimesndex="${this.sessionMetadataService.imageCount()}"></perp-fc-live>` : ''}
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
                    <div>Time: ${formatTime(this._x)} (${formatTime(timeDifference(this._x, new Date(this.startTime)), true)})</div>
                    <div>Lane: ${this._activeLane?.text}</div>
                    <div class="ranks">${this._lanes?.filter((l) => !!l.time)?.sort((l1, l2) => l1.time - l2.time)?.map((l) => {
                        const res = html`<div>${l.text}<br>${lastTime ? '+' + formatTime(timeDifference(l.time, lastTime), true) : ''}</div>`;
                        lastTime = l.time;
                        return res;
                    })}</div>
                </div>
            </div>
        `;
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
        if (!this.alreadyScrolledRight && this.sessionMetadataService.isLive()) {
            this.alreadyScrolledRight = true;
            setTimeout(() => this.scrollToRight(), 500);
        }
    }

    scrollToRight() {
        this.imagesRef.value.scrollLeft = this.imagesRef.value.scrollWidth;
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
                        this._activeLane.time = this._x;
                        if (this._activeLane.input) {
                            this._activeLane.input.value = formatTime(this._x);
                        }
                        this.requestUpdate();
                    }
                }
                event.preventDefault();
                break;
            case 'mouseup':
            case 'mouseleave':
                if (this._resizingLaneIndex !== undefined) {
                    this._resizingLaneIndex = undefined;
                    localStorage.setItem("laneHeightPercentages", JSON.stringify(this._laneHeightPercentages));
                }
               // Intentional! no break;
            case 'mousemove':
                if (this._resizingLaneIndex !== undefined) {
                    this._handleLaneResize(event);
                }
                this._handleMouseMove(event);
                if (event.buttons == 1 && this._x && this._activeLane) {
                    this._activeLane.time = this._x;
                    this.requestUpdate();
                }
                event.preventDefault();
                break;
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
        this.canvasRef.value?.drawLiveCrosshair(event.pageX - this.boundingBox.left, event.pageY - this.boundingBox.top);

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