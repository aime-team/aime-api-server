
import operator
import json
from .utils.ffmpeg import FFmpeg, MediaParams, FORMAT_CODEC_DICT
from .utils.misc import shorten_strings, run_in_executor

TYPES_DICT = {
    'string': str,
    'str': str,
    'integer': int,
    'int': int,
    'float': float,
    'bool': bool,
    'boolean': bool,
    'image': str, 
    'audio': str,
    'json': str
    }


class InputValidationHandler():
    """Handler to validate and convert API server input parameters.

    Args:
        input_params (dict): Dictionary containing all input parameters.
        ep_input_param_config (dict): Endpoint configuration of all input parameters.
        server_input_param_config (dict): Server configuration of all input parameters.
    """       

    def __init__(self, input_params, ep_input_param_config, server_input_param_config):
        """Handler to validate and convert API server input parameters.

        Args:
            input_params (dict): Dictionary containing all input parameters.
            ep_input_param_config (dict): Endpoint configuration of all input parameters.
            server_input_param_config (dict): Server configuration of all input parameters.
        """        
        self.input_params = input_params
        self.ep_input_param_config = ep_input_param_config
        self.server_input_param_config = server_input_param_config
        self.validation_errors = list()
        self.param_config = dict()
        self.param_type = str()
        self.ep_input_param_name = str()
        self.ffmpeg_cmd = list()
        self.convert_data = False


    async def validate_input_parameters(self):
        """Validate all input parameters.

        Returns:
            tuple(dict, list): Tuple of dictionary containing valid parameters and list of validation errors.
        """        
        job_data = dict()
        self.check_for_unknown_parameters()
        for ep_input_param_name, param_config in self.ep_input_param_config.items():
            self.param_config = param_config
            self.param_type = param_config.get('type', 'string')
            self.ep_input_param_name = ep_input_param_name
            value = self.validate_required_argument(self.input_params.get(ep_input_param_name))       
            value = self.validate_input_type(value)
            if self.param_type == 'selection':
                job_data[ep_input_param_name] = self.validatate_selection_parameter(value)
            else:
                if isinstance(value, (int, float)):
                    job_data[ep_input_param_name] = self.validate_number(value)
                elif isinstance(value, str):
                    if self.param_type == 'string':
                        job_data[ep_input_param_name] = self.validate_string(value)
                    elif self.param_type == 'json':
                        job_data[ep_input_param_name] = self.validate_and_convert_json(value)
                    elif self.param_type in ('audio', 'image'):
                        if FFmpeg.ffmpeg_installed:
                            job_data[ep_input_param_name] = await self.validate_media_base64_string(value)
                        else:
                            self.validation_errors.append('Media input parameters like "image" and "audio" are disabled since FFmpeg is not installed on the API Server!')

        return job_data, self.validation_errors

    
    def check_for_unknown_parameters(self):
        for param in self.input_params.keys():
            if param not in self.ep_input_param_config:
                self.validation_errors.append(f'Invalid parameter: {param}')


    def validate_required_argument(self, value):
        if value is None:
            if self.param_config.get('required'):
                self.validation_errors.append(f'Missing required argument: {self.ep_input_param_name}')
            else:
                return self.param_config.get('default', None)
        return value

    def validatate_selection_parameter(self, value):
        if value not in self.param_config.get('supported'):
            if self.param_config.get('auto_convert') == True:
                if self.param_config.get('default'):
                    return self.param_config.get('default')
                elif self.param_config.get('supported'):
                    return self.param_config.get('supported')[0]
            else:
                self.validation_errors.append(
                    f'Parameter {self.ep_input_param_name} = {value} not in supported values {self.param_config.get("supported")}!'
                    f'\nSet auto_convert = true for {self.ep_input_param_name} in the [INPUT] section of the endpoint config file to avoid this error.\n')
        else:
            return value


    def validate_input_type(self, value):
        if self.param_config.get('type') == 'selection':
            expected_value_type = type(self.param_config.get('default') or self.param_config.get('supported')[0])
        else:
            expected_value_type = TYPES_DICT[self.param_config.get('type', 'string')]
        if value is not None and not isinstance(value, expected_value_type):
            if expected_value_type in (int, float) and isinstance(value, (int, float)):
                return expected_value_type(value)
            elif self.param_config.get('auto_convert'):
                try:
                    return expected_value_type(value)
                except (ValueError, TypeError):
                    self.validation_errors.append(f'Could not convert {self.ep_input_param_name}={shorten_strings(value)} from {type(value)} to {expected_value_type}!')
            else:
                self.validation_errors.append(f'Invalid argument type {self.ep_input_param_name}={shorten_strings(value)}. Expected: {expected_value_type} but got {type(value)}!')

        else:
            return value


    def validate_number(self, param_value):
        return self.validate_numerical_value(
            param_value,
            self.ep_input_param_name,
            self.param_config
        )
        

    def validate_string(self, value):
        max_length = self.param_config.get('max_length', None)
        if max_length is not None and len(value) > max_length:
            if self.param_config.get('auto_convert'):
                return max_length
            else:
                self.validation_errors.append(f'Length of argument {self.ep_input_param_name}={shorten_strings(value)} exceeds the maximum length ({max_length})!')

        #self.validate_supported_values(self.ep_input_param_name)
        return value


    def validate_and_convert_json(self, value):
        if value:
            try:
                return json.loads(value)
            except (TypeError, json.decoder.JSONDecodeError):
                self.validation_errors.append(f'Input parameter {self.ep_input_param_name}={shorten_strings(value)} has invalid json format!')


    async def validate_media_base64_string(self, media_base64):
        """Validation of given base64 representation of media input parameter. Checks the media attributes with ffprobe and validates it with the server and the endpoint configuration. 
        If auto_convert is True in endpoint configuration, media input parameter will be converted to valid target media attributes with ffmpeg defined in the endpoint config.

        Args:
            media_base64 (str): Base64 representation of media input parameter

        Returns:
            str: Base64 representation of validated and converted media input parameter
        """        
        ffmpeg_media = FFmpeg(self.ep_input_param_name, media_base64, self.param_config, self.validation_errors)
        await ffmpeg_media.analyze()
        if not self.validation_errors:
            await run_in_executor(
                self.validate_media_parameters_on_server,
                    ffmpeg_media.media_params
            )
            target_media_params = await run_in_executor(
                self.validate_media_parameters_on_endpoint,
                    ffmpeg_media.media_params
            )
            if not self.validation_errors:
                if target_media_params != {key: value for key, value in ffmpeg_media.media_params.items() if key != "encoder"}:
                    await ffmpeg_media.convert(target_media_params)
                return await ffmpeg_media.get_data()


    def validate_media_parameters_on_server(self, params):
        if params:
            for param_name, param_value in params.items():
                arg_definition_server = self.server_input_param_config.get(self.param_type).get(param_name)
                if arg_definition_server:
                    
                    allowed_values_list = FFmpeg.get_ffmpeg_conform_parameter(arg_definition_server.get('allowed'), param_name)
                    param_value = FFmpeg.get_ffmpeg_conform_parameter(param_value, param_name)
                    value_container = param_value.split(',') if isinstance(param_value, str) else [param_value]
                    if allowed_values_list and not any(value in allowed_values_list for value in value_container):
                        self.validation_errors.append(
                            f'{"Invalid parameter" if param_value else "Unknown"} {param_name} {param_value if param_value else ""}. '+\
                            f'Only {", ".join(arg_definition_server.get("allowed"))} are allowed by the AIME API Server!'
                        )


    def validate_media_parameters_on_endpoint(self, params):
        if not self.validation_errors:
            valid_params = dict()
            for param_name, param_value in params.items():
                target_param_value = self.validate_supported_values(param_value, param_name)
                target_param_value = self.validate_numerical_attribute(target_param_value, param_name)
                if not self.param_type == 'audio' and param_name == MediaParams.SIZE:
                    target_param_value = self.validate_size(param_value, target_param_value)
                valid_params[param_name] = target_param_value
            return self.correct_invalid_format_codec_combo(valid_params)


    def validate_size(self, param_value, target_param_value):
        if param_value in (None, (0,0), (None, None)):
            self.validation_errors.append(f'Could not determine the {MediaParams.SIZE} of the parameter {self.ep_input_param_name}.')
        elif self.param_config.get(MediaParams.SIZE, {}).get('keep_aspect_ratio'):
            width, height = param_value
            target_width, target_height = target_param_value
            if height and target_height:
                original_aspect_ratio = width / height
                target_aspect_ratio = target_width / target_height
                if original_aspect_ratio > target_aspect_ratio:
                    target_height = round(target_width / original_aspect_ratio)
                else:
                    target_width = round(target_height * original_aspect_ratio)
                return self.validate_numerical_attribute((target_width, target_height), MediaParams.SIZE)
        else:
            return target_param_value


    def correct_invalid_format_codec_combo(self, valid_params):
        if self.param_type in ('image', 'video'):
            target_media_format = valid_params[MediaParams.FORMAT]
            if valid_params.get(MediaParams.VIDEO_CODEC) is not FORMAT_CODEC_DICT.get(target_media_format, target_media_format):
                valid_params[MediaParams.VIDEO_CODEC] = FORMAT_CODEC_DICT.get(target_media_format, target_media_format)               
        if self.param_type in ('audio', 'video'):
            if valid_params.get(MediaParams.AUDIO_CODEC) is not FORMAT_CODEC_DICT.get(valid_params.get(MediaParams.FORMAT), valid_params.get(MediaParams.FORMAT)):
                target_media_format = valid_params[MediaParams.FORMAT]
                valid_params[MediaParams.AUDIO_CODEC] = FORMAT_CODEC_DICT.get(target_media_format, target_media_format)
        return valid_params


    def validate_supported_values(self, param_value, param_name):
        
        arg_param_definition = self.param_config.get(param_name)
        if arg_param_definition:
            supported_value_list = FFmpeg.get_ffmpeg_conform_parameter(arg_param_definition.get('supported'), param_name)
            param_value = FFmpeg.get_ffmpeg_conform_parameter(param_value, param_name)
            value_container = param_value.split(',') if isinstance(param_value, str) else [param_value]
            if supported_value_list:
                for value in value_container:
                    if value in supported_value_list:
                        return value
                if not any(value in supported_value_list for value in value_container):
                    if arg_param_definition.get('auto_convert'):
                        return FFmpeg.get_ffmpeg_conform_parameter(arg_param_definition.get('default'), param_name)
                    else: 
                        self.validation_errors.append(
                            f'{"Invalid" if param_value else "Unknown"} {param_name}{": " + param_value + " " if param_value else ""}!\n'+\
                            f'Only {", ".join(supported_value_list)} are supported by this endpoint!\n'+\
                            f'Set {param_name}.{{ auto_convert = true }} in the [INPUT] section of the endpoint config file to avoid this error.'
                        )
            else:
                return param_value
        else:
            return param_value


    def validate_numerical_attribute(self, param_value, param_name):
        target_param_value = self.validate_numerical_value(
            param_value,
            f'{self.ep_input_param_name}.{param_name}',
            self.param_config.get(param_name)
        )
        return target_param_value


    def validate_numerical_value(self, param_value, param_name, definition):
        if definition:
            param_value = self.convert_to_limit(
                param_value,
                param_name,
                definition.get('max') or definition.get('maximum'),
                definition.get('auto_convert'),
                'max'
            )
            param_value = self.convert_to_limit(
                param_value,
                param_name,
                definition.get('min') or definition.get('minimum'),
                definition.get('auto_convert'),
                'min'
            )
            return self.convert_to_align_value(
                param_value,
                param_name,
                definition.get('align'),
                definition.get('min') or definition.get('minimum'),
                definition.get('auto_convert')
            )
        else:
            return param_value


    def convert_to_limit(self, param_value, param_name, param_limit, auto_convert, mode):
        is_out_of_limit = operator.gt if mode == 'max' else operator.lt
        if isinstance(param_value, (int, float)) and isinstance(param_limit, (int, float)):

            if is_out_of_limit(param_value, param_limit):
                if auto_convert:
                    return param_limit
                else:
                    self.validation_errors.append(
                        f'Parameter {param_name} = {param_value} is too {"high" if mode == "max" else "low"}. '+\
                        f'{mode.capitalize()} supported value for {param_name} on this endpoint is {param_limit}!\n'+\
                        f'\nSet auto_convert = true for {param_name} in the [INPUT] section of the endpoint config file to avoid this error.\n'
                    )
        elif isinstance(param_value, list) and isinstance(param_limit, (list, tuple)):
            return [self.convert_to_limit(element, param_name, element_limit, auto_convert, mode) for element, element_limit in zip(param_value, param_limit)]
        elif isinstance(param_value, tuple) and isinstance(param_limit, (list, tuple)):
            return tuple(self.convert_to_limit(element, param_name, element_limit, auto_convert, mode) for element, element_limit in zip(param_value, param_limit))
        return param_value


    def convert_to_align_value(self, param_value, param_name, align_value, min_value, auto_convert):
        if isinstance(param_value, (int, float)) and isinstance(align_value, (int, float)):
            if param_value % align_value:
                if auto_convert:
                    if isinstance(min_value, (int, float)) and (param_value - param_value % align_value) < min_value:
                        return param_value - param_value % align_value + align_value
                    else:
                        return param_value - param_value % align_value
                else:
                    self.validation_errors.append(
                        f'Parameter {param_name} = {param_value} is not aligning with {align_value}. '+\
                        f'Choose multiple of {align_value} for {param_name} on this endpoint!\n'+\
                        f'\nSet auto_convert = true for {param_name} in the [INPUT] section of the endpoint config file to avoid this error.\n'
                    )
        elif isinstance(param_value, list) and isinstance(align_value, (list, tuple)):
            return [self.convert_to_align_value(element, param_name, element_align_value, min_value, auto_convert) for element, element_align_value in zip(param_value, align_value)]
        elif isinstance(param_value, tuple) and isinstance(align_value, (list, tuple)):
            return tuple(self.convert_to_align_value(element, param_name, element_align_value, min_value, auto_convert) for element, element_align_value in zip(param_value, align_value))
        return param_value


