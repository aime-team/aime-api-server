// Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
//
// This software may be used and distributed according to the terms of the MIT LICENSE

const API_USER = 'aime'
const API_KEY = '6a17e2a5b70603cb1a3294b4a1df67da'

const languages = [
	{ code: 'eng', name: 'English' },
];

const voices = [
	{ code: 'train_grace', name: 'Grace*' },
	{ code: 'train_daws', name: 'Daws*' },
	{ code: 'angie', name: 'Angie' },
    { code: 'emma', name: 'Emma' },
	{ code: 'freeman', name: 'Freeman' },
	{ code: 'jlaw', name: 'Jlaw' },
	{ code: 'deniro', name: 'Deniro' },
	{ code: 'train_atkins', name: 'Atkins*' },
	{ code: 'train_dreams', name: 'Dreams*' },
	{ code: 'train_empire', name: 'Empire*' },
    { code: 'train_kennard', name: 'Kennard*' },
	{ code: 'train_lescault', name: 'Lescault*' },
	{ code: 'train_mouse', name: 'Mouse*' }
];

const presets = [
	{ code: 'ultra_fast', name: 'Ultra Fast' },
	{ code: 'fast', name: 'Fast' },
	{ code: 'standard', name: 'Standard' },
    { code: 'high_quality', name: 'High Quality' },
];
let infoBox = document.getElementById('info_box');
let readyToSendRequest = true;
let audioOutputElement = new Audio();
let audioContext = new (window.AudioContext || window.webkitAudioContext)();
let bufferSources = [];
let textQueue = [];
let currentJobID;
let lastEndTime = audioContext.currentTime; // Track when the last buffer should end
let textInputLines;

let mediaRecorder;
let audioChunks = [];
let timerInterval;

const modelAPI = new ModelAPI('tts_tortoise', API_USER, API_KEY);

function onSendAPIRequest() {

    textInputLines = document.getElementById('textInput').value.split(';');
	let params = new Object();
	params.language = document.getElementById('srcLang').value;
	params.voice = document.getElementById('voice').value;
	params.preset = document.getElementById('preset').value;
    params.stream_chunk_size = parseInt(document.getElementById('streamChunkSize').value);
	params.temperature = parseFloat(document.getElementById('temperature').value);
	params.length_penalty = parseFloat(document.getElementById('lengthPenalty').value);
    params.repetition_penalty = parseFloat(document.getElementById('repetitionPenalty').value);
    params.top_p = parseFloat(document.getElementById('topP').value);
    params.max_mel_tokens = parseInt(document.getElementById('maxMelTokens').value);
    params.cvvp_amount = parseFloat(document.getElementById('cvvpAmount').value);


    params.text = textInputLines.shift();

    response = modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback, true)
    .catch((error) => {
        removeSpinner();
        enableSendButton();
    });
}

function onResultCallback(data) {
    
    if (data.error) {
        if (data.error.indexOf('Client session authentication key not registered in API Server') > -1) {
          modelAPI.doAPILogin( () => onSendAPIRequest(), function (error) {
            infoBox.textContent = 'Login Error: ' + error + '\n';
            enableSendButton();
            removeSpinner();
          });
        }
        else {
            infoBox.textContent = 'Error: ' + data.error + '\n';
            enableSendButton();
            removeSpinner();            
        }
    } else {
        enableSendButton();
        removeSpinner();

        infoBox.textContent = 'Total job duration: ' + data.total_duration + 's' + '\nCompute duration: ' + data.compute_duration + ' s';

        if (data.model_name) {              infoBox.textContent += '\nModel name: ' + data.model_name; }
        if (data.task) {                    infoBox.textContent += '\nTask: ' + data.task; }
        if (data.auth) {                    infoBox.textContent += '\nWorker: ' + data.auth; }
        if (data.worker_interface_version) { infoBox.textContent += '\nAPI Worker Interface version: ' + data.worker_interface_version; }
        
        adjustTextareasHeight();

    }
}

