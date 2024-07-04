import uuid
import asyncio
import base64
import subprocess
import json
import re
from sanic.log import logging
import aiofiles

from .misc import run_in_executor

logger = logging.getLogger('API')

class MediaParams(dict):
    """Specialized dictionary class designed to store media parameter information.
    It inherits from Python's built-in dict class and predefines keys related to the media attributes.
    """    
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



class FFmpeg():
    """Python binding for FFmpeg to analyze and convert media data.

    Args:
        param_name (str): Name of the input parameter.
        base64_string (str, optional): String of base64 encoded input parameter. Defaults to None.
        config (dict, optional): Configuration of parameter containing arg_type, resize_method, input_temp_file_config, output_temp_file_config and check_conversion_config. Defaults to {}.
        errors (list, optional): Error list to accumulate errors occuring during media analysis or conversion. If not given, errors will be raise. Defaults to None.
        media_binary (bytes, optional): Binary data of input data as alternative to base64_string. Defaults to None.
        arg_type (str, optional): Input parameter type. Must be present if no config is given. Supported values: ('image', 'audio', 'video'). Defaults to None.
        resize_method (str, optional): Resize method for input image conversion. Supported values: ('scale', 'crop'). Defaults to None.
        input_temp_file_config (str, optional): Config whether an input temp file is generated. Supported values: ('auto', 'yes', 'no'). Defaults to None.
        output_temp_file_config (str, optional): Config whether an output temp file is generated. Supported values: ('auto', 'yes', 'no'). Defaults to None.
        check_conversion_config (bool, optional): Config whether to check if the media attributes of the input parameter are as supposed after its conversion. Defaults to False.
    """        
    def __init__(
        self,
        param_name,
        base64_string=None,
        config={},
        errors=None,
        media_binary=None,
        arg_type=None,
        resize_method=None,
        input_temp_file_config=None,
        output_temp_file_config=None,
        check_conversion_config=False,
        ):
        """Python binding for FFmpeg to analyze and convert media data.

        Args:
            param_name (str): Name of the input parameter.
            base64_string (str, optional): String of base64 encoded input parameter. Defaults to None.
            config (dict, optional): Configuration of parameter containing arg_type, resize_method, input_temp_file_config, output_temp_file_config and check_conversion_config. Defaults to {}.
            errors (list, optional): Error list to accumulate errors occuring during media analysis or conversion. If not given, errors will be raise. Defaults to None.
            media_binary (bytes, optional): Binary data of input data as alternative to base64_string. Defaults to None.
            arg_type (str, optional): Input parameter type. Must be present if no config is given. Supported values: ('image', 'audio', 'video'). Defaults to None.
            resize_method (str, optional): Resize method for input image conversion. Supported values: ('scale', 'crop'). Defaults to None.
            input_temp_file_config (str, optional): Config whether an input temp file is generated. Supported values: ('auto', 'yes', 'no'). Defaults to None.
            output_temp_file_config (str, optional): Config whether an output temp file is generated. Supported values: ('auto', 'yes', 'no'). Defaults to None.
            check_conversion_config (bool, optional): Config whether to check if the media attributes of the input parameter are as supposed after its conversion. Defaults to False.
        """        
        self.param_name = param_name
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
        """Analyze input parameter with ffprobe. Save the measured media parameters in self.media_params and return it.

        Args:
            base64_string (str, optional): String of base64 encoded input parameter. Defaults to None.
            media_binary (bytes, optional): Binary data of input data as alternative to base64_string. Defaults to None. Defaults to None.

        Returns:
            MediaParams: Measured media parameters as instance of MediaParams.
        """        
       
        self.media_binary = media_binary or self.media_binary
        if not self.media_binary:
            self.base64_string = base64_string or self.base64_string             
            self.media_binary = await run_in_executor(self.convert_base64_string_to_binary)
        await self.__check_media_with_ffprobe()
        return self.media_params


    async def convert(self, target_media_params, resize_method=None):
        """Convert input parameter with ffmpeg to given target_media_paramters

        Args:
            target_media_params (MediaParams or dict): Target media parameters for conversion.
            resize_method (str, optional): Resize method for input image conversion to change resize method given at initialization. Supported values: ('scale', 'crop'). Defaults to None.
        """        
        self.resize_method = resize_method or self.resize_method
        ffmpeg_cmd = self.__make_ffmpeg_cmd(target_media_params)
        if ffmpeg_cmd:
            ffmpeg_process = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            logger.info(f'Input parameter "{self.param_name}" type "{self.arg_type}" converting from {self.format_params_for_logger(self.media_params)} to {self.format_params_for_logger(target_media_params)}')
            
            self.media_binary, conversion_error = await ffmpeg_process.communicate(input=self.media_binary if not self.current_temp_file else None)
            if self.current_temp_file:
                await aiofiles.os.remove(self.current_temp_file)
                self.current_temp_file = None
            if ffmpeg_process.returncode != 0:
                self.__handle_error(f'ffmpeg returned error code {ffmpeg_process.returncode} and the message {conversion_error.decode()}', TypeError)
            else:
                if self.output_temp_file:
                    self.current_temp_file = self.output_temp_file
                    async with aiofiles.open(self.output_temp_file, 'rb') as file:
                        self.media_binary = await file.read()
                self.media_converted = True
                if self.check_conversion_config:
                    await self.__check_media_with_ffprobe()
                    warning = False
                    for param_name, param_value in target_media_params.items(): 
                        if self.media_params[param_name] not in MEDIA_ATTRIBUTE_DICT.get(param_name, {}).get(self.__get_attribute_class(param_value, param_name), [param_value]):
                            warning = True
                    if warning:
                        logger.warning(
                            f"WARNING: The media input parameters do not match the target parameters after the conversion! "+\
                            f"Parameters should be {self.format_params_for_logger(target_media_params)} but are {self.format_params_for_logger(self.media_params)}."
                        )
        if self.current_temp_file:
            await aiofiles.os.remove(self.current_temp_file)


    async def get_data(self, output_format='base64'):
        """Get the base64 or binary representation of the stored media data

        Args:
            output_format (str, optional): Desired output format. Supported values: ('base64', 'binary'). Defaults to 'base64'.

        Returns:
            str or bytes: Base64 or binary representation of stored media data.
        """        
        if output_format == 'base64':
            if self.media_converted:
                return await run_in_executor(self.convert_binary_to_base64_string)
            else:
                return self.base64_string
        elif output_format in ('binary', bytes):
            return self.media_binary



    def convert_base64_string_to_binary(self):
        if not self.base64_string :
            self.__handle_error(f'base64_string of media input parameter {self.param_name} is missing.', ValueError)
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
            self.__handle_error(f'Invalid base64 body of media input parameter {self.param_name}', error)
        except IndexError:
            self.__handle_error(f'Invalid base64 format of media input parameter {self.param_name}. Valid example: "data:<media_type>/<format>;base64,<body>"', IndexError)

    def convert_binary_to_base64_string(self):
        if self.media_binary and not self.errors:
            media_format = self.media_params.get(MediaParams.FORMAT).split(',')[0]
            return f'data:{self.arg_type}/{media_format};base64,' + base64.b64encode(self.media_binary).decode('utf-8')
        

    def __handle_error(self, error_message, error_type):
        if self.errors is not None:
            self.errors.append(error_message)
        else:
            raise error_type(error_message)


    def __parse_media_params_from_ffprobe_result(self, ffprobe_result):
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
                                self.media_params[param_name] = self.__get_ffprobe_param(format_header, param_name) 
                    else:
                        self.media_params[param_name] = self.__get_ffprobe_param(format_header, param_name)
            for stream in streams:
                codec_type = stream.get('codec_type')
                for param_name in self.media_params.keys():
                    if FFPROBE_DICT[param_name] in stream or FFPROBE_DICT[param_name][0] in stream:
                        if ('audio' not in param_name and 'video' not in param_name) or codec_type in param_name:
                            value = self.__get_ffprobe_param(stream, param_name)
                            if value is not None or (isinstance(value, tuple) and any(value)):
                                self.media_params[param_name] = value              


    async def __check_media_with_ffprobe(self):
        if not self.output_temp_file:
            ffprobe_process = await asyncio.create_subprocess_exec(
                *self.__make_ffprobe_command(), 
                stdin=asyncio.subprocess.PIPE, 
                stdout=asyncio.subprocess.PIPE, 
                stderr=asyncio.subprocess.PIPE
            )
            ffprobe_result, _ = await ffprobe_process.communicate(input=self.media_binary)
            self.__parse_media_params_from_ffprobe_result(ffprobe_result)
            logger.info(f'ffprobe analysis of input parameter "{self.param_name}" type "{self.arg_type}": {self.format_params_for_logger(self.media_params)}')
            try:
                await ffprobe_process.stdin.wait_closed()
            except BrokenPipeError:
                pass    # Non-critical issue in asyncio.create_subprocess_exec, see https://github.com/python/cpython/issues/104340
                        # Didn't find solution for process being closed before input is fully received.
                        # BrokenPipeError only handable in process.stdin.wait_closed() but is ignored anyway. Result is still present.

            if self.media_params.get(MediaParams.FORMAT):
                if self.base64_format not in self.media_params.get(MediaParams.FORMAT, '').split(',') and not self.media_converted:
                    logger.warning(
                        f'Media format "{self.base64_format}" specified in base64 header of {self.param_name} is different to' +\
                        f'media format measured by ffprobe "{self.media_params.get(MediaParams.FORMAT)}"!'
                    )
            auto_temp_file_condition = not self.arg_type == 'image' or self.media_params.get(MediaParams.FORMAT) == 'tiff' or self.base64_format == 'gif'
            if not self.current_temp_file and (self.input_temp_file_config == 'yes' or \
            (self.input_temp_file_config == 'auto' and auto_temp_file_condition)):
                self.current_temp_file = f'{str(uuid.uuid4())[:8]}.{(self.media_params.get(MediaParams.FORMAT) or self.base64_format).split(",")[0]}'
                async with aiofiles.open(self.current_temp_file, 'wb') as temp_file:
                    await temp_file.write(self.media_binary)
        if self.current_temp_file:
            ffprobe_process = await asyncio.create_subprocess_exec(*self.__make_ffprobe_command(self.current_temp_file), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            ffprobe_result, _ = await ffprobe_process.communicate()
            self.__parse_media_params_from_ffprobe_result(ffprobe_result)
            logger.info(f'ffprobe analysis of input parameter with temp file "{self.param_name}" type "{self.arg_type}": {self.format_params_for_logger(self.media_params)}')
        if not self.media_params.get(MediaParams.FORMAT):
            self.__handle_error(f'Parameter {self.param_name} denied. Format not recognized by ffprobe.', TypeError)


    def __get_ffprobe_param(self, ffprobe_result_section, param_name):
        ffprobe_label = FFPROBE_DICT.get(param_name, param_name)

        if isinstance(ffprobe_label, tuple):
            return tuple(self.__get_ffprobe_param(ffprobe_result_section, sub_label) for sub_label in ffprobe_label)
        else:
            value = ffprobe_result_section.get(ffprobe_label)
            try:
                return round(float(value))
            except (TypeError, ValueError):
                value = value.replace('_pipe', '') if param_name == MediaParams.FORMAT else value
                return value


    def __make_ffmpeg_cmd(self, target_media_params):
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
                        ffmpeg_value = self.__get_video_filter_string(target_param_value, target_param_name)  
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


    def __get_video_filter_string(self, target_param_value, param_name):

        if param_name == MediaParams.SIZE:
            crop_size, top_left = self.__get_crop_parameter(self.media_params[param_name], target_param_value, param_name)
            return f'crop={crop_size[0]}:{crop_size[1]}:{top_left[0]}:{top_left[1]},scale={target_param_value[0]}:{target_param_value[1]}'
        elif param_name == MediaParams.COLOR_SPACE:
            return f'format={target_param_value}'
        else:
            return target_param_value


    def __get_crop_parameter(self, size, target_size, param_name):

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


    def __make_ffprobe_command(self, input_source='pipe:0'):
        return (
            'ffprobe',
            '-i', input_source,
            '-show_entries',
            'format=format_name,duration,bit_rate:stream=codec_type,duration,bit_rate,codec_name,channels,sample_rate,sample_fmt,width,height,pix_fmt',
            '-v', 'quiet',
            '-of', 'json'
        )


    @staticmethod
    def __get_attribute_class(param_value, param_name):
        for param_class, param_values in MEDIA_ATTRIBUTE_DICT.get(param_name, {}).items():
            if param_value is not None and param_value in param_values:
                return param_class

    
    @staticmethod
    def get_ffmpeg_conform_parameter(param_value, param_name):
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


    @staticmethod
    def format_params_for_logger(media_params):
        return '\n    ' + ', '.join(f'{key}: {value}' for key, value in media_params.items() if value not in (None, (None, None)))
