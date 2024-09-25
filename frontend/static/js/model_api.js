// AIME Model API Request Javascript interface
// Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
//
// This software may be used and distributed according to the terms of the MIT LICENSE

/**
 * Class for communication with the AIME Model API.
 * @class
 */
class ModelAPI {

    static version = 'JavaScript AIME API Client Interface 0.8.2';
    
    /**
    * Constructor of the class.
    * @constructor
    * @param {string} endpointName - The name of the API endpoint.
    * @param {string} user - api user
    * @param {sting} key - api Key required to authenticate and authorize to use api endpoint    * 
    * @param {number} [defaultProgressIntervall=300] - The intervall for progress updates in milliseconds. The default progress update intervall is 300.
    */
    constructor(endpointName, user, key, defaultProgressIntervall = 300) {
        this.endpointName = endpointName;
        this.user = user;
        this.key = key;
        this.clientSessionAuthKey = null;
        this.defaultProgressIntervall = defaultProgressIntervall;
        this.jobsCanceled = {};
        this.progress_input_params = {};
    }

    /**
     * Method for retrieving the authentication key.
     * @async
     * @param {string} endpointName - The name of the API endpoint.
     * @returns {string} - The authentication key if successful
     */
    async fetchAuthKey() {
        
        const response = await this.fetchAsync(`/${this.endpointName}/login?user=${this.user}&key=${this.key}&version=${encodeURIComponent(ModelAPI.version)}`);
        
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
     * Method for API login.
     * @async
     * @param {function} [resultCallback=null] - The callback after successful login.
     * @param {string} user - optinal: set to new api user
     * @param {sting} key - optional: set to new api Key required to authenticate and authorize to use api endpoint
     * 
     */
    async doAPILogin(resultCallback = null, errorCallback = null, user = null, key = null) {
        if (user != null) {
            this.user = user;
        }
        if (key != null) {
            this.key = key;
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
        console.log(`API Key: ${this.clientSessionAuthKey}`);

        params = await this.stringifyObjects(params)
        params.client_session_auth_key = this.clientSessionAuthKey;
        params.wait_for_result = !progressCallback;
        // console.log('Params', params); // DEBUG output
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
                    this.pollProgress(url, jobID, resultCallback, progressCallback, true);
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
        return response
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
    async pollProgress(url, jobID, resultCallback, progressCallback, stream = false) {
        let fetchProgress;
        let progressURL;

        if (stream) {

            progressURL = `/${this.endpointName}/progress_stream`;
            fetchProgress = async (progressURL, params) => {
                try {
                    return await this.fetchAsync(progressURL, params, true);
                } catch (error) {
                    console.error('Error fetching progress data:', error);
                    return {};
                }
            }
        }
        else {
            progressURL = `/${this.endpointName}/progress?client_session_auth_key=${encodeURIComponent(this.clientSessionAuthKey)}&job_id=${encodeURIComponent(jobID)}`;

            fetchProgress = async (progressURL, params) => {
                try {
                    const response = await fetch(progressURL);
                    return response.json();
                } catch (error) {
                    console.error('Error fetching progress data:', error);
                    return {};
                }
            }
        }


        const checkProgress = async () => {
            let params = new Object();
            if (jobID in this.progress_input_params) {
                params.progress_input_params = this.progress_input_params[jobID];
                
            }
            params.client_session_auth_key = this.clientSessionAuthKey;
            params.job_id = jobID;
            params.canceled = (jobID in this.jobsCanceled) || (null in this.jobsCanceled) ? true : false;
            delete this.jobsCanceled[jobID];
            delete this.jobsCanceled[null];

            const result = await fetchProgress(progressURL, params);
            // console.log(`Poll Progress: ${result.success}, job_state: ${result.job_state}`, result);

            if (result.success) {
                delete this.progress_input_params[jobID];
                if (params.canceled) {
                    console.log('CANCELED')
                    delete this.jobsCanceled[jobID];
                }
                else {
                    if (result.job_state === 'done') {
                        const jobResult = result.job_result;
                        resultCallback(jobResult);
                    } else {
                        const progress = result.progress;
                        if (progress) {
                            for (const progress_step of progress) { 
                                const progressInfo = {
                                    job_id: jobID,
                                    progress: progress_step.progress,
                                    queue_position: progress_step.queue_position,
                                    estimate: progress_step.estimate,
                                    num_workers_online: progress_step.num_workers_online
                                };

                                progressCallback(progressInfo, progress_step.progress_data);
                            }
                        }
                        if (result.job_state === 'canceled') {
                            // Do nothing
                        }
                        else {
                            setTimeout(checkProgress.bind(this), this.defaultProgressIntervall);        
                        }
                    }
                }
            }
        }
        checkProgress(this.defaultProgressIntervall);
    }

    async cancelRequest(jobID = null) {
        this.jobsCanceled[jobID] = true;
    }

    async append_progress_input_params(jobID, params) {
        if (jobID in this.progress_input_params) {
            this.progress_input_params[jobID].push(params)
           
        }
        else {
            this.progress_input_params[jobID] = [ params, ]
        }
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
function doAPIRequest(endpointName, params, resultCallback, user = null, key = null, progressCallback = null) {
    const model = new ModelAPI(endpointName, user, key);
    model.doAPILogin((data) => {
        model.doAPIRequest(params, resultCallback, progressCallback);
    });
}