function onProgressCallback(progress_info, progress_data) {
    const progress = progress_info.progress;
    const queue_position = progress_info.queue_position;
    const estimate = progress_info.estimate;
    const num_workers_online = progress_info.num_workers_online;
    currentJobID = progress_info.job_id
    const new_text = textInputLines.shift();
    if (new_text && currentJobID) {
        progressParams = new Object();
        progressParams.text_input = new_text;
        modelAPI.append_progress_input_params(currentJobID, progressParams)
    }

    document.getElementById('progress_label').innerText = 'Generated audio chunks: ' + progress;
    document.getElementById('tasks_to_wait_for').innerText = ' | Queue Position: ' + queue_position;
    document.getElementById('estimate').innerText = ' | Estimate time: ' + estimate;
    document.getElementById('num_workers_online').innerText = ' | Workers online: ' + num_workers_online;
    if (progress_data?.text_output) {
        textQueue.push(progress_data.text_output);
        if (!document.getElementById('textOutput').textContent) {
            document.getElementById('textOutput').textContent = textQueue.shift();
        }
    }
    if (progress_data?.audio_output && !modelAPI.jobsCanceled[currentJobID]) {
        const audioChunkArrayBuffer = base64ToArrayBuffer(progress_data.audio_output);

        audioContext.decodeAudioData(audioChunkArrayBuffer, (audioBuffer) => {
            schedulePlayback(audioBuffer);
        });
    }
}



function schedulePlayback(audioBuffer) {
    const bufferSource = audioContext.createBufferSource();
    bufferSource.buffer = audioBuffer;
    bufferSource.connect(audioContext.destination);
    if (audioContext.state === 'suspended') {
        audioContext.resume();
    }
    const startTime = Math.max(audioContext.currentTime, lastEndTime); 
    bufferSource.start(startTime);
    lastEndTime = startTime + audioBuffer.duration;
    bufferSource.onended = () => {
        if (textQueue.length > 0) {
            document.getElementById('textOutput').textContent += textQueue.shift();
        }
        bufferSource?.disconnect();
    };
    bufferSources.push(bufferSource);
}

function base64ToArrayBuffer(base64) {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
}

function populateDropdowns() {
    languages.forEach((language) => {
        for (const drpdwn of document.getElementsByClassName('langselector')){
            const option = document.createElement('option');
            option.value = language.code;
            option.text = language.name;
            drpdwn.add(option);
         }
	});
    document.getElementById('srcLang').value = 'eng'; // better: get browser language ?

    voices.forEach((voice) => {
        for (const drpdwn of document.getElementsByClassName('voiceselector')){
            const option = document.createElement('option');
            option.value = voice.code;
            option.text = voice.name;
            drpdwn.add(option);
         }
	});
    document.getElementById('voice').value = 'train_grace';

    presets.forEach((preset) => {
        for (const drpdwn of document.getElementsByClassName('presetselector')){
            const option = document.createElement('option');
            option.value = preset.code;
            option.text = preset.name;
            drpdwn.add(option);
         }
	});
    document.getElementById('preset').value = 'ultra_fast';

}

function downloadHandler() {
	const blob = new Blob([base64ToArrayBuffer(audioOutputElement.src)], { type: 'audio/wav' });
	const url = URL.createObjectURL(blob);
    var unixTimestamp = Date.now();
	const a = document.createElement('a');
	a.href = url;
	a.download = 'translated_audio_output_' + document.getElementById('tgtLang').value + '_' + unixTimestamp.toString() + '.wav';
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}

function base64ToArrayBuffer(base64) {
	const binaryString = window.atob(base64.split(',')[1]);
	const len = binaryString.length;
	const bytes = new Uint8Array(len);

	for (let i = 0; i < len; i++) {
		bytes[i] = binaryString.charCodeAt(i);
	}

	return bytes.buffer;
}

