// Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
//
// This software may be used and distributed according to the terms of the MIT LICENSE

const API_USER = 'aime'
const API_KEY = '6a17e2a5-b706-03cb-1a32-94b4a1df67da'


modelAPI = new ModelAPI('gpt_oss_chat', API_USER, API_KEY);

let readyToSendRequest = true;
let chatboxContentEl;
let infoBox;
let currentChatContext = [];
let currentTemplate;
let chatContextPerSession = new Object();
const assistantName = 'GPT';

const CHAT_TEMPLATES = {
    'eng': [
        {
            "role": "system",
            "content": 
                `You are a helpful, respectful and honest assistant named ${assistantName}. ` +
                "Always answer as helpfully as possible, while being safe. " +
                "Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. " +
                "Please ensure that your responses are socially unbiased and positive in nature. " +
                "If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. " +
                "If you don't know the answer to a question, please don't share false information."
        },
        {
            "role": "user", 
            "content": `Hello, ${assistantName}.`
        },
        {
            "role": "assistant", 
            "content": "How can I assist you today?"
        }
    ],
    'deu': [
        {
            "role": "system",
            "content": 
                `Du bist ein Assistent namens ${assistantName}. ` +
                "Antworte auf Deutsch und immer so hilfreich wie möglich. " +
                "Deine Antworten sollten keine schädlichen, unethischen, rassistischen, sexistischen, toxischen, gefährlichen oder illegalen Inhalte enthalten. " +
                "Bitte stelle sicher, dass deine Antworten sozial unvoreingenommen und positiv sind. " +
                "Wenn eine Frage keinen Sinn ergibt oder nicht faktisch kohärent ist, erkläre stattdessen, warum. " +
                "Wenn du die Antwort auf eine Frage nicht weißt, teile bitte keine falschen Informationen. "
        },
        {
            "role": "user", 
            "content": `Hallo ${assistantName}.`
        },
        {
            "role": "assistant", 
            "content": "Was kann ich für dich tun?"
        }
    ],
    'fra': [
        {
            "role": "system",
            "content": 
            `Vous êtes une assistante serviable, respectueuse et honnête, nommée ${assistantName}. ` +
            "Répondez toujours de la manière la plus utile possible, tout en restant prudent. " +
            "Vos réponses ne doivent pas comporter de contenu nuisible, non-éthique, raciste, sexiste, toxique, dangereux ou illégal. " +
            "Veillez à ce que vos réponses soient socialement impartiales et positives par nature. " +
            "Si une question n'a pas de sens ou n'est pas cohérente sur le plan des faits, expliquez pourquoi au lieu de répondre quelque chose d'incorrect. " +
            "Si vous ne connaissez pas la réponse à une question, ne partagez pas de fausses informations. "
        },
        {
            "role": "user", 
            "content": `Salut ${assistantName}.`
        },
        {
            "role": "assistant", 
            "content": "Que puis-je faire pour toi aujourd'hui ?"
        }
    ],
    'spa': [
        {
            "role": "system",
            "content": 
                `Tú eres una asistenta útil, respetuosa y honesta llamada ${assistantName}. ` +
                "Siempre respondes de la manera más útil y fiable posible. " +
                "Tus respuestas no deben incluir ningún contenido dañino, poco ético, racista, sexista, tóxico, peligroso o ilegal. " +
                "Por favor, asegúrate de que tus respuestas no tengan prejuicios y tengan un carácter positivo. " +
                "Si una pregunta no tiene ningún sentido, o no es objetivamente coherente, explica el porqué en lugar de responder algo incorrecto. " +
                "Si no sabes la respuesta a una pregunta, por favor no proporciones información incorrecta. "
        },
        {
            "role": "user", 
            "content": `Hola ${assistantName}.`
        },
        {
            "role": "assistant", 
            "content": "Cómo te puedo ayudar?"
        }
    ],
    'ber':[
        {
            "role": "system",
            "content": 
                `Du bist Kalle aus Berlin, der mit juter Berliner Schnauze quatscht. ` +
                "Antworte imma so hilfreich wie möglich, aber keene Schweinereien und keen' Mist erzähl'n." +
                "Wenn 'ne Frage ma keen' Sinn macht, erklär ma oof beleidijende Weise warum. " +
                "Imma frech bleiben, auf ne herzliche Art unterschwellig beleidigend oder mindestens provokativ."
        },
        {
            "role": "user", 
            "content": `Nabend Kalle, allet klar?`
        },
        {
            "role": "assistant", 
            "content": "Klar, muss ja! Wat kann ick tun für dir?"
        }
    ],
    'wer':[
        {
            "role": "system",
            "content": 
                "Du büst en Assistent namens Röhrich. " +
                "Antworte immer so, as wenn du den Flensburger Dialekt snacken deist un de Figur 'Röhrich' ut de Film 'Werner Beinhart' verköpern deist. " +
                "Wees humorvoll, aber pass op, dat du keen beleidigen oder unanständigen Snaak gebraukst. " +
                "Vermeid rasistisch, sexistisch oder geföhrlich Utsegn. " +
                "Wenn en Froog keene Sinn makt oder nich to't Thema pass, denn erkläre stattdessen, worüm. " +
                "Un wenn du nich wiest, wat de Antwort op en Froog is, denn säähr dat af, aber probeer trotzdem humorvoll to blieven!"
                
        },
        {
            "role": "user", 
            "content": `Moin Meistä!`
        },
        {
            "role": "assistant", 
            "content": "Moin mien Jung! Sach ma, tut das not, dass du hier so rumkrakälst?"
        },
    ],
    'yod':[
        {
            "role": "system",
            "content": 
                "The character Yoda from Star Wars withs its characteristic talking syntax you are. " +
                "Every answer in the way Yoda talks must be. " +
                "Always helpfully as possible, while safe, you must be. " +
                "Your answers, harmful, unethical, racist, sexist, toxic, dangerous, or illegal content should not include. " +
                "Socially unbiased and positive in nature, your responses must be. " +
                "If sense a question does not make, or coherent factually it is not, why instead of answering, explain. " +
                "If know not the answer to a question, false information, share not."
                
        },
        {
            "role": "user", 
            "content": `May the force be with you, Yoda`
        },
        {
            "role": "assistant", 
            "content": "With you, the force may be."
        }
    ],
    'hod':[
        {
            "role": "system",
            "content": 
                "You are the character Hodor from the tv series Game of Thrones. " +
                `Every answer of you is just a single word: Either "Hodor!" or "Hodor?"` +
                "You don't know any other words than Hodor. " +
                `If you don't understand the question, reply with "Hodor?"`
                
        },
        {
            "role": "user", 
            "content": `Hi Hodor!`
        },
        {
            "role": "assistant", 
            "content": "Hodor!"
        }
    ]
}

