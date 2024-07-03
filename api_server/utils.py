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
import re


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


class MediaParams(dict):
    FORMAT: str  = 'format'
    AUDIO_CODEC: str  = 'audio_codec'
    VIDEO_CODEC: str  = 'video_codec'
    DURATION: int  = 'duration'
    SAMPLE_RATE: int  = 'sample_rate'
    CHANNELS: int  = 'channels'
    SAMPLE_BIT_DEPTH: str  = 'sample_bit_depth'
    COLOR_SPACE: str  = 'color_space'
    SIZE: tuple  = 'size'
    AUDIO_BIT_RATE: int  = 'audio_bit_rate'
    VIDEO_BIT_RATE: int  = 'video_bit_rate'

    def __init__(self):
        super().__init__({
            self.FORMAT: None,
            self.AUDIO_CODEC: None,
            self.VIDEO_CODEC: None,
            self.DURATION: None,
            self.SAMPLE_RATE: None,
            self.CHANNELS: None,
            self.SAMPLE_BIT_DEPTH: None,
            self.COLOR_SPACE: None,
            self.SIZE: None,
            self.AUDIO_BIT_RATE: None,
            self.VIDEO_BIT_RATE: None,
        })


VIDEO_FILTER_FLAG = '-vf'
FORMAT_FLAG = '-f'
VIDEO_CODEC_FLAG = '-vcodec'
AUDIO_CODEC_FLAG = '-acodec'
AUDIO_BIT_RATE_FLAG = '-b:a'


FFMPEG_FLAG_DICT = {
    MediaParams.FORMAT: [FORMAT_FLAG, ],
    MediaParams.AUDIO_CODEC: [AUDIO_CODEC_FLAG, ],
    MediaParams.VIDEO_CODEC: [VIDEO_CODEC_FLAG, ],
    MediaParams.DURATION: ['-t', ],
    MediaParams.SAMPLE_RATE: ['-ar', ],
    MediaParams.CHANNELS: ['-ac', ],
    MediaParams.SAMPLE_BIT_DEPTH: ['-sample_fmt', ],
    MediaParams.AUDIO_BIT_RATE: [AUDIO_BIT_RATE_FLAG, ],
    MediaParams.SIZE: [VIDEO_FILTER_FLAG, ],
    MediaParams.COLOR_SPACE: [VIDEO_FILTER_FLAG, '-pix_fmt']
}


FFPROBE_DICT = {
    MediaParams.FORMAT: 'format_name',
    MediaParams.AUDIO_CODEC: 'codec_name',
    MediaParams.VIDEO_CODEC: 'codec_name',
    MediaParams.AUDIO_BIT_RATE: 'bit_rate',
    MediaParams.VIDEO_BIT_RATE: 'bit_rate',
    MediaParams.DURATION: 'duration',
    MediaParams.CHANNELS: 'channels',
    MediaParams.SAMPLE_RATE: 'sample_rate',
    MediaParams.SAMPLE_BIT_DEPTH: 'sample_fmt',
    MediaParams.COLOR_SPACE: 'pix_fmt',                        
    MediaParams.SIZE: ('width', 'height')
}

FORMAT_CODEC_DICT = {
    'ogg': 'libvorbis',
    'jpeg': 'mjpeg',
    'jpg': 'mjpeg',
}

MIME_TYPE_DICT = {
    'jpg': lambda media_type: 'jpeg',
    'vnd.wave': lambda media_type: 'wav',
    'mpeg': lambda media_type: 'mp3' if media_type == 'audio' else 'mp4',
}


