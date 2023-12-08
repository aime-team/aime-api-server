function onSendRequest() {

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

    modelAPI = new ModelAPI('example_api');
    modelAPI.doAPILogin(function (data) {
        modelAPI.doAPIRequest(params, function (data) {
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

function handleKeyPress(event) {
    if (event.keyCode === 13) { // Enter key
        event.preventDefault();
        onSendRequest();
    }
}

// ### UI ELEMENTS ######################################

// SLIDER WIDGET: put class .slider-widget to .input-group and initialize
function updateSliderValue() {
    // slider change
    if ($(this).is('input[type="range"]')) {
        $(this).closest('.form-group').find('input[type="number"]').val($(this).val());    
    } 
    // input field change
    else if ($(this).is('input[type="number"]')) {
        const $input = $(this).closest('.form-group').find('input[type="range"]');
        let value = $(this).val();
        // if ( $input.attr('max') && value > $input.prop('max') ) value = $input.prop('max');
        // if ( $input.attr('min') && value < $input.prop('min') ) value = $input.prop('min');
        $(this).closest('.form-group').find('input[type="range"]').val(value);
    }
}

// ### FORM FIELD INTERACTION
function getFormValues() {
    const form = document.getElementById('form-example'); // Formular-Element auswählen
    const formData = new FormData(form); // Alle Eingabefelder innerhalb des Formulars auswählen
    const formDataObject = {}; // JSON-Objekt erstellen und Felder hinzufügen

    formData.forEach((value, key) => {
        formDataObject[key] = value;
    });

    console.log(formDataObject);
    // via AJAX an Server senden ...
}

$(document).ready(function() {
    // init all slider-value widgets
    $('.slider-widget input[type="range"]').each(updateSliderValue);
    $('.slider-widget input[type="range"]').on('input change', updateSliderValue);
    $('.slider-widget input[type="number"]').on('input', updateSliderValue);
});
