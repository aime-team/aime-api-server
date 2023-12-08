import Widget from './widget.js';

/*
#### TextAreaWidget ####

type: 'textArea',
label: '', 
name: '', 
targetId: '',
attributes: {
    readonly: true
}

*/

class TextAreaWidget extends Widget {
    constructor(options) {
        super(options);
    }

    initialize() {
        this.readonly = this.attributes.readonly || false;
        super.initialize();
    }
    
    createElements() {
        super.createElements();
        
        if (this.label) {
            const label = document.createElement('label');
            label.setAttribute('for', this.name);
            label.textContent = this.label;
            this.widgetTemplate.appendChild(label);
        }

        const textarea = document.createElement('textarea');
        textarea.setAttribute('id', this.name + '_textarea');
        textarea.readOnly = this.readonly;
        this.widgetTemplate.appendChild(textarea);
    }
}

export default TextAreaWidget;
