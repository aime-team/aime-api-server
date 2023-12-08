modelAPI = new ModelAPI('stable_diffusion_xl_txt2img');

function onSendAPIRequest() {
    params = new Object({
        negative_prompt:        document.getElementById('negative_prompt_input').value, // out of frame, lowres, text, error, cropped, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, out of frame, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck, username, watermark, signature
        num_samples:            parseInt(document.getElementById('num_samples_range').value),
        seed:                   parseInt(document.getElementById('seed_range').value),
        height:                 parseInt(document.getElementById('height_range').value),
        width:                  parseInt(document.getElementById('width_range').value),
        base_steps:             parseInt(document.getElementById('steps_base_range').value),
        refine_steps:           parseInt(document.getElementById('steps_refine_range').value),
        scale:                  parseFloat(document.getElementById('scale_range').value),
        aesthetic_score:        parseFloat(document.getElementById('aesthetic_score_range').value),
        negative_aesthetic_score: parseFloat(document.getElementById('negative_aesthetic_score_range').value),
        img2img_strength:       parseFloat(document.getElementById('img2img_strength_range').value),
        orig_width:             parseInt(document.getElementById('orig_width_range').value),
        orig_height:            parseInt(document.getElementById('orig_height_range').value),
        crop_coords_top:        parseInt(document.getElementById('crop_coords_top_range').value),
        crop_coords_left:       parseInt(document.getElementById('crop_coords_left_range').value),
        sigma_min:              parseFloat(document.getElementById('sigma_min_range').value),
        sigma_max:              parseFloat(document.getElementById('sigma_max_range').value),
        rho:                    parseFloat(document.getElementById('rho_range').value),
        s_churn:                parseFloat(document.getElementById('s_churn_range').value),
        s_tmin:                 parseFloat(document.getElementById('s_tmin_range').value),
        s_tmax:                 parseFloat(document.getElementById('s_tmax_range').value),
        s_noise:                parseFloat(document.getElementById('s_noise_range').value),
        eta:                    parseFloat(document.getElementById('eta_range').value),
        order:                  parseInt(document.getElementById('order_range').value),
        base_sampler:           document.getElementById('base_sampler').value,
        refine_sampler:         document.getElementById('refine_sampler').value,
        base_discretization:    document.getElementById('base_discretization').value,
        refine_discretization:  document.getElementById('refine_discretization').value
    });

    prompt_input = document.getElementById('prompt_input').value
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
    // prompt_input.value = '';
    modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback);
}
        
function onResultCallback(data) {
    enableSendButton();
    removeSpinner();
    if (data.images) {
        console.log(data);
        info_box = document.getElementById('info_box');
        
        if (data["error"]) {
            info_box.textContent = data.error;
        }
        else {
            info_box.textContent = 'Prompt: ' +  data.prompt + '\nSeed: ' + data.seed + '\nTotal job duration: ' + data.total_duration + 's' + '\nCompute duration: ' + data.compute_duration + 's';
        }
        if (data.auth) {
            info_box.textContent += '\nWorker: ' + data.auth;
        }
        if (data.worker_interface_version) {
            info_box.textContent += '\nAPI Worker Interface version: ' + data.worker_interface_version;
        }
        info_box.style.height = 'auto';
        // info_box.style.height = info_box.scrollHeight + 'px';
        
        var imageContainer = document.getElementById('image_container');
        var images = data.images;
        // imageContainer.innerHTML = '';
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

function downloadBase64File(base64Data, prompt, seed, indx) {
    const downloadLink = document.createElement("a");
    downloadLink.href = base64Data;

    let fileName = generateFileName(prompt);
    if(fileName === '') {
        fileName = 'sdxl_empty_prompt';
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

 function onButtonClick() {
    info_box = document.getElementById('info_box');
    info_box.textContent = 'Request sent.\nWaiting for response...';
    
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
    document.getElementById('tab_button_output').click();
    
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

function roundToNearestMultipleOf8(number) {
    if (number % 8 === 0) {
      return number;
    } else {
      return Math.round(number / 8) * 8;
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
    }
    hljs.highlightAll();

    const sliderInputs = document.querySelectorAll('.slider-widget input[type="range"]');
    sliderInputs.forEach(function(input) {
        updateSliderValue({ target: input });
        input.addEventListener('input', updateSliderValue);
        input.addEventListener('change', updateSliderValue);
    });

    const numberInputs = document.querySelectorAll('.slider-widget input[type="number"]');
    numberInputs.forEach(function(input) {
        input.addEventListener('input', updateSliderValue);
    });

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

    initializeSizeSwapButton();
    initializeImageContainer();
    refreshRangeInputLayout();
    modelAPI.doAPILogin();

});
