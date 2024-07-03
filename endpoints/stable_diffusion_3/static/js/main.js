// Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
//
// This software may be used and distributed according to the terms of the MIT LICENSE

const API_USER = 'aime'
const API_KEY = '6a17e2a5b70603cb1a3294b4a1df67da'

const modelAPI = new ModelAPI('stable_diffusion_3', API_USER, API_KEY);

let infoBox = document.getElementById('info_box');
var inputBase64String = ''

function onSendAPIRequest() {
    params = new Object({
        negative_prompt:        document.getElementById('negative_prompt_input').value, // out of frame, lowres, text, error, cropped, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, out of frame, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck, username, watermark, signature
        num_samples:            parseInt(document.getElementById('num_samples_range').value),
        seed:                   parseInt(document.getElementById('seed_range').value),
        height:                 parseInt(document.getElementById('height_range').value),
        width:                  parseInt(document.getElementById('width_range').value),
        steps:                  parseInt(document.getElementById('steps_range').value),
        cfg_scale:              parseFloat(document.getElementById('cfg_scale_range').value),
        denoise:              parseFloat(document.getElementById('denoise_range').value),
    });
    if (inputBase64String) {
        params.image = inputBase64String;
    }
    let prompt_input = document.getElementById('prompt_input').value
    // set default prompts if empty
    // if (prompt_input === '') {
    //     prompt_input = 'Astronaut on Mars During sunset sitting on a giant rubber duck, ultra realistic, 8k, Mirrorless, 28mm lens, f/2.5 aperture, ISO 400, natural daylight'
    // }

    params.prompt = prompt_input;
    
    var provide_progress_images_radio = document.getElementsByName('provide_progress_images');
    for (i = 0; i < provide_progress_images_radio.length; i++) {
        if (provide_progress_images_radio[i].checked)
            var provide_progress_images = provide_progress_images_radio[i].value;
    }
    params.provide_progress_images = provide_progress_images;
    modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback);
}
        
