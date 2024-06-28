# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

import os
import sys
import time
from pathlib import Path
import shutil
import uuid
from functools import partial
from enum import Enum
import asyncio
import base64
import io
import operator

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


class MediaParams(Enum):
    FORMAT = 'format'
    DURATION = 'duration'
    SAMPLE_RATE = 'sample_rate'
    CHANNELS = 'channels'
    SAMPLE_BIT_DEPTH = 'sample_bit_depth'
    COLOR_SPACE = 'color_space'
    SIZE = 'size'
    AUDIO_BIT_RATE = 'audio_bit_rate'


VIDEO_FILTER_FLAG = '-vf'
FORMAT_FLAG = '-f'
VCODEC_FLAG = '-vcodec'
AUDIO_BIT_RATE_FLAG = '-b:a'


FFMPEG_FLAG_DICT = {
    MediaParams.FORMAT: [FORMAT_FLAG, VCODEC_FLAG, '-acodec'],
    MediaParams.DURATION: ['-t', ],
    MediaParams.SAMPLE_RATE: ['-ar', ],
    MediaParams.CHANNELS: ['-ac', ],
    MediaParams.SAMPLE_BIT_DEPTH: ['-sample_fmt', ],
    MediaParams.AUDIO_BIT_RATE: [AUDIO_BIT_RATE_FLAG, ],
    MediaParams.SIZE: [VIDEO_FILTER_FLAG, ],
    MediaParams.COLOR_SPACE: [VIDEO_FILTER_FLAG, '-pix_fmt']
}


