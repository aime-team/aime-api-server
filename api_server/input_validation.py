
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

    def __init__(self, input_args, ep_input_param_config, server_input_type_config):
        self.input_args = input_args
        self.ep_input_param_config = ep_input_param_config
        self.server_input_type_config = server_input_type_config
        self.validation_errors = list()
        self.arg_definition = dict()
        self.arg_type = str()
        self.ep_input_param_name = str()
        self.ffmpeg_cmd = list()
        self.convert_data = False


    async def validate_input_parameter(self):
        job_data = dict()
        self.check_for_unknown_parameters()
        for ep_input_param_name, arg_definition in self.ep_input_param_config.items():
            self.arg_definition = arg_definition
            self.arg_type = arg_definition.get('type', 'string')
            self.ep_input_param_name = ep_input_param_name
            value = self.validate_required_argument(self.input_args.get(ep_input_param_name))       
            value = self.validate_input_type(value)
            if self.arg_type == 'selection':
                job_data[ep_input_param_name] = self.validatate_selection_parameter(value)
            else:
                if isinstance(value, (int, float)):
                    job_data[ep_input_param_name] = self.validate_number(value)
                elif isinstance(value, str):
                    if self.arg_type == 'string':
                        job_data[ep_input_param_name] = self.validate_string(value)
                    elif self.arg_type == 'json':
                        job_data[ep_input_param_name] = self.validate_and_convert_json(value)
                    else:
                        job_data[ep_input_param_name] = await self.validate_media_base64_string(value)
        return job_data, self.validation_errors

    
    def check_for_unknown_parameters(self):
        for param in self.input_args.keys():
            if param not in self.ep_input_param_config:
                self.validation_errors.append(f'Invalid parameter: {param}')


    def validate_required_argument(self, value):
        if value is None:
            if self.arg_definition.get('required'):
                self.validation_errors.append(f'Missing required argument: {self.ep_input_param_name}')
            else:
                return self.arg_definition.get('default', None)
        return value

    def validatate_selection_parameter(self, value):
        if value not in self.arg_definition.get('supported'):
            if self.arg_definition.get('auto_convert') == True:
                if self.arg_definition.get('default'):
                    return self.arg_definition.get('default')
                elif self.arg_definition.get('supported'):
                    return self.arg_definition.get('supported')[0]
            else:
                self.validation_errors.append(
                    f'Parameter {self.ep_input_param_name} = {value} not in supported values {self.arg_definition.get("supported")}!'
                    f'\nSet auto_convert = true for {self.ep_input_param_name} in the [INPUT] section of the endpoint config file to avoid this error.\n')
        else:
            return value


    def validate_input_type(self, value):
        if self.arg_definition.get('type') == 'selection':
            expected_value_type = type(self.arg_definition.get('default') or self.arg_definition.get('supported')[0])
        else:
            expected_value_type = TYPES_DICT[self.arg_definition.get('type', 'string')]
        if value is not None and not isinstance(value, expected_value_type):
            if expected_value_type in (int, float) and isinstance(value, (int, float)):
                return expected_value_type(value)
            elif self.arg_definition.get('auto_convert'):
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
            self.arg_definition
        )
        

    def validate_string(self, value):
        max_length = self.arg_definition.get('max_length', None)
        if max_length is not None and len(value) > max_length:
            if self.arg_definition.get('auto_convert'):
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
        ffmpeg_media = FFmpeg(self.ep_input_param_name, media_base64, self.arg_definition, self.validation_errors)
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
            if target_media_params != ffmpeg_media.media_params and not self.validation_errors:
                await ffmpeg_media.convert(target_media_params)
                return await ffmpeg_media.get_data()


    def validate_media_parameters_on_server(self, params):
        if params:
            for param_name, param_value in params.items():
                arg_definition_server = self.server_input_type_config.get(self.arg_type).get(param_name)
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
                param_value = self.validate_supported_values(param_value, param_name)
                param_value = self.validate_numerical_attribute(param_value, param_name)
                valid_params[param_name] = param_value
            if self.arg_type in ('image', 'video'):
                target_media_format = valid_params[MediaParams.FORMAT]
                
                if valid_params.get(MediaParams.VIDEO_CODEC) != FORMAT_CODEC_DICT.get(target_media_format, target_media_format):
                    valid_params[MediaParams.VIDEO_CODEC] = FORMAT_CODEC_DICT.get(target_media_format, target_media_format)
                if params.get(MediaParams.SIZE) in (None, (0,0)):
                    self.validation_errors.append(f'Could not determine the {MediaParams.SIZE} of the parameter {self.ep_input_param_name}.')
            
            if self.arg_type in ('audio', 'video'):
                if valid_params.get(MediaParams.AUDIO_CODEC) is not FORMAT_CODEC_DICT.get(valid_params.get(MediaParams.FORMAT), valid_params.get(MediaParams.FORMAT)):
                    target_media_format = valid_params[MediaParams.FORMAT]
                    valid_params[MediaParams.AUDIO_CODEC] = FORMAT_CODEC_DICT.get(target_media_format, target_media_format)
            if self.arg_type in ('image', 'video'):
                if valid_params.get(MediaParams.VIDEO_CODEC) is not FORMAT_CODEC_DICT.get(valid_params.get(MediaParams.FORMAT), valid_params.get(MediaParams.FORMAT)):
                    target_media_format = valid_params[MediaParams.FORMAT]
                    valid_params[MediaParams.VIDEO_CODEC] = FORMAT_CODEC_DICT.get(target_media_format, target_media_format)
            return valid_params


    def validate_supported_values(self, param_value, param_name):
        
        arg_param_definition = self.arg_definition.get(param_name)
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
            self.arg_definition.get(param_name)
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


