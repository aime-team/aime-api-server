// Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
//
// This software may be used and distributed according to the terms of the MIT LICENSE

const API_USER = 'aime'
const API_KEY = '6a17e2a5-b706-03cb-1a32-94b4a1df67da'


modelAPI = new ModelAPI('mistral_chat', API_USER, API_KEY);

let readyToSendRequest = true;
let chatboxContentEl;
let infoBox;
let currentChatContext = [];
let currentTemplate;
let chatContextPerSession = new Object();
const assistantName = 'Mistral';

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
	params.chat_context = currentChatContext;
    params.prompt_input = document.getElementById('chat_input').value
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
                        ${isResponse ? '<svg width="24" height="24" viewBox="0 0 353 481" xmlns="http://www.w3.org/2000/svg" class="size-6 w-5 h-5"><path d="M48.6975244,480.51694 C66.463719,370.073037 66.463719,304.82768 48.6975244,284.780869 C62.1430574,281.34228 79.4415372,269.973002 82.2076003,260.383878 C85.0259208,250.613595 81.558876,245.052535 79.65848,240.716616 C68.2402743,235.442468 41.0170643,234.972457 34.382326,242 C30.7641328,238.574055 28.9550362,235.103033 28.9550362,231.586934 C42.116695,206.430387 56.544962,189.434021 72.2398372,180.597835 C65.2356022,161.898224 38.6235315,80.6945657 55.8773428,23.8992774 C42.8913348,17 -11.9895261,65.77312 48.6975244,175.542228 C35.5358656,186.663842 28.9550362,190.425175 28.9550362,186.826227 C-17.9395379,88.8848174 -6.87686419,26.9148393 62.1430574,0.916293048 C68.8742439,7.28181109 72.2398372,10.4645701 72.2398372,10.4645701 C77.185599,73.8256414 89.7398152,117.921168 109.902486,142.751149 C114.904819,135.516856 160.38404,130.327387 176.498726,130.219577 C176.579585,130.217865 176.662609,130.218009 176.746471,130.218297 L177,130.217865 L177,130.217865 C193.115132,130.327589 238.592686,135.516996 243.594922,142.751149 C263.757593,117.921168 276.311809,73.8256414 281.257571,10.4645701 L281.257571,10.4645701 L281.269173,10.4535982 C281.489614,10.2451325 284.85134,7.06603082 291.354351,0.916293048 C360.374272,26.9148393 371.436946,88.8848174 324.542372,186.826227 C324.542372,189.87988 319.804658,187.634671 310.329231,180.0906 L309.644357,179.542727 C308.143007,178.336141 306.528182,177.002642 304.799884,175.542228 C365.486934,65.77312 310.606073,17 297.620065,23.8992774 C314.873877,80.6945657 288.261806,161.898224 281.257571,180.597835 C296.952446,189.434021 311.380713,206.430387 324.542372,231.586934 C324.542372,235.103033 322.733275,238.574055 319.115082,242 C312.480344,234.972457 285.257134,235.442468 273.838928,240.716616 C271.938532,245.052535 268.471487,250.613595 271.289808,260.383878 C274.055871,269.973002 291.354351,281.34228 304.799884,284.780869 C287.033689,304.82768 287.033689,370.073037 304.799884,480.51694 L304.799884,480.51694 L48.6975244,480.51694 Z M209.817946,389.831848 C195.94536,394.168012 184.838514,395.603227 176.497408,394.137494 L176.748408,394.179293 L176.542288,394.214566 C168.254094,395.550078 157.299819,394.089172 143.679462,389.831848 L137.583284,400.011326 C153.532163,414.436405 166.587504,421.707909 176.749306,421.82584 C186.910509,421.707573 199.965614,414.436071 215.914124,400.011326 L215.914124,400.011326 Z M157.668888,212.274953 C152.008062,225.358118 147.788284,234.339767 144.056295,243.438169 L143.572202,244.625926 C139.399344,254.931567 135.796859,265.620773 131.387705,282.787102 C130.345266,286.845673 132.410459,289.408309 137.583284,290.475009 C147.295838,285.349738 155.336009,283.451691 161.703796,284.780869 C166.26582,287.263688 170.910824,303.974377 168.036706,307.048869 C163.013876,312.421874 153.963997,312.421874 140.88707,307.048869 C127.793127,340.074517 119.299983,360.477072 115.407637,368.256532 C136.921112,385.361508 157.284621,384.044269 176.498164,364.304816 L176.497408,363.784781 C176.581165,363.872321 176.664943,363.95951 176.748744,364.046348 L177,363.784781 L177,363.784781 L176.999244,364.304816 C196.212787,384.044269 216.576296,385.361508 238.089771,368.256532 C234.197425,360.477072 225.704281,340.074517 212.610338,307.048869 C199.533411,312.421874 190.483532,312.421874 185.460702,307.048869 C182.586584,303.974377 187.231588,287.263688 191.793612,284.780869 C198.161399,283.451691 206.20157,285.349738 215.914124,290.475009 C221.086949,289.408309 223.152142,286.845673 222.109703,282.787102 C213.63056,249.774931 208.134663,240.716616 195.82852,212.274953 C191.869434,208.00915 185.697901,204.607171 176.999927,206.106811 L177,206.198394 L177,206.198394 L176.748408,206.152293 L176.497408,206.198394 L176.497408,206.198394 L176.497571,206.106827 C167.799549,204.607148 161.627988,208.009136 157.668888,212.274953 Z" fill="#FFFFFF"></path></svg>' : ''}
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
