const modelAPI = new ModelAPI('example_api');

let readyToSendRequest = true;
let log_textarea, chat_input, info_box;

function onSendAPIRequest() {
    
    let params = new Object({
        prompt: chat_input.value,
        sleep_duration:  parseFloat(document.getElementById('sleep_duration').value),
        progress_steps:  parseInt(document.getElementById('progress_steps').value)
    });
    chat_input.value = '';
    log_textarea.value = 'step 0';

    modelAPI.doAPILogin(function (data) {
        modelAPI.doAPIRequest(params, 

            // onResultCallback
            function (data) {
                readyToSendRequest = true;
                enableSendButton();
                removeSpinner();

                if (data.error) {
                    info_box.textContent = data.error;
                }
                else {
                    log_textarea.value += '\n' + data.text + '\n';
                    log_textarea.scrollTop = log_textarea.scrollHeight;
                    info_box.textContent = 'Response received. Request finished succesfully!';

                    document.getElementById('progress_bar').value = 100;
                    document.getElementById('progress_label').innerText = '100%';
                }
                adjustTextareasHeight();
            },

            // onProgressCallback
            function (progress_info, progress_data) {
                const progress = progress_info.progress;
                const queue_position = progress_info.queue_position;
                let progressTxt = 'Receiving response: ';
                

                if((queue_position < 0) || (queue_position == null)) {
                    progressTxt += 'Sending Request'
                } 
                else if(queue_position == 0) {
                    if(progress < 100) {
                        progressTxt += 'Processing...';
                    }
                }
                else {
                    progressTxt += 'Waiting in queue at position ' + queue_position
                }
                info_box.textContent = progressTxt;

                document.getElementById('progress_bar').value = progress;
                document.getElementById('progress_label').innerText = progress.toFixed(1) + '% | ' + progressTxt;
                
                if(progress_data != null) {
                    log_textarea.value += '\n' + progress_data['status'];
                    log_textarea.scrollTop = log_textarea.scrollHeight;                
                }

                adjustTextareasHeight();
            }
        );
    });
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

function adjustTextareasHeight() {
    log_textarea.style.height = 'auto';
    log_textarea.style.height = log_textarea.scrollHeight + 'px';

    info_box.style.height = 'auto';
    info_box.style.height = info_box.scrollHeight + 'px';
}

function handleKeyPress(event) {
    if (event.keyCode === 13) { // Enter key
        event.preventDefault();
        onButtonClick();
    }
}

function onButtonClick() {
    
    if(readyToSendRequest) {
        readyToSendRequest = false;
        info_box = document.getElementById('info_box');
        info_box.textContent = 'Request sent.\nWaiting for response...';
        disableSendButton();
        addSpinner();
        onSendAPIRequest();

        // set Tabs to output section
        const output_btn =  document.getElementById('tab_button_output');
        if(!output_btn.active) {
            output_btn.click();
        }
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
                    'aime_green': '#CBE4C9'
            }
        },
        //   container: {
        //     padding: '2rem',
        //   },
        }
    };
    hljs.highlightAll();
   
    log_textarea = document.getElementById('chat_log');
    chat_input = document.getElementById('chat_input');
    info_box = document.getElementById('info_box');

    log_textarea.innerText = 'Welcome, User! Please type in a message, set your number of steps and a job duration, then press the send button.';

    document.addEventListener('keydown', function(event) {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
            const button = document.getElementById('chat_send');
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

    refreshRangeInputLayout();
});
