// Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
//
// This software may be used and distributed according to the terms of the MIT LICENSE

const API_USER = 'aime'
const API_KEY = '6a17e2a5-b706-03cb-1a32-94b4a1df67da'

const languages = [
    { code: 'none', name: 'Auto (perform language detection)' },
	{ code: 'af', name: 'Afrikaans' },
	{ code: 'am', name: 'Amharic' },
	{ code: 'ar', name: 'Arabic' },
	{ code: 'as', name: 'Assamese' },
	{ code: 'az', name: 'Azerbaijani' },
	{ code: 'ba', name: 'Bashkir' },
	{ code: 'be', name: 'Belarusian' },
	{ code: 'bg', name: 'Bulgarian' },
	{ code: 'bn', name: 'Bengali' },
	{ code: 'bo', name: 'Tibetan' },
	{ code: 'br', name: 'Breton' },
	{ code: 'bs', name: 'Bosnian' },
	{ code: 'ca', name: 'Catalan' },
	{ code: 'cs', name: 'Czech' },
	{ code: 'cy', name: 'Welsh' },
	{ code: 'da', name: 'Danish' },
	{ code: 'de', name: 'German' },
	{ code: 'el', name: 'Greek' },
	{ code: 'en', name: 'English' },
	{ code: 'es', name: 'Spanish' },
	{ code: 'et', name: 'Estonian' },
	{ code: 'eu', name: 'Basque' },
	{ code: 'fa', name: 'Persian' },
	{ code: 'fi', name: 'Finnish' },
	{ code: 'fo', name: 'Faroese' },
	{ code: 'fr', name: 'French' },
	{ code: 'gl', name: 'Galician' },
	{ code: 'gu', name: 'Gujarati' },
	{ code: 'ha', name: 'Hausa' },
	{ code: 'haw', name: 'Hawaiian' },
	{ code: 'he', name: 'Hebrew' },
	{ code: 'hi', name: 'Hindi' },
	{ code: 'hr', name: 'Croatian' },
	{ code: 'ht', name: 'Haitian Creole' },
	{ code: 'hu', name: 'Hungarian' },
	{ code: 'hy', name: 'Armenian' },
	{ code: 'id', name: 'Indonesian' },
	{ code: 'is', name: 'Icelandic' },
	{ code: 'it', name: 'Italian' },
	{ code: 'ja', name: 'Japanese' },
	{ code: 'jw', name: 'Javanese' },
	{ code: 'ka', name: 'Georgian' },
	{ code: 'kk', name: 'Kazakh' },
	{ code: 'km', name: 'Khmer' },
	{ code: 'kn', name: 'Kannada' },
	{ code: 'ko', name: 'Korean' },
	{ code: 'la', name: 'Latin' },
	{ code: 'lb', name: 'Luxembourgish' },
	{ code: 'ln', name: 'Lingala' },
	{ code: 'lo', name: 'Lao' },
	{ code: 'lt', name: 'Lithuanian' },
	{ code: 'lv', name: 'Latvian' },
	{ code: 'mg', name: 'Malagasy' },
	{ code: 'mi', name: 'Māori' },
	{ code: 'mk', name: 'Macedonian' },
	{ code: 'ml', name: 'Malayalam' },
	{ code: 'mn', name: 'Mongolian' },
	{ code: 'mr', name: 'Marathi' },
	{ code: 'ms', name: 'Malay' },
	{ code: 'mt', name: 'Maltese' },
	{ code: 'my', name: 'Burmese' },
	{ code: 'ne', name: 'Nepali' },
	{ code: 'nl', name: 'Dutch' },
	{ code: 'nn', name: 'Norwegian Nynorsk' },
	{ code: 'no', name: 'Norwegian' },
	{ code: 'oc', name: 'Occitan' },
	{ code: 'pa', name: 'Punjabi' },
	{ code: 'pl', name: 'Polish' },
	{ code: 'ps', name: 'Pashto' },
	{ code: 'pt', name: 'Portuguese' },
	{ code: 'ro', name: 'Romanian' },
	{ code: 'ru', name: 'Russian' },
	{ code: 'sa', name: 'Sanskrit' },
	{ code: 'sd', name: 'Sindhi' },
	{ code: 'si', name: 'Sinhala' },
	{ code: 'sk', name: 'Slovak' },
	{ code: 'sl', name: 'Slovenian' },
	{ code: 'sn', name: 'Shona' },
	{ code: 'so', name: 'Somali' },
	{ code: 'sq', name: 'Albanian' },
	{ code: 'sr', name: 'Serbian' },
	{ code: 'su', name: 'Sundanese' },
	{ code: 'sv', name: 'Swedish' },
	{ code: 'sw', name: 'Swahili' },
	{ code: 'ta', name: 'Tamil' },
	{ code: 'te', name: 'Telugu' },
	{ code: 'tg', name: 'Tajik' },
	{ code: 'th', name: 'Thai' },
	{ code: 'tk', name: 'Turkmen' },
	{ code: 'tl', name: 'Tagalog' },
	{ code: 'tr', name: 'Turkish' },
	{ code: 'tt', name: 'Tatar' },
	{ code: 'uk', name: 'Ukrainian' },
	{ code: 'ur', name: 'Urdu' },
	{ code: 'uz', name: 'Uzbek' },
	{ code: 'vi', name: 'Vietnamese' },
	{ code: 'yi', name: 'Yiddish' },
	{ code: 'yo', name: 'Yoruba' },
	{ code: 'zh', name: 'Chinese (Simplified)' },
	{ code: 'yue', name: 'Cantonese' }
];

