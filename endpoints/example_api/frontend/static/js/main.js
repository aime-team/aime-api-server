const modelAPI = new ModelAPI('example_api');
let readyToSendRequest = true;

function onSendAPIRequest() {

    log_textarea = document.getElementById('chat_log');
    prompt_input = document.getElementById('chat_input');

    params = new Object();
    params['prompt'] = prompt_input.value;
    params['sleep_duration'] = parseFloat(document.getElementById('sleep_duration').value);
    params['progress_steps'] = parseInt(document.getElementById('progress_steps').value);

    prompt_input.value = '';

//		doAPIRequest('example_api', params, function (data) {
//			log_textarea.value += data['text'] + '\n';
//			log_textarea.scrollTop = log_textarea.scrollHeight;
//		});

    
    modelAPI.doAPILogin(function (data) {
        modelAPI.doAPIRequest(params, 
            function (data) {
                readyToSendRequest = true;
                enableSendButton();
                log_textarea.value += '\n' + data['text'] + '\n';
                log_textarea.scrollTop = log_textarea.scrollHeight;
            },
            function (progress_info, progress_data) {
                const progress = progress_info['progress'];
                const queue_position = progress_info['queue_position'];
                var progress_status = "Progress";
                if((queue_position < 0) || (queue_position == null)) {
                    progress_status += " - Sending Request"
                } 
                else if(queue_position == 0) {
                    if(progress < 100) {
                        progress_status += " - Processing"
                    }
                }
                else {
                    progress_status += ' - Waiting in queue at position ' + queue_position
                }
                document.getElementById("progress_status").innerText = progress_status;            
                document.getElementById("progress_bar").value = progress;
                document.getElementById('progress_label').innerText = progress.toFixed(1) + '%';
                if(progress_data != null) {
                    log_textarea.value += " " + progress_data['status'];
                    log_textarea.scrollTop = log_textarea.scrollHeight;                
                }
            });
    });
}

function disableSendButton() {
    const button = document.getElementById('prompt_send');
    if (button) {
      button.disabled = true;
      button.classList.add('disabled:opacity-50');
      button.classList.add('disabled:cursor-not-allowed');
    }
}
function enableSendButton() {
    const button = document.getElementById('prompt_send');
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
        onSendAPIRequest();
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
   
    document.addEventListener('keydown', function(event) {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
            const button = document.getElementById('prompt_send');
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
    modelAPI.doAPILogin();

});