async function startStopRecording() {
    const recordButton = document.getElementById('recordButton');
    const dropzoneContent = document.getElementById('dropzone-content');
    const dropzoneInput = document.getElementById('dropzone-input');

    const stopRecording = () => {
        mediaRecorder.stop();
        recordButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
            </svg>
        `;
    };

    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    }
    else {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {

                removeAudioPlayerIfAny();

                let dropzoneContentEl = document.getElementById('dropzone-text');
                const initialDropzoneContent = dropzoneContentEl.innerHTML;

                let remainingTime = 15;
                const updateTimer = () => {
                    dropzoneContentEl.innerHTML = `
                        <p class="animate-blink text-aime_red">Recording Audio... 0:${remainingTime >= 10 ? remainingTime : `0${remainingTime}`}</p>
                        <p class="text-xs">Press Stop to end recording.</p>
                    `;
                    if (remainingTime <= 0) {
                        clearInterval(timerInterval);
                        stopRecording();
                    }
                    remainingTime -= 1;
                };

                updateTimer();
                timerInterval = setInterval(updateTimer, 1000);

                audioChunks = [];
                const mimeType = getMimeType();
                mediaRecorder = new MediaRecorder(stream, { 'mimeType': mimeType });

                mediaRecorder.ondataavailable = event => {
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                    }
                };

                mediaRecorder.onstop = () => {
                    clearInterval(timerInterval);
                    audioInputBlob = new Blob(audioChunks, { 'type': mimeType });
                    createAudioPlayer(audioInputBlob);
                    recordButton.classList.remove('bg-red-500', 'recording');

                    dropzoneContentEl.innerHTML = initialDropzoneContent;

                    dropzoneContent.classList.remove('opacity-50', 'pointer-events-none');
                    dropzoneInput.disabled = false;
                    enableSendButton();
                };
                
                mediaRecorder.onerror = (event) => {
                    console.error(`error recording stream: ${event.error.name}`);
                };

                mediaRecorder.start();
                recordButton.classList.add('bg-red-500', 'recording');
                recordButton.classList.remove('border-dashed', 'focus:border-dashed');
                recordButton.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6">
                    <path fill-rule="evenodd" d="M4.5 7.5a3 3 0 0 1 3-3h9a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-9a3 3 0 0 1-3-3v-9Z" clip-rule="evenodd" />
                </svg>
                `;
                
                dropzoneContent.classList.add('opacity-50', 'pointer-events-none');
                dropzoneInput.disabled = true;
                disableSendButton();
            })
            .catch(error => console.error('Error accessing microphone:', error));
        }
        else {
            console.error("getUserMedia not supported on your browser! In firefox and chrome getUserMedia only works via https!");
        }
    }
}

// function formatTime(seconds) {
//     const hours = Math.floor(seconds / 3600);
//     const minutes = Math.floor((seconds % 3600) / 60);
//     const remainingSeconds = seconds % 60;

//     const formattedHours = hours.toString().padStart(2, '0');
//     const formattedMinutes = minutes.toString().padStart(2, '0');
//     const formattedSeconds = remainingSeconds.toString().padStart(2, '0');

//     return `${formattedHours}:${formattedMinutes}:${formattedSeconds}`;
// }

function getMimeType() {
    const isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
    const isFirefox = typeof InstallTrigger !== 'undefined';
    const isEdge = /Edg/.test(navigator.userAgent) && /Microsoft Corporation/.test(navigator.vendor);
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

    if (isChrome || isEdge) {
        return 'audio/webm';
    } else if (isFirefox) {
        return 'audio/ogg';
    } else if (isSafari) {
        return 'audio/mp4';
    } else {
        return 'audio/wav';
    }
}

function adjustTextareasHeight() {
    var textarea = document.getElementById('textOutput');
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';

    infoBox.style.height = 'auto';
    infoBox.style.height = infoBox.scrollHeight + 'px';
}

