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
