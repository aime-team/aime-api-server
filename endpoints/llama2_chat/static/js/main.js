modelAPI = new ModelAPI('llama2_chat');


async function initializeTab() {
	modelAPI.doAPILogin(function (data) {
		console.log('Key: ' + modelAPI.clientSessionAuthKey)
	});
}

window.onload = initializeTab;

var currentText = "";
 
function onSendAPIRequest() {

	chatLogTextarea = document.getElementById('chat_log');
	chatInput = document.getElementById('chat_input');
	info_box = document.getElementById('info_box');
    info_box.textContent = 'Request sent.\nWaiting for response...';

	currentText = chatLogTextarea.value;
	currentText += 'User: ' + chatInput.value + '\nDave:'

	params = new Object();
	params.text = currentText
	params.top_k = parseInt(document.getElementById('top_k_range').value)
	params.top_p = parseFloat(document.getElementById('top_p_range').value)
	params.temperature = parseFloat(document.getElementById('temperature_range').value)
	params.seed = parseInt(document.getElementById('seed').value)

	chatInput.value = ''
  	chatLogTextarea.value = currentText;
  	chatLogTextarea.scrollTop = chatLogTextarea.scrollHeight

	modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback);
}


function onResultCallback(data) {
	infoBox = document.getElementById('info_box');
	if (data["error"]) {
		infoBox.textContent = data.error;
	}
	else {
		console.log(data)
		//num_images = parseInt(document.getElementById('num_samples_range').value);

		//imagesPerSec = num_images / data.total_duration
		if (data.seed) {
			infoBox.textContent = 'Seed: ' + data.seed + '\n';
		}
		if (data.total_duration) {
			infoBox.textContent += 'Total job duration: ' + data.total_duration + 's' + '\n';
		}
		if (data.compute_duration) {
			infoBox.textContent += 'Compute duration: ' + data.compute_duration + 's' + '\n';
		}
		if (data.num_generated_tokens) {
			infoBox.textContent += 'Generated tokens: ' + data.num_generated_tokens + '\n';
		}
		if (data.compute_duration && data.num_generated_tokens) {
			tokensPerSec = data.num_generated_tokens / data.compute_duration
			infoBox.textContent += 'Tokens per second: ' + tokensPerSec.toFixed(1) + '\n';
		}
	if (data.model_name) {
		infoBox.textContent += '\nModel name: ' + data.model_name +'\n';
	}
	
	}
	if (data.auth) {
		infoBox.textContent += 'Worker: ' + data.auth + '\n';
	}
	if (data.worker_interface_version) {
		var versionNo = data.worker_interface_version.match(/\d+\.\d+\.\d+/);

		if (versionNo) {
			infoBox.textContent += 'Worker Interface version: ' + versionNo[0] + '\n';
		}
	}
	if (data.ep_version != null) {
		infoBox.textContent += 'Endpoint version: ' + data.ep_version;
	}

	infoBox.style.height = 'auto';
	infoBox.style.height = infoBox.scrollHeight + 'px';
	chatLogTextarea.value = data.text;
	chatLogTextarea.scrollTop = chatLogTextarea.scrollHeight;
};


function onProgressCallback(progressInfo, progressData) {

	const queuePosition = progressInfo.queue_position;
	const estimate = progressInfo.estimate;
	const numWorkersOnline = progressInfo.num_workers_online;
	const progress = progressInfo.progress;
	
	if(progressData != null)
		{
			chatLogTextarea.value = currentText + ' ' + progressData.text;
			chatLogTextarea.scrollTop = chatLogTextarea.scrollHeight;
		}
	document.getElementById('tasks_to_wait_for').innerText = ' | Queue Position: ' + queuePosition;
	document.getElementById('estimate').innerText = ' | Estimate time: ' + estimate;
	document.getElementById('num_workers_online').innerText = ' | Workers online: ' + numWorkersOnline;
	document.getElementById('progress_label').innerText = ' | Generated tokens: ' + progress;
};



function handleKeyPress(event) {
    if (event.keyCode === 13) { // Check if the Enter key was pressed
      event.preventDefault(); // Prevent the default behavior of the Enter key
      onSendAPIRequest();
    }
}
  