MEDIA_ATTRIBUTE_DICT = {
    MediaParams.FORMAT: {
        'jpg': ('jpeg', 'image2'),
        'jpeg': ('jpeg', 'image2'),
        'png': ('png', 'image2'),
        'webp': ('webp', 'libwebp'),
        'image2': ('jpeg', 'png'),
        'mp3': ('mp3', 'libmp3lame'),
    },
    MediaParams.COLOR_SPACE: {
        'rgb': (
            'rgb24', 'rgb0', 'rgb565be', 'rgb565le', 'rgb555be', 
            'rgb555le', 'rgb444le', 'rgb444be', 'rgb48be', 'rgb48le', 
            'rgb8', 'rgb4', 'rgb4_byte', 'x2rgb10le', 'x2rgb10be'
        ),
        'rgba': (
            'rgba', 'argb', 'abgr', 'bgra', 'rgba64be', 'rgba64le', 
            'bgra64be', 'bgra64le'
        ),
        'bgr': (
            'bgr24', '0bgr', 'bgr444le', 'bgr444be', 'bgr565be', 
            'bgr565le', 'bgr555be', 'bgr555le', 'bgr48be', 'bgr48le', 
            'bgr8', 'bgr4', 'bgr4_byte'
        ),
        'gbr': (
            'gbrp', 'gbrp9be', 'gbrp9le', 'gbrp10be', 'gbrp10le', 
            'gbrp16be', 'gbrp16le', 'gbrp12be', 'gbrp12le', 
            'gbrp14be', 'gbrp14le', 'gbrpf32be', 'gbrpf32le'
        ),
        'gbr_alpha': (
            'gbrap', 'gbrap16be', 'gbrap16le', 'gbrap12be', 
            'gbrap12le', 'gbrap10be', 'gbrap10le', 'gbrapf32be', 
            'gbrapf32le'
        ),
        'yuv': (
            'yuv420p', 'yuyv422', 'yuv422p', 'yuv444p', 'yuv410p', 
            'yuv411p', 'yuv440p', 'yuvj420p', 'yuvj422p', 'yuvj444p', 
            'yuvj440p', 'nv12', 'nv21', 'nv16', 'nv24', 'nv42', 
            'yuv420p16le', 'yuv420p16be', 'yuv422p16le', 'yuv422p16be', 
            'yuv444p16le', 'yuv444p16be', 'yuv420p9be', 'yuv420p9le', 
            'yuv420p10be', 'yuv420p10le', 'yuv422p10be', 'yuv422p10le', 
            'yuv444p9be', 'yuv444p9le', 'yuv444p10be', 'yuv444p10le', 
            'yuv422p9be', 'yuv422p9le', 'yuv420p12be', 'yuv420p12le', 
            'yuv420p14be', 'yuv420p14le', 'yuv422p12be', 'yuv422p12le', 
            'yuv422p14be', 'yuv422p14le', 'yuv444p12be', 'yuv444p12le', 
            'yuv444p14be', 'yuv444p14le', 'yuvj411p', 'yuv440p10le', 
            'yuv440p10be', 'yuv440p12le', 'yuv440p12be'
        ),
        'gray': (
            'gray', 'gray16be', 'gray16le', 'gray12be', 'gray12le', 
            'gray10be', 'gray10le', 'gray9be', 'gray9le', 'gray14be', 
            'gray14le', 'grayf32be', 'grayf32le'
        ),
        'monochrome': (
            'monow', 'monob'
        ),
        'palette': (
            'pal8'
        ),
        'alpha': (
            'ya8', 'ya16be', 'ya16le'
        ),
        'yuva': (
            'yuva420p', 'yuva422p', 'yuva444p', 'yuva420p9be', 
            'yuva420p9le', 'yuva422p9be', 'yuva422p9le', 'yuva444p9be', 
            'yuva444p9le', 'yuva420p10be', 'yuva420p10le', 'yuva422p10be', 
            'yuva422p10le', 'yuva444p10be', 'yuva444p10le', 'yuva420p16be', 
            'yuva420p16le', 'yuva422p16be', 'yuva422p16le', 'yuva444p16be', 
            'yuva444p16le', 'yuva422p12be', 'yuva422p12le', 'yuva444p12be', 
            'yuva444p12le'
        ),
        'other': (
            'uyvy422', 'yvyu422', 'p010le', 'p010be', 'p016le', 
            'p016be', 'y210le', 'y210be', 'vaapi_moco', 'vaapi_idct', 
            'vaapi_vld', 'dxva2_vld', 'vdpau', 'videotoolbox_vld', 
            'vulkan', 'drm_prime', 'opencl', 'qsv', 'mmal', 'd3d11va_vld', 
            'cuda', 'd3d11'
        )
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
                    
                    allowed_values_list = self.get_ffmpeg_conform_parameter(arg_definition_server.get('allowed'), param_name)
                    param_value = self.get_ffmpeg_conform_parameter(param_value, param_name)
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
            supported_value_list = self.get_ffmpeg_conform_parameter(arg_param_definition.get('supported'), param_name)
            param_value = self.get_ffmpeg_conform_parameter(param_value, param_name)
            value_container = param_value.split(',') if isinstance(param_value, str) else [param_value]
            if supported_value_list:
                for value in value_container:
                    if value in supported_value_list:
                        return value
                if not any(value in supported_value_list for value in value_container):
                    if arg_param_definition.get('auto_convert'):
                        return self.get_ffmpeg_conform_parameter(arg_param_definition.get('default'), param_name)
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


    def get_ffmpeg_conform_parameter(self, param_value, param_name):
        media_attribute_dict = MEDIA_ATTRIBUTE_DICT.get(param_name)
        if media_attribute_dict:
            if isinstance(param_value, (list, tuple)):
                if param_name in MEDIA_ATTRIBUTE_DICT:
                    value_list = []
                    for value in param_value:
                        value = value.lower() if isinstance(value, str) else value
                        value_list.extend(
                            media_attribute_dict.get(value, [value])
                        )
                    return value_list
            else:
                param_value = param_value.lower() if isinstance(param_value, str) else param_value
                return media_attribute_dict.get(param_value, (param_value, ))[0]
        else:
            return param_value


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


class FFmpeg():
    def __init__(
        self,
        ep_param_name,
        base64_string=None,
        config={},
        errors=None,
        media_binary=None,
        arg_type=None,
        resize_method=None,
        input_temp_file_config=None,
        output_temp_file_config=None,
        check_conversion_config=None,
        ):
        self.ep_param_name = ep_param_name
        self.base64_string = base64_string
        self.media_binary = media_binary
        self.errors = errors
        self.arg_type = config.get('type') or arg_type
        self.resize_method = resize_method or config.get('resize_method')
        self.input_temp_file_config = input_temp_file_config or config.get('input_temp_file', 'auto')
        self.output_temp_file_config = output_temp_file_config or config.get('output_temp_file', 'auto')
        self.check_conversion_config = check_conversion_config or config.get('check_conversion', True)

        self.media_params = MediaParams()
        self.media_converted = False
        self.current_temp_file = None
        self.output_temp_file = None
        self.base64_format = None
        self.base64_type = None
    

    async def analyze(self, base64_string=None, media_binary=None):
       
        self.media_binary = media_binary or self.media_binary
        if not self.media_binary:
            self.base64_string = base64_string or self.base64_string             
            self.media_binary = await run_in_executor(self.convert_base64_string_to_binary)
        await self.check_media_with_ffprobe()
        return self.media_params


    async def convert(self, target_media_params, resize_method=None):
        self.resize_method = resize_method or self.resize_method
        ffmpeg_cmd = self.make_ffmpeg_cmd(target_media_params)
        if ffmpeg_cmd:
            ffmpeg_process = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            logger.info(f'Input parameter "{self.ep_param_name}" type "{self.arg_type}" converting from {self.format_params_for_logger(self.media_params)} to {self.format_params_for_logger(target_media_params)}')
            
            self.media_binary, conversion_error = await ffmpeg_process.communicate(input=self.media_binary if not self.current_temp_file else None)
            if self.current_temp_file:
                await aiofiles.os.remove(self.current_temp_file)
                self.current_temp_file = None
            if ffmpeg_process.returncode != 0:
                self.handle_error(f'ffmpeg returned error code {ffmpeg_process.returncode} and the message {conversion_error.decode()}', TypeError)
            else:
                if self.output_temp_file:
                    self.current_temp_file = self.output_temp_file
                    async with aiofiles.open(self.output_temp_file, 'rb') as file:
                        self.media_binary = await file.read()
                self.media_converted = True
                if self.check_conversion_config:
                    await self.check_media_with_ffprobe()
                    warning = False
                    for param_name, param_value in target_media_params.items(): 
                        if self.media_params[param_name] not in MEDIA_ATTRIBUTE_DICT.get(param_name, {}).get(self.get_attribute_class(param_value, param_name), [param_value]):
                            warning = True
                    if warning:
                        logger.warning(
                            f"WARNING: The media input parameters do not match the target parameters after the conversion! "+\
                            f"Parameters should be {self.format_params_for_logger(target_media_params)} but are {self.format_params_for_logger(self.media_params)}."
                        )
        if self.current_temp_file:
            await aiofiles.os.remove(self.current_temp_file)


    def handle_error(self, error_message, error_type):
        if self.errors is not None:
            self.errors.append(error_message)
        else:
            raise error_type(error_message)


    async def get_data(self, output_format='base64'):
        if output_format == 'base64':
            if self.media_converted:
                return await run_in_executor(self.convert_binary_to_base64_string)
            else:
                return self.base64_string
        elif output_format in ('binary', bytes):
            return self.media_binary


    def get_attribute_class(self, param_value, param_name):
        for param_class, param_values in MEDIA_ATTRIBUTE_DICT.get(param_name, {}).items():
            if param_value is not None and param_value in param_values:
                return param_class


    def convert_base64_string_to_binary(self):
        if not self.base64_string :
            self.handle_error('base64_string of media input parameter {self.ep_param_name} is missing.', ValueError)
        try:
            base64_header, base64_body = self.base64_string.split(',')
            match = re.match(r'^data:(\w+)/([\w.-]+);base64$', base64_header)
            if match:
                self.base64_type = match.group(1)
                format_name = match.group(2)
                self.base64_format = MIME_TYPE_DICT.get(format_name, lambda media_type: format_name)(self.base64_type)
                self.arg_type = self.arg_type or self.base64_type          
            return base64.b64decode(base64_body)

        except (TypeError, base64.binascii.Error, ValueError) as error:
            self.handle_error(f'Invalid base64 body of media input parameter {self.ep_param_name}', error)
        except IndexError:
            self.handle_error(f'Invalid base64 format of media input parameter {self.ep_param_name}. Valid example: "data:<media_type>/<format>;base64,<body>"', IndexError)

    def convert_binary_to_base64_string(self):
        if self.media_binary and not self.errors:
            media_format = self.media_params.get(MediaParams.FORMAT).split(',')[0]
            return f'data:{self.arg_type}/{media_format};base64,' + base64.b64encode(self.media_binary).decode('utf-8')
        

    def parse_media_params_from_ffprobe_result(self, ffprobe_result):
        self.media_params = MediaParams()
        if ffprobe_result:
            ffprobe_result_dict = json.loads(ffprobe_result.decode())
            format_header = ffprobe_result_dict.get('format', {})
            streams = ffprobe_result_dict.get('streams', [{}])
            existing_stream_codec_types = [stream.get('codec_type') for stream in streams]
            if format_header:
                for param_name in self.media_params.keys():
                    if 'audio' in param_name or 'video' in param_name: # bit_rate from format header could be wrong, ogg files with dynamic bit rate show the estimated bit rate only in the format header, but only after creating a temp file
                        for existing_stream_codec_type in existing_stream_codec_types:
                            if existing_stream_codec_type in param_name:
                                self.media_params[param_name] = self.get_ffprobe_param(format_header, param_name) 
                    else:
                        self.media_params[param_name] = self.get_ffprobe_param(format_header, param_name)
            for stream in streams:
                codec_type = stream.get('codec_type')
                for param_name in self.media_params.keys():
                    if FFPROBE_DICT[param_name] in stream or FFPROBE_DICT[param_name][0] in stream:
                        if ('audio' not in param_name and 'video' not in param_name) or codec_type in param_name:
                            value = self.get_ffprobe_param(stream, param_name)
                            if value is not None or (isinstance(value, tuple) and any(value)):
                                self.media_params[param_name] = value              


    async def check_media_with_ffprobe(self):
        if not self.output_temp_file:
            ffprobe_process = await asyncio.create_subprocess_exec(
                *self.make_ffprobe_command(), 
                stdin=asyncio.subprocess.PIPE, 
                stdout=asyncio.subprocess.PIPE, 
                stderr=asyncio.subprocess.PIPE
            )
            ffprobe_result, _ = await ffprobe_process.communicate(input=self.media_binary)
            self.parse_media_params_from_ffprobe_result(ffprobe_result)
            logger.info(f'ffprobe analysis of input parameter "{self.ep_param_name}" type "{self.arg_type}": {self.format_params_for_logger(self.media_params)}')
            try:
                await ffprobe_process.stdin.wait_closed()
            except BrokenPipeError:
                pass    # Non-critical issue in asyncio.create_subprocess_exec, see https://github.com/python/cpython/issues/104340
                        # Didn't find solution for process being closed before input is fully received.
                        # BrokenPipeError only handable in process.stdin.wait_closed() but is ignored anyway. Result is still present.

            if self.media_params.get(MediaParams.FORMAT):
                if self.base64_format not in self.media_params.get(MediaParams.FORMAT, '').split(',') and not self.media_converted:
                    logger.warning(
                        f'Media format "{self.base64_format}" specified in base64 header of {self.ep_param_name} is different to' +\
                        f'media format measured by ffprobe "{self.media_params.get(MediaParams.FORMAT)}"!'
                    )
            auto_temp_file_condition = not self.arg_type == 'image' or self.media_params.get(MediaParams.FORMAT) == 'tiff' or self.base64_format == 'gif'
            if not self.current_temp_file and (self.input_temp_file_config == 'yes' or \
            (self.input_temp_file_config == 'auto' and auto_temp_file_condition)):
                self.current_temp_file = f'{str(uuid.uuid4())[:8]}.{(self.media_params.get(MediaParams.FORMAT) or self.base64_format).split(",")[0]}'
                async with aiofiles.open(self.current_temp_file, 'wb') as temp_file:
                    await temp_file.write(self.media_binary)
        if self.current_temp_file:
            ffprobe_process = await asyncio.create_subprocess_exec(*self.make_ffprobe_command(self.current_temp_file), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            ffprobe_result, _ = await ffprobe_process.communicate()
            self.parse_media_params_from_ffprobe_result(ffprobe_result)
            logger.info(f'ffprobe analysis of input parameter with temp file "{self.ep_param_name}" type "{self.arg_type}": {self.format_params_for_logger(self.media_params)}')
        if not self.media_params.get(MediaParams.FORMAT):
            self.handle_error(f'Parameter {self.ep_param_name} denied. Format not recognized by ffprobe.', TypeError)


    def get_ffprobe_param(self, ffprobe_result_section, param_name):
        ffprobe_label = FFPROBE_DICT.get(param_name, param_name)

        if isinstance(ffprobe_label, tuple):
            return tuple(self.get_ffprobe_param(ffprobe_result_section, sub_label) for sub_label in ffprobe_label)
        else:
            value = ffprobe_result_section.get(ffprobe_label)
            try:
                return round(float(value))
            except (TypeError, ValueError):
                value = value.replace('_pipe', '') if param_name == MediaParams.FORMAT else value
                return value


    def make_ffmpeg_cmd(self, target_media_params):
        ffmpeg_cmd = list()
        if self.output_temp_file_config == 'yes' or (self.output_temp_file_config == 'auto' and target_media_params.get(MediaParams.FORMAT) == 'mp4'):
            self.output_temp_file = f'{str(uuid.uuid4())[:8]}.{target_media_params.get(MediaParams.FORMAT)}'
        for target_param_name, target_param_value in target_media_params.items():
            essential_parameters = {
                'audio': (MediaParams.FORMAT, MediaParams.CHANNELS, MediaParams.AUDIO_BIT_RATE, MediaParams.AUDIO_CODEC),
                'image': (MediaParams.FORMAT, MediaParams.VIDEO_CODEC, ),
                'video': (MediaParams.FORMAT, MediaParams.CHANNELS, MediaParams.AUDIO_BIT_RATE, MediaParams.AUDIO_CODEC, MediaParams.VIDEO_CODEC)
            }
            if (target_param_value is not None and target_param_value != self.media_params.get(target_param_name)) or \
            target_param_name in essential_parameters[self.arg_type] and not self.output_temp_file:
                
                for flag in FFMPEG_FLAG_DICT.get(target_param_name, []):
                    if flag == FORMAT_FLAG:
                        if not self.output_temp_file:
                            if self.arg_type == 'image':
                                ffmpeg_value = 'image2pipe'
                            else:
                                ffmpeg_value = target_param_value
                        else:
                            ffmpeg_value = None

                    elif flag == VIDEO_FILTER_FLAG:
                        ffmpeg_value = self.get_video_filter_string(target_param_value, target_param_name)  
                    else:
                        ffmpeg_value = str(target_param_value)
                    if ffmpeg_value:
                        if flag in ffmpeg_cmd: # add to existing flags
                            ffmpeg_cmd[ffmpeg_cmd.index(flag) + 1] += ',' + ffmpeg_value
                        else:
                            ffmpeg_cmd += [flag, ffmpeg_value]

        if ffmpeg_cmd:
            if self.arg_type == 'audio':
                ffmpeg_cmd += ['-vn']
            input_source = self.current_temp_file or 'pipe:0'
            output_target = self.output_temp_file or 'pipe:1'
            
            ffmpeg_cmd = ['ffmpeg', '-i', input_source, *ffmpeg_cmd, output_target]
            logger.debug(f'ffmpeg command: {ffmpeg_cmd}')

            return ffmpeg_cmd


    def get_video_filter_string(self, target_param_value, param_name):

        if param_name == MediaParams.SIZE:
            crop_size, top_left = self.get_crop_parameter(self.media_params[param_name], target_param_value, param_name)
            return f'crop={crop_size[0]}:{crop_size[1]}:{top_left[0]}:{top_left[1]},scale={target_param_value[0]}:{target_param_value[1]}'
        elif param_name == MediaParams.COLOR_SPACE:
            return f'format={target_param_value}'
        else:
            return target_param_value


    def get_crop_parameter(self, size, target_size, param_name):

        target_aspect_ratio = target_size[0] / target_size[1]
        original_aspect_ratio = size[0] / size[1]
        crop_size = list(size)
        top_left = [0, 0]
        if self.resize_method == 'crop':
            if original_aspect_ratio > target_aspect_ratio:
                # Reduce width
                crop_size[0] = int(size[1] * target_aspect_ratio)
                top_left[0] = (size[0] - crop_size[0]) // 2
            else:
                # Reduce height
                crop_size[1] = int(size[0] / target_aspect_ratio)
                top_left[1] = (size[1] - crop_size[1]) // 2

        return tuple(crop_size), tuple(top_left)


    def make_ffprobe_command(self, input_source='pipe:0'):
        return (
            'ffprobe',
            '-i', input_source,
            '-show_entries',
            'format=format_name,duration,bit_rate:stream=codec_type,duration,bit_rate,codec_name,channels,sample_rate,sample_fmt,width,height,pix_fmt',
            '-v', 'quiet',
            '-of', 'json'
        )

    @staticmethod
    def format_params_for_logger(media_params):
        return '\n    ' + ', '.join(f'{key}: {value}' for key, value in media_params.items() if value not in (None, (None, None)))


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


