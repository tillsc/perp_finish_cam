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

    drawLiveCrosshair(x, y, color) {
        this.clear();
        this.canvasContext.beginPath()
        this.canvasContext.moveTo(0, y)
        this.canvasContext.lineTo(this.canvas.width, y)
        this.canvasContext.moveTo(x, 0)
        this.canvasContext.lineTo(x, this.canvas.height)
        this.canvasContext.strokeStyle = color
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
            const dpr = window.devicePixelRatio || 1;
            const width = entry.contentRect.width;
            const height = entry.contentRect.height;

            // Set canvas size in physical pixels
            this.canvas.width = width * dpr;
            this.canvas.height = height * dpr;

            // Set CSS size (logical pixels)
            this.canvas.style.width = `${width}px`;
            this.canvas.style.height = `${height}px`;

            // Scale context for high DPI displays
            this.canvasContext.setTransform(dpr, 0, 0, dpr, 0, 0);
        });
        resizer.observe(this.canvas);
    }
}

customElements.define("perp-fc-measuring-canvas", PerpFinishcamMeasuringCanvasElement);