function onResultCallback(data) {
    if (data.error) {
        if (data.error.indexOf('Client session authentication key not registered in API Server') > -1) {
          modelAPI.doAPILogin( () => onSendAPIRequest(), function (error) {
            infoBox.textContent = 'Login Error: ' + error + '\n';
            enableSendButton();                     
            removeSpinner();
          });
        }
        else {
            infoBox.textContent = 'Error: ' + data.error + '\n';
            if (data.images) {
                infoBox.style.height = 'auto';
                infoBox.style.height = infoBox.scrollHeight + 'px';
                
                var imageContainer = document.getElementById('image_container');
                imageContainer.innerHTML = '';
                var images = data.images;
                for (var i = 0; i < images.length; i++) {
                    var image_data = images[i].trim();
                    if (image_data) {
                        var img = document.createElement('img');
                        img.src = image_data;
                        img.classList.add('generated_image');
                        // img.style.width = '1024px';
                        img.style.marginBottom = '10px';
        
                        var imageDiv = document.createElement('div');
                        imageDiv.appendChild(img);
                        appendDownloadIcon(imageDiv, image_data, data.prompt, data.seed, i);
                        imageContainer.appendChild(imageDiv);
                    }
                }
            }
            enableSendButton();
            removeSpinner();
        }
    }
    else {
        enableSendButton();
        removeSpinner();
    
        document.getElementById('tasks_to_wait_for').innerText = '';
        document.getElementById('estimate').innerText = '';
        document.getElementById('num_workers_online').innerText = '';
        document.getElementById('progress_bar').value = 100;
        document.getElementById('progress_label').innerText = '';

        num_images = parseInt(document.getElementById('num_samples_range').value);
        console.log(data)
        imagesPerSec = num_images / data.total_duration
        infoBox.textContent = 'Prompt: ' +  data.prompt + '\nSeed: ' + data.seed + '\nTotal job duration: ' + 
            data.total_duration + 's' + '\nCompute duration: ' + data.compute_duration + 's' + '\nImages per second: ' + imagesPerSec.toFixed(1);
    
        if (data.auth) {
            infoBox.textContent += '\nWorker: ' + data.auth;
        }
        
        if (data.worker_interface_version) {
            infoBox.textContent += '\nAPI Worker Interface version: ' + data.worker_interface_version;
        }
        
        if (data.images) {
    
            infoBox.style.height = 'auto';
            infoBox.style.height = infoBox.scrollHeight + 'px';
            
            var imageContainer = document.getElementById('image_container');
            imageContainer.innerHTML = '';
            var images = data.images;
            for (var i = 0; i < images.length; i++) {
                var image_data = images[i].trim();
                if (image_data) {
                    var img = document.createElement('img');
                    img.src = image_data;
                    img.classList.add('generated_image');
                    // img.style.width = '1024px';
                    img.style.marginBottom = '10px';
    
                    var imageDiv = document.createElement('div');
                    imageDiv.appendChild(img);
                    appendDownloadIcon(imageDiv, image_data, data.prompt, data.seed, i);
                    imageContainer.appendChild(imageDiv);
                }
            }
        }
    }
}
function onProgressCallback(progress_info, progress_data) {
    const progress = progress_info.progress;
    const queue_position = progress_info.queue_position;
    const estimate = progress_info.estimate;
    const num_workers_online = progress_info.num_workers_online;
    
    if(progress_data) {
        var imageContainer = document.getElementById('image_container');
        imageContainer.innerHTML = '';
        if(progress_data.progress_images) {
            var latent_images = progress_data.progress_images;
            for (var i = 0; i < latent_images.length; i++) {
                var image_data = latent_images[i].trim();
                if (image_data) {
                    var img = document.createElement('img');
                    img.src = image_data;
                    img.style.width = '100%';
                    img.style.marginBottom = '10px';
                    img.classList.add('rounded');
                    imageContainer.appendChild(img);
                }
            }
        }
    }
    document.getElementById('tasks_to_wait_for').innerText = ' | Queue Position: ' + queue_position;
    document.getElementById('estimate').innerText = ' | Estimate time: ' + estimate;
    document.getElementById('num_workers_online').innerText = ' | Workers online: ' + num_workers_online;
    document.getElementById('progress_bar').value = progress;
    document.getElementById('progress_label').innerText = progress+'%';
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
        const button = document.getElementById('prompt_send');
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

function disableSendButton() {
    readyToSendRequest = false;
    const button = document.getElementById('prompt_send');
    if (button) {
      button.disabled = true;
      button.classList.add('disabled:opacity-50');
      button.classList.add('disabled:cursor-not-allowed');
    }
}
function enableSendButton() {
    readyToSendRequest = true;
    const button = document.getElementById('prompt_send');
    if (button) {
        button.disabled = false;
        button.classList.remove('disabled:opacity-50');
        button.classList.remove('disabled:cursor-not-allowed');
    }
}
function swapSizeValues() {
    var heightInput = document.getElementById('height_range');
    var widthInput = document.getElementById('width_range');
    var tmpValue = heightInput.value;
    heightInput.value = widthInput.value;
    widthInput.value = tmpValue;
}

function initializeSizeSwapButton() {
    var swapButton = document.createElement('div');
    swapButton.className = 'w-1/12 swap-button mx-auto my-auto pt-6 hover:cursor-pointer flex items-center justify-center';
    swapButton.innerHTML = `
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"
             xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"></path>
    `;
    swapButton.addEventListener('click', swapSizeValues);
    
    var flexContainer = document.getElementById('size_container');
    flexContainer.insertBefore(swapButton, flexContainer.children[1]);
}
function initializeImageContainer() {
    const container = document.getElementById('image_container');
    container.innerHTML = `<div class="w100 rounded flex flex-col items-center justify-center p-5 bg-gray-100">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.0" stroke="currentColor" class="w-20 h-20 text-aime_green" id="image_placeholder">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
        </svg>
        <p id="img_gen_msg" class="text-gray-400 text-sm">Your generated image will be placed here...</p>
    </div>`;
}

// TODO: if any error (get errors from ModelAPI also) -> show error
// function showNotification(msgTxt) {
//     var notification = document.createElement('div');
//     notification.className = 'notification bg-blue-500 text-white p-4 rounded';
//     notification.innerText = msgTxt;
//     document.body.appendChild(notification);
//     notification.style.display = 'block';
//     setTimeout(function() {
//         document.body.removeChild(notification);
//     }, 3000);
// }

function initializeDropZone() {
    var dropzone = document.createElement('div');
    dropzone.className = 'w100 rounded dropzone flex flex-col items-center justify-center p-7 bg-gray-100 border-2 border-dashed';
    dropzone.id = 'dropzone-content';
    dropzone.title = "Klick here to select file to be uploaded...";
    dropzone.innerHTML = `
        <div id="dropzone-preview" class="flex flex-col justify-center items-center">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-12 h-12 text-grey mb-3">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
            </svg>
            
            <p class="text-grey text-base font-bold">Drop image file here.</p>
            <p class="text-grey text-sm font-semibold">(png, jpeg, bmp or webp)</p>
        </div>
        <div id="dropzone-label" class="flex flex-col justify-center items-center">
        </div>
        <input id="dropzone-input" class="mt-7 hidden" type="file" accept="image/png, image/jpg, image/jpeg, image/bmp, image/webp, image/gif, image/tiff">
    `;
    document.getElementById('dropzone').insertAdjacentElement('afterbegin', dropzone);

    //['drag', 'dragstart', 'dragend', 'dragover', 'dragenter', 'dragleave', 'drop'].forEach(function(event) {
    //    dropzone.addEventListener(event, function(e) {
    //        e.preventDefault();
    //        e.stopPropagation();
    //    });
    //});
    dropzone.addEventListener('dragover', function() {  dropzone.classList.add('hover', 'shadow-inner'); });  
    dropzone.addEventListener('dragleave', function() { dropzone.classList.remove('hover', 'shadow-inner'); });
    dropzone.addEventListener('click', () => dropzone.querySelector('#dropzone-input').click() );
  
    dropzone.addEventListener('drop', function(e) {
        this.classList.remove('hover', 'shadow-inner');
        var file = e.dataTransfer.files[0];
        handleFileSelection(file);
      }, false);

    dropzone.querySelector('#dropzone-input').addEventListener('change', function(e) {
        var file = this.files[0];
        handleFileSelection(file);
    });
}

function handleFileSelection(file) {
    const imageInput = document.getElementById('dropzone-input');
    var allowedFormats = imageInput.accept.split(',').map(function (item) { return item.trim(); });
    input_image_type = file.type
    console.log(file.type)
    let fileSizeMB = ( ( file.size / 1024 ) / 1024).toFixed(2);

    if (allowedFormats.includes(file.type)) {
        let dropzoneContentEl = document.getElementById('dropzone-preview');
        
        
        dropzoneContentEl.innerHTML = '';
        var image = document.createElement('img');
        image.style.maxWidth = '100%';
        dropzoneContentEl.appendChild(image)
        const reader = new FileReader();
        reader.onload = function(event) {
            image.src = event.target.result;
            image.onload = function() {
                document.getElementById('dropzone-label').innerHTML = `<p class="text-xs">Filename: ${file.name}; Size: ${fileSizeMB} MB; Resolution: ${image.naturalWidth} x ${image.naturalHeight} </p>`
            }
            const base64Image = event.target.result.split(',')[1]; // Get the base64 part
            const imageType = file.type;
            inputBase64String = `data:${imageType};base64,${base64Image}`;
            appendResetIcon(dropzoneContentEl)
            
        };
        reader.readAsDataURL(file);
    } else {
        alert('Sorry, but only image files of type ' + allowedFormats + ' are allowed!');
        
    }
}



function appendDownloadIcon(containerEl, image_data, prompt, seed, indx) {
    const template = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-white shadow-md drop-shadow-md">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>`;

    const dwnldIcon = document.createElement('div');
    dwnldIcon.className = 'absolute top-0 right-0 p-2 hover:cursor-pointer';
    dwnldIcon.innerHTML = template;
    containerEl.appendChild(dwnldIcon);
    containerEl.classList.add('relative');

    dwnldIcon.addEventListener('click', ()=>{ downloadBase64File(image_data, prompt, seed, indx); });
}

function appendResetIcon(containerEl) {
   
    const template = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6 text-white shadow-md drop-shadow-md">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
</svg>`;

    const resetIcon = document.createElement('div');
    resetIcon.id = 'resetButton';
    resetIcon.title = "Remove image";
    resetIcon.className = 'resetButton absolute top-0 right-0 p-2 hover:cursor-pointer';
    resetIcon.innerHTML = template;
    // Add event listener for hover effect on SVG element
    resetIcon.addEventListener('mouseover', function() {
        const svgElement = resetIcon.querySelector('svg');
        svgElement.style.border = '1px solid #CBE4C9';
    });

    resetIcon.addEventListener('mouseout', function() {
        const svgElement = resetIcon.querySelector('svg');
        svgElement.style.border = 'none';
    });

    containerEl.appendChild(resetIcon);


    containerEl.classList.add('relative');

    resetIcon.addEventListener('click', function() {
        event.stopPropagation();
        resetDropZone()
        initializeDropZone();
    });

}


function resetDropZone() {
    document.getElementById('dropzone-content').remove();
    inputBase64String = ''

}

function downloadBase64File(base64Data, prompt, seed, indx) {
    const downloadLink = document.createElement("a");
    downloadLink.href = base64Data;

    let fileName = generateFileName(prompt);
    if(fileName === '') {
        fileName = 'sd3_empty_prompt';
    }
    fileName = fileName + '_' + seed + '_' + indx;
    downloadLink.download = fileName;
    downloadLink.click();
}

function generateFileName(text) {
    const words = text.toLowerCase().split(/\s+/);
    const stopWords = ['a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were', 'will', 'with'];
    const importantWords = words.filter(word => !stopWords.includes(word));
    const selectedWords = importantWords.slice(0, 4);
    const fileName = selectedWords.join('_');
    return fileName;
  }

function handleKeyPress(event) {
    if (event && event.keyCode === 13) {
        event.preventDefault();
        onButtonClick();
    }
 }

 let readyToSendRequest = true;

 function onButtonClick() {
    
    if(readyToSendRequest) {

        infoBox.textContent = 'Request sent.\nWaiting for response...';

        disableSendButton();
        addSpinner();
        initializeImageContainer();
    
        const image_placeholder = document.getElementById('image_placeholder');
        if(image_placeholder) {
            image_placeholder.classList.add('animate-bounce');
        }
    
        const img_gen_msg = document.getElementById('img_gen_msg');
        if(img_gen_msg) {
            img_gen_msg.textContent = 'Your image will now be generated. Please wait...';
        }
    
        // set Tabs to output section
        const output_btn =  document.getElementById('tab_button_output');
        if(!output_btn.active) {
            output_btn.click();
        }
        
        // scroll output_section into view when on mobile
        if (window.innerWidth <= 768) {
            const outputElement = document.getElementById('output_section');
            if (outputElement) {
                outputElement.scrollIntoView({ behavior: 'smooth', block: "start" });
                // window.scrollTo({ top: outputElement.offsetTop, left: 0, behavior: 'smooth' });
            }
        }
        
        onSendAPIRequest();
    }
 }

function handleImageUpload(event) {
    const fileInput = event.target;
    const imagePreview = document.getElementById('image_preview');

    if (fileInput.files && fileInput.files[0]) {
        const reader = new FileReader();
        reader.onload = function (e) {
            const image = document.createElement('img');
            image.src = e.target.result;
            image.style.maxWidth = '100%';
            imagePreview.innerHTML = ''; // Clear any previous preview
            imagePreview.appendChild(image);
			const file_name = fileInput.files[0].name;
            const file_extension_temp = file_name.split('.').pop().toLowerCase()
			const file_extension = (file_extension_temp === 'jpg') ? 'jpeg' : file_extension_temp; //convert .jpg to .jpeg
            fileInput.setAttribute('data-extension', file_extension);
        };
        reader.readAsDataURL(fileInput.files[0]);
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

function roundToNearestMultipleOf64(number) {
    if (number % 64 === 0) {
      return number;
    } else {
      return Math.round(number / 64) * 64;
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

    infoBox = document.getElementById('info_box');

    initializeSizeSwapButton();
    initializeImageContainer();
    initializeDropZone();
    refreshRangeInputLayout();

    modelAPI.doAPILogin(function (data) {
        console.log('Key: ' + modelAPI.clientSessionAuthKey)
    },
    function (error) {
        infoBox.textContent = 'Login Error: ' + error + '\n';
    });
});
