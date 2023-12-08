// import Widget from './widget.js';
import SliderInputWidget from './sliderInputWidget.js';
import TextAreaWidget from './textAreaWidget.js';

/*
TODO: 
- Validierungs-Feedback-Feld pro Widget oder dynamisch durch den Validator einfügen? -> https://formvalidation.io/ einbinden?
- Bulk Generation der Widgets anhand eines Eingangsobjektes, das denn vom Endpunkt erwarteten Daten entspricht
*/


class WidgetManager {
    constructor(inputObject) {
        // use as a sigleton
        if (WidgetManager.instance) {
            return WidgetManager.instance;
        }

        this.widgetTypes = [
            'sliderInput',
            'textArea',
            'textField'
            // ...
        ];

        this.widgets = [];
        this.enpointURL = inputObject.endpointURL || null;
        this.btnTxt = inputObject.btnTxt || 'Send';
       
        WidgetManager.instance = this;
        this.initialize();
    }

    initialize() {
        if(this.enpointURL) {
            // TODO: add send button
            // use btn_text
        }
    }

    createWidget(widgetObject) {
        if(this.checkIfWidgetIsNotAlreadyRegistered(widgetObject)) {
            if (widgetObject.hasOwnProperty('type') && this.widgetTypes.includes(widgetObject.type)) {
                switch (widgetObject.type) {
                    case 'sliderInput':
                        new SliderInputWidget(widgetObject); // TODO: required für Validator als option durchreichen?
                        break;
                    case 'textArea':
                        new TextAreaWidget(widgetObject);
                        
                    // ...
                    
                    default:
                        break;
                }
            }
            else {
                console.error('WidgetManager: Widget of following type is not available: ', widgetObject.type);
            }
        }
    }

    addWidget(widget) {
        this.widgets.push(widget);
    }

    checkIfWidgetIsNotAlreadyRegistered(widgetObject) {
        // TODO: check if attribute 'name' is not null or undefined
        // 
        // ...

        // check if widget with same ID already exists
        const existingWidget = this.widgets.find((w) => w.name === widgetObject.name);
        if (existingWidget) {
            console.error('WidgetManager: Abbording creation of widget. A widget with the same name already exists:', widgetObject.name, ', type:', widgetObject.type);
            return false;
        }
        else {
            return true;
        }
    }

    setEndpoint(enpointURL) {
        this.enpointURL = enpointURL;
    }

    collectData(){
        // TODO: go through all widgets and collect data 
        // validation step II: Felder prüfen, ob ausgefüllt, Typen-Korrektheit prüfen, Wertebereich usw. 
        // collect dataElements Objects and merge into one
        // then collect all data
        // ...
    }

    sendData(){
        // TODO: send data async to endpoint
        // ...
    }

    checkInitialization() {
        this.widgets.forEach(function(widget) {
            if (widget.isInitialized()) {
                console.log(widget.name + ' ist initialisiert.');
            } else {
                console.log(widget.name + ' ist nicht initialisiert.');
            }
        });
    }

    static getInstance() {
        return WidgetManager.instance || null;
    }
}

// TODO: Gruppen definieren, die dann in eigenen COLUMNS erzeugt werden
// ...


export default WidgetManager;
