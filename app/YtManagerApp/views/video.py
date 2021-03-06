import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import HttpRequest, FileResponse
from django.views.generic import DetailView
from django.conf import settings

from YtManagerApp.models import Video


class VideoDetailView(LoginRequiredMixin, DetailView):
    template_name = 'YtManagerApp/video.html'
    model = Video

    def get_template_names(self):
        return [self.object.subscription.provider+"/videoframe.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video, mime = self.object.find_video()
        if video is not None:
            context['video_mime'] = mime

        if self.request.GET.get('next'):
            up_next_videos = self.request.GET.get('next').split(',')
            context['up_next_count'] = len(up_next_videos)
            context['up_next_duration'] = str(
                datetime.timedelta(seconds=Video.objects.filter(id__in=up_next_videos).aggregate(Sum('duration'))['duration__sum']))

        return context


@login_required
def video_detail_view(request: HttpRequest, pk):
    video = Video.objects.get(id=pk)
    video_file, _ = video.find_video()

    f = open(video_file, 'rb')
    return FileResponse(f)
