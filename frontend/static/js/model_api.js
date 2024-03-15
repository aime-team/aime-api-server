// AIME Model API Request Javascript interface

/**
 * Class for communication with the AIME Model API.
 * @class
 */
class ModelAPI {

    static version = 'JavaScript AIME API Client Interface 0.5.0';
    
    /**
    * Constructor of the class.
    * @constructor
    * @param {string} endpointName - The name of the API endpoint.
    * @param {number} [defaultProgressIntervall=300] - The intervall for progress updates in milliseconds. The default progress update intervall is 300.
    */
    constructor(endpointName, defaultProgressIntervall = 300) {
        this.endpointName = endpointName;
        this.clientSessionAuthKey = null;
        this.defaultProgressIntervall = defaultProgressIntervall;
    }

    /**
     * Method for retrieving the authentication key.
     * @async
     * @param {string} endpointName - The name of the API endpoint.
     * @returns {string} - The authentication key if successful
     */
    async fetchAuthKey() {
        
        const response = await this.fetchAsync(`/${this.endpointName}/get_client_session_auth_key?version=${encodeURIComponent(ModelAPI.version)}`);
        
        if (response.success) {
            return response.client_session_auth_key;
        }
        else {
            var errorMessage = `Authentication failed! ${response.msg}.`
            if (response.ep_version) {
                errorMessage += ` Endpoint version: ${response.ep_version}`
            }
            throw new Error(errorMessage)
        }
    }

    /**
     * Method for asynchronous HTTP requests (GET and POST).
     * @async
     * @param {string} url - The URL of the request.
     * @param {Object} params - The parameters of the request.
     * @param {boolean} [doPost=true] - Specifies whether the request is a POST request (default: true).
     * @returns {Object} - The JSON data of the response.
     */
    async fetchAsync(url, params, doPost = true) {
        const method = doPost ? 'POST' : 'GET';
        const headers = doPost ? { 'Content-type': 'application/json; charset=UTF-8' } : {};
        const body = doPost ? JSON.stringify(params) : null;

        const response = await fetch(url, { method, headers, body });

        // if (response.ok) {
        //    ...
        // }
        // else {
        //     switch (response.status) {
        //         case 401: // Unauthorized
        //             // ...
        //             break;
            
        //         default:
        //             break;
        //     }
        // }

        return response.json();
    }

    /**
     * Method for API login.
     * @async
     * @param {function} [resultCallback=null] - The callback after successful login.
     */
    async doAPILogin(resultCallback = null) {
        try {
            const authKey = await this.fetchAuthKey();
            this.clientSessionAuthKey = authKey;
            console.log(`Login successful. Got API Key: ${this.clientSessionAuthKey}`);
            if (resultCallback && typeof resultCallback === 'function') {
                resultCallback(authKey);
            }
        } 
        catch (error) {
            console.error('Error during API login:', error);
        }
    }

    /**
     * Method for API requests with options for progress updates.
     * @async
     * @param {Object} params - The parameters of the API request.
     * @param {function} resultCallback - The callback after the request is completed.
     * @param {function} [progressCallback=null] - The callback for progress updates.
     * @param {boolean} [progressStream=false] - Specifies whether the progress should be streamed (default: false). Attention: The stream feature is not yet fully implemented.
     */
    async doAPIRequest(params, resultCallback, progressCallback = null, progressStream = false) {
        const url = `/${this.endpointName}`;
        console.log(`sending API request to URL: ${url} with API Key: ${this.clientSessionAuthKey} and progressStream: ${progressStream}`);

        params.client_session_auth_key = this.clientSessionAuthKey;
        params.wait_for_result = !progressCallback;

        const response = await this.fetchAsync(url, params, true);
        // console.log('doAPIRequest response', response); // DEBUG output

        if (response.success) {
            const jobID = response.job_id;
            const progressInfo = {
                job_id: jobID,
                progress: 0,
                queue_position: -1,
                estimate: -1,
                num_workers_online: -1
            };
            if (progressCallback){
                progressCallback(progressInfo, null); // Initial progress update

                if (progressStream) {
                    this.setupProgressStream(jobID, resultCallback, progressCallback);
                } else {
                    this.pollProgress(url, jobID, resultCallback, progressCallback);
                }
            }
            else {
                resultCallback(response);
            }
        }
        else {
            resultCallback(response);
        }
    }