const subs = [
    { code: 'srt', name: 'srt' },
	{ code: 'vtt', name: 'vtt' },
	{ code: 'txt', name: 'txt' },
	{ code: 'tsv', name: 'tsv' },
	{ code: 'json', name: 'json' },
	{ code: 'aud', name: 'aud' },
];

let readyToSendRequest = true;
let audioOutputElement = new Audio();
var audioInputBlob;
let mediaRecorder;
let audioChunks = [];
let timerInterval;
let currentSubtitleIndex = 0;
let subtitles = [];

const modelAPI = new ModelAPI('whisper_x', API_USER, API_KEY);

function onSendAPIRequest() {
    const audioTabButton = document.getElementById('tab_button_audio_input');

    let params = {};
    params.src_lang = document.getElementById('srcLang').value;
    params.subFile = document.getElementById('subFile').value;
    const chunkSizeInput = document.getElementById('chunk_size_slider');
    params.chunk_size = parseInt(chunkSizeInput.value);

    if (audioTabButton.classList.contains('active') && audioInputBlob) {
        const reader = new FileReader();
        
        reader.onload = function (e) {
            const base64Audio = e.target.result;
            params.audio_input = base64Audio;

            if (!params.audio_input) {
                console.error("Missing required parameters:", params);
                alert("Please ensure all required fields are filled in.");
                return;
            }


            console.log("Sending API request with params:", params);
            modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback)
                    .catch((error) => {
                        removeSpinner();
                        enableSendButton();
                        console.error("API request failed:", error);
            });
        };
        reader.readAsDataURL(audioInputBlob);
    } else {
        alert('Please upload/record an audio file or provide text input.');
    }
}