function updateWordCount() {
    var textarea = document.getElementById('textInput');
    var wordCount = document.getElementById('wordCount');
  
    var words = textarea.value.match(/\b\w+\b/g);
    var count = words ? words.length : 0;
    wordCount.textContent = count + (count === 1 ? ' word' : ' words') + ' (max_seq_len: 1024 subword tokens)';
  }

function addSpinner() {
    var spinner = document.createElement('div');
        spinner.id = 'process-spinner';
        spinner.className = 'animate-spin mr-2';
        spinner.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-aime_orange">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
        `;
        const button = document.getElementById('sendButton');
        if (button) {
            button.parentNode.insertBefore(spinner, button);
        }
}
function removeSpinner() {
    const spinner  = document.getElementById('process-spinner');
    if(spinner) {
        spinner.remove();
    }
}

function disableSendButton() {
    readyToSendRequest = false;
    const button = document.getElementById('sendButton');
    if (button) {
      button.disabled = true;
      button.classList.add('disabled:opacity-50');
      button.classList.add('disabled:cursor-not-allowed');
    }
}
function enableSendButton() {
    readyToSendRequest = true;
    const button = document.getElementById('sendButton');
    if (button) {
        button.disabled = false;
        button.classList.remove('disabled:opacity-50');
        button.classList.remove('disabled:cursor-not-allowed');
    }
}


function removeAudioPlayerIfAny() {
    var audioPlayerEl = document.getElementById('audio-player');
    var audioFileInfo = document.getElementById('audio-fileinfo');

    if (audioPlayerEl) {
        audioPlayerEl.parentNode.removeChild(audioPlayerEl);
        audioFileInfo.parentNode.removeChild(audioFileInfo);
    }
}

function createAudioPlayer(file) {
    removeAudioPlayerIfAny();

    var audioPlayer = document.createElement('audio');
    audioPlayer.id = 'audio-player';
    audioPlayer.className = 'flex-grow text-aime_darkblue hover:text-white font-bold rounded mt-5 w100';
    audioPlayer.setAttribute('controls', 'true');
    audioPlayer.textContent = 'Your browser does not support the audio element. The audio player can not be displayed, sorry...';

    var audioContainer = document.getElementById('tab_audio_input');
    audioContainer.appendChild(audioPlayer);

    audioPlayer.src = URL.createObjectURL(file);

    var audioFileInfo = document.getElementById('audio-fileinfo');
    audioFileInfo = document.createElement('p');
    audioFileInfo.id = 'audio-fileinfo';
    audioFileInfo.className = 'text-xs italic m-1 text-gray-700';
    file.name = `recorded_audio_${Date.now()}`;
    audioFileInfo.textContent = file.name + ' | Size: ' + formatFileSize(file.size);
    audioContainer.append(audioFileInfo);
}

function formatFileSize(size) {
    if (size < 1024) {
        return size + ' bytes';
    } else if (size < 1024 * 1024) {
        return (size / 1024).toFixed(2) + ' KB';
    } else {
        return (size / (1024 * 1024)).toFixed(2) + ' MB';
    }
}

function onButtonClick() {
    if(readyToSendRequest) {
        infoBox.textContent = 'Request sent.\nWaiting for response...';
        document.getElementById('textOutput').textContent = '';
        // disableSendButton();
        addSpinner();

        // set Tabs to output section
        const output_btn =  document.getElementById('tab_button_output');
        if(!output_btn.active) {
            output_btn.click();
        }

        // scroll output_section into view when on mobile
        if (window.innerWidth <= 768) {
            const outputElement = document.getElementById('output_section');
            if (outputElement) {
                outputElement.scrollIntoView({ behavior: 'smooth', block: "start" });
                window.scrollTo({ top: outputElement.offsetTop, left: 0, behavior: 'smooth' });
            }
        }

        onSendAPIRequest();
    }
}

function onCancelButtonClick() {
    removeSpinner()
    bufferSources.forEach(source => {
        source.stop(0); // Stop immediately
        source.disconnect();
    });
    bufferSources = []; // Clear the list
    modelAPI.cancelRequest(currentJobID)
}


function refreshRangeInputLayout() {
    const selectLabelElements = document.querySelectorAll('p.select-label');
    selectLabelElements.forEach((selectLabelElement) => {
        const inputElement = selectLabelElement.nextElementSibling;
        const labelElement = inputElement.nextElementSibling;
        if (
            inputElement && inputElement.tagName === 'INPUT' &&
            inputElement.type === 'range' &&
            labelElement && labelElement.tagName === 'LABEL'
        ) {
            const labelText = selectLabelElement.textContent.trim();
            const sliderId = inputElement.getAttribute('id'); // + '_range';
            const minAttributeValue = inputElement.getAttribute('min');
            const maxAttributeValue = inputElement.getAttribute('max');
            const stepAttributeValue = inputElement.getAttribute('step');
            const valueAttributeValue = inputElement.getAttribute('value');

            const template = `
              <div class="range-group mb-3">
                <label for="${sliderId}" class="select-label text-gray-700 text-sm font-bold">${labelText}</label>
                <div class="input-group flex items-center">
                  <input type="range" class="form-range slider flex-grow" id="${sliderId}" min="${minAttributeValue}" max="${maxAttributeValue}" step="${stepAttributeValue}" value="${valueAttributeValue}" oninput="document.getElementById('${sliderId}_value').value = this.value">
                  <div class="mx-2"></div>
                  <input type="number" class="form-input col-span-1 text-sm w-1/4" id="${sliderId}_value" min="${minAttributeValue}" max="${maxAttributeValue}" step="${stepAttributeValue}" value="${valueAttributeValue}" oninput="document.getElementById('${sliderId}').value = this.value">
                </div>
              </div>
            `;

            const newBlock = document.createElement('div');
            newBlock.innerHTML = template;

            labelElement.remove();
            inputElement.remove();
            selectLabelElement.replaceWith(newBlock);
        }
    });
}


function handleKeyPress(event) {
    if (event && event.keyCode === 13) {
        event.preventDefault();
        onButtonClick();
    }
 }

window.addEventListener('load', function() {
    // Styling with Tailwind CSS
    tailwind.config = {
        'theme': {
            'screens': {
                'xs': '475px',
                'sm': '640',
                'md': '768px',
                'lg': '1024px',
                'xl': '1280px',
                '2xl': '1536px'
            },
            'extend': {
                'colors': {
                    'aime_blue': '#4FBFD7',
                    'aime_darkblue': '#263743',
                    'aime_red': '#D55151',
                    'aime_orange': '#F6BE5C',
                    'aime_green': '#CBE4C9'
                },
                'animation': {
                    'blink': 'blink 4s infinite ease-in-out',
                },
                'keyframes': {
                    'blink': {
                    '0%, 50%, 100%': { 'opacity': 1 },
                    '25%, 75%': { 'opacity': 0.6 },
                    },
                },
            },
        //   container: {
        //     padding: '2rem',
        //   },
        }
    };
    hljs.highlightAll();

    populateDropdowns();
    refreshRangeInputLayout();
    updateWordCount();

    infoBox = document.getElementById('infoBox');
    
    document.addEventListener('keydown', function(event) {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
            const button = document.getElementById('sendButton');
            if (!button.disabled) {
                event.preventDefault();
                onButtonClick();
            }
        }
    });
    
    document.getElementById('scrollToTopBtn').addEventListener('click', function() {
        // document.body.scrollTop = 0; // For Safari
        // document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE, and Opera
        var textarea = document.getElementById('textInput');
        textarea.scrollIntoView({ behavior: 'smooth', block: "start" });
        window.scrollTo({ top: textarea.offsetTop, left: 0, behavior: 'smooth' });
        textarea.focus();
        textarea.select();
    });

    modelAPI.doAPILogin(function (data) {
        console.log('Key: ' + modelAPI.clientSessionAuthKey)
    },
    function (error) {
        infoBox.textContent = 'Login Error: ' + error + '\n';
    });
});