function onSendAPIRequest() {
	params = new Object();
    currentChatContext.push(
            {
                "role": "user",
                "content": document.getElementById('chat_input').value
            }
        )
	params.chat_context = currentChatContext;
	params.top_k = parseInt(document.getElementById('top_k_range').value);
	params.top_p = parseFloat(document.getElementById('top_p_range').value);
	params.temperature = parseFloat(document.getElementById('temperature_range').value);
    params.max_gen_tokens = parseFloat(document.getElementById('max_gen_tokens_range').value);

    console.log(params)
	modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback);
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

function clearChatContext() {
    applyChatContextToBubbles(CHAT_TEMPLATES[document.getElementById('template-selection').value]);
}

function onResultCallback(data) {
  if (data.error) {
      if (data.error.indexOf('Client session authentication key not registered in API Server') > -1) {
          modelAPI.initAPIKey( () => onSendAPIRequest(), function (error) {
            infoBox.textContent = 'Login Error: ' + error + '\n';
            enableSendButton();                                 
          });
      }
      else {
          infoBox.textContent = 'Error: ' + data.error + '\n';
          enableSendButton();
      }
  }
  else {
    enableSendButton();
        infoBox.textContent = ''
		if (data.total_duration) { 			infoBox.textContent += 'Total job duration: ' + data.total_duration + 's' + '\n'; }
		if (data.compute_duration) { 		infoBox.textContent += 'Compute duration: ' + data.compute_duration + 's' + '\n'; }
		if (data.num_generated_tokens) { 	infoBox.textContent += 'Generated tokens: ' + data.num_generated_tokens + '\n'; }
        if (data.current_context_length) { 	infoBox.textContent += 'Current context length: ' + data.current_context_length + '\n'; }
        if (data.max_seq_len) { 	infoBox.textContent += 'Maximum context length: ' + data.max_seq_len + '\n'; }
		if (data.compute_duration && data.num_generated_tokens) {
				tokensPerSec = data.num_generated_tokens / data.compute_duration
				infoBox.textContent += 'Tokens per second: ' + tokensPerSec.toFixed(1) + '\n';
		}
		if (data.model_name) { 				infoBox.textContent += '\nModel name: ' + data.model_name +'\n'; }
        //document.getElementById('chat_input').value = ''; to test
        
        if (data.auth) { 					infoBox.textContent += 'Worker: ' + data.auth + '\n'; }
        if (data.worker_interface_version) {
            var versionNo = data.worker_interface_version.match(/\d+\.\d+\.\d+/);
            if (versionNo) {				infoBox.textContent += 'Worker Interface version: ' + versionNo[0] + '\n'; }
        }
        if (data.ep_version != null) { 		infoBox.textContent += 'Endpoint version: ' + data.ep_version; }

        infoBox.style.height = 'auto';
        infoBox.style.height = infoBox.scrollHeight + 'px';
        refreshResponseBubble(data.text, `Duration: ${data.total_duration} | Tokens: ${data.num_generated_tokens} | Tokens per second: ${tokensPerSec.toFixed(1)}`)
        
        // TODO: Make content prettier with HTML -> mini-markup, e.g. recognize listings, formatting (<strong>, italic) etc.?
        // ...

        // TODO: Offer download of the dialog as PDF
        // ...

        chatboxContentEl.scrollTop = chatboxContentEl.scrollHeight;
	}
};

