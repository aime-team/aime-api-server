// How to use:

// add 
// <script type="module" src="/static/js/form_widgets.js"></script>
// and 
// <div id="aime-widgets" class="container"></div>
// <div id="aime-widgets-chatbox" class="container">
//     <div id="textarea-widget" class="col"></div>
//     <div id="slider-widgets" class="col"></div>
// </div>


import WidgetManager from '/model_api/frontend/js/widgets/widgetManager.js';
const wm = new WidgetManager({
    enpointURL: 'http://api.aime.info/api_endpoint',
    btnTxt: 'Senden'
});

wm.createWidget({
    type: 'sliderInput',
    label: 'Progress Steps',
    name: 'progress_steps_test',
    targetId: 'slider-widgets',
    class: 'col mb-3',
    // required: true,
    attributes: {
        min: 0,
        max: 100,
        step: 1,
        value: 10
    }
});
wm.createWidget({
    type: 'sliderInput',
    label: 'Progress Steps (0.1 Stepsize)', 
    name: 'progress_steps_2',
    targetId: 'slider-widgets',
    class: 'col',
    // required: true,
    attributes: {
        min: 0,
        max: 100,
        step: 0.1,
        value: 20
    }
});

wm.createWidget({
    type: 'textArea',
    // label: 'Chat Output', 
    name: 'chat_log_test',
    targetId: 'textarea-widget',
    class: 'mlapi',
    attributes: {
        readonly: true
    }
});



console.log('WidgetManager', wm);


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
