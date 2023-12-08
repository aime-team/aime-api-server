'use strict';

//webkitURL is deprecated but nevertheless
URL = window.URL || window.webkitURL;

var serverURL = '/stt';

var gumStream; 						//stream from getUserMedia()
var rec; 							//Recorder.js object
var input; 							//MediaStreamAudioSourceNode we'll be recording

// shim for AudioContext when it's not avb. 
var AudioContext = window.AudioContext || window.webkitAudioContext;
var audioContext //audio context to help us record

var recordButton = document.getElementById('recordButton');
var stopButton = document.getElementById('stopButton');
var pauseButton = document.getElementById('pauseButton');

//add events to those 2 buttons
recordButton.addEventListener('click', startRecording);
stopButton.addEventListener('click', stopRecording);
pauseButton.addEventListener('click', pauseRecording);

initAudioDrop();

function startRecording() {
	console.log('recordButton clicked');
    
    var constraints = { audio: true, video:false };

    // Disable the record button until we get a success or fail from getUserMedia() 
	recordButton.disabled = true;
	stopButton.disabled = false;
	pauseButton.disabled = false;

	navigator.mediaDevices.getUserMedia(constraints).then(function(stream) {
		console.log('getUserMedia() success, stream created, initializing Recorder.js ...');

		audioContext = new AudioContext();

		document.getElementById('formats').innerHTML='Format: 1 channel pcm @ '+audioContext.sampleRate/1000+'kHz';

		gumStream = stream;
		input = audioContext.createMediaStreamSource(stream);
		rec = new Recorder(input,{numChannels:1});
		rec.record();

		console.log('Recording started');

	}).catch(function(err) {
    	recordButton.disabled = false;
    	stopButton.disabled = true;
    	pauseButton.disabled = true;
	});
}

function pauseRecording(){
	console.log('pauseButton clicked rec.recording=',rec.recording );
	if (rec.recording){
		//pause
		rec.stop();
		pauseButton.innerHTML='Resume';
	}else{
		//resume
		rec.record()
		pauseButton.innerHTML='Pause';

	}
}

function stopRecording() {
	console.log('stopButton clicked');

	stopButton.disabled = true;
	recordButton.disabled = false;
	pauseButton.disabled = true;

	pauseButton.innerHTML='Pause';
	
	rec.stop();

	//stop microphone access
	gumStream.getAudioTracks()[0].stop();

	//create the wav blob and pass it on to createDownloadLink
	rec.exportWAV(createDownloadLink);
}

function createDownloadLink(blob) {
	
	var url = URL.createObjectURL(blob);
	var au = document.createElement('audio');
	var li = document.createElement('li');
	var link = document.createElement('a');

	//name of .wav file to use during upload and download (without extendion)
	var filename = new Date().toISOString();

	//add controls to the <audio> element
	au.controls = true;
	au.src = url;

	//save to disk link
	link.href = url;
	link.download = filename+'.wav'; //download forces the browser to donwload the file using the  filename
	link.innerHTML = 'Save to disk';
	link.classList.add('recording-link');

	li.appendChild(au);
	
	//add the filename to the li
	var txtWrapper = document.createElement('div');
	txtWrapper.classList.add('recording-description');
	txtWrapper.appendChild(document.createTextNode(filename+'.wav '));
	li.appendChild(txtWrapper);

	//add the save to disk link to li
	li.appendChild(link);
	
	//upload link
	var upload = document.createElement('a');
	upload.classList.add('upload-link');
	upload.href='#';
	upload.innerHTML = 'Upload';
	upload.addEventListener('click', function(event){
		  var xhr=new XMLHttpRequest();
		  xhr.onload=function(e) {
		      if(this.readyState === 4) {
		          console.log('Server returned: ',e.target.responseText);
		      }
		  };
		  var fd=new FormData();
		  fd.append('audio_data',blob, filename);
		  xhr.open('POST', serverURL);
		  xhr.send(fd);
	})
	li.appendChild(document.createTextNode (' '))//add a space in between
	li.appendChild(upload)//add the upload link to li

	//add the li element to the ol
	recordingsList.appendChild(li);
}


function initAudioDrop() {
	AudioDrop({

	  context: new AudioContext(),
	  elements: document.querySelector('#dropZone'),

	  drop: function(buffer, file) {
	  	console.log('filde dropped', buffer, file);
	  	document.querySelector('#dropZone').classList.remove('dropzone-hover');

	  	
	  	console.log('buffer', buffer);

// TODO: check num of channels, mix into one channel only
// ... https://github.com/audiojs/audio-buffer-remix


// TODO: slice into chunks of max. 10 seconds and send multiple API calls
// ...	https://github.com/audiojs/audio-buffer-utils -> subbuffer

	  	// audioBlob = new Blob(buffer, { 'type' : 'audio/ogg; codecs=opus' });
	  	// console.log('audioBlob', audioBlob);

	    window[file.name] = buffer;
	    console.log('Added the buffer ' + file.name + ' to the window.');

		// var name = file.name.replace(/\.[^/.]+$/, "");
	 //    if( AudioDrop.isValidVariableName(name) ) {
	 //      window[name] = buffer;
	 //      console.log('Added the variable "' + name + '"" to the window.');
	 //    } else {
	 //      window[name + '-sample'] = buffer;
	 //      console.log('Added the variable window["' + name + '-sample"] to the window.');
	 //    }
	  },

	  
	  dragEnter: function(e) { 
	  	console.log('dragEnter', e); 
	  	document.querySelector('#dropZone').classList.add('dropzone-hover');
	  },

	  dragOver: function(e) { },

	  dragLeave: function(e) { 
	  	console.log('dragLeave', e); 
	  	document.querySelector('#dropZone').classList.remove('dropzone-hover');
	  },
	})
}