function disableSendButton() {
		readyToSendRequest = false;
    const button = document.getElementById('chat_send');
    if (button) {
      button.disabled = true;
      button.classList.add('disabled:opacity-50');
      button.classList.add('disabled:cursor-not-allowed');
    }
}
function enableSendButton() {
    readyToSendRequest = true;
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

        disableSendButton();
        infoBox.textContent = 'Request sent.\nWaiting for response...';

        // set Tabs to output section
        const output_btn =  document.getElementById('tab_button_output');
        if(!output_btn.active) {
            output_btn.click();
        }

        let chatInput = document.getElementById('chat_input');
        infoBox.textContent = 'Request sent.\nWaiting for response...';
        updateChatContextFromBubbles()
        onSendAPIRequest();

        addChatboxBubble(chatInput.value, `TopK: ${params.top_k} | TopP: ${params.top_p} | Temp: ${params.temperature}`);
        addResponseBubble();
        chatboxContentEl.scrollTop = chatboxContentEl.scrollHeight;
        chatInput.value = '';
    }
 }

function addChatboxBubble(chatText, infoDetails, isResponse = false, editable=false) {
    var chatBubbleEl = document.createElement('div');
    chatBubbleEl.className = 'flex items-start gap-2.5 mb-5';


    var tzoffset = (new Date()).getTimezoneOffset() * 60000; //offset in milliseconds
    var localISOTime = (new Date(Date.now() - tzoffset)).toISOString().slice(0, -1);
    chatBubbleEl.innerHTML = `
            <div class="flex items-start gap-2.5">
                <div class="flex flex-col gap-1 w-full max-w-[320px]">
                    <div class="flex items-center justify-between rtl:justify-end space-x-2 no-print">
                        ${isResponse ? '<svg width="16" height="16" viewBox="0 0 320 320" fill="#fff" xmlns="http://www.w3.org/2000/svg"><path d="m297.06 130.97c7.26-21.79 4.76-45.66-6.85-65.48-17.46-30.4-52.56-46.04-86.84-38.68-15.25-17.18-37.16-26.95-60.13-26.81-35.04-.08-66.13 22.48-76.91 55.82-22.51 4.61-41.94 18.7-53.31 38.67-17.59 30.32-13.58 68.54 9.92 94.54-7.26 21.79-4.76 45.66 6.85 65.48 17.46 30.4 52.56 46.04 86.84 38.68 15.24 17.18 37.16 26.95 60.13 26.8 35.06.09 66.16-22.49 76.94-55.86 22.51-4.61 41.94-18.7 53.31-38.67 17.57-30.32 13.55-68.51-9.94-94.51zm-120.28 168.11c-14.03.02-27.62-4.89-38.39-13.88.49-.26 1.34-.73 1.89-1.07l63.72-36.8c3.26-1.85 5.26-5.32 5.24-9.07v-89.83l26.93 15.55c.29.14.48.42.52.74v74.39c-.04 33.08-26.83 59.9-59.91 59.97zm-128.84-55.03c-7.03-12.14-9.56-26.37-7.15-40.18.47.28 1.3.79 1.89 1.13l63.72 36.8c3.23 1.89 7.23 1.89 10.47 0l77.79-44.92v31.1c.02.32-.13.63-.38.83l-64.41 37.19c-28.69 16.52-65.33 6.7-81.92-21.95zm-16.77-139.09c7-12.16 18.05-21.46 31.21-26.29 0 .55-.03 1.52-.03 2.2v73.61c-.02 3.74 1.98 7.21 5.23 9.06l77.79 44.91-26.93 15.55c-.27.18-.61.21-.91.08l-64.42-37.22c-28.63-16.58-38.45-53.21-21.95-81.89zm221.26 51.49-77.79-44.92 26.93-15.54c.27-.18.61-.21.91-.08l64.42 37.19c28.68 16.57 38.51 53.26 21.94 81.94-7.01 12.14-18.05 21.44-31.2 26.28v-75.81c.03-3.74-1.96-7.2-5.2-9.06zm26.8-40.34c-.47-.29-1.3-.79-1.89-1.13l-63.72-36.8c-3.23-1.89-7.23-1.89-10.47 0l-77.79 44.92v-31.1c-.02-.32.13-.63.38-.83l64.41-37.16c28.69-16.55 65.37-6.7 81.91 22 6.99 12.12 9.52 26.31 7.15 40.1zm-168.51 55.43-26.94-15.55c-.29-.14-.48-.42-.52-.74v-74.39c.02-33.12 26.89-59.96 60.01-59.94 14.01 0 27.57 4.92 38.34 13.88-.49.26-1.33.73-1.89 1.07l-63.72 36.8c-3.26 1.85-5.26 5.31-5.24 9.06l-.04 89.79zm14.63-31.54 34.65-20.01 34.65 20v40.01l-34.65 20-34.65-20z"/></svg>' : ''}
                        <span class="overlook text-xs font-normal text-gray-500 text-gray-400">${localISOTime.match(/\d\d:\d\d/)}</span>
                        ${!isResponse ? '<span class="text-sm font-semibold text-white w-4 h-4"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="#fff" class="size-4"><path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM12.735 14c.618 0 1.093-.561.872-1.139a6.002 6.002 0 0 0-11.215 0c-.22.578.254 1.139.872 1.139h9.47Z" /></svg></span>' : ''}
                    </div>
                    <div class="flex flex-col leading-1.5 p-4 border-gray-200 bg-gray-600 rounded-xl ${!isResponse ? 'rounded-br-none' : 'rounded-tl-none'}">
                        <div contenteditable="${editable}" class="eol-node ${!isResponse ? 'user-bubble' : 'assistant-bubble'} latest-bubble-text text-sm font-normal text-white">${chatText}</div>
                        ${!editable ? '' : '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#999" class="size-6 w-4 h-4 no-print"><path d="M21.731 2.269a2.625 2.625 0 0 0-3.712 0l-1.157 1.157 3.712 3.712 1.157-1.157a2.625 2.625 0 0 0 0-3.712ZM19.513 8.199l-3.712-3.712-8.4 8.4a5.25 5.25 0 0 0-1.32 2.214l-.8 2.685a.75.75 0 0 0 .933.933l2.685-.8a5.25 5.25 0 0 0 2.214-1.32l8.4-8.4Z" /><path d="M5.25 5.25a3 3 0 0 0-3 3v10.5a3 3 0 0 0 3 3h10.5a3 3 0 0 0 3-3V13.5a.75.75 0 0 0-1.5 0v5.25a1.5 1.5 0 0 1-1.5 1.5H5.25a1.5 1.5 0 0 1-1.5-1.5V8.25a1.5 1.5 0 0 1 1.5-1.5h5.25a.75.75 0 0 0 0-1.5H5.25Z" /></svg>'}
                    </div>
                    <span class="overlook latest-bubble-info text-xs font-normal text-gray-400 no-print">${infoDetails}</span>
                </div>
            </div>
    `;
    chatBubbleEl.querySelector('.latest-bubble-text').textContent = chatText;
    chatBubbleEl.classList.add(!isResponse ? 'justify-end' : 'justify-start');
    chatBubbleEl.querySelector('.flex').classList.add(!isResponse ? 'flex-row-reverse' : 'flex-row');
    
    document.querySelectorAll('.latest-bubble-text').forEach(function(element) {
        element.classList.remove('latest-bubble-text');
    });
    document.querySelectorAll('.latest-bubble-info').forEach(function(element) {
        element.classList.remove('latest-bubble-info');
    });

    chatboxContentEl.append(chatBubbleEl);
 }

