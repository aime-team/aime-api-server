// by headkit-studio.de
// using https://github.com/higuma/web-audio-recorder-js


/*

2DO:

- after recording animate recording button to textbox, after decision animate to position
	- .decision-position
	- .topleft-position
	- .topright-position

- set input to zero when playback
- Aussteuerungsanzeige mit Farbcodes für optimale Lautstärke

- Option-Box 'Allow anonymous usage of recording for model optimization'

- errors:
	- server connection
	- no speech signal detected

*/


'use strict';

import Spectrum from './spectrum.js';
import Waveform from './waveform.js';
import Spectrogram from './spectrogram.js';

URL = window.URL || window.webkitURL;

var serverURL = '/stt';
var input;
var audioBlob = null;
var audiofile = null;
var chunks = [];

var AudioContext = window.AudioContext || window.webkitAudioContext;
var mediaRecorder, mediaStream;
var audioContext = new AudioContext; //new audio context to help us record 
var spectrum, waveform, spectrogram;

var waveFormCanvas = document.getElementById('waveform-canvas');
var playButton = null;

var recordButton = document.getElementById('recordButton');
recordButton.disabled = true;
recordButton.addEventListener('click', onRecordButtonClicked);
var recordingIsOn = false;
var recordBufferFilled = false;

var resetButton = document.getElementById('resetButton');
resetButton.addEventListener('click', onResetButtonClicked);

var resultMessageBox = document.getElementById('result');
var systemMessage = document.getElementById('msg-system');
var resultMessage = document.getElementById('msg-result');

var logitsResult = document.getElementById('logits');
var resultList = document.getElementById('resultlist');

var maxTimerInSec = 10;
var timerTime = maxTimerInSec;
var display = document.getElementById('timer-display');
var timer = null

function runTimer() {
	timerTime--;
	display.innerHTML = timerTime;
	if (timerTime < 1) {
	    stopRecording()
	}
}

function clearTimer() {
	clearInterval(timer);
	display.innerHTML = '';
	timerTime = maxTimerInSec;
}

function onRecordButtonClicked(e) { 
	console.log('recordButton clicked', e); 
	if (!recordingIsOn && !recordBufferFilled) {
		startRecording();
	}
	else if (!recordingIsOn && recordBufferFilled) {
		playAudioBuffer();
	}
	else {
		stopRecording();
	}
}

function onResetButtonClicked() {
	recordBufferFilled = false;
	recordButton.disabled = false;
	recordButton.classList.remove('disabled');
	resultMessageBox.classList.remove('morphed');
	resultMessageBox.classList.remove('sending-data');
	resultList.classList.add('empty');

	if(playButton) {
		playButton.removeEventListener('click', onPlayButtonClicked);
	}

	logitsResult.classList.add('empty');
	resetButton.classList.add('hidden');
	clearTimer();
	resultMessage.innerHTML = '';
	logitsResult.innerHTML = '';
	resultList.innerHTML = '';
	waveform.clearRender();
	spectrogram.clearRender();

	createAudioContext(mediaStream);
	// input = null;
	// audiofile = null;
	// audioBlob = null;
}



function startRecording() {
	recordingIsOn = true;
	mediaRecorder.start();
	waveform.startRender();
	spectrogram.startRender();
	spectrum.startRender();
	console.log('mediaRecorder.state', mediaRecorder.state);
	recordButton.classList.add('recording');
	
	display.innerHTML = maxTimerInSec;
	timer = setInterval(runTimer, 1000);
}

function stopRecording() {
	recordingIsOn = false;
	recordBufferFilled = true;
	mediaRecorder.stop();
	waveform.stopRender();
	spectrogram.stopRender();
	spectrum.stopRender();

	clearTimer();
	// rest happens in onStopRecording()

	console.log('mediaRecorder.state', mediaRecorder.state);
}

