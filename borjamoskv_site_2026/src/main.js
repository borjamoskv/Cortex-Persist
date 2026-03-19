import './style.css'
import Game from './World/Game.js'

const canvas = document.querySelector('#webgl-canvas')
if (canvas) {
    const game = new Game(canvas)
} else {
    console.error("Canvas element #webgl-canvas not found.");
}
