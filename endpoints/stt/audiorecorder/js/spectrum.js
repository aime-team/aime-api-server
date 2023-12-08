'use strict';

class Spectrum {

	constructor(audioContext, src){
		console.log('initialized Spectrum', document.getElementById('canvas'));
		this.context = audioContext;
		this.src = src; //this.context.createMediaElementSource(stream);
		this.analyser = this.context.createAnalyser();

		this.canvas = document.querySelector('#canvas'); //document.getElementById('canvas');
		this.canvas.width = window.innerWidth;
	    this.canvas.height = window.innerHeight;
	    this.ctx = this.canvas.getContext('2d');

		this.src.connect(this.analyser);
	    // this.analyser.connect(this.context.destination);
	    this.analyser.fftSize = 256;

	    this.bufferLength = this.analyser.frequencyBinCount;
		this.dataArray = new Uint8Array(this.bufferLength),

		this.WIDTH = this.canvas.width;
	    this.HEIGHT = this.canvas.height;
	    this.barWidth = (this.WIDTH / this.bufferLength) * 2.5;
	    this.barHeight = null;
	    this.x = 0;

	    this.animationFrameRequestID = null;
	    this.isRendering = false;

	    console.log('initialized spectrum module with bufferLength ', this.bufferLength);
	}

	initRender() {
		if (!this.animationFrameRequestID) {
     		this.animationFrameRequestID = window.requestAnimationFrame(this.render.bind(this));
     	}
	}

    startRender() {
    	this.isRendering = true;
    }

    render() {
    	this.x = 0;

		this.analyser.getByteFrequencyData(this.dataArray);

      	this.ctx.fillStyle = '#000';
      	this.ctx.fillRect(0, 0, this.WIDTH, this.HEIGHT);

      	for (var i = 0; i < this.bufferLength; i++) {
        	if (this.isRendering) {
        		this.barHeight = this.dataArray[i];
        	}
        	else {
        		this.barHeight = 0;	
        	}
	        
	        var r = this.barHeight + (25 * (i/this.bufferLength));
	        var g = 250 * (i/this.bufferLength);
	        var b = 50;

	        this.ctx.fillStyle = 'rgb(' + r + ',' + g + ',' + b + ')';
	        this.ctx.fillRect(this.x, this.HEIGHT - this.barHeight, this.barWidth, this.barHeight);

	        this.x += this.barWidth + 1;
	    }

	    this.animationFrameRequestID = window.requestAnimationFrame(this.render.bind(this));
	    // console.log(this.isRendering);
    }

    stopRender() {
    	this.isRendering = false;
	    window.cancelAnimationFrame(this.animationFrameRequestID);
	    this.animationFrameRequestID = null;
	    this.ctx.clearRect(0, 0, this.WIDTH, this.HEIGHT);
    }
};

export default Spectrum;