function onStopRecording(e) {
	// console.log('stopped recording, preparing blob...');

	recordButton.classList.remove('recording');
	recordButton.disabled = true;
	recordButton.classList.add('disabled');
	resetButton.classList.remove('hidden');
	// spectrum.stopRender();

	systemMessage.innerHTML = 'Sending data...';
	resultMessageBox.classList.add('sending-data');

	audioBlob = new Blob(chunks, { 'type' : 'audio/ogg; codecs=opus' });
	chunks = [];

	// var file = getAudioFileFromBlob(audioBlob);
	sendAudioFileToServer(audioBlob);


// LOCALHOST- TEST
// var response = {
//   "success": true,
//   "text": "guten tag wie geht es ihnen",
//   "logits": "gutteenn   tagg  eewi ggett  ss  ihnnneeenn",
//   "decoder_scores": [
//     {
//       "score": 50.2106323242,
//       "text": "guten tag wie geht es ihnen"
//     },
//     {
//       "score": 65.8055038452,
//       "text": "guten tag wie geht es ihnen "
//     },
//     {
//       "score": 60.0631103516,
//       "text": "guten tag wie geht es denen"
//     },
//     {
//       "score": 58.5398483276,
//       "text": "guten tag wie geht es deinen"
//     },
//     {
//       "score": 56.0203933716,
//       "text": "guten tag er wie geht es ihnen"
//     }
//   ]
// }
// onReceiveServerResponse(response);
// LOCALHOST- TEST // END

}



function onReceiveServerResponse(response) {
	console.log('onReceiveServerResponse', response);


	if( response != undefined && response.success) {
		addResultContent(response)
	}
	else if ( response != undefined && !response.success) {
		systemMessage.innerHTML = 'Fehler:';
		resultMessage.innerHTML = response.error;
	}
	else {
		systemMessage.innerHTML = 'Problem:';
		resultMessage.innerHTML = 'Es scheint ein Problem mit der Serververbindung zu bestehen. Bitte versuchen Sie es etwas später erneut.';
	}
	resultMessageBox.classList.add('morphed');
	resultMessageBox.classList.remove('sending-data');
}

function addResultContent(response) {
	resultList.classList.remove('empty');
	logitsResult.classList.remove('empty');
	systemMessage.innerHTML = response.logits; // 'Resultat:';
	resultMessage.innerHTML = response.text;


	var waveFormImage = waveFormCanvas.toDataURL('image/png');

	logitsResult.innerHTML = '<div id="audio-content"><span id="icon-play" class="icon-play"></span><img src="' + waveFormImage + '" class="waveform-image"/></div>'; //response.logits;
	var resultListContent = response.decoder_scores;


	playButton = document.getElementById('icon-play');
	playButton.addEventListener('click', onPlayButtonClicked);

	// resultListContent.sort(function(a, b) {
	//     return parseFloat(b.score) - parseFloat(a.score);
	// });

	resultListContent.forEach(function(item, indx) {
		var newcontent = '<div class="possible-result decoder-' + indx + '"><span>' + parseFloat(item.score).toFixed(2) + '</span> '  + item.text + '</div>';
		setTimeout(() => {
			resultList.innerHTML += newcontent;
		}, (indx-1)*100);
	});

	waveform.clearRender();

}

function onPlayButtonClicked(e) {
	console.log('onPlayButtonClicked');
	playAudioBuffer();
}

function getAudioFileFromBlob(audioblob) {
	return new Audio( URL.createObjectURL(audioblob) );
}

function playAudioBuffer() {
	// console.log('play audiobuffer', audioBlob, audiofile)
    const audioUrl = URL.createObjectURL(audioBlob);
    if (audiofile) { audiofile.pause(); }
    audiofile = new Audio(audioUrl);
	audiofile.play();
	// if (spectrum) {
	// 	spectrum.startRender();
	// 	// spectrum.stopRender();
	// }

	// TODO: send audio as stream to spectrum rendering
	// ...
}

function createDownloadLink(blob, encoding) { 
	console.log('createDownloadLink');

	// var url = URL.createObjectURL(blob);
 //    var au = document.createElement('audio');
 //    var li = document.createElement('li');
 //    var link = document.createElement('a');
    
 //    au.controls = true;
 //    au.src = url;
 //    link.href = url;
 //    var fileName = new Date().toISOString();
 //    link.download = fileName + '.' + encoding;
 //    link.innerHTML = link.download;
}

