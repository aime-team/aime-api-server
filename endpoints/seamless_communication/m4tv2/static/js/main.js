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

let audioOutputElement = new Audio();
var audioInputBlob;
let mediaRecorder;
let audioChunks = [];

modelAPI = new ModelAPI('sc_m4tv2');


function downloadHandler() {
	const blob = new Blob([base64ToArrayBuffer(audioOutputElement.src)], { type: 'audio/wav' });
	const url = URL.createObjectURL(blob);

	const a = document.createElement('a');
	a.href = url;
	a.download = 'audio.wav';
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

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };
            mediaRecorder.onstop = () => {
                audioInputBlob = new Blob(audioChunks, { type: 'audio/wav' });
				document.getElementById('audioPlayerInput').src = URL.createObjectURL(audioInputBlob);
            };

            mediaRecorder.start();
            document.getElementById('startRecordingButton').disabled = true;
            document.getElementById('stopRecordingButton').disabled = false;
        })
        .catch(error => console.error('Error accessing microphone:', error));
}

function stopRecording() {
    if (mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        document.getElementById('startRecordingButton').disabled = false;
        document.getElementById('stopRecordingButton').disabled = true;
    }
}

function downloadAudio(blob) {
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'audio_recording.wav';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}



function populateDropdown(dropdownId) {
	var dropdown = document.getElementById(dropdownId);

	languages.forEach((language) => {
		const option = document.createElement('option');
		option.value = language.code;
		option.text = language.name;
		dropdown.add(option);
	});
}


function onSendAPIRequest() {
	disableSendButton();
    addSpinner();
	params = new Object();
	
	params.src_lang = document.getElementById('srcLang').value;
	params.tgt_lang = document.getElementById('tgtLang').value;

	const textInput = document.getElementById('textInput').value;

	params.generate_audio = document.getElementById('generateAudio').checked;
	if (audioInputBlob) {
		const reader = new FileReader();
		reader.onload = function (e) {
			const base64Audio = e.target.result
			params.audio_input = base64Audio;
			modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback);
		};

		reader.readAsDataURL(audioInputBlob);

	}
	else if (textInput) {
		params.text_input = textInput;
		modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback);
	}
	else {
		alert('Please select an audio file or give text input.');
	}
	
}

function onResultCallback(data) {
	enableSendButton();
    removeSpinner();
	console.log(data.audio_output)
	document.getElementById('textOutput').textContent = data.text_output;


	if (data.audio_output) {

		infoBox = document.getElementById('infoBox');
		
		if (data["error"]) {
			infoBox.textContent = data.error;
		}
		else {
			infoBox.textContent = 'Total job duration: ' + data.total_duration + 's' + '\nCompute duration: ' + data.compute_duration + 's';
		}
		if (data.auth) {
			infoBox.textContent += '\nWorker: ' + data.auth;
		}
		if (data.worker_interface_version) {
			infoBox.textContent += '\nAPI Worker Interface version: ' + data.worker_interface_version;
		}
		infoBox.style.height = 'auto';

		audioOutputElement.src = data.audio_output;
    	document.getElementById('audioPlayerOutput').src = data.audio_output;
		document.getElementById('audioOutputContainer').style.display = 'block';

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
    document.getElementById('progress_bar').value = progress;
    document.getElementById('progress_label').innerText = progress+'%';
}

function setupAudioPlayerInput() {
	const audioPlayerInput = document.getElementById('audioPlayerInput');
	const audioUpload = document.getElementById('audioUpload');

	audioUpload.addEventListener('change', function (event) {
	  const file = event.target.files[0];

	  if (file) {
		const objectUrl = URL.createObjectURL(file);
		audioPlayerInput.src = objectUrl;
		audioInputBlob = file
	  }
	});
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

function swapSizeValues() {
    var heightInput = document.getElementById('height_range');
    var widthInput = document.getElementById('width_range');
    var tmpValue = heightInput.value;
    heightInput.value = widthInput.value;
    widthInput.value = tmpValue;
}

function initializeSizeSwapButton() {
    var swapButton = document.createElement('div');
    swapButton.className = 'w-1/12 swap-button mx-auto my-auto pt-6 hover:cursor-pointer flex items-center justify-center';
    swapButton.innerHTML = `
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"
             xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"></path>
    `;
    swapButton.addEventListener('click', swapSizeValues);
    
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

	document.getElementById('audioOutputContainer').style.display = 'none'

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
                    'aime_orange': '#F6BE5C',
                    'aime_green': '#CBE4C9'
            }
        },
        //   container: {
        //     padding: '2rem',
        //   },
        }
    }
    hljs.highlightAll();



    document.addEventListener('keydown', function(event) {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
            const button = document.getElementById('sendButton');
            if (!button.disabled) {
                event.preventDefault();
                onButtonClick();
            }
        }
      });

    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
        const tabName = button.getAttribute('data-tab');

        tabButtons.forEach(tabButton => {
            tabButton.classList.remove('active');
        });
        tabContents.forEach(tabContent => {
            tabContent.classList.add('hidden');
        });

        button.classList.add('active');
        document.getElementById(tabName).classList.remove('hidden');
        });
    });

	

	populateDropdown('srcLang');
	document.getElementById('srcLang').value = 'eng';

	populateDropdown('tgtLang');
	document.getElementById('tgtLang').value = 'deu';
    initializeSizeSwapButton();
    refreshRangeInputLayout();
    modelAPI.doAPILogin();
	setupAudioPlayerInput();

});

