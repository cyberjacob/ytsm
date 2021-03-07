import os

from YtManagerApp.models import Video
from YtManagerApp.scheduler import Job, scheduler


class DeleteVideoJob(Job):
    name = "DeleteVideoJob"

    def __init__(self, job_execution, video: Video) -> None:
        super().__init__(job_execution)
        self._video = video

    def get_description(self):
        return f"Deleting video {self._video}"

    def run(self):
        count = 0

        try:
            for file in self._video.get_files():
                self.log.info("Deleting file %s", file)
                count += 1
                try:
                    os.unlink(file)
                except OSError as e:
                    self.log.error("Failed to delete file %s: Error: %s", file, e)

        except OSError as e:
            self.log.error("Failed to delete video %d [%s %s]. Error: %s", self._video.pk,
                           self._video.video_id, self._video.name, e)

        self._video.downloaded_path = None
        self._video.save()

        self.log.info('Deleted video %d successfully! (%d files) [%s %s]', self._video.pk, count,
                      self._video.video_id, self._video.name)

    @staticmethod
    def schedule(video: Video):
        """
        Schedules a delete video job to run immediately.
        :param video:
        :return:
        """
        scheduler.add_job(DeleteVideoJob, args=[video])
