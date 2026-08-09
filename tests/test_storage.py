from pathlib import Path

from groovegrab.core.models import DownloadOptions, DownloadStatus, DownloadTask, TrackInfo
from groovegrab.queue.storage import TaskStorage


def make_task(task_id: str = "task-1") -> DownloadTask:
    return DownloadTask(
        id=task_id,
        track=TrackInfo(title="Track", artist="Artist", provider_name="Test"),
        options=DownloadOptions(output_dir="/tmp/downloads"),
    )


def test_storage_persists_and_updates_a_task(tmp_path: Path):
    storage = TaskStorage(tmp_path / "groovegrab.db")
    task = make_task()
    storage.save_task(task)

    task.status = DownloadStatus.COMPLETED
    task.output_path = "/tmp/downloads/Artist - Track.mp3"
    storage.save_task(task)

    tasks = storage.list_tasks()
    assert len(tasks) == 1
    assert tasks[0].status == DownloadStatus.COMPLETED
    assert tasks[0].output_path == task.output_path


def test_storage_ignores_corrupt_history_rows(tmp_path: Path):
    storage = TaskStorage(tmp_path / "groovegrab.db")
    storage.save_task(make_task())
    with storage._get_connection() as conn:
        conn.execute("UPDATE download_tasks SET task_json = ? WHERE id = ?", ("not json", "task-1"))

    assert storage.list_tasks() == []
    assert storage.list_tasks(0) == []
