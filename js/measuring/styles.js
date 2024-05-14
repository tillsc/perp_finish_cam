import {css} from '../lit.js';

export const measuringCss = css`
  :host {
    display: block;
    background-color: lightgray;
  }

  .wrapper {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }

  .images-outer {
    cursor: crosshair;
    flex: 1 1 auto;
    
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }

  .images-outer > .lanes {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 15px;
    width: 150px;
    background: #888888;
    opacity: 0.8;

    display: grid;
    grid-template-rows: var(--perp-fc-lanes-grid-template-rows);
  }

  .images-outer > .lanes > .lane {
    padding: 0 0.4rem;
    display: flex;
    align-items: center;
    position: relative;
  }

  .images-outer > .lanes > .lane:not(:last-child):after {
    content: '';
    background-color: #444;
    position: absolute;
    left: 0;
    bottom: 0;
    right: 0;
    height: 2px;
    cursor: ns-resize;
  }

  .images-outer > .lanes > .lane.active {
    background: #ccc;
  }

  .images-outer > .lanes > .lane.has-time {
    background: #7b7;
  }


  .images-outer > .lanes > .lane.active.has-time {
    background: #cfc;
  }
  
  .images-outer > .lanes > .lane.resizing, .images-outer > .lanes > .lane.resizing.has-time {
    background: #ffc;
  }

  .images-outer > .images {
    overflow-x: scroll;
    overflow-y: hidden;
    padding-bottom: 15px;
    padding-left: 150px;
    flex: 1 1 200px;

    display: flex;
    flex-direction: row;
    justify-content: start;
    position: relative;
  }

  .images-outer > .images > * {
    flex: 1 1 auto;
    aspect-ratio: var(--perp-fc-image-ratio, auto);
    height: 100%;
  }
  
  .images-outer > .images > .times {
    position: absolute;
    top: 0;
    bottom: 15px;
    height: auto;
    
    display: grid;
    grid-template-rows: var(--perp-fc-lanes-grid-template-rows);
  }

  .images-outer > .images > .times > .time.has-time {
    border-left: 1.5px solid #5F5;
    color: #5F5;
    padding-left: 0.5rem;
    position: relative;
    left: calc(var(--perp-fc-time-x, 0) * var(--perp-fc-image-scale, 1));
  }
  
  .hud {
    flex: 0 0 auto;
    padding: 0.3rem;
    background-color: #888888;
    display: flex;
    justify-content: space-around;
    gap: 1rem;
  }
`;

export const browserCss = css`
  :host {
    display: block;
    padding: 1rem;
    position: absolute;
    top: var(--perp-fc-padding-top, 0);
    bottom: 0;
    left: 0;
    right: 0;
    overflow: scroll;
  }
    
  table td {
  padding: 0.1rem 0.3rem;
  }
  
  perp-fc-measuring {
    position: absolute;
    top: 2.5rem;
    right: 0;
    left: 0;
    bottom: 0;
  }
`;
