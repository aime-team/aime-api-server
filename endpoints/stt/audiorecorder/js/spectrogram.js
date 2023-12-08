'use strict';

class Spectrogram {

	constructor(audioContext, src){
		console.log('initializing Spectrogram', document.querySelector('#spectrogram-canvas'));

		this.context = audioContext;
		this.src = src;
		this.analyser = this.context.createAnalyser();
		this.analyser.smoothingTimeConstant = 0.3; // 0.3;
  		this.analyser.fftSize = 1024*4;
  		this.timeScale = 1024;

		this.canvas = document.querySelector('#spectrogram-canvas');
		this.canvas.width = 1224; //window.innerWidth;
	    this.canvas.height = window.innerHeight;
	    this.canvasContext = this.canvas.getContext('2d');

	    // create a temp canvas we use for copying and scrolling
    	this.tempCanvas = document.createElement('canvas'),
        this.tempCtx = this.tempCanvas.getContext('2d');
	    this.tempCanvas.width = this.canvas.width;
	    this.tempCanvas.height = this.canvas.height;

	    // used for color distribution
	    this.colorScale = chroma.scale(
				['#000000', '#002744', '#0093ff', '#ffffff'],
				[0, .05, .75, 1] // 0 .25 .75 1
			)
			.mode('rgb')
			.domain([0, 300]
		);
		// this.xPos = 0;

	    this.scriptProcessor = audioContext.createScriptProcessor(this.timeScale, 1, 1);

		this.shouldRender = false;

		this.width = this.canvas.offsetWidth;
	    this.height = this.canvas.offsetHeight;
	    this.halfHeight = this.canvas.offsetHeight / 2;
	    this.canvasContext.canvas.width = this.width;
	    this.canvasContext.canvas.height = this.height;

	    this.src.connect(this.analyser);
	    this.analyser.connect(this.scriptProcessor);
	    this.scriptProcessor.connect(audioContext.destination);

	    this.animationFrameRequestID = null;

	    this.scriptProcessor.onaudioprocess =  (e) => {
		    if (this.shouldRender) {
		    	// console.log('Waveform processInput', e);
			    var array = new Uint8Array(this.analyser.frequencyBinCount);
		    	this.analyser.getByteFrequencyData(array);
		    	this.drawSpectrogram(array);

		    } else {
		      // not rendering -> reset
		      // ...
		    }
		}
	}


    drawSpectrogram(array) {
 
        // copy the current canvas onto the temp canvas
        this.tempCtx.drawImage(this.canvas, 0, 0, this.canvas.width, this.canvas.height);
 
        // iterate over the elements from the array
        for (var i = 0; i < array.length; i++) {
            // draw each pixel with the specific color
            let clr = this.colorScale(array[i]).hex();
            this.canvasContext.fillStyle = clr;
 
            // draw the line at the right side of the canvas
            //this.canvasContext.fillRect(this.xPos, this.canvas.height - i, 1, 1); 
            this.canvasContext.fillRect(this.canvas.width - 1, this.canvas.height - i, 1, 1);
        }
 
        // set translate on the canvas
        this.canvasContext.translate(-1, 0);
        // draw the copied image
        this.canvasContext.drawImage(this.tempCanvas, 0, 0, this.canvas.width, this.canvas.height, 0, 0, this.canvas.width, this.canvas.height);
 		// this.xPos += 1;
        // reset the transformation matrix
        this.canvasContext.setTransform(1, 0, 0, 1, 0, 0);
    }

    startRender() {
     	console.log('Start rendering Spectrogram');
     	this.shouldRender = true;
	}
    
    stopRender() {
    	// window.cancelAnimationFrame(this.animationFrameRequestID);
    	console.log('Stop rendering Spectrogram');
    	this.shouldRender = false;	    
    }

    clearRender() {
    	this.canvasContext.clearRect(0, 0, this.width, this.height);
    	this.tempCtx.clearRect(0, 0, this.width, this.height);
    	// this.xPos = 0;
    }
};

export default Spectrogram;