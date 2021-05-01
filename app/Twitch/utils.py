import logging
from string import Template

import os
import youtube_dl

from YtManagerApp.models import Video


def build_youtube_dl_params(video: Video):
    sub = video.subscription
    user = sub.user

    # resolve path
    download_path = user.preferences['download_path']

    template_dict = build_template_dict(video)
    output_pattern = Template(user.preferences['download_file_pattern']).safe_substitute(template_dict)

    output_path = os.path.join(download_path, output_pattern)
    output_path = os.path.normpath(output_path)

    youtube_dl_params = {
        'logger': logging.getLogger(youtube_dl.__name__),
        'format': user.preferences['download_format'],
        'outtmpl': output_path,
        'writethumbnail': False,
        'writedescription': False,
        'writesubtitles': user.preferences['download_subtitles'],
        'writeautomaticsub': user.preferences['download_autogenerated_subtitles'],
        'allsubtitles': user.preferences['download_subtitles_all'],
        'merge_output_format': 'mp4',
        'postprocessors': [
            {
                'key': 'FFmpegMetadata'
            },
        ]
    }

    sub_langs = user.preferences['download_subtitles_langs'].split(',')
    sub_langs = [i.strip() for i in sub_langs]
    if len(sub_langs) > 0:
        youtube_dl_params['subtitleslangs'] = sub_langs

    sub_format = user.preferences['download_subtitles_format']
    if len(sub_format) > 0:
        youtube_dl_params['subtitlesformat'] = sub_format

    return youtube_dl_params, output_path


def build_template_dict(video: Video):
    return {
        'channel': video.subscription.channel_name,
        'channel_id': video.subscription.channel_id,
        'playlist': video.subscription.name,
        'playlist_id': video.subscription.playlist_id,
        'playlist_index': "{:03d}".format(1 + video.playlist_index),
        'title': video.name,
        'id': video.video_id,
    }