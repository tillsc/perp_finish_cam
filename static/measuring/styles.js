import {css} from '../lit.js';

export const measuringCss = css`
:host {
    display: block;
    background-color: lightgray;
}

.wrapper {
    height: 100%;

    display: flex;
    flex-direction: column;
    align-items: stretch;
}

.images-outer {
    cursor: crosshair;
    flex: 1 1 auto;

    display: flex;
    flex-direction: column;
    align-items: stretch;
}

.images-outer > .images {
    overflow-x: scroll;
    overflow-y: hidden;
    padding-bottom: 20px;
    flex: 1 1 0;
   
    display: flex;
    flex-direction: row;
    justify-content: start;
}

.hud {
    padding: 1rem;
    background-color: #888888;
    overflow: scroll;
    flex: 0 0 200px;
}
`;

export const browserCss = css`
:host {
  display: block;
  padding: 1rem;
}
  
table td {
padding: 0.1rem 0.3rem;
}
`;
