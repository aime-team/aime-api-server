import Widget from './widget.js';

/*
#### SliderInputWidget ####

type: 'sliderInput',
label: '', 
name: '', 
targetId: '',
// required: false, // true, false
attributes: {
    min: 0,
    max: 100,
    step: 1,
    value: 10 // default value
}

### TODO: 
    
    - add validation
    - Optional Einheiten anzeigen

*/

class SliderInputWidget extends Widget {
    constructor(options) {
        super(options);
    }

    initialize() {
        super.initialize();
        // to initialize the input element we want to call updateSliderValue but need an event for that if we don't want to repeat code
        // const simulatedEvent = new Event('input', { bubbles: true, cancelable: true });
        // const target = document.getElementById(this.name + '_range');
        // Object.defineProperty(simulatedEvent, 'target', {value: target, enumerable: true});
        // this.updateSliderValue(simulatedEvent);
    }
    
    createElements() {
        super.createElements();
        
        if (this.label) {
            const label = document.createElement('label');
            label.setAttribute('for', this.name);
            label.textContent = this.label;
            this.widgetTemplate.appendChild(label);
        }

        const inputGroup = document.createElement('div');
        inputGroup.className = 'input-group slider-widget flex-centered';
        this.widgetTemplate.appendChild(inputGroup);

        const rangeInput = document.createElement('input');
        rangeInput.type = 'range';
        rangeInput.className = 'form-control-range mt-sm-2 col-9';
        rangeInput.setAttribute('id', this.name + '_range');
        rangeInput.setAttribute('min', this.attributes.min);
        rangeInput.setAttribute('max', this.attributes.max);
        rangeInput.setAttribute('value', this.attributes.value);
        rangeInput.setAttribute('step', this.attributes.step);
        inputGroup.appendChild(rangeInput);
        this.dataElements[this.name + '_range'] = rangeInput;

        const numberInput = document.createElement('input');
        numberInput.type = 'number';
        numberInput.className = 'form-control col-2';
        numberInput.setAttribute('id', this.name + '_value');
        numberInput.setAttribute('min', this.attributes.min);
        numberInput.setAttribute('max', this.attributes.max);
        numberInput.setAttribute('value', this.attributes.value);
        numberInput.setAttribute('step', this.attributes.step);
        inputGroup.appendChild(numberInput);
    }

    addEventListeners() {
        document.getElementById(this.name + '_range').addEventListener('input', this.updateSliderValue.bind(this));
        document.getElementById(this.name + '_value').addEventListener('change', this.updateSliderValue.bind(this));
    }

    updateSliderValue(event) {
        const input = event.target;
        const numberInput = document.getElementById(this.name + '_value');
        const rangeInput = document.getElementById(this.name + '_range');

        if (input.type === 'range') {
            const value = this.encloseValue(input);
            numberInput.value = value;
        } else if (input.type === 'number') {
            // only if input is no string
            const value = this.encloseValue(input);
            if(!isNaN(value)) {
                rangeInput.value = value;
                numberInput.value = value;
            }
            else {
                numberInput.value = rangeInput.value    
            }
        }
    }

    encloseValue(input) {
        let value = parseFloat(input.value);
        const min = parseFloat(input.min);
        const max = parseFloat(input.max);

        // round to stepsize
        const step = parseFloat(input.step);
        value = Math.round(value / step) * step;
        value = value.toFixed(this.getDecimalPlaces(step));

        // keep in boundries
        if (value < min) {
            value = min;
        } else if (value > max) {
            value = max;
        }
        return value;
    }

    getDecimalPlaces(value) {
        const match = value.toString().match(/\.(\d+)$/);
        if (!match) return 0;
        return match[1].length;
    }
}

export default SliderInputWidget;