MEDIA_ATTRIBUTE_DICT = {
    MediaParams.FORMAT: {
        'jpeg': ('mjpeg', ),
        'jpg': ('mjpeg', ),
        'webp': ('libwebp', )
    },
    MediaParams.COLOR_SPACE: {
        'rgb': ('rgb24', 'rgb0'),
        'yuv': ('yuvj420p', 'yuvj422p', 'yuvj444p'),

    },
    MediaParams.SAMPLE_BIT_DEPTH: {
        8: ('u8', 'u8p'),
        16: ('s16', 's16p'),
        32: ('s32', 'flt', 's32p', 'fltp'),
        64: ('s64', 's64p', 'dbl', 'dblp')
    }
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
            self.log_static_info(slug, route)


    def log_static_info(self, slug, route):
        compile_type = route.get('compile')

        if route.get('compiled_path'):
            compiled_path = Path(route.get('compiled_path')).resolve()
        route_path = route.get('path', route.get('file'))
        if compile_type == 'md':
            compile_str = f' ({compile_type} files compiled to html in {compiled_path} with css in {Path(route.get("css_file")).resolve()})'
        elif compile_type == 'scss':
            compile_str = f' ({compile_type} files compiled to css in {compiled_path})'
        else:
            compile_str = ''
        self.app.logger.info(f'Static: {slug} -> {(self.config_file_path / route_path).resolve()}{compile_str}')


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
        media_binary = await run_in_executor(self.convert_base64_string_to_binary, media_base64)
        if media_binary:
            media_params = await self.get_media_parameters(media_binary)
            await run_in_executor(
                self.validate_media_parameters_on_server,
                    media_params
            )
            logger.info(f'ffprobe analysis media parameters: {format_params_for_logger(media_params)}')
            target_media_params = await run_in_executor(
                self.validate_media_parameters_on_endpoint,
                    media_params
            )
            if self.convert_data and not self.validation_errors:
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


    def validate_media_parameters_on_server(self, params):
        if params:
            for param_name, param in params.items():
                arg_definition_server = self.server_input_type_config.get(self.arg_type)
                if arg_definition_server:
                    arg_param_definition_server = arg_definition_server.get(param_name.value)
                    if arg_param_definition_server:
                        allowed_values_list = arg_param_definition_server.get(f'allowed')
                        if allowed_values_list and param not in allowed_values_list:
                            self.validation_errors.append(
                                f'{"Invalid" if param else "Unknown"} {param_name.value} {param if param else ""}. '+\
                                f'Only {", ".join(allowed_values_list)} are allowed by the AIME API Server!'
                            )


    def validate_media_parameters_on_endpoint(self, params):
        if not self.validation_errors:
            valid_params = dict()
            for param_name, param_value in params.items():
                param_value = self.validate_supported_values(param_value, param_name)
                param_value = self.validate_numerical_attribute(param_value, param_name)
                valid_params[param_name] = param_value
            return valid_params


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


    def parse_media_params_from_result(self, result):
        if result:
            result = json.loads(result.decode())
            return {
                    MediaParams.FORMAT: self.get_media_format(result), 
                    MediaParams.DURATION: round(float(result.get('format', {}).get('duration'))) if result.get('format', {}).get('duration') is not None else None,
                    MediaParams.AUDIO_BIT_RATE: result.get('format', {}).get('bit_rate'),
                    MediaParams.CHANNELS: self.get_stream_param(result, 'channels', int),
                    MediaParams.SAMPLE_RATE: self.get_stream_param(result, 'sample_rate', int),
                    MediaParams.SAMPLE_BIT_DEPTH: self.get_stream_param(result, 'sample_fmt'),
                    MediaParams.COLOR_SPACE: self.get_stream_param(result, 'pix_fmt'),
                    MediaParams.SIZE: (
                        self.get_stream_param(result, 'width', int), 
                        self.get_stream_param(result, 'height', int)
                    )
            }
        else:
            return {param.value: None for param in MediaParams}


    async def get_media_parameters(self, media_binary):
        process = await asyncio.create_subprocess_exec(
            *make_ffprobe_command('pipe:0'), 
            stdin=asyncio.subprocess.PIPE, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        result, _ = await process.communicate(input=media_binary)
        media_params = self.parse_media_params_from_result(result)
        try:
            await process.stdin.wait_closed()
        except BrokenPipeError:
            pass    # Non-critical issue in asyncio.create_subprocess_exec, see https://github.com/python/cpython/issues/104340
                    # Didn't find solution for process being closed before input is fully received.
                    # BrokenPipeError only handable in process.stdin.wait_closed() but is ignored anyway. Result is still present.

        if any(param is None for param in media_params.values()):
            if media_params[MediaParams.FORMAT]:
                temp_file_name = f'{str(uuid.uuid4())[:8]}.{media_params[MediaParams.FORMAT]}'
                process = await asyncio.create_subprocess_exec(*['ffmpeg', '-i', 'pipe:0', VCODEC_FLAG, 'copy', '-acodec', 'copy', temp_file_name], stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                await process.communicate(input=media_binary)

                process = await asyncio.create_subprocess_exec(*make_ffprobe_command(temp_file_name), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                result, _ = await process.communicate()
                await aiofiles.os.remove(temp_file_name)

                media_params_copied = self.parse_media_params_from_result(result)
                media_params = {
                    key: param if param else media_params_copied[key] for key, param in media_params.items()
                }
            else:
                logger.info(f'Parameter {self.ep_input_param_name} denied. Format not recognized by ffprobe.')
        return media_params


    def get_media_format(self, result):
        media_format_list = result.get('format', {}).get('format_name', '').split(',')
        if media_format_list:
            if len(media_format_list) > 1:
                allowed_formats = self.server_input_type_config.get(self.arg_type, {}).get('format', {}).get('allowed', [])
                media_format_list = [media_format for media_format in media_format_list if media_format in allowed_formats]
            return media_format_list[0].replace('_pipe', '')


    def get_stream_param(self, result, param_name, param_type=None):
        value = None
        for stream in result.get('streams', [{}]):
            value = stream.get(param_name)
        if value is not None and param_type is not None:
            try:
                return param_type(value)
            except (ValueError, TypeError):
                return None
        return value


    async def convert_media_data(
        self,
        media_binary,
        media_params,
        target_media_params
        ):
        if self.ffmpeg_cmd:
            if FORMAT_FLAG not in self.ffmpeg_cmd:
                target_format = target_media_params.get(MediaParams.FORMAT) if not self.arg_type == 'image' else 'image2pipe'
                self.ffmpeg_cmd += [FORMAT_FLAG, MEDIA_ATTRIBUTE_DICT.get(target_format, target_format)] # using 'pipe:x' needs explicit format definition
            if VCODEC_FLAG not in self.ffmpeg_cmd and self.arg_type == 'image':
                self.ffmpeg_cmd += [
                    VCODEC_FLAG, 
                    MEDIA_ATTRIBUTE_DICT[MediaParams.FORMAT].get(
                        media_params.get(MediaParams.FORMAT), 
                        media_params.get(MediaParams.FORMAT)
                    )[0]
                ]
            if AUDIO_BIT_RATE_FLAG not in self.ffmpeg_cmd and self.arg_type == 'audio':
                self.ffmpeg_cmd += [AUDIO_BIT_RATE_FLAG, media_params.get(MediaParams.AUDIO_BIT_RATE)]

            if self.arg_type == 'audio' and FFMPEG_FLAG_DICT[MediaParams.CHANNELS][0] not in self.ffmpeg_cmd:
                self.ffmpeg_cmd += [FFMPEG_FLAG_DICT[MediaParams.CHANNELS][0], str(target_media_params.get(MediaParams.CHANNELS, 1))] # If not specifies sometimes output has different channels then source
            
            ffmpeg_cmd = ['ffmpeg', '-i', 'pipe:0'] + self.ffmpeg_cmd + ['pipe:1']
            logger.debug(f'ffmpeg command: {ffmpeg_cmd}')
            process = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            logger.info(f'Media input data converted from {format_params_for_logger(media_params)} to {format_params_for_logger(target_media_params)}')
            self.ffmpeg_cmd.clear()
            media_binary, conversion_error = await process.communicate(input=media_binary)
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
                media_params = await self.get_media_parameters(media_binary)
                logger.info(f'After conversion: ffprobe analysis media parameters: {format_params_for_logger(media_params)}')
                if target_media_params != media_params:
                    logger.debug(
                        f"WARNING: The media input parameters do not match the target parameters after the conversion! "+\
                        f"Parameters should be {format_params_for_logger(target_media_params)} but are {format_params_for_logger(media_params)}."
                    )
                    # Error handling with self.validation_errors? Sometimes conversion of sample_bit_depth doesn't work!
        return media_binary


    def validate_supported_values(self, param_value, param_name):
        
        arg_param_definition = self.arg_definition.get(param_name.value)
        if arg_param_definition:
            param_value, default_value, supported_value_list = self.get_ffmpeg_conform_parameters(param_value, param_name)
            if supported_value_list and param_value not in supported_value_list:
                if arg_param_definition.get('auto_convert'):
                    self.convert_data = True
                    self.add_ffmpeg_cmd(param_value, default_value, param_name)
                    return default_value
                else: 
                    self.validation_errors.append(
                        f'{"Invalid" if param_value else "Unknown"} {param_name}{": " + param_value + " " if param_value else ""}!\n'+\
                        f'Only {", ".join(supported_value_list)} are supported by this endpoint!\n'+\
                        f'Set {param_name}.{{ auto_convert = true }} in the [INPUT] section of the endpoint config file to avoid this error.'
                    ) 
            else:
                return param_value


    def validate_numerical_attribute(self, param_value, param_name):
        target_param_value = self.validate_numerical_value(
            param_value,
            f'{self.ep_input_param_name}.{param_name}',
            self.arg_definition.get(param_name.value)
        )
        if self.arg_type in ('audio','image') and target_param_value != param_value:
            self.convert_data = True
            self.add_ffmpeg_cmd(param_value, target_param_value, param_name)
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
        elif isinstance(param_value, (list, tuple)) and isinstance(param_limit, (list, tuple)):
            return [self.convert_to_limit(element, param_name, element_limit, auto_convert, mode) for element, element_limit in zip(param_value, param_limit)]
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
        elif isinstance(param_value, (list, tuple)) and isinstance(align_value, (list, tuple)):
            return [self.convert_to_align_value(element, param_name, element_align_value, min_value, auto_convert) for element, element_align_value in zip(param_value, align_value)]
        return param_value

    
    def add_ffmpeg_cmd(self, param_value, target_param_value, param_name):

        for flag in FFMPEG_FLAG_DICT.get(param_name, []):
            if flag == VIDEO_FILTER_FLAG:
                ffmpeg_value = self.get_video_filter_string(param_value, target_param_value, param_name)
                        
            elif flag == FORMAT_FLAG and self.arg_type == 'image':
                ffmpeg_value = 'image2pipe'
            else:
                ffmpeg_value = str(target_param_value)

            if flag in self.ffmpeg_cmd:
                self.ffmpeg_cmd[
                    self.ffmpeg_cmd.index(flag) + 1
                ] += ',' + ffmpeg_value
            else:
                self.ffmpeg_cmd += [flag, ffmpeg_value]


    def get_ffmpeg_conform_parameters(self, param_value, param_name):
        arg_param_definition = self.arg_definition.get(param_name.value)
        default_value = arg_param_definition.get('default')           
        default_value = default_value.lower() if isinstance(default_value, str) else default_value

        if param_name in MEDIA_ATTRIBUTE_DICT:
            media_attribute_dict = MEDIA_ATTRIBUTE_DICT[param_name]
            supported_value_list = []
            for supported_value in arg_param_definition.get('supported'):
                supported_value = supported_value.lower() if isinstance(supported_value, str) else supported_value
                for converted_param in media_attribute_dict.get(supported_value, [supported_value]):
                    supported_value_list.extend(
                        media_attribute_dict.get(supported_value, [supported_value])
                    )
            return media_attribute_dict.get(param_value, [param_value])[0], media_attribute_dict.get(default_value, [default_value])[0], supported_value_list
        else:
            return param_value, default_value, arg_param_definition.get('supported')


    def get_video_filter_string(self, param_value, target_param_value, param_name):

        if param_name == MediaParams.SIZE:
            crop_size, top_left = self.get_crop_parameter(param_value, target_param_value, param_name)
            return f'crop={crop_size[0]}:{crop_size[1]}:{top_left[0]}:{top_left[1]},scale={target_param_value[0]}:{target_param_value[1]}'
        elif param_name == MediaParams.COLOR_SPACE:
            return f'format={target_param_value}'


    def get_crop_parameter(self, size, target_size, param_name):
        
        target_aspect_ratio = target_size[0] / target_size[1]
        original_aspect_ratio = size[0] / size[1]
        crop_size = list(size)
        top_left = [0, 0]
        print(param_name, self.arg_definition)
        if self.arg_definition.get(param_name.value).get('resize_method') == 'crop':
            if original_aspect_ratio > target_aspect_ratio:
                # Reduce width
                crop_size[0] = int(size[1] * target_aspect_ratio)
                top_left[0] = (size[0] - crop_size[0]) // 2
            else:
                # Reduce height
                crop_size[1] = int(size[0] / target_aspect_ratio)
                top_left[1] = (size[1] - crop_size[1]) // 2

        return tuple(crop_size), tuple(top_left)


class CustomFormatter(logging.Formatter):
    BACKGROUND_AIME_DARK_BLUE = '\033[48;2;35;55;68m'
    AIME_LIGHT_BLUE ='\033[38;2;0;194;218m'
    AIME_RED = '\033[38;2;239;104;104m'
    AIME_BOLD_RED = '\033[1m\033[38;2;239;104;104m'
    AIME_YELLOW = '\033[38;2;255;188;68m'
    AIME_LIGHT_GREEN = '\033[38;2;197;229;199m'
    RESET = '\033[0m'

        

    desc_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    FORMATS = {
        logging.DEBUG: AIME_LIGHT_BLUE + desc_format + RESET,
        logging.INFO: AIME_LIGHT_GREEN + desc_format + RESET,
        logging.WARNING: AIME_YELLOW + desc_format + RESET,
        logging.ERROR: AIME_RED + desc_format + RESET,
        logging.CRITICAL: AIME_BOLD_RED + desc_format + RESET
    }

    def __init__(self, no_colour=False):
        super().__init__()
        self.no_colour = no_colour


    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno) if not self.no_colour else self.desc_format
        formatter = logging.Formatter(log_fmt, datefmt = '%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def make_ffprobe_command(input_source):
    
    return (
        'ffprobe',
        '-i', input_source,
        '-show_entries',
        'format=format_name,bit_rate,duration:stream=channels,sample_rate,sample_fmt,width,height,pix_fmt',
        '-v', 'quiet',
        '-of', 'json'
    )


def format_params_for_logger(media_params):
    return '{ ' + ', '.join(f'{key.value}: {value}' for key, value in media_params.items()) + ' }'


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