    /**
     * Method to set up a progress stream.
     * @async
     * @param {string} jobID - The ID of the job for the progress stream.
     * @param {function} progressCallback - The callback for progress updates.
     */
    async setupProgressStream(jobID, resultCallback, progressCallback) {
        console.error('Error: The stream feature is not yet fully implemented. Please call doAPIRequest() without progressStream=true.');
        alert('Attention: The stream feature is not yet fully implemented. Please call doAPIRequest() without progressStream=true.')
        const eventSourceURL = `/stream_progress?client_session_auth_key=${encodeURIComponent(this.clientSessionAuthKey)}&job_id=${encodeURIComponent(jobID)}`;
        const eventSource = new EventSource(eventSourceURL);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('eventSource.onmessage data:', data);
            const progressInfo = {
                progress: data.progress,
                queue_position: data.queue_position,
                estimate: -1
            };

            progressCallback(progressInfo, data.progress_data);

            if (data.job_state === 'done') {
                const jobResult = data.job_result;
                jobResult.job_id = data.job_id;
                jobResult.success = data.success;
                resultCallback(jobResult);
                eventSource.close();
            } else if (data.job_state === 'canceled') {
                eventSource.close();
            }
        };
    }

    /**
     * Method for polling progress updates.
     * @async
     * @param {string} url - The URL for progress updates.
     * @param {string} jobID - The ID of the job for progress updates.
     * @param {function} resultCallback - The callback after the request is completed.
     * @param {function} progressCallback - The callback for progress updates.
     */
    async pollProgress(url, jobID, resultCallback, progressCallback) {
        const progressURL = `/${this.endpointName}/progress?client_session_auth_key=${encodeURIComponent(this.clientSessionAuthKey)}&job_id=${encodeURIComponent(jobID)}`;

        const fetchProgress = async (progressURL) => {
            try {
                const response = await fetch(progressURL);
                return response.json();
            } catch (error) {
                console.error('Error fetching progress data:', error);
                return {};
            }
        }

        const checkProgress = async () => {
            const result = await fetchProgress(progressURL);
            // console.log(`Poll Progress: ${result.success}, job_state: ${result.job_state}`, result);

            if (result.success) {
                if (result.job_state === 'done') {
                    const jobResult = result.job_result;
                    resultCallback(jobResult);
                } else {
                    const progress = result.progress;
                    const progressInfo = {
                        progress: progress.progress,
                        queue_position: progress.queue_position,
                        estimate: progress.estimate,
                        num_workers_online: progress.num_workers_online
                    };

                    progressCallback(progressInfo, progress.progress_data);

                    if (result.job_state === 'canceled') {
                        // Do nothing
                    } else {
                        setTimeout(checkProgress.bind(this), this.defaultProgressIntervall);        
                    }
                }
            }
        }
        checkProgress(this.defaultProgressIntervall);
    }
}


/**
 * Simple single call interface for API requests.
 * @function
 * @param {string} endpointName - The name of the API endpoint.
 * @param {Object} params - The parameters of the API request.
 * @param {function} resultCallback - The callback after the request is completed.
 * @param {function} [progressCallback=null] - The callback for progress updates.
 */
function doAPIRequest(endpointName, params, resultCallback, progressCallback = null) {
    const model = new ModelAPI(endpointName);
    model.doAPILogin((data) => {
        model.doAPIRequest(params, resultCallback, progressCallback);
    });
}
