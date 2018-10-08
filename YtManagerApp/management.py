from .models import SubscriptionFolder, Subscription, Video, Channel
from .youtube import YoutubeAPI, YoutubeChannelInfo, YoutubePlaylistItem
from apscheduler.schedulers.background import BackgroundScheduler
import os

class FolderManager(object):

    @staticmethod
    def create_or_edit(fid, name, parent_id):
        # Create or edit
        if fid == '#':
            folder = SubscriptionFolder()
        else:
            folder = SubscriptionFolder.objects.get(id=int(fid))

        # Set attributes
        folder.name = name
        if parent_id == '#':
            folder.parent = None
        else:
            folder.parent = SubscriptionFolder.objects.get(id=int(parent_id))

        FolderManager.__validate(folder)
        folder.save()

    @staticmethod
    def __validate(folder: SubscriptionFolder):
        # Make sure folder name is unique in the parent folder
        for dbFolder in SubscriptionFolder.objects.filter(parent_id=folder.parent_id):
            if dbFolder.id != folder.id and dbFolder.name == folder.name:
                raise ValueError('Folder name is not unique!')

        # Prevent parenting loops
        current = folder
        visited = []

        while not (current is None):
            if current in visited:
                raise ValueError('Parenting cycle detected!')
            visited.append(current)
            current = current.parent

    @staticmethod
    def delete(fid: int):
        folder = SubscriptionFolder.objects.get(id=fid)
        folder.delete()


class SubscriptionManager(object):
    __scheduler = BackgroundScheduler()

    @staticmethod
    def create_or_edit(sid, url, name, parent_id):
        # Create or edit
        if sid == '#':
            sub = Subscription()
            SubscriptionManager.create(url, parent_id, YoutubeAPI.build_public())
        else:
            sub = Subscription.objects.get(id=int(sid))
            sub.name = name

            if parent_id == '#':
                sub.parent_folder = None
            else:
                sub.parent_folder = SubscriptionFolder.objects.get(id=int(parent_id))

            sub.save()

    @staticmethod
    def create(url, parent_id, yt_api: YoutubeAPI):
        sub = Subscription()
        # Set parent
        if parent_id == '#':
            sub.parent_folder = None
        else:
            sub.parent_folder = SubscriptionFolder.objects.get(id=int(parent_id))

        # Pull information about the channel and playlist
        url_type, url_id = yt_api.parse_channel_url(url)

        if url_type == 'playlist_id':
            info_playlist = yt_api.get_playlist_info(url_id)
            channel = SubscriptionManager.__get_or_create_channel('channel_id', info_playlist.getChannelId(), yt_api)
            sub.name = info_playlist.getTitle()
            sub.playlist_id = info_playlist.getId()
            sub.description = info_playlist.getDescription()
            sub.channel = channel
            sub.icon_default = info_playlist.getDefaultThumbnailUrl()
            sub.icon_best = info_playlist.getBestThumbnailUrl()

        else:
            channel = SubscriptionManager.__get_or_create_channel(url_type, url_id, yt_api)
            # No point in getting the 'uploads' playlist info
            sub.name = channel.name
            sub.playlist_id = channel.upload_playlist_id
            sub.description = channel.description
            sub.channel = channel
            sub.icon_default = channel.icon_default
            sub.icon_best = channel.icon_best

        sub.save()

    @staticmethod
    def __get_or_create_channel(url_type, url_id, yt_api: YoutubeAPI):

        channel: Channel = None
        info_channel: YoutubeChannelInfo = None

        if url_type == 'user':
            channel = Channel.find_by_username(url_id)
            if not channel:
                info_channel = yt_api.get_channel_info_by_username(url_id)
                channel = Channel.find_by_channel_id(info_channel.getId())

        elif url_type == 'channel_id':
            channel = Channel.find_by_channel_id(url_id)
            if not channel:
                info_channel = yt_api.get_channel_info(url_id)

        elif url_type == 'channel_custom':
            channel = Channel.find_by_custom_url(url_id)
            if not channel:
                found_channel_id = yt_api.search_channel(url_id)
                channel = Channel.find_by_channel_id(found_channel_id)
                if not channel:
                    info_channel = yt_api.get_channel_info(found_channel_id)

        # Store information about the channel
        if info_channel:
            if not channel:
                channel = Channel()
            if url_type == 'user':
                channel.username = url_id
            SubscriptionManager.__update_channel(channel, info_channel)

        return channel

    @staticmethod
    def __update_channel(channel: Channel, yt_info: YoutubeChannelInfo):
        channel.channel_id = yt_info.getId()
        channel.custom_url = yt_info.getCustomUrl()
        channel.name = yt_info.getTitle()
        channel.description = yt_info.getDescription()
        channel.icon_default = yt_info.getDefaultThumbnailUrl()
        channel.icon_best = yt_info.getBestThumbnailUrl()
        channel.upload_playlist_id = yt_info.getUploadsPlaylist()
        channel.save()

    @staticmethod
    def __create_video(yt_video: YoutubePlaylistItem, subscription: Subscription):
        video = Video()
        video.video_id = yt_video.getVideoId()
        video.name = yt_video.getTitle()
        video.description = yt_video.getDescription()
        video.watched = False
        video.downloaded_path = None
        video.subscription = subscription
        video.playlist_index = yt_video.getPlaylistIndex()
        video.publish_date = yt_video.getPublishDate()
        video.icon_default = yt_video.getDefaultThumbnailUrl()
        video.icon_best = yt_video.getBestThumbnailUrl()
        video.save()

    @staticmethod
    def __synchronize(subscription: Subscription, yt_api: YoutubeAPI):
        # Get list of videos
        for video in yt_api.list_playlist_videos(subscription.playlist_id):
            results = Video.objects.filter(video_id=video.getVideoId(), subscription=subscription)
            if len(results) == 0:
                print('New video for subscription "', subscription, '": ', video.getVideoId(), video.getTitle())
                SubscriptionManager.__create_video(video, subscription)

    @staticmethod
    def __synchronize_all():
        print("Running scheduled synchronization... ")
        yt_api = YoutubeAPI.build_public()
        for subscription in Subscription.objects.all():
            SubscriptionManager.__synchronize(subscription, yt_api)

    @staticmethod
    def start_scheduler():
        SubscriptionManager.__scheduler.add_job(SubscriptionManager.__synchronize_all, 'cron',
                                                hour='*', minute=44, max_instances=1)
        SubscriptionManager.__scheduler.start()
