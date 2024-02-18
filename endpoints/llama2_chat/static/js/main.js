modelAPI = new ModelAPI('llama2_chat');

var inputContext = 'A dialog, where User interacts with an helpful, kind, obedient, honest and very reasonable assistant called Dave.\n';
let readyToSendRequest = true;
let chatboxContentEl;
let chatLogTextarea = document.getElementById('chat_log'); // TO BE REMOVED
let info_box = document.getElementById('info_box');
 
function onSendAPIRequest() {
	let chatInput = document.getElementById('chat_input');
    info_box.textContent = 'Request sent.\nWaiting for response...';

	let currentText = getChatboxContext();
	currentText += 'User: ' + chatInput.value + '\nDave:'; // vorher war ohne \n bei user
    console.log('currentText:'+ currentText);

	params = new Object();
	params.text = currentText;
	params.top_k = parseInt(document.getElementById('top_k_range').value);
	params.top_p = parseFloat(document.getElementById('top_p_range').value);
	params.temperature = parseFloat(document.getElementById('temperature_range').value);
	params.seed = parseInt(document.getElementById('seed').value);

    // TODO: aus aktuellem return-Text die chatblasen basteln
    // ...
    // chatboxContentEl. ...
    
    addChatboxBubble(chatInput.value, `Seed: ${params.seed} | TopK: ${params.top_k} | TopP: ${params.top_p} | Temp: ${params.temperature}`, true);
    addResponseBubble();
    chatboxContentEl.scrollTop = chatboxContentEl.scrollHeight;

    chatInput.value = '';
	modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback);
    console.log('sent:', params);
}

function onProgressCallback(progressInfo, progressData) {
	const queuePosition = progressInfo.queue_position;
	const estimate = progressInfo.estimate;
	const numWorkersOnline = progressInfo.num_workers_online;
	const progress = progressInfo.progress;
	
    refreshResponseBubble(null, `queuePosition: ${queuePosition} | estimate: ${estimate}`)

	if(progressData != null) {
        refreshResponseBubble(progressData.text, `answering... | progress: ${progress}`);
		chatboxContentEl.scrollTop = chatboxContentEl.scrollHeight;
	}

	document.getElementById('progress_label').innerText = 'Generated tokens: ' + progress;
    document.getElementById('tasks_to_wait_for').innerText = ' | Queue Position: ' + queuePosition;
	document.getElementById('estimate').innerText = ' | Estimate time: ' + estimate;
	document.getElementById('num_workers_online').innerText = ' | Workers online: ' + numWorkersOnline;
};

function onResultCallback(data) {
	enableSendButton();
    // removeSpinner();
    readyToSendRequest = true;

	infoBox = document.getElementById('info_box');
	if (data['error']) {
		infoBox.textContent = data.error;
	}
	else {
		console.log('result: ', data);
		if (data.seed) { 					infoBox.textContent = 'Seed: ' + data.seed + '\n'; }
		if (data.total_duration) { 			infoBox.textContent += 'Total job duration: ' + data.total_duration + 's' + '\n'; }
		if (data.compute_duration) { 		infoBox.textContent += 'Compute duration: ' + data.compute_duration + 's' + '\n'; }
		if (data.num_generated_tokens) { 	infoBox.textContent += 'Generated tokens: ' + data.num_generated_tokens + '\n'; }
		if (data.compute_duration && data.num_generated_tokens) {
											tokensPerSec = data.num_generated_tokens / data.compute_duration
											infoBox.textContent += 'Tokens per second: ' + tokensPerSec.toFixed(1) + '\n';
		}
		if (data.model_name) { 				infoBox.textContent += '\nModel name: ' + data.model_name +'\n'; }
	}
	if (data.auth) { 						infoBox.textContent += 'Worker: ' + data.auth + '\n'; }
	if (data.worker_interface_version) {
		var versionNo = data.worker_interface_version.match(/\d+\.\d+\.\d+/);
		if (versionNo) {					infoBox.textContent += 'Worker Interface version: ' + versionNo[0] + '\n'; }
	}
	if (data.ep_version != null) { 			infoBox.textContent += 'Endpoint version: ' + data.ep_version; }

	infoBox.style.height = 'auto';
	infoBox.style.height = infoBox.scrollHeight + 'px';

    refreshResponseBubble(data.text, `Duration: ${data.total_duration} | Tokens: ${data.num_generated_tokens} | Tokens per second: ${tokensPerSec.toFixed(1)}`)

    // TODO: aufhübschen durch HTML -> mini-markup, z.B. Auflistungen erkennen, Formatierungen (<strong>, italic) usw.?
    // ...

    // TODO: Download des Dialogs als PDF anbieten
    // ...

    // const dialogParts = extractDialogParts(data.text);
    // console.log("Dave-Teile:", dialogParts.text_dave);
    // console.log("User-Teile:", dialogParts.text_user);

    console.log('text:' + data.text);
	chatboxContentEl.scrollTop = chatboxContentEl.scrollHeight;
};