function onResultCallback(data) {
    const infoBox = document.getElementById('infoBox');
    const mediaPlayer = document.getElementById('mediaPlayerOutput');
    const textOutput = document.getElementById('textOutput');
    const downloadLinkContainer = document.getElementById('downloadLinkContainer');
    const subtitleTrack = document.getElementById('mediaSubtitles');
    const subtitleText = document.getElementById('subtitleText');
    const subtitlePlayer = document.getElementById('subtitlePlayer');

    if (data.error) {
        if (data.error.includes('Client session authentication key not registered in API Server')) {
            modelAPI.doAPILogin(() => onSendAPIRequest(), function (error) {
                infoBox.textContent = 'Login Error: ' + error + '\n';
                enableSendButton();
                removeSpinner();
            });
        } else {
            infoBox.textContent = 'Error: ' + data.error + '\n';
            enableSendButton();
            removeSpinner();
        }
    } else {
        enableSendButton();
        removeSpinner();

        console.log(data);
        textOutput.textContent = data.result || "No text output.";
        infoBox.textContent = 'Total job duration: ' + data.total_duration + 's\nCompute duration: ' + data.compute_duration + ' s';

        if (data.model_name) infoBox.textContent += '\nModel name: ' + data.model_name;
        if (data.task) infoBox.textContent += '\nTask: ' + data.task;
        if (data.auth) infoBox.textContent += '\nWorker: ' + data.auth;
        if (data.worker_interface_version) infoBox.textContent += '\nAPI Worker Interface version: ' + data.worker_interface_version;

        adjustTextareasHeight();

        if (data.align_result) {
            const alignedData = JSON.parse(data.align_result);
            const vttContent = generateVTT(alignedData);

            const blob = new Blob([vttContent], { type: 'text/vtt' });
            const url = URL.createObjectURL(blob);

            subtitleTrack.src = url;

            loadSubtitles(alignedData);

            
            const downloadButton = document.getElementById('downloadButton');
            downloadButton.onclick = () => {
                createVTTFile(vttContent);
            };

            // Optionally, show the download button if hidden
            downloadButton.classList.remove('hidden');
        }
    }
}

function onProgressCallback(progress_info, progress_data) {
    const progress = progress_info.progress;
    const queue_position = progress_info.queue_position;
    const estimate = progress_info.estimate;
    const num_workers_online = progress_info.num_workers_online;

    document.getElementById('tasks_to_wait_for').innerText = ' | Queue Position: ' + queue_position;
    document.getElementById('estimate').innerText = ' | Estimate time: ' + estimate;
    document.getElementById('num_workers_online').innerText = ' | Workers online: ' + num_workers_online;
    document.getElementById('progress_label').innerText = progress+'%';
}

function syncSubtitles() {
    let currentTime = document.getElementById('mediaPlayerOutput').currentTime;
    const subtitleText = document.getElementById('subtitleText');
    const subtitlePlayer = document.getElementById('subtitlePlayer');


    let currentSentence = subtitles.find(sentence => 
        currentTime >= sentence.start && currentTime <= sentence.end
    );

    if (currentSentence) {
        subtitleText.textContent = currentSentence.text.trim();
        let highlightedText = currentSentence.words.map(word => {
            if (currentTime >= word.start && currentTime <= word.end) {
                return `<span class="highlight">${word.text}</span>`;  // Highlight current word
            }
            return word.text;  // Regular word
        }).join(" ");
        
        subtitleText.innerHTML = highlightedText;  // Set the updated HTML with highlighted word
        subtitlePlayer.classList.remove('hidden');
    } else {
        subtitlePlayer.classList.add('hidden');  // Hide subtitles if no matching sentence
    }
}

function loadSubtitles(alignedData) {
    subtitles = [];

    alignedData.segments.forEach(segment => {
        let sentence = {
            text: "",
            words: [],
            start: segment.start,
            end: segment.end,
        };

        segment.words.forEach(word => {
            sentence.text += word.word + " ";
            sentence.words.push({
                start: word.start,
                end: word.end,
                text: word.word
            });
        });

        subtitles.push(sentence);
    });
    setInterval(syncSubtitles, 50);
}

function generateVTT(alignedData) {
    let vttContent = "WEBVTT\n\n";

    alignedData.segments.forEach(segment => {
        segment.words.forEach(word => {
            const startTime = formatTime(word.start);
            const endTime = formatTime(word.end);
            vttContent += `${startTime} --> ${endTime}\n`;
            vttContent += `${word.word}\n\n`;
        });
    });

    return vttContent;
}

function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) {
        console.error('Invalid time value:', seconds);
        return '00:00:00.000';
    }

    const date = new Date(0);
    date.setSeconds(seconds);
    return date.toISOString().substr(11, 8) + '.' + Math.round((seconds % 1) * 1000).toString().padStart(3, '0');
}

