modelAPI = new ModelAPI('llama2_chat');

async function initialize_tab() {
	modelAPI.doAPILogin(function (data) {
		console.log('Key: ' + modelAPI.client_session_auth_key)
	});
}

window.onload = initialize_tab;

function onSendAPIRequest() {

	chat_log_textarea = document.getElementById('chat_log');
	chat_input = document.getElementById('chat_input');

	var text = chat_log_textarea.value;
	text += 'User: ' + chat_input.value + '\nDave:'

	params = new Object();
	params['text'] = text
	params['top_k'] = parseInt(document.getElementById('top_k_range').value)
	params['top_p'] = parseFloat(document.getElementById('top_p_range').value)
	params['temperature'] = parseFloat(document.getElementById('temperature_range').value)
	params['seed'] = parseInt(document.getElementById('seed').value)

	chat_input.value = ''
    chat_log_textarea.value = text;
    chat_log_textarea.scrollTop = chat_log_textarea.scrollHeight

	modelAPI.doAPIRequest(params, function (data) {
      	chat_log_textarea.value = data["text"];
      	chat_log_textarea.scrollTop = chat_log_textarea.scrollHeight;
	},
	function (progress_info, progress_data) {
		
		if(progress_data != null)
		{
			chat_log_textarea.value = text + ' ' + progress_data["text"];
			chat_log_textarea.scrollTop = chat_log_textarea.scrollHeight;
			document.getElementById('queue_position').innerText = 'Queue position: ' + progress_info['queue_position']
		}
    });
}

function handleKeyPress(event) {
    if (event.keyCode === 13) { // Check if the Enter key was pressed
      event.preventDefault(); // Prevent the default behavior of the Enter key
      onSendAPIRequest();
    }
  }
  