modelAPI = new ModelAPI('llama2_chat');

async function initializeTab() {
	modelAPI.doAPILogin(function (data) {
		console.log('Key: ' + modelAPI.clientSessionAuthKey)
	});
}

window.onload = initializeTab;

var text_status = "";

function onSendAPIRequest() {

	chatLogTextarea = document.getElementById('chat_log');
	chatInput = document.getElementById('chat_input');

	text_status = chatLogTextarea.value;
	text_status += 'User: ' + chatInput.value + '\nDave: '

	params = new Object();
	params.text = text_status
	params.top_k = parseInt(document.getElementById('top_k_range').value)
	params.top_p = parseFloat(document.getElementById('top_p_range').value)
	params.temperature = parseFloat(document.getElementById('temperature_range').value)
	params.seed = parseInt(document.getElementById('seed').value)

	chatInput.value = ''
  chatLogTextarea.value = text_status;
  chatLogTextarea.scrollTop = chatLogTextarea.scrollHeight

	modelAPI.doAPIRequest(params, onResultCallback, onProgressCallback);
}


function onResultCallback(data) {
	infoBox = document.getElementById('info_box');
	if (data["error"]) {
		infoBox.textContent = data.error;
	}
	else {
		if (data.seed) {
			infoBox.textContent += 'Seed: ' + data.seed + '\n';
		}
		if (data.total_duration) {
			infoBox.textContent += 'Total job duration: ' + data.total_duration + 's' + '\n';
		}
		if (data.compute_duration) {
			infoBox.textContent += 'Compute duration: ' + data.compute_duration + 's' + '\n';
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
	// infoBox.style.height = infoBox.scrollHeight + 'px';
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
			chatLogTextarea.value = text_status + progressData.text;
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
  