function createVTTFile(vttContent) {
    const blob = new Blob([vttContent], { type: 'text/vtt' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'subtitles.vtt';
    link.click();
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

function clearSubtitleFile() {
    const subtitleTrack = document.getElementById('mediaSubtitles');
    const subtitleText = document.getElementById('subtitleText');
    const subtitlePlayer = document.getElementById('subtitlePlayer');
    const downloadButton = document.getElementById('downloadButton');

    subtitleTrack.src = '';
    subtitlePlayer.classList.add('hidden');
    subtitleText.textContent = '';
    downloadButton.classList.add('hidden');
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
    document.getElementById('srcLang').value = 'none';

    subs.forEach((sub) => {
        for (const drpdwn of document.getElementsByClassName('subselector')){
            const option = document.createElement('option');
            option.value = sub.code;
            option.text = sub.name;
            drpdwn.add(option);
         }
	});
    document.getElementById('subFile').value = 'vtt';
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
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
        recordButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
            </svg>
        `;
    };

    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    } else {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {

                removeMediaPlayerIfAny();

                let dropzoneContentEl = document.getElementById('dropzone-text');
                const initialDropzoneContent = dropzoneContentEl.innerHTML;

                let recordedSeconds = 0;
                const maxRecordingTime = 180; // 3 minutes
                const updateTimer = () => {
                    recordedSeconds += 1;
                    const minutes = Math.floor(recordedSeconds / 60);
                    const seconds = recordedSeconds % 60;

                    dropzoneContentEl.innerHTML = `
                        <p class="animate-blink text-aime_red">
                            Recording Audio... ${minutes}:${seconds >= 10 ? seconds : `0${seconds}`}
                        </p>
                        <p class="text-xs">Press Stop to end recording.</p>
                    `;

                    if (recordedSeconds >= maxRecordingTime) {
                        clearInterval(timerInterval);
                        stopRecording();
                    }
                };

                updateTimer();
                const timerInterval = setInterval(updateTimer, 1000);

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
                    createMediaPlayer(audioInputBlob);
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
        } else {
            console.error("getUserMedia not supported on your browser! In firefox and chrome getUserMedia only works via https!");
        }
    }
}


function getMimeType() {
    const userAgent = navigator.userAgent || ''; 
    const vendor = navigator.vendor || ''; 
    const platform = navigator.platform || ''; 

    const isChrome = /Chrome/.test(userAgent) && /Google Inc/.test(vendor);
    const isFirefox = /Firefox/.test(userAgent);
    const isEdge = /Edg/.test(userAgent) && /Microsoft/.test(vendor);
    const isSafari = /Safari/.test(userAgent) && !/Chrome/.test(userAgent);

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

function initializeDropZone() {
    var dropzone = document.createElement('div');
    dropzone.className = 'w100 rounded dropzone flex flex-col items-center justify-center p-7 bg-gray-100 border-2 border-dashed';
    dropzone.id = 'dropzone-content';
    dropzone.title = "Click here to select file to be uploaded...";
    dropzone.innerHTML = `
        <div id="dropzone-text" class="flex flex-col justify-center items-center">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-12 h-12 text-grey mb-3">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
            </svg>
            
            <p class="text-grey text-base font-bold">Drop audio file here.</p>
            <p class="text-grey text-sm font-semibold">(wav, mp3, or ogg)</p>
            <p class="text-grey text-xs mt-2 italic">Or press the record button.</p>
        </div>
        <input id="dropzone-input" class="mt-7 hidden" type="file" accept="audio/wav, audio/x-wav, audio/mp3, audio/mp4, video/mp4, audio/mpeg, video/mpeg, audio/vnd.wave, audio/ogg, video/ogg">
    `;

    document.getElementById('dropzone').insertAdjacentElement('afterbegin', dropzone);

    ['drag', 'dragstart', 'dragend', 'dragover', 'dragenter', 'dragleave', 'drop'].forEach(function(event) {
        dropzone.addEventListener(event, function(e) {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    dropzone.addEventListener('dragover', function() {  
        dropzone.classList.add('hover', 'shadow-inner'); 
    });

    dropzone.addEventListener('dragleave', function() { 
        dropzone.classList.remove('hover', 'shadow-inner'); 
    });

    dropzone.addEventListener('click', () => dropzone.querySelector('#dropzone-input').click());

    dropzone.addEventListener('drop', function(e) {
        this.classList.remove('hover', 'shadow-inner');
        const file = e.dataTransfer.files[0];
        if (file) {
            handleFileSelection(file);
        } else {
            console.error("No file was dropped.");
        }
    });

    dropzone.querySelector('#dropzone-input').addEventListener('change', function(e) {
        const file = this.files[0];
        if (file) {
            handleFileSelection(file);
        } else {
            console.error("No file was selected.");
        }
    });
}

function handleFileSelection(file) {
    const audioInput = document.getElementById('dropzone-input');
    const allowedFormats = audioInput.accept.split(',').map(item => item.trim());
    removeMediaPlayerIfAny();

    if (allowedFormats.includes(file.type)) {
        audioInputBlob = file;

        const mediaPlayer = document.getElementById('mediaPlayerOutput');
        mediaPlayer.src = URL.createObjectURL(file);
        mediaPlayer.classList.remove('hidden');
        createMediaPlayer(file);
    } else {
        alert('Sorry, only audio or video files of types ' + allowedFormats + ' are allowed!');
        audioInput.value = '';
    }
}

function removeMediaPlayerIfAny() {
    const mediaPlayer = document.getElementById('media-player');
    const fileInfo = document.getElementById('media-fileinfo');

    if (mediaPlayer) {
        mediaPlayer.remove();
    }
    if (fileInfo) {
        fileInfo.remove();
    }

    clearSubtitleFile();
    document.getElementById('textOutput').textContent = '';
    document.getElementById('infoBox').textContent = '';
    adjustTextareasHeight();
}


function createMediaPlayer(file) {
    console.log('file:', file);
    removeMediaPlayerIfAny();

    const type = file.type.startsWith('video') ? 'video' : 'audio';
    const mediaSrc = URL.createObjectURL(file);

    displayMedia(type, mediaSrc, file);
}


function displayMedia(type, src, file = null) {
    const mediaPlayer = document.getElementById('mediaPlayerOutput');
    const mediaOutputContainer = document.getElementById('mediaOutputContainer');
    const mediaControls = document.getElementById('media-controls');

    mediaPlayer.classList.remove('hidden');
    mediaPlayer.src = src;
    mediaPlayer.type = type;
    mediaPlayer.removeAttribute('disabled');

    let mediaInfoSection = document.getElementById('media-fileinfo-section');
    if (!mediaInfoSection) {
        mediaInfoSection = document.createElement('div');
        mediaInfoSection.id = 'media-fileinfo-section';
        mediaInfoSection.className = 'mt-4';
        mediaOutputContainer.appendChild(mediaInfoSection);
    }

    if (file) {
        mediaInfoSection.innerHTML = `
            <p class="text-sm text-gray-700 italic">
                ${file.name || 'Recorded Media'} | Size: ${formatFileSize(file.size)}
            </p>
        `;
    }
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
        // document.getElementById('textOutput').textContent = '';
        disableSendButton();
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

    initializeDropZone();
    populateDropdowns();

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

    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');
            const tabGroup = button.getAttribute('data-tab-group');
            

            tabButtons.forEach(tabButton => {
                if (tabButton.getAttribute('data-tab-group') === tabGroup) {
                    tabButton.classList.remove('active');
                }
            });
            tabContents.forEach(tabContent => {
                if (tabContent.getAttribute('data-tab-group') === tabGroup) {
                    tabContent.classList.add('hidden');
                }
            });

            button.classList.add('active');            
            document.getElementById(tabName).classList.remove('hidden');
        });
    });

    modelAPI.doAPILogin(function (data) {
        console.log('Key: ' + modelAPI.clientSessionAuthKey)
    },
    function (error) {
        infoBox.textContent = 'Login Error: ' + error + '\n';
    });
});
