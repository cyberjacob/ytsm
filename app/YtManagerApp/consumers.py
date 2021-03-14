from channels.generic.websocket import WebsocketConsumer
import json

import datetime
import collections
import django_celery_results
from celery.result import AsyncResult


def flatten(item_list):
    for el in item_list:
        if isinstance(el, collections.Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten(el)
        else:
            yield el


def get_all_children(t):
    if t.children is None:
        return [t]
    return [t] + [get_all_children(b) for b in t.children]


class EventConsumer(WebsocketConsumer):
    http_user = True

    def receive(self, text=None, bytes=None, **kwargs):
        text_data_json = json.loads(text)
        request = text_data_json['request']

        if request == "jobs":
            self.jobs()

    def jobs(self):
        #TODO: User filtering

        sync_all_tasks = django_celery_results.models.TaskResult.objects.filter(task_name="YtManagerApp.tasks.synchronize_all", date_created__gte=datetime.datetime.now()-datetime.timedelta(days=1))

        all_children = []
        response = []

        for taskResult in sync_all_tasks:
            task = AsyncResult(taskResult.task_id)

            children = flatten(get_all_children(task))
            complete_tasks = 0
            all_tasks = 0

            for child in children:
                if child.task_id not in all_children:
                    all_children += [child.task_id]

                if child.successful():
                    complete_tasks += 1
                all_tasks += 1

            if all_tasks - complete_tasks == 0:
                continue

            progress = float(complete_tasks) / all_tasks

            response += [{
                'id': task.task_id,
                'description': "Synchronize All",
                'progress': progress,
                'message': str(complete_tasks) + " / " + str(all_tasks)
            }]

        sync_other_tasks = django_celery_results.models.TaskResult.objects.filter(date_done__isnull=True).exclude(task_id__in=all_children)

        for taskResult in sync_other_tasks:
            task = AsyncResult(taskResult.task_id)

            children = flatten(get_all_children(task))
            complete_tasks = 0
            all_tasks = 0

            for child in children:
                if child.successful():
                    complete_tasks += 1
                all_tasks += 1

            progress = float(complete_tasks) / all_tasks

            response += [{
                'id': task.task_id,
                'description': "Synchronize All",
                'progress': progress,
                'message': str(complete_tasks) + " / " + str(all_tasks)
            }]

        self.send(text_data=json.dumps({
            'request': 'jobs',
            'data': response
        }))

    def connect(self):
        self.accept()
        self.jobs()