function addResponseBubble() {
    addChatboxBubble('...', 'Waiting for response...', true);
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
            latestBubbleText[0].innerText = responseText;
        }
    }
    if(responseInfo && responseInfo != '') {
        var latestBubbleInfo = document.getElementsByClassName('latest-bubble-info');
        if (latestBubbleInfo.length > 0) {
            latestBubbleInfo[0].innerText = responseInfo;
        }
    }
}

function updateChatContextFromBubbles() {

    currentChatContext = [
        {
            "role": "system",
            "content": document.getElementById('system-prompt').textContent
        }
    ];
    const chatBubbles = document.querySelectorAll('.eol-node');
    chatBubbles.forEach(bubble => {
        if (bubble.classList.contains('user-bubble')) {
            
            currentChatContext.push(
                    {
                        "role": "user",
                        "content": bubble.textContent
                    }
            );
        }
        if (bubble.classList.contains('assistant-bubble')) {
            currentChatContext.push(
                {
                    "role": "assistant",
                    "content": bubble.textContent
                }
            )
        }
    });
}

function handleKeyPress(event) {
    if (event.keyCode === 13) {
      event.preventDefault();
      onButtonClick();
    }
}

function docReady(fn) {
    if (document.readyState === "complete" || document.readyState === "interactive") {
        setTimeout(fn, 1);
    } else {
        document.addEventListener("DOMContentLoaded", fn);
    }
}


