import { LitElement, html, ref, createRef } from '../lit.js';

import { measuringCss } from './styles.js';
import { SessionMetadataService } from './metadata.js';
import './canvas.js';

import { formatTime, addSeconds } from '../time.js';

import '../live.js';

class PerpFinishcamMeasuringElement extends LitElement {
    static properties = {
        href: {type: String},

        // Internal properties
        _error: {type: String, state: true},
        _lanes: {type: Array, state: true},
        _laneHeightPercentages: {type: Array, state: true},
        _activeLane: {type: Object, state: true},
        _resizingLaneIndex: {type: Number, state: true},
        _x: {type: Number, state: true}
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
        document.body.style['overscroll-behavior-x'] = 'none';
        document.documentElement.style['overscroll-behavior-x'] = 'none';

        this.firstTimeLoad = true;
        this.sessionMetadataService.start(this.href);
        this.initLanes();
    }

    initLanes() {
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
                    time = new Date(`1980-01-01T${input.value}`);
                }
                this._lanes.push({text: element.innerText, input, time, ...base});
            } else {
                this._lanes.push({text: "Lane ${index + 1}", ...base});
            }
        });
        let stored = localStorage.getItem("laneHeightPercentages");
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
            return html`
                <div class="alert alert-danger" role="alert">Error: ${this._error}</div>`
        } else if (this.sessionMetadataService.loaded()) {
            if (this.firstTimeLoad) {
                this.handleFirstTimeLoad();
            }
            return this.renderWorkspace()
        } else {
            return html`
                <div class="alert alert-primary" role="alert">Loading...</div>`
        }
    }

    handleFirstTimeLoad() {
        this.firstTimeLoad = false;
        this.style.setProperty("--perp-fc-image-width", this.sessionMetadataService.imageWidth() + "px");
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
            <div class="wrapper" @mousemove="${this}" @mouseup="${this}" @mousedown="${this}" @mouseleave="${this}">
                <div class="images-outer">
                    <div class="lanes"
                         style="--perp-fc-lanes-grid-template-rows: ${this._laneHeightPercentages?.map(perc => `${perc}%`)?.join(' ')}" }>
                        ${this._lanes?.map(l => this.renderLane(l))}
                    </div>
                    <div class="images">
                        ${[...Array(this.sessionMetadataService.imageCount()).keys()].map(index => this.renderImg(index))}
                        ${this.renderLive()}
                    </div>
                    <perp-fc-measuring-canvas ${ref(this.canvasRef)}></perp-fc-measuring-canvas>
                </div>
                <div class="hud">
                        <div>Time: ${formatTime(this._x)}</div>
                        <div>Lane: ${this._activeLane?.text}</div>
                </div>
            </div>
        `;
    }

    renderLane(lane) {
        return html`
            <div class="lane ${lane.time ? 'has-time' : ''} ${lane === this._activeLane ? 'active' : ''} ${(this._resizingLaneIndex === lane.index || this._resizingLaneIndex === lane.index - 1) ? 'resizing' : ''}"
                 ${ref(lane.ref)} .data-lane=${lane}
                 title="${lane.time ? formatTime(lane.time) : ''}"
            >
                ${lane.text}
            </div>`;
    }

    handleEvent(event) {
        switch (event.type) {
            case 'mousedown':
                if (event.target.classList.contains('lane')) {
                    if (event.offsetY > event.target.getBoundingClientRect().height - 3) {
                        const resizingLane = event.target['data-lane'];
                        if (resizingLane.index >= 0 && resizingLane.index <= this._lanes.length - 1) {
                            this._resizingLaneIndex = resizingLane.index;
                        }
                    }
                }
                else {
                    this._handleMouseMove(event);
                    if (this._x && this._activeLane) {
                        this._activeLane.time = this._x;
                        this.requestUpdate();
                    }
                }
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
        const bb = this.getBoundingClientRect();
        this.canvasRef.value?.drawLiveCrosshair(event.pageX - bb.left, event.pageY - bb.top);

        if (event.target?.timeStart) {
            this._x = addSeconds(event.target.timeStart, this.sessionMetadataService.timeSpan() * (event.offsetX - 1) / event.target.width);
        }
        else if (this._x) {
            this._x = null;
        }

        this._activeLane = this._lanes?.find(l => {
            const r = l.ref?.value.getBoundingClientRect();
            return r && r.top <= event.clientY && r.bottom >= event.clientY;
        });
    }

    renderImg(index) {
        return html`<img src="${this.sessionMetadataService.buildUri(`img${index}.webp`)}"
                         .timeStart="${this.sessionMetadataService.timeStart(index)}">`;
    }

    renderLive() {
        if (this.sessionMetadataService.isLive()) {
            return html`
                <perp-fc-live
                  .timeStart=${this.sessionMetadataService.timeStart(this.sessionMetadataService.imageCount())}
                  for-index="${this.sessionMetadataService.imageCount()}"></perp-fc-live>`;
        }
    }

}

customElements.define("perp-fc-measuring", PerpFinishcamMeasuringElement);