function addSpinner() {
    var spinner = document.createElement('div');
        spinner.id = 'process-spinner';
        spinner.className = 'animate-spin mr-2';
        spinner.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-aime_orange">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
        `;
        const button = document.getElementById('chat_send');
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
    const button = document.getElementById('chat_send');
    if (button) {
      button.disabled = true;
      button.classList.add('disabled:opacity-50');
      button.classList.add('disabled:cursor-not-allowed');
    }
}
function enableSendButton() {
    const button = document.getElementById('chat_send');
    if (button) {
        button.disabled = false;
        button.classList.remove('disabled:opacity-50');
        button.classList.remove('disabled:cursor-not-allowed');
    }
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

function onButtonClick() {
    if(readyToSendRequest) {
        readyToSendRequest = false;

        info_box = document.getElementById('info_box');
        info_box.textContent = 'Request sent.\nWaiting for response...';

        disableSendButton();
        // addSpinner();

        // set Tabs to output section
        const output_btn =  document.getElementById('tab_button_output');
        if(!output_btn.active) {
            output_btn.click();
        }
        
        onSendAPIRequest();
    }
 }

 function addChatboxBubble(chatText, infoDetails, isResponse = false) {
    var chatBubbleEl = document.createElement('div');
    chatBubbleEl.className = 'flex items-start gap-2.5 mb-5';

    var tzoffset = (new Date()).getTimezoneOffset() * 60000; //offset in milliseconds
    var localISOTime = (new Date(Date.now() - tzoffset)).toISOString().slice(0, -1);

    chatBubbleEl.innerHTML = `
            <div class="flex items-start gap-2.5">
                <div class="flex flex-col gap-1 w-full max-w-[320px]">
                    <div class="flex items-center justify-between rtl:justify-end space-x-2">
                        <span class="text-sm font-semibold text-gray-900 dark:text-white">${isResponse ? 'User: ' : 'Dave: '}</span>
                        <span class="overlook text-xs font-normal text-gray-500 dark:text-gray-400 ml-auto">${localISOTime.match(/\d\d:\d\d/)}</span>
                    </div>
                    <div class="flex flex-col leading-1.5 p-4 border-gray-200 bg-gray-100 rounded-xl ${isResponse ? 'rounded-br-none' : 'rounded-tl-none'} dark:bg-gray-600">
                        <p class="eol-node latest-bubble-text text-sm font-normal text-gray-900 dark:text-white">${chatText}</p>
                    </div>
                    <span class="overlook latest-bubble-info text-xs font-normal text-gray-500 dark:text-gray-400">${infoDetails}</span>
                </div>
            </div>
    `;

    chatBubbleEl.classList.add(isResponse ? 'justify-end' : 'justify-start');
    chatBubbleEl.querySelector('.flex').classList.add(isResponse ? 'flex-row-reverse' : 'flex-row');
    
    document.querySelectorAll('.latest-bubble-text').forEach(function(element) {
        element.classList.remove('latest-bubble-text');
    });
    document.querySelectorAll('.latest-bubble-info').forEach(function(element) {
        element.classList.remove('latest-bubble-info');
    });

    chatboxContentEl.append(chatBubbleEl);
 }

 function addResponseBubble() {
    addChatboxBubble('...', 'Waiting for response...');
    var latestBubble = document.getElementsByClassName('latest-bubble-text');
    if (latestBubble.length > 0) {
        latestBubble[0].innerHTML = `
            <div class="flex items-center">
                <div class="dot animate-blink"></div>
                <div class="dot animate-blinkDelay-1"></div>
                <div class="dot animate-blinkDelay-2"></div>
            </div>
        `;
    }
 }

 function refreshResponseBubble(responseText, responseInfo) {
    if(responseText && responseText != '') {
        var latestBubbleText = document.getElementsByClassName('latest-bubble-text');
        if (latestBubbleText.length > 0) {
            latestBubbleText[0].innerHTML = responseText;
        }
    }
    if(responseInfo && responseInfo != '') {
        var latestBubbleInfo = document.getElementsByClassName('latest-bubble-info');
        if (latestBubbleInfo.length > 0) {
            latestBubbleInfo[0].innerText = responseInfo;
        }
    }
}

 function getChatboxContext() {
    const chatboxContent = document.getElementById('chatbox');
    const getTextFromElement = (element) => {
        let text = '';
        if (element.nodeType === Node.TEXT_NODE) {
            text += element.nodeValue.replace(/\s+/g, ' ');//.trim();
        } 
        else if (element.nodeType === Node.ELEMENT_NODE) {
            if (!element.classList.contains('overlook')) {
                for (const child of element.childNodes) {
                    text += getTextFromElement(child);
                    if(element.classList.contains('eol-node')) {
                        text += '\n';
                    }
                }    
            }
        }
        return text;
    }
    const resultText = getTextFromElement(chatboxContent).replace(/\\n\s*|\n\s*/g, '\n');
    return resultText;
 }

 function extractDialogParts(text) {
    const dialogParts = {
        text_dave: [],
        text_user: []
    };
    const startOfDialogIndex = text.indexOf('Dave: ');
    let inputText = text.substring(startOfDialogIndex);

    while (inputText.includes('Dave: ') || inputText.includes('User: ')) {
        // Extract Dave-part
        const davePart = inputText.substring('Dave: '.length, inputText.indexOf('\nUser: ')).trim();
        inputText = inputText.slice(davePart.length);
        
        console.log('davePart', davePart);
        dialogParts.text_dave.push(davePart);

        // Schneide den Dave-Teil ab und extrahiere den User-Teil
        // const startOfUserIndex = inputText.indexOf('User');
        // inputText = inputText.substring(startOfUserIndex);
        // const endOfUserIndex = inputText.indexOf('\nDave: ') !== -1 ? inputText.indexOf('\nDave: ') : inputText.length;
        // const userPart = inputText.substring(0, endOfUserIndex).trim();
        // dialogParts.text_user.push(userPart);

        // // Aktualisiere den Text für den nächsten Durchlauf
        // inputText = inputText.substring(endOfUserIndex);
    }
    console.log('dialogParts', dialogParts);
    return dialogParts;
}

function handleKeyPress(event) {
    if (event.keyCode === 13) {
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
                    'aime_orange': '#F6BE5C',
                    'aime_green': '#CBE4C9',
                    'aime_lightgreen': '#f2f6f2'
                },
                'gradientColorStopPositions': {
                    33: '33%',
                  },
                'keyframes': {
                    'blink': {
                    '0%, 100%': { 'opacity': 0.8 },
                    '50%': { 'opacity': 0.3 },
                    },
                    'blinkDelay-1': {
                        '0%, 100%': { 'opacity': 0.8 },
                        '50%': { 'opacity': 0.3 },
                    },
                    'blinkDelay-2': {
                        '0%, 100%': { 'opacity': 0.8 },
                        '50%': { 'opacity': 0.3 },
                    },
                },
                'animation': {
                    'blink': 'blink 1s infinite ease-in-out',
                    'blinkDelay-1': 'blinkDelay-1 1s infinite ease-in-out 0.3333s',
                    'blinkDelay-2': 'blinkDelay-2 1s infinite ease-in-out 0.6666s',
                },
            }
        }
    };
    hljs.highlightAll();

    chatboxContentEl = document.getElementById('chatbox-content');
	refreshRangeInputLayout();

    document.getElementById('input-context').textContent = inputContext;
    addChatboxBubble('Hello, Dave.', '', true);
    addChatboxBubble('How can I assist you today?', '');

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
	});
});