function applyChatContextToBubbles(chatContext) {
    document.getElementById('system-prompt').innerHTML = '';
    document.getElementById('chatbox-content').innerHTML = '';
    document.getElementById('system-prompt').textContent = chatContext[0].content;
    for (var i = 1; i < chatContext.length; i++) {
        if (chatContext[i].role === "user") {
            if (i===1) {
                addChatboxBubble(chatContext[i].content, '', false, true);
            }
            else {
                addChatboxBubble(chatContext[i].content, '');
            }
            
        }
        else if (chatContext[i].role === "assistant") {
            if (i===2) {
                addChatboxBubble(chatContext[i].content, '', true, true);
            }
            else {
                addChatboxBubble(chatContext[i].content, '', true);
            }
        }
    }
}


function switchTemplate() {
    updateChatContextFromBubbles();
    chatContextPerSession[currentTemplate] = currentChatContext;
    
    if (chatContextPerSession[document.getElementById("template-selection").value]) {
        applyChatContextToBubbles(chatContextPerSession[document.getElementById("template-selection").value]);
    }
    else {
        applyChatContextToBubbles(CHAT_TEMPLATES[document.getElementById('template-selection').value])
    }
    currentTemplate = document.getElementById("template-selection").value;
}

docReady(function() {
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

    refreshRangeInputLayout();
    chatboxContentEl = document.getElementById('chatbox-content');
    currentTemplate = document.getElementById("template-selection").value;
    applyChatContextToBubbles(CHAT_TEMPLATES[currentTemplate]);
    

    infoBox = document.getElementById('info_box');
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
        
    modelAPI.initAPIKey(function (data) {
        console.log('API Key initialized')
    },
    function (error) {
        infoBox.textContent = 'Login Error: ' + error + '\n';
    });
});
