import time
from pathlib import Path
import shutil
import uuid

import asyncio
import base64
import io
import os
import sys
import operator
from functools import partial
from enum import Enum
import subprocess
from concurrent.futures import ThreadPoolExecutor
import json
import random


from sanic_sass import SassManifest
from sanic.log import logging

import aiofiles
from PIL import Image, UnidentifiedImageError

from .markdown_compiler import MarkDownCompiler


logger = logging.getLogger('API')
thread_pool = ThreadPoolExecutor()

class MediaParams:
    FORMAT = "format"
    DURATION = "duration"
    SAMPLE_RATE = 'sample_rate'
    CHANNELS = 'channels'
    SAMPLE_BIT_DEPTH = 'sample_bit_depth'
    COLOR_SPACE = 'color_space'
    SIZE = 'size'
    AUDIO_BIT_RATE = 'audio_bit_rate'


FFMPEG_CMD_DICT = {
    MediaParams.FORMAT: '-f',
    MediaParams.DURATION: '-t',
    MediaParams.SAMPLE_RATE: '-ar',
    MediaParams.CHANNELS: '-ac',
    MediaParams.SAMPLE_BIT_DEPTH: '-sample_fmt',
    MediaParams.AUDIO_BIT_RATE: '-b:a'
}
BIT_DEPTH_DICT = {
    8: ('u8', 'u8p'),
    16: ('s16', 's16p'),
    32: ('s32', 'flt', 's32p', 'fltp'),
    64: ('s64', 's64p', 'dbl', 'dblp')
}
TYPES_DICT = {
    'string': str,
    'str': str,
    'integer': int,
    'int': int,
    'float': float,
    'bool': bool,
    'boolean': bool,
    'image': str, 
    'audio': str
    }


class StaticRouteHandler:
    def __init__(self, config_file_path, app, endpoint_name=None):
        self.config_file_path = Path(config_file_path)
        self.endpoint_name = endpoint_name if endpoint_name else 'app'
        self.app = app
        self.num = 0


    def setup_file_route(self, slug, route):
        route_path = Path(route.get('path', route.get('file')))
        if route_path:
            if not route_path.is_absolute():
                route_path = (self.config_file_path / route_path).resolve()
            self.app.static(slug, route_path, name=f'{self.endpoint_name}_static{str(self.num)}')
            self.num += 1


    def setup_markdown_route(self, slug, route):
        route_path = route.get('path', route.get('file'))
        compiled_path = (self.config_file_path / route.get('compiled_path')).resolve()
        css_file = route.get('css_file')
        output_file = compiled_path / f'{Path(route_path).stem}.html'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        MarkDownCompiler.compile(route_path, output_file, css_file)
        self.app.static(slug, output_file, name=f'{self.endpoint_name}_static{str(self.num)}')
        self.num += 1


    def setup_scss_route(self, slug, route):
        compiled_path = (self.config_file_path / Path(route.get('compiled_path'))).resolve()
        manifest = SassManifest(slug, str(compiled_path), route.get('path', route.get('file')), css_type='scss')
        manifest.compile_webapp(self.app, register_static=True)
        self.num += 1


    def setup_static_routes(self, static_routes):
        for slug, route in static_routes.items():
            compile_type = route.get('compile')
            if compile_type == 'md':
                self.setup_markdown_route(slug, route)
            elif compile_type == 'scss':
                self.setup_scss_route(slug, route)
            else:
                self.setup_file_route(slug, route)
            self.log_static_info(slug, compile_type, route.get('path', route.get('file')))


    def log_static_info(self, slug, compile_type, route_path):
        self.app.logger.info(f'Static: {slug} -> [{compile_type}] {route_path}')



