import WidgetManager from './widgetManager.js';


class Widget {

    constructor(options) {
        this.type = options.type || null;
        this.label = options.label || null;
        this.targetId = options.targetId || 'aime-widgets';
        this.class = options.class || null;
        this.attributes = options.attributes || {}; // widget specific attributes

        this.widgetTemplate = null;
        this.widgetManager = null;
        this.registerWithManager();
        this.name = this.name = this.generateUniqueName(options.name);
        this.dataElements = {};

        this.initialize();
    }

    initialize() {
        this.createElements();
        this.insertElementsToDOM();
        this.addEventListeners();
        this.initialized = true;
    }

    createElements() {
        this.widgetTemplate = document.createElement('div');
        this.widgetTemplate.id = this.name;
        if (this.class) {
            this.widgetTemplate.classList.add(...this.class.split(' '));
        }
    }
    
    insertElementsToDOM() {
        const targetElement = document.getElementById(this.targetId);
        if (targetElement) {
            targetElement.insertAdjacentHTML('beforeend', this.widgetTemplate.outerHTML);

        }
        else {
            console.error('No targetElement was found in the DOM with Id: ', this.targetId);
        }
    }
    
    addEventListeners() {
        // to be defined in each widget type
    }

    getDataElements() {
        return this.dataElements;
    }

    generateUniqueName(initialName) {
        let uniqueName = initialName || this.label.replace(/\s+/g, '_').toLowerCase();
        while (this.isNameTaken(uniqueName)) {
            uniqueName = this.generateRandomName(uniqueName);
        }
        return uniqueName;
    }

    isNameTaken(name) {
        const existingWidget = this.widgetManager.widgets.find((w) => w.name === name);
        return !!existingWidget;
    }

    generateRandomName(baseName) {
        const randomSuffix = Math.floor(Math.random() * 1000); // Zufällige Zahl
        return `${baseName}_${randomSuffix}`;
    }

    isInitialized() {
        return this.initialized;
    }

    registerWithManager() {
        if (!WidgetManager.getInstance()) {
            this.widgetManager = new WidgetManager();
        }
        else {
            this.widgetManager = WidgetManager.getInstance();
        }
        WidgetManager.getInstance().addWidget(this);
    }
}

export default Widget;
