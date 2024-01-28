import {LitElement, html, css} from './lit.js';

class PerpFinishcamMeasuringElement extends LitElement {
    static properties = {
        timeStart: { type: Number },
        timeSpan: { type: Number }
      };

      static styles = css`
        .wrapper {
            cursor: crosshair;
            display: inline-block;
            position: relative;
        }

        .hud {
            position: absolute;
            bottom: 0;
            z-index: 100;
            left: 0;
            right: 0;
            height: 100px;
            background-color: #ffffff77;
        }
        `;

    constructor() {
        super();  
        this.timeStart = Date.now();  
        this.timeSpan = 10;
    }

    timeStartAsDate() {
        return new Date(this.timeStart);
    }

    timeEndAsDate() {
        return new Date(this.timeStart + (1000 * this.timeSpan));
    }

    render() {
        return html`
        <div class="wrapper">
          <slot></slot>
          <div class="hud">
          Beginn: ${this.timeStartAsDate()}<br>
          Ende: ${this.timeEndAsDate()}<br>
          Dauer: ${this.timeSpan}Sek
          </div>
        </div>
        `
    }
}

customElements.define("perp-finishcam-measuring", PerpFinishcamMeasuringElement);