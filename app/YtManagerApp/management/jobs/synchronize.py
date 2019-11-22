import errno
import itertools
import datetime
from threading import Lock

from apscheduler.triggers.cron import CronTrigger
from django.db.models import Max, F
from django.conf import settings


from YtManagerApp.management.appconfig import appconfig
from YtManagerApp.management.downloader import fetch_thumbnail, downloader_process_subscription
from YtManagerApp.models import *
from YtManagerApp.scheduler import scheduler, Job
from YtManagerApp.utils import youtube
from external.pytaw.pytaw.utils import iterate_chunks

_ENABLE_UPDATE_STATS = True


class SynchronizeJob(Job):
    name = "SynchronizeJob"
    __lock = Lock()
    running = False
    __global_sync_job = None

    def __init__(self, job_execution, subscription: Optional[Subscription] = None):
        super().__init__(job_execution)
        self.__subscription = subscription
        self.__api = youtube.YoutubeAPI.build_public()
        self.__new_vids = []

    def get_description(self):
        if self.__subscription is not None:
            return "Running synchronization for subscription " + self.__subscription.name
        return "Running synchronization..."

    def get_subscription_list(self):
        if self.__subscription is not None:
            return [self.__subscription]
        return Subscription.objects.all().order_by(F('last_synchronised').desc(nulls_first=True))

    def get_videos_list(self, subs):
        return Video.objects.filter(subscription__in=subs)

    def run(self):
        self.__lock.acquire(blocking=True)
        SynchronizeJob.running = True
        try:
            self.log.info(self.get_description())

            # Build list of work items
            work_subs = self.get_subscription_list()
            work_vids = self.get_videos_list(work_subs)

            self.set_total_steps(len(work_subs) + len(work_vids))

            # Remove the 'new' flag
            work_vids.update(new=False)

            # Process subscriptions
            for sub in work_subs:
                self.progress_advance(1, "Synchronizing subscription " + sub.name)
                self.check_new_videos(sub)
                self.fetch_missing_thumbnails(sub)

            # Add new videos to progress calculation
            self.set_total_steps(len(work_subs) + len(work_vids) + len(self.__new_vids))

            # Process videos
            all_videos = itertools.chain(work_vids, self.__new_vids)
            for batch in iterate_chunks(all_videos, 50):
                video_stats = {}

                if _ENABLE_UPDATE_STATS:
                    batch_ids = [video.video_id for video in batch]
                    video_stats = {v.id: v for v in self.__api.videos(batch_ids, part='id,statistics,contentDetails')}
                else:
                    batch_ids = [video.video_id for video in filter(lambda video: video.duration == 0, batch)]
                    video_stats = {v.id: v for v in self.__api.videos(batch_ids, part='id,statistics,contentDetails')}

                for video in batch:
                    self.progress_advance(1, "Updating video " + video.name)
                    self.check_video_deleted(video)
                    self.fetch_missing_thumbnails(video)

                    if video.video_id in video_stats:
                        self.update_video_stats(video, video_stats[video.video_id])


            # Start downloading videos
            for sub in work_subs:
                downloader_process_subscription(sub)

        finally:
            SynchronizeJob.running = False
            self.__lock.release()

    def check_new_videos(self, sub: Subscription):
        playlist_items = self.__api.playlist_items(sub.playlist_id)
        if sub.rewrite_playlist_indices:
            playlist_items = sorted(playlist_items, key=lambda x: x.published_at)
        else:
            playlist_items = sorted(playlist_items, key=lambda x: x.position)

        for item in playlist_items:
            results = Video.objects.filter(video_id=item.resource_video_id, subscription=sub)

            if not results.exists():
                self.log.info('New video for subscription %s: %s %s"', sub, item.resource_video_id, item.title)

                # fix playlist index if necessary
                if sub.rewrite_playlist_indices or Video.objects.filter(subscription=sub, playlist_index=item.position).exists():
                    highest = Video.objects.filter(subscription=sub).aggregate(Max('playlist_index'))['playlist_index__max']
                    item.position = 1 + (highest or -1)

                self.__new_vids.append(Video.create(item, sub))
        sub.last_synchronised = datetime.datetime.now()
        sub.save()

    def fetch_missing_thumbnails(self, obj: Union[Subscription, Video]):
        if obj.thumbnail.startswith("http"):
            if isinstance(obj, Subscription):
                obj.thumbnail = fetch_thumbnail(obj.thumbnail, 'sub', obj.playlist_id, settings.THUMBNAIL_SIZE_SUBSCRIPTION)
            elif isinstance(obj, Video):
                obj.thumbnail = fetch_thumbnail(obj.thumbnail, 'video', obj.video_id, settings.THUMBNAIL_SIZE_VIDEO)
            obj.save()

    def check_video_deleted(self, video: Video):
        if video.downloaded_path is not None:
            files = []
            try:
                files = list(video.get_files())
            except OSError as e:
                if e.errno != errno.ENOENT:
                    self.log.error("Could not access path %s. Error: %s", video.downloaded_path, e)
                    self.usr_err(f"Could not access path {video.downloaded_path}: {e}", suppress_notification=True)
                    return

            # Try to find a valid video file
            found_video = False
            for file in files:
                mime, _ = mimetypes.guess_type(file)
                if mime is not None and mime.startswith("video"):
                    found_video = True

            # Video not found, we can safely assume that the video was deleted.
            if not found_video:
                self.log.info("Video %d was deleted! [%s %s]", video.id, video.video_id, video.name)
                # Clean up
                for file in files:
                    try:
                        os.unlink(file)
                    except OSError as e:
                        self.log.error("Could not delete redundant file %s. Error: %s", file, e)
                        self.usr_err(f"Could not delete redundant file {file}: {e}", suppress_notification=True)
                video.downloaded_path = None

                # Mark watched?
                user = video.subscription.user
                if user.preferences['mark_deleted_as_watched']:
                    video.watched = True

                video.save()

    def update_video_stats(self, video: Video, yt_video):
        if yt_video.n_likes is not None \
                and yt_video.n_dislikes is not None \
                and yt_video.n_likes + yt_video.n_dislikes > 0:
            video.rating = yt_video.n_likes / (yt_video.n_likes + yt_video.n_dislikes)

        video.views = yt_video.n_views
        video.duration = yt_video.duration.total_seconds()
        video.save()

    @staticmethod
    def schedule_global_job():
        trigger = CronTrigger.from_crontab(appconfig.sync_schedule)

        if SynchronizeJob.__global_sync_job is None:
            trigger = CronTrigger.from_crontab(appconfig.sync_schedule)
            SynchronizeJob.__global_sync_job = scheduler.add_job(SynchronizeJob, trigger, max_instances=1, coalesce=True)

        else:
            SynchronizeJob.__global_sync_job.reschedule(trigger, max_instances=1, coalesce=True)

    @staticmethod
    def schedule_now():
        scheduler.add_job(SynchronizeJob, max_instances=1, coalesce=True)

    @staticmethod
    def schedule_now_for_subscription(subscription):
        scheduler.add_job(SynchronizeJob, user=subscription.user, args=[subscription])
