// AIME Model API Request Javascript interface
// Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
//
// This software may be used and distributed according to the terms of the MIT LICENSE

/**
 * Class for communication with the AIME Model API.
 * @class
 */
class ModelAPI {

    static version = 'JavaScript AIME API Client Interface 0.8.3';
    
    /**
    * Constructor of the class.
    * @constructor
    * @param {string} endpointName - The name of the API endpoint.
    * @param {string} user - api user
    * @param {sting} apiKey - api Key required to authenticate and authorize to use api endpoint    * 
    * @param {number} [defaultProgressIntervall=300] - The intervall for progress updates in milliseconds. The default progress update intervall is 300.
    */
    constructor(endpointName, user, apiKey, defaultProgressIntervall = 300) {
        this.endpointName = endpointName;
        this.user = user;
        this.apiKey = apiKey;
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
        
        const response = await this.fetchAsync(`/${this.endpointName}/login?user=${this.user}&key=${this.apiKey}&version=${encodeURIComponent(ModelAPI.version)}`);
        
        if (response.success) {
            return response.client_session_auth_key;
        }
        else {
            var errorMessage = `${response.error}`
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

        //if (!response.ok) {
        //    throw new Error(`Failed to fetch data from ${url}. Response ${response}`);
        //}

        return response.json();
    }

    /**
     * Method for API Key Initialization.
     * @async
     * @param {function} [resultCallback=null] - The callback after successful API key validation.
     * @param {function} [resultCallback=null] - The error callback for unsuccessful API key validation.
     * @param {sting} apiKey - optional: set to new api Key required to authenticate and authorize to use api endpoint
     * 
     */
    async initAPIKey(resultCallback = null, errorCallback = null, apiKey = null) {
        if (apiKey != null) {
            this.apiKey = apiKey;
        }
        try {
                const response = await this.fetchAsync(
                    `/api/validate_key?key=${this.apiKey}&version=${encodeURIComponent(ModelAPI.version)}`, false
                );
                if (response.success) {
                    if (resultCallback && typeof resultCallback === 'function') {
                        resultCallback(response);
                    }
                    else {
                        console.log(`API Key initialized`);
                    }
                    return response;
                }
                else {
                    var errorMessage = `${response.error}`
                    if (response.ep_version) {
                        errorMessage += ` Endpoint version: ${response.ep_version}`
                    }
                    throw new Error(errorMessage)
                }
            } 
        catch (error) {
            console.error('Error during API Key Validation:', error);
            if (errorCallback && typeof errorCallback === 'function') {
                errorCallback(error);
            }
        }
    }

    /**
     * Method for API login.
     * @async
     * @param {function} [resultCallback=null] - The callback after successful login.
     * @param {string} user - optinal: set to new api user
     * @param {sting} apiKey - optional: set to new api Key required to authenticate and authorize to use api endpoint
     * 
     */
    async doAPILogin(resultCallback = null, errorCallback = null, user = null, apiKey = null) {
        if (user != null) {
            this.user = user;
        }
        if (apiKey != null) {
            this.apiKey = apiKey;
        }
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
            if (errorCallback && typeof errorCallback === 'function') {
                errorCallback(error);
            }
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
        console.log(`URL: ${url}`);
        //console.log('progressStream: ', progressStream);

        params = await this.stringifyObjects(params)
        params.client_session_auth_key = this.clientSessionAuthKey;
        params.key = this.apiKey;
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
        const progressURL = `/${this.endpointName}/progress?key=${encodeURIComponent(this.apiKey)}&job_id=${encodeURIComponent(jobID)}`;

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
    async stringifyObjects(params) {
        var transformedParams = new Object()
        for (let key in params) {
            if (params.hasOwnProperty(key)) {
                if (typeof params[key] === 'object' && params[key] !== null) {
                    transformedParams[key] = JSON.stringify(params[key]);
                } else {
                    transformedParams[key] = params[key];
                }
            }
        }
        return transformedParams;
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
function doAPIRequest(endpointName, params, resultCallback, user = null, apiKey = null, progressCallback = null) {
    const model = new ModelAPI(endpointName, user, apiKey);
    model.initAPIKey((data) => {
        model.doAPIRequest(params, resultCallback, progressCallback);
    });
}

// Export the ModelAPI class and doAPIRequest function
module.exports = {
    ModelAPI,
    doAPIRequest
};