function sendAudioFileToServer(fileOrBlob) {
	// var oReq = new XMLHttpRequest();
	// oReq.open('POST', serverURL, true);
	// oReq.onload = function (oEvent) {
	//   // Uploaded.
	//   console.log('Recorded File was uploaded!', oEvent);
	//   onReceiveServerResponse(oEvent);
	// };
	// oReq.send(fileOrBlob);


	var reader = new FileReader();
	var base64Data = reader.onloadend = function() {
		
		// appends none-base64 characters to the front of the string ??
		// better: var base64 = dataUrl.split(',')[1];
		// console.log( reader.result.substr(reader.result.indexOf(',')+1) ); 
		
		var jsonObj = {
			 	'config': {
			    	'encoding': 'OGG',
			    	'languageCode': 'de',
			    	'enableWordTimeOffsets': false,
			    	'enableWordConfidence': false,
			  },
			  	'audio': {
			        'uri': reader.result
			   }
			};

			var xmlhttp = new XMLHttpRequest();
			xmlhttp.open('POST', serverURL);
			xmlhttp.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
			xmlhttp.onreadystatechange = function(e) {
		        if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
		            // console.log('Recorded File was uploaded!', JSON.parse(xmlhttp.responseText));
		            // console.log('event', e);
				 	onReceiveServerResponse(JSON.parse(xmlhttp.responseText));
		        }
		    }
			// xmlhttp.onload = function (xmlhttp.response) {
			//   // Uploaded.
			//   console.log('Recorded File was uploaded!', oEvent);
			//   onReceiveServerResponse(xmlhttp.response);
			// };
			xmlhttp.send(JSON.stringify(jsonObj));
	}
	reader.readAsDataURL(fileOrBlob);

}

// BYTE CHUNKS HOCHLADEN
// function sendArrayBuffer() {
//   var xhr = new XMLHttpRequest();
//   xhr.open('POST', '/server', true);
//   xhr.onload = function(e) { ... };

//   var uInt8Array = new Uint8Array([1, 2, 3]);

//   xhr.send(uInt8Array.buffer);
// }

function setKeyboardShortcuts() {

    document.onkeyup = function(e) {
        e.preventDefault();

        // if (e.key !== e.altKey) {

        if (e.key == 'Escape') {
        	if (recordingIsOn) {
        		stopRecording();
        	}
        	onResetButtonClicked();
        }
        if (e.key === ' ' || e.key === 'Spacebar') {
        	if (!recordButton.classList.contains('disabled')) {
        		if (!recordingIsOn) {
        		startRecording();
	        	}
	        	else if (recordingIsOn) {
	        		stopRecording();
	        	}
	        }
        }
        // }
        // else if ...

    }
}

function createAudioContext(stream) {
	// visuals
	console.log('stream', stream);
	audioContext = new AudioContext;
	var source = audioContext.createMediaStreamSource(stream);
	// var analyser = audioContext.createAnalyser();
	// analyser.fftSize = 2048;
	// var bufferLength = analyser.frequencyBinCount;
	// var dataArray = new Uint8Array(bufferLength);
	// source.connect(analyser);


	spectrum = new Spectrum(audioContext, source);
	spectrum.initRender();

	waveform = new Waveform(audioContext, source);

	spectrogram = new Spectrogram(audioContext, source);

	return source;
}

window.addEventListener('load', function () {
 	startApp();
});

function startApp() {
	console.log('init');
	if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
		navigator.mediaDevices.getUserMedia({ audio: true/*, video: false */}).then(function(stream) {
		    console.log('getUserMedia() success, stream created, initializing Recorder.js ...', stream); 
		    
			mediaRecorder = new MediaRecorder(stream, {audioBitsPerSecond : 128000});
			recordButton.disabled = false;

			mediaRecorder.ondataavailable = function(e) {
				chunks.push(e.data);
			}

			mediaRecorder.onstop = function(e) {
				onStopRecording(e);
			}
			
			mediaStream = stream;
			createAudioContext(stream);
			setKeyboardShortcuts();

		}).catch(function(err) {
		    console.log('CATCHED err:', err);
		    recordButton.disabled = true;
		    systemMessage.innerHTML = err; 
			resultMessage.innerHTML = 'Your browser does not support the audio recording feature! Please try again using another browser.';
			resultMessageBox.classList.add('morphed');
			resultMessageBox.classList.add('sending-data');
		});

	}
	else {
		console.error('ERROR: getUserMedia NOTsupported!');
		// TODO: show error message that browser is outdated and does not support audio recording
		// ...
	}
	
}