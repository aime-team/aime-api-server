const languages = [
	{ code: 'arb', name: 'Modern Standard Arabic' },
	{ code: 'ben', name: 'Bengali' },
	{ code: 'cat', name: 'Catalan' },
	{ code: 'ces', name: 'Czech' },
	{ code: 'cmn', name: 'Mandarin Chinese' },
	{ code: 'cym', name: 'Welsh' },
	{ code: 'dan', name: 'Danish' },
	{ code: 'deu', name: 'German' },
	{ code: 'eng', name: 'English' },
	{ code: 'est', name: 'Estonian' },
	{ code: 'fin', name: 'Finnish' },
	{ code: 'fra', name: 'French' },
	{ code: 'hin', name: 'Hindi' },
	{ code: 'ind', name: 'Indonesian' },
	{ code: 'ita', name: 'Italian' },
	{ code: 'jpn', name: 'Japanese' },
	{ code: 'kor', name: 'Korean' },
	{ code: 'mlt', name: 'Maltese' },
	{ code: 'nld', name: 'Dutch' },
	{ code: 'pes', name: 'Western Persian' },
	{ code: 'pol', name: 'Polish' },
	{ code: 'por', name: 'Portuguese' },
	{ code: 'ron', name: 'Romanian' },
	{ code: 'rus', name: 'Russian' },
	{ code: 'slk', name: 'Slovak' },
	{ code: 'spa', name: 'Spanish' },
	{ code: 'swe', name: 'Swedish' },
	{ code: 'swh', name: 'Swahili' },
	{ code: 'tam', name: 'Tamil' },
	{ code: 'tel', name: 'Telugu' },
	{ code: 'tgl', name: 'Tagalog' },
	{ code: 'tha', name: 'Thai' },
	{ code: 'tur', name: 'Turkish' },
	{ code: 'ukr', name: 'Ukrainian' },
	{ code: 'urd', name: 'Urdu' },
	{ code: 'uzn', name: 'Northern Uzbek' },
	{ code: 'vie', name: 'Vietnamese' },
];

let readyToSendRequest = true;
let audioOutputElement = new Audio();
var audioInputBlob;
let mediaRecorder;
let audioChunks = [];
let timerInterval;

const modelAPI = new ModelAPI('sc_m4tv2');

function onSendAPIRequest() {

    const textInput = document.getElementById('textInput').value;
    const textTabButton= document.getElementById('tab_button_text_input');
    const audioTabButton= document.getElementById('tab_button_audio_input');
    // let infoBox = document.getElementById('infoBox');

	let params = new Object();
	params.src_lang = document.getElementById('srcLang').value;
	params.tgt_lang = document.getElementById('tgtLang').value;
	params.generate_audio = document.getElementById('generateAudio').checked;

	if (audioTabButton.classList.contains('active') && audioInputBlob) {
        const reader = new FileReader();
        reader.onload = function (e) {
            const base64Audio = e.target.result;
            params.audio_input = base64Audio;
            modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback)
                .catch((error) => {
                    removeSpinner();
                    enableSendButton();
                });
        };

        reader.readAsDataURL(audioInputBlob);
	}
	else if (textTabButton.classList.contains('active') && textInput) {
        try {
            params.text_input = textInput;
            modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback)
            .catch((error) => {
                removeSpinner();
                enableSendButton();
            });
        } catch (error) {
            console.error('Problem while sending API request.');
        }
	}
	else {
		alert('Please upload/record an audio file or give text input.');
	}	
}

