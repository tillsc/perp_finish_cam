class PerpFinishcamMeasuringCanvasElement extends HTMLElement {
    connectedCallback() {
        this.canvas = document.createElement('canvas');
        this.append(this.canvas);
        this.canvasContext = this.canvas.getContext("2d");
        this._setStyles();
    }

    clear() {
        this.canvasContext.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    drawLiveCrosshair(x, y) {
        this.clear();
        this.canvasContext.beginPath()
        this.canvasContext.moveTo(0, y)
        this.canvasContext.lineTo(this.canvas.width, y)
        this.canvasContext.moveTo(x, 0)
        this.canvasContext.lineTo(x, this.canvas.height)
        this.canvasContext.strokeStyle = '#000'
        this.canvasContext.stroke()
        this.canvasContext.closePath()
    }

    _setStyles() {
        this.parentElement.style.position = 'relative';

        this.style.position = 'absolute';
        this.style.inset = 0;
        this.style.height = '100%';
        this.style.width = '100%';
        this.style.pointerEvents = 'none';

        this.canvas.style.position = 'absolute';
        this.canvas.style.inset = 0;
        this.canvas.style.height = '100%';
        this.canvas.style.width = '100%';
        this.canvas.style.pointerEvents = 'none';

        let resizer = new ResizeObserver(([entry]) => {
            // `<canvas>` requires explicit dimensions
            const { inlineSize: width, blockSize: height } = entry.borderBoxSize[0];
            Object.assign(this.canvas, { width, height });
        });
        resizer.observe(this.canvas);
    }
}

customElements.define("perp-finishcam-measuring-canvas", PerpFinishcamMeasuringCanvasElement);