class InputValidationHandler():

    def __init__(self, input_args, ep_input_param_config, server_input_type_config):
        self.input_args = input_args
        self.ep_input_param_config = ep_input_param_config
        self.server_input_type_config = server_input_type_config
        self.validation_errors = list()
        self.arg_definition = dict()
        self.arg_type = str()
        self.ep_input_param_name = str()
        self.conversion_command = list()
        self.image = None
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
            if isinstance(value, (int, float)):
                job_data[ep_input_param_name] = self.validate_number(value)
            elif isinstance(value, str):
                if self.arg_type == 'string':
                    job_data[ep_input_param_name] = self.validate_string(value)
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


    def validate_input_type(self, value):
        expected_value_type = TYPES_DICT[self.arg_definition.get('type', 'string')]
        if value is not None and not isinstance(value, expected_value_type):
            if expected_value_type in (int, float) and isinstance(value, (int, float)):
                return expected_value_type(value)
            elif self.arg_definition.get('auto_convert'):
                try:
                    return expected_value_type(value)
                except (ValueError, TypeError):
                    self.validation_errors.append(f'Could not convert {self.ep_input_param_name}={shorten_strings(value)} from {type(value)} to {expected_value_type}')
            else:
                self.validation_errors.append(f'Invalid argument type {self.ep_input_param_name}={shorten_strings(value)}. Expected: {expected_value_type} but got {type(value)}')
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
                self.validation_errors.append(f'Length of argument {self.ep_input_param_name}={shorten_strings(value)} exceeds the maximum length ({max_length})')
        return value


    async def validate_media_base64_string(self, media_base64):
        media_binary = await run_in_executor(self.convert_base64_string_to_binary, media_base64)
        if media_binary:
            media_params = await self.get_media_parameters(media_binary)
            await run_in_executor(
                self.validate_media_parameters_on_server,
                    media_params
            )
            target_media_params = await run_in_executor(
                self.validate_media_parameters_on_endpoint,
                    media_params
            )
            if self.convert_data:
                media_binary = await self.convert_media_data(
                    media_binary,
                    media_params,
                    target_media_params,
                )
                
                return await run_in_executor(
                    self.convert_binary_to_base64_string, 
                        media_binary,
                        target_media_params
                )
            elif not self.validation_errors:
                return media_base64


    async def get_media_parameters(self, media_binary):
        if self.arg_type == 'audio':
            return await self.get_audio_parameters(media_binary)
        elif self.arg_type == 'image':
            return await run_in_executor(
                self.get_image_parameters,
                media_binary
            )


    def validate_media_parameters_on_server(self, params):
        if params:
            for param_name, param in params.items():
                arg_definition_server = self.server_input_type_config.get(self.arg_type)
                if arg_definition_server:
                    arg_param_definition_server = arg_definition_server.get(param_name)
                    if arg_param_definition_server:
                        allowed_values_list = arg_param_definition_server.get(f'allowed')
                        if allowed_values_list and param not in allowed_values_list:
                            self.validation_errors.append(
                                f'{"Invalid" if param else "Unknown"} {param_name} {param if param else ""}. '+\
                                f'Only {", ".join(allowed_values_list)} are allowed by the AIME API Server!'
                            )


    def validate_media_parameters_on_endpoint(self, params):
        if not self.validation_errors:
            valid_params = dict()
            for param_name, param_value in params.items():
                param_value = self.validate_supported_values(param_value, param_name)
                param_value = self.validate_numerical_parameter(param_value, param_name)
                valid_params[param_name] = param_value
            return valid_params


    async def convert_media_data(
        self,
        media_binary,
        media_params,
        target_media_params
        ):
        if not self.validation_errors:
            if self.arg_type == 'audio':
                return await self.convert_audio_data(media_binary, media_params, target_media_params)
            elif self.arg_type == 'image':
                return await run_in_executor(
                    self.convert_image_data,
                    media_binary,
                    target_media_params
                )

    
    def convert_base64_string_to_binary(self, base64_string):
        try:
            return base64.b64decode(base64_string.split(',')[1])
        except (TypeError, base64.binascii.Error, ValueError):
            validation_errors.append(f'Invalid base64 body')
        except IndexError:
            validation_errors.append(f'Invalid base64 format. Valid example: "data:<media_type>/<format>;base64,,<body>"')
        

    def convert_binary_to_base64_string(self, media_binary, target_media_params):
        if media_binary and not self.validation_errors:
            media_format = target_media_params.get(MediaParams.FORMAT)
            return f'data:{self.arg_type}/{media_format};base64,' + base64.b64encode(media_binary).decode('utf-8')


    async def get_audio_parameters(self, audio_binary):
        process = await asyncio.create_subprocess_exec(*make_ffprobe_command('pipe:0'), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        result, _ = await process.communicate(input=audio_binary)
        if result:
            result = json.loads(result.decode())
            media_params = {
                MediaParams.FORMAT: self.get_media_format(result), 
                MediaParams.DURATION: round(float(result.get('format', {}).get('duration'))) if result.get('format', {}).get('duration') is not None else None,
                MediaParams.AUDIO_BIT_RATE: result.get('format', {}).get('bit_rate'),
                MediaParams.CHANNELS: int(self.get_stream_param(result, 'channels')) if self.get_stream_param(result, 'channels') is not None else None,
                MediaParams.SAMPLE_RATE: int(self.get_stream_param(result, 'sample_rate')) if self.get_stream_param(result, 'sample_rate') is not None else None,
                MediaParams.SAMPLE_BIT_DEPTH: self.get_stream_param(result, 'sample_fmt')
            }
            try:
                await process.stdin.wait_closed()
            except BrokenPipeError:
                pass    # Non-critical issue in asyncio.create_subprocess_exec, see https://github.com/python/cpython/issues/104340
                        # Didn't find solution for process being closed before input is fully received.
                        # BrokenPipeError only handable in process.stdin.wait_closed() but is ignored anyway. Result is still present.

            """
            if True:#not result or b'N/A' in result:
                async with aiofiles.tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    await temp_file.write(audio_binary)
                process_2 = await asyncio.create_subprocess_exec(*make_ffprobe_command(temp_file.name), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                result, _ = await process_2.communicate() 
                await run_in_executor(os.unlink, temp_file.name)
            """
            if any(param is None for param in media_params.values()):
                if media_params[MediaParams.FORMAT]:
                    temp_file_name = f'{str(uuid.uuid4())[:8]}.{media_params[MediaParams.FORMAT]}'
                    process = await asyncio.create_subprocess_exec(*['ffmpeg', '-i', 'pipe:0', '-vcodec', 'copy', '-acodec', 'copy', temp_file_name], stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    await process.communicate(input=audio_binary)
                    process = await asyncio.create_subprocess_exec(*make_ffprobe_command(temp_file_name), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    result, _ = await process.communicate()
                    await aiofiles.os.remove(temp_file_name)
                    if result:
                        result = json.loads(result.decode())
                        media_params_copied = {
                            MediaParams.FORMAT: self.get_media_format(result), 
                            MediaParams.DURATION: round(float(result.get('format', {}).get('duration'))) if result.get('format', {}).get('duration') is not None else None,
                            MediaParams.AUDIO_BIT_RATE: result.get('format', {}).get('bit_rate'),
                            MediaParams.CHANNELS: int(self.get_stream_param(result, 'channels')) if self.get_stream_param(result, 'channels') is not None else None,
                            MediaParams.SAMPLE_RATE: int(self.get_stream_param(result, 'sample_rate')) if self.get_stream_param(result, 'sample_rate') is not None else None,
                            MediaParams.SAMPLE_BIT_DEPTH: self.get_stream_param(result, 'sample_fmt')
                        }
                        media_params = {
                            key: param if param else media_params_copied[key] for key, param in media_params.items()
                        }
                    else:
                        return media_params
                else:
                    logger.info(f'Parameter {self.ep_input_param_name} denied. Format not recognized by ffprobe.')

            logger.info(f'ffprobe analysis audio parameters: {str(media_params)}')
            return media_params

        else:
            return {
                MediaParams.FORMAT: None, 
                MediaParams.DURATION: None, 
                MediaParams.CHANNELS: None,
                MediaParams.SAMPLE_RATE: None, 
                MediaParams.SAMPLE_BIT_DEPTH: None,
                MediaParams.AUDIO_BIT_RATE: None
            }


    def get_media_format(self, result):
        media_format_list = result.get('format', {}).get('format_name', '').split(',')
        if media_format_list:
            if len(media_format_list) > 1:
                allowed_formats = self.server_input_type_config.get(self.arg_type, {}).get('format', {}).get('allowed', [])
                media_format_list = [media_format for media_format in media_format_list if media_format in allowed_formats]
            return media_format_list[0]


    def get_stream_param(self, result, param_name):
        return result.get('streams')[0].get(param_name, 0) if result.get('streams') and result.get('streams')[0] else 0


    async def convert_audio_data(
        self,
        audio_binary,
        audio_params,
        target_audio_params
        ):
        if self.conversion_command:
            if '-f' not in self.conversion_command:
                self.conversion_command += ['-f', target_audio_params.get(MediaParams.FORMAT, 'wav')] # using 'pipe:x' needs explicit format definition
            if '-ac' not in self.conversion_command:
                self.conversion_command += ['-ac', str(target_audio_params.get(MediaParams.CHANNELS, 1))] # If not specifies sometimes output has different channels then source

            conversion_command = ['ffmpeg', '-i', 'pipe:0'] + self.conversion_command + ['pipe:1']
            print(conversion_command)
            process = await asyncio.create_subprocess_exec(*conversion_command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            logger.debug(f'Audio input data converted from {str(audio_params)} to {str(target_audio_params)}')
            self.conversion_command.clear()
            audio_binary, conversion_error = await process.communicate(input=audio_binary)
            try:
                await process.stdin.wait_closed()
            except BrokenPipeError:
                pass    # Non-critical issue in asyncio.create_subprocess_exec, see https://github.com/python/cpython/issues/104340
                        # Didn't find solution for process being closed before input is fully received.
                        # BrokenPipeError only handable in process.stdin.wait_closed() but is ignored anyway. Result is still present.
            if process.returncode != 0:
                self.validation_errors.append(f'ffmpeg returned error code {process.returncode} and the message {conversion_error}')
                logger.debug(conversion_error)
            else:
                media_params = await self.get_audio_parameters(audio_binary)
                if target_audio_params != media_params:
                    logger.debug(
                        f"WARNING: The audio input parameters do not match the target parameters after the conversion! "+\
                        f"Parameters should be {target_audio_params} but are {media_params}."
                    )
                    # Error handling with self.validation_errors? Sometimes conversion of sample_bit_depth doesn't work!
        return audio_binary
       

    def get_image_parameters(self, image_binary):
        image_params = {MediaParams.FORMAT: None, MediaParams.COLOR_SPACE: None, MediaParams.SIZE: None}
        if image_binary:
            try:
                with io.BytesIO(image_binary) as buffer:
                    image = Image.open(buffer)
                    image_params = {MediaParams.FORMAT: image.format.lower(), MediaParams.COLOR_SPACE: image.mode.lower(), MediaParams.SIZE: image.size}
                    
                    self.convert_data = True
                    self.image = image.copy()
                    self.image.format = image.format                
                    return image_params
            except UnidentifiedImageError as error:
                self.validation_erros.append(error)
        return image_params


    def convert_image_data(self, image_binary, target_image_params):

        if self.convert_data:
            if self.arg_definition.get(MediaParams.SIZE) and self.arg_definition.get(MediaParams.SIZE).get('auto_convert'):
                image = resize_image(self.image, target_image_params.get(MediaParams.SIZE), self.arg_definition.get('option_resize_method', 'scale'))
            else:
                image = self.image
            target_format = target_image_params.get('format', 'jpeg')
            target_color_space = target_image_params.get(MediaParams.COLOR_SPACE, 'RGB').upper()
            if self.arg_definition.get(MediaParams.COLOR_SPACE) and self.arg_definition.get(MediaParams.COLOR_SPACE).get('auto_convert'):
                image.convert(target_color_space)
            with io.BytesIO() as buffer:
                image.save(buffer, format=target_format)
                
                logger.debug(f'Input image got converted from {str(self.image.format).lower()}, {str(image.mode).lower()} to {str(image.format).lower()}, {str(image.mode).lower()}')
                return buffer.getvalue()
        else:
            return image_binary


    def validate_supported_values(self, param_value, param_name):
        arg_param_definition = self.arg_definition.get(param_name)
        if arg_param_definition:
            supported_value_list = arg_param_definition.get('supported')
            default_value = arg_param_definition.get('default')
            if param_name == MediaParams.SAMPLE_BIT_DEPTH:
                supported_value_list, default_value = specify_sample_bit_depth(supported_value_list, default_value)
            if supported_value_list and param_value not in supported_value_list:
                if arg_param_definition.get('auto_convert'):
                    self.convert_data = True
                    if param_name in FFMPEG_CMD_DICT:
                        self.conversion_command += [FFMPEG_CMD_DICT[param_name], str(default_value)]
                    return default_value
                else: 
                    self.validation_errors.append(
                        f'{"Invalid" if param_value else "Unknown"} {param_name}{": " + param_value + " " if param_value else ""}!\n'+\
                        f'Only {", ".join(supported_value_list)} are supported by this endpoint!\n'+\
                        f'Set {param_name}.{{ auto_convert = true }} in the [INPUT] section of the endpoint config file to avoid this error.'
                    ) 
            else:
                return param_value


    def validate_numerical_parameter(self, param_value, param_name):
        param_value_unchanged = param_value
        param_value = self.validate_numerical_value(
            param_value,
            f'{self.ep_input_param_name}.{param_name}',
            self.arg_definition.get(param_name)
        )
        
        if self.arg_type == 'audio' or 'image':
            if param_value_unchanged != param_value:
                self.convert_data = True
                if param_name in FFMPEG_CMD_DICT:
                    self.conversion_command += [FFMPEG_CMD_DICT[param_name], str(param_value)]
        return param_value


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
                        f'\nSet auto_convert = true for {param_name} in the [INPUT] section of the endpoint config file to avoid this error.'
                    )
        elif isinstance(param_value, (list, tuple)) and isinstance(param_limit, (list, tuple)):
            return [self.convert_to_limit(element, param_name, element_limit, auto_convert, mode) for element, element_limit in zip(param_value, param_limit)]
        return param_value


    def convert_to_align_value(self, param_value, param_name, align_value, min_value, auto_convert):
        if isinstance(param_value, (int, float)) and isinstance(align_value, (int, float)):
            if not (param_value % align_value):
                if auto_convert:
                    if isinstance(min_value, (int, float)) and (param_value - param_value % align_value) < min_value:
                        return param_value - param_value % align_value + align_value
                    else:
                        return param_value - param_value % align_value
                else:
                    self.validation_errors.append(
                        f'Parameter {self.ep_input_param_name}.{param_name} = {param_value} is not aligning with {align_value}. '+\
                        f'Choose multiple of {align_value} for {self.ep_input_param_name}.{param_name} on this endpoint!\n'+\
                        f'\nSet auto_convert = true for {self.ep_input_param_name}.{param_name} in the [INPUT] section of the endpoint config file to avoid this error.'
                    )
        elif isinstance(param_value, (list, tuple)) and isinstance(align_value, (list, tuple)):
            return [self.convert_to_align_value(element, param_name, element_align_value, min_value, auto_convert) for element, element_align_value in zip(param_value, align_value)]
        return param_value


def make_ffprobe_command(input_source):
    
    return (
        'ffprobe',
        '-i',
        input_source,
        '-show_entries',
        'format=format_name,bit_rate,duration:stream=channels,sample_rate,sample_fmt',
        '-v',
        'quiet',
        '-of',
        'json'
    )


def resize_image(image, target_image_size, resize_method):
    if image.size != target_image_size:
        if resize_method.lower() == 'scale':
            image_resized = image.resize(target_image_size, resample=Image.Resampling.LANCZOS)
        elif resize_method.lower() == 'crop':
            image_resized = crop_center(image, *target_image_size)
        logger.debug(f'Input image got resized from {"x".join(map(str, image.size))} to {"x".join(map(str, target_image_size))} by the method "{resize_method}"')
        return image_resized
    else:
        return image


def crop_center(image, crop_width, crop_height):
    img_width, img_height = image.size
    left = (img_width - crop_width) / 2
    top = (img_height - crop_height) / 2
    right = (img_width + crop_width) / 2
    bottom = (img_height + crop_height) / 2
    return image.crop((left, top, right, bottom))


def specify_sample_bit_depth(supported_sample_bit_depth_list, default_value):
    detailed_supported_sample_bit_depth_list = []
    for param in supported_sample_bit_depth_list:
        detailed_supported_sample_bit_depth_list.extend(BIT_DEPTH_DICT.get(param))
    return detailed_supported_sample_bit_depth_list, BIT_DEPTH_DICT.get(default_value)[0]


def calculate_estimate_time(estimate_duration, start_time):
    return round(estimate_duration - (time.time() - start_time), 1)


async def run_in_executor(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, partial(func, *args, **kwargs))


def shorten_strings(obj, max_length=30):
    if isinstance(obj, dict):
        return {key: shorten_strings(value, max_length) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [shorten_strings(item, max_length) for item in obj]
    elif isinstance(obj, str) and len(obj) > max_length:
        return obj[:max_length] + "..."
    elif isinstance(obj, bytes) and len(obj) > max_length:
        return obj[:max_length] + "..."
    else:
        return obj


def generate_auth_key():
    return str(uuid.uuid4())


def check_if_valid_base64_string(test_string):
    """
    Check if given string is a valid base64-encoded string.

    Args:
        test_string (str): The string to test.

    Returns:
        bool: True if the string is a valid base64-encoded string, False otherwise.
    """
    try:
        body = test_string.split(',')[1] if ',' in test_string else None
        return base64.b64encode(base64.b64decode(body.encode('utf-8'))).decode('utf-8') == body if body else False
    except (TypeError, base64.binascii.Error, ValueError):
        return False

def copy_js_client_interface_to_frontend_folder():
    js_client_interface_folder = Path('./api_client_interfaces/js')

    if js_client_interface_folder.exists():
        js_client_interface_filename = 'model_api.js'
        frontend_folder = Path('./frontend/static/js/')
        logger.info(f'Subrepository "AIME API Client Interfaces" folder in {js_client_interface_folder.parent.resolve()} is present. Javascript client interface {js_client_interface_filename} is copied from {js_client_interface_folder.resolve()} to {frontend_folder.resolve()}.')
        shutil.copy(js_client_interface_folder / js_client_interface_filename, frontend_folder / js_client_interface_filename)