function onResultCallback(data) {
	enableSendButton();
    removeSpinner();
    readyToSendRequest = true;
	document.getElementById('textOutput').textContent = data.text_output;
    
    let infoBox = document.getElementById('infoBox');

    if (data["error"]) {
        infoBox.textContent = 'Error: ' + data.error;
    } else {
        infoBox.textContent = 'Total job duration: ' + data.total_duration + 's' + '\nCompute duration: ' + data.compute_duration + 's';
    }

    if (data.model_name) {
        infoBox.textContent += '\nModel name: ' + data.model_name;
    }
    
    if (data.task) {
        infoBox.textContent += '\nTask: ' + data.task;
    }
    
    if (data.auth) {
        infoBox.textContent += '\nWorker: ' + data.auth;
    }
    
    if (data.worker_interface_version) {
        infoBox.textContent += '\nAPI Worker Interface version: ' + data.worker_interface_version;
    }
    
    adjustTextareasHeight();

    let audioOutputContainer = document.getElementById('audioOutputContainer');
    let audioOutput = document.getElementById('audioPlayerOutput');
    audioOutputContainer.classList.remove('hidden');
	
    if (data.audio_output) {
		audioOutputElement.src = data.audio_output;
    	audioOutput.src = data.audio_output;
        audioOutput.play();
	} else {
        audioOutputElement.src = '';
    	audioOutput.src = '';
        audioOutputContainer.classList.add('hidden');
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
	document.getElementById('tgtLang').value = 'deu';
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

    let infoBox = document.getElementById('infoBox');
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
    const button = document.getElementById('sendButton');
    if (button) {
      button.disabled = true;
      button.classList.add('disabled:opacity-50');
      button.classList.add('disabled:cursor-not-allowed');
    }
}
function enableSendButton() {
    const button = document.getElementById('sendButton');
    if (button) {
        button.disabled = false;
        button.classList.remove('disabled:opacity-50');
        button.classList.remove('disabled:cursor-not-allowed');
    }
}

function swapLanguageValues() {
    var srcLang = document.getElementById('srcLang');
    var tgtLang = document.getElementById('tgtLang');
    var tmpValue = srcLang.value;
    srcLang.value = tgtLang.value;
    tgtLang.value = tmpValue;
}

function initializeLanguageSwapButton() {
    var swapButton = document.createElement('div');
    swapButton.className = 'w-1/12 swap-button mx-auto my-auto pt-3 hover:cursor-pointer flex items-center justify-center';
    swapButton.innerHTML = `
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"
             xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"></path>
    `;
    swapButton.addEventListener('click', swapLanguageValues);

    var flexContainer = document.getElementById('language-selector');
    flexContainer.insertBefore(swapButton, flexContainer.children[1]);
}

function initializeDropZone() {
    var dropzone = document.createElement('div');
    dropzone.className = 'w100 rounded dropzone flex flex-col items-center justify-center p-7 bg-gray-100 border-2 border-dashed';
    dropzone.id = 'dropzone-content';
    dropzone.title = "Klick here to select file to be uploaded...";
    dropzone.innerHTML = `
        <div id="dropzone-text" class="flex flex-col justify-center items-center">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-12 h-12 text-grey mb-3">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
            </svg>
            
            <p class="text-grey text-base font-bold">Drop audio file here.</p>
            <p class="text-grey text-sm font-semibold">(wav, mp3 or ogg)</p>
            <p class="text-grey text-xs mt-2 italic">Or press the record button.</p>
        </div>
        <input id="dropzone-input" class="mt-7 hidden" type="file" accept="audio/wav, audio/x-wav, audio/mp3, audio/mp4, video/mp4, audio/mpeg, audio/vnd.wave, audio/ogg, video/ogg, audio/ogg; codecs=vorbis">
    `; // Audio MIME Types to handle: audio/mp3, audio/mpeg, audio/wav, audio/x-wav, audio/aac, audio/ogg, audio/flac, audio/amr, audio/x-ms-wma
    document.getElementById('dropzone').insertAdjacentElement('afterbegin', dropzone);

    ['drag', 'dragstart', 'dragend', 'dragover', 'dragenter', 'dragleave', 'drop'].forEach(function(event) {
        dropzone.addEventListener(event, function(e) {
            e.preventDefault();
            e.stopPropagation();
        });
    });
    dropzone.addEventListener('dragover', function() {  dropzone.classList.add('hover', 'shadow-inner'); });  
    dropzone.addEventListener('dragleave', function() { dropzone.classList.remove('hover', 'shadow-inner'); });
    dropzone.addEventListener('click', () => dropzone.querySelector('#dropzone-input').click() );
  
    dropzone.addEventListener('drop', function(e) {
        this.classList.remove('hover', 'shadow-inner');
        var file = e.dataTransfer.files[0];
        handleFileSelection(file);
      }, false);

    dropzone.querySelector('#dropzone-input').addEventListener('change', function(e) {
        var file = this.files[0];
        handleFileSelection(file);
    });
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
    console.log('file', file);
    removeAudioPlayerIfAny();

    var audioPlayer = document.createElement('audio');
    audioPlayer.id = 'audio-player';
    audioPlayer.className = 'flex-grow text-aime_darkblue hover:text-white font-bold rounded mt-5 w100';
    audioPlayer.setAttribute('controls', 'true');
    audioPlayer.textContent = 'Your browser does not support the audio element. The audio player can not be displayed, sorry...';

    var audioContainer = document.getElementById('tab_audio_input');
    audioContainer.appendChild(audioPlayer);

    audioPlayer.src = URL.createObjectURL(file);
    console.log('src', audioPlayer.src);

    var audioFileInfo = document.getElementById('audio-fileinfo');
    audioFileInfo = document.createElement('p');
    audioFileInfo.id = 'audio-fileinfo';
    audioFileInfo.className = 'text-xs italic m-1 text-gray-700';
    file.name = `recorded_audio_${Date.now()}`;
    audioFileInfo.textContent = file.name + ' | Size: ' + formatFileSize(file.size);
    audioContainer.append(audioFileInfo);
}

function handleFileSelection(file) {
    const audioInput = document.getElementById('dropzone-input');
    var allowedFormats = audioInput.accept.split(',').map(function (item) { return item.trim(); });
    console.log(file.type)

    if (allowedFormats.includes(file.type)) {
        audioInputBlob = file;
        createAudioPlayer(file);
    } else {
        alert('Sorry, but only audio files of type ' + allowedFormats + ' are allowed!');
        audioInput.value = '';
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
        readyToSendRequest = false;

        let infoBox = document.getElementById('infoBox');
        infoBox.textContent = 'Request sent.\nWaiting for response...';
        document.getElementById('textOutput').textContent = '';
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

    populateDropdowns();
    initializeLanguageSwapButton();
    initializeDropZone();
    updateWordCount();
    
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

    modelAPI.doAPILogin();
});
