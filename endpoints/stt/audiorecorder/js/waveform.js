'use strict';

class Waveform {

	constructor(audioContext, src){
		console.log('initializing Waveform', document.querySelector('#waveform-canvas'));
		this.context = audioContext;
		this.src = src;
		this.analyser = this.context.createAnalyser();

		this.canvas = document.querySelector('#waveform-canvas');
		this.canvas.width = window.innerWidth;
	    this.canvas.height = window.innerHeight;
	    this.canvasContext = this.canvas.getContext('2d');

	    this.scriptProcessor = audioContext.createScriptProcessor(2048, 1, 1);

		this.analyser.smoothingTimeConstant = 0.3;
  		this.analyser.fftSize = 1024;

	    this.barWidth = 4; // (this.WIDTH / this.bufferLength) * 2.5;
	    this.barGutter = 3;
  		this.barColor = "#0093FF";

		this.bars = [];
		this.width = 0;
		this.height = 0;
		this.halfHeight = 0;
		this.drawing = false;
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
		    	this.bars.push(this.getAverageVolume(array));

		    	if (this.bars.length <= Math.floor(this.width / (this.barWidth + this.barGutter))) {
		    	    this.renderBars(this.bars);
		    	} else {
		    	    this.renderBars(this.bars.slice(this.bars.length - Math.floor(this.width / (this.barWidth + this.barGutter))), this.bars.length);
		    	}

		    } else {
		      this.bars = [];
		    }
		}
	}

	getAverageVolume(array) {
		var length = array.length;

		let values = 0;
		let i = 0;

		for (; i < length; i++) {
		    values += array[i];
		}

		return values / length;
	}

	renderBars(bars) {
		if (!this.drawing) {
			this.drawing = true
			this.animationFrameRequestID = window.requestAnimationFrame(() => {
			  this.canvasContext.clearRect(0, 0, this.width, this.height)
			  bars.forEach((bar, index) => {
			    this.canvasContext.fillStyle = this.barColor;
			    this.canvasContext.fillRect((index * (this.barWidth + this.barGutter)), this.halfHeight, this.barWidth, (this.halfHeight * (bar / 100)));
			    this.canvasContext.fillRect((index * (this.barWidth + this.barGutter)), (this.halfHeight - (this.halfHeight * (bar / 100))), this.barWidth, (this.halfHeight * (bar / 100)));
			  })
			   this.drawing = false;
			});
		}
	}

    startRender() {
    	// if (!this.animationFrameRequestID) {
     		// this.animationFrameRequestID = window.requestAnimationFrame(this.startRender.bind(this));
     	// }
     	console.log('Start rendering Waveform');
     	this.shouldRender = true;

	}
    
    stopRender() {
    	// window.cancelAnimationFrame(this.animationFrameRequestID);
    	console.log('Stop rendering Waveform');
    	this.shouldRender = false;

   //  	if (this.animationFrameRequestID) {

			
			// // this.analyser.disconnect(this.context.destination);
	  //   }
	    
    }

    clearRender() {
    	this.canvasContext.clearRect(0, 0, this.width, this.height)
    }
};

export default Waveform;