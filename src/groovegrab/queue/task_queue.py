"""
Multi-threaded Task Queue Execution Manager
"""

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Optional

from groovegrab.core.models import TrackInfo, DownloadOptions, DownloadTask, DownloadStatus
from groovegrab.engines.ytdlp_engine import YtDlpEngine
from groovegrab.engines.metadata_tagger import MetadataTagger
from groovegrab.engines.lyric_fetcher import LyricFetcher
from groovegrab.queue.storage import TaskStorage


class TaskQueueManager:
    def __init__(self, storage: Optional[TaskStorage] = None):
        self.downloader = YtDlpEngine()
        self.tagger = MetadataTagger()
        self.lyric_fetcher = LyricFetcher()
        self.storage = storage or TaskStorage()

    def process_tracks(
        self,
        tracks: List[TrackInfo],
        options: DownloadOptions,
        on_progress: Optional[Callable[[DownloadTask], None]] = None
    ) -> List[DownloadTask]:
        tasks = [
            DownloadTask(
                id=str(uuid.uuid4()),
                track=track,
                options=options,
                status=DownloadStatus.PENDING
            )
            for track in tracks
        ]

        # Save initial pending states
        for task in tasks:
            self.storage.save_task(task)

        results = []
        max_workers = min(options.concurrent_downloads, len(tasks)) or 1

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self._execute_single_task, task, on_progress): task
                for task in tasks
            }

            for future in as_completed(future_to_task):
                task = future.result()
                results.append(task)
                self.storage.save_task(task)

        return results

    def _execute_single_task(
        self,
        task: DownloadTask,
        on_progress: Optional[Callable[[DownloadTask], None]] = None
    ) -> DownloadTask:
        try:
            # 0. Check if file already downloaded
            if not task.options.overwrite:
                existing_file = self.downloader.find_existing_file(task.track, task.options)
                if existing_file:
                    task.status = DownloadStatus.SKIPPED
                    task.output_path = str(existing_file)
                    task.progress = 100.0
                    if on_progress:
                        on_progress(task)
                    return task

            # 1. Downloading
            task.status = DownloadStatus.DOWNLOADING
            task.progress = 10.0
            if on_progress:
                on_progress(task)

            def ytdlp_hook(d):
                if d.get('status') == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                    downloaded = d.get('downloaded_bytes', 0)
                    task.progress = min(80.0, 10.0 + (downloaded / total) * 70.0)
                    task.speed = d.get('_speed_str', '')
                    task.eta = d.get('_eta_str', '')
                    if on_progress:
                        on_progress(task)

            file_path = self.downloader.download_track(task.track, task.options, progress_hook=ytdlp_hook)
            task.output_path = str(file_path)

            # 2. Lyrics Fetching
            synced_lrc, plain_lyrics = None, None
            if task.options.fetch_lyrics:
                synced_lrc, plain_lyrics = self.lyric_fetcher.fetch_lyrics(task.track)
                if synced_lrc:
                    self.lyric_fetcher.save_lrc_file(file_path, synced_lrc)

            # 3. Tagging
            if task.options.embed_cover:
                task.status = DownloadStatus.TAGGING
                task.progress = 90.0
                if on_progress:
                    on_progress(task)
                
                lyrics_to_embed = plain_lyrics or synced_lrc
                self.tagger.tag_file(file_path, task.track, lyrics=lyrics_to_embed)

            task.status = DownloadStatus.COMPLETED
            task.progress = 100.0
            if on_progress:
                on_progress(task)

        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
            if on_progress:
                on_progress(task)

        return task
