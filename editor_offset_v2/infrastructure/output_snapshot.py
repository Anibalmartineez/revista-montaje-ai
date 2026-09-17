"""Request-scoped immutable inputs and short publication locks for V2 output.

Lock order: job revision lock, then artifact-directory publication lock. Readers
receive bytes already held by the request, never a mutable retained filename.
"""
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
import hashlib
import json
from pathlib import Path
from threading import BoundedSemaphore

from .job_repository import JobRepository, JobRepositoryError
from .process_lock import exclusive_file_lock

_OUTPUT_WORKERS = BoundedSemaphore(2)
MAX_SOURCE_BYTES = 128 * 1024 * 1024


class OutputSnapshotError(ValueError):
    def __init__(self, code, message, status_code=409):
        self.code, self.message, self.status_code = code, message, status_code
        super().__init__(message)


class OutputSnapshot(JobRepository):
    def __init__(self, repository, job_id, options=None):
        super().__init__(repository.jobs_root)
        self.job_id = job_id
        # Validate identity/existence before lock creation, avoiding ghost jobs.
        repository.read_layout(job_id)
        with exclusive_file_lock(self.job_lock_path(job_id)):
            self.layout_bytes = self.layout_path(job_id).read_bytes()
        self._layout = json.loads(self.layout_bytes)
        self.digest = hashlib.sha256(self.layout_bytes).hexdigest()
        self.options = deepcopy(options or {})
        self.sources = {}
        self.prepared = {}
        self.prepared_by_source = {}

    def read_layout(self, job_id):
        if job_id != self.job_id:
            raise OutputSnapshotError('PREFLIGHT_SUBJECT_MISMATCH', 'Snapshot belongs to another job')
        return deepcopy(self._layout)

    def read_source(self, path):
        key = str(path)
        if key not in self.sources:
            if Path(path).stat().st_size + sum(len(data) for data in self.sources.values()) > MAX_SOURCE_BYTES:
                raise OutputSnapshotError('OUTPUT_RESOURCE_LIMIT','The request exceeds the 128 MiB source budget',422)
            self.sources[key] = Path(path).read_bytes()
        return self.sources[key]

    @property
    def request_key(self):
        data = json.dumps({'layout':self.digest, 'options':self.options}, sort_keys=True, allow_nan=False).encode()
        return hashlib.sha256(data).hexdigest()[:16]

    def assert_current(self, *, sources=True):
        try:
            unchanged = hashlib.sha256(self.layout_path(self.job_id).read_bytes()).hexdigest() == self.digest
            if sources:
                unchanged = unchanged and all(Path(path).read_bytes() == data for path, data in self.sources.items())
        except OSError:
            unchanged = False
        if not unchanged:
            raise OutputSnapshotError('PREFLIGHT_STALE', 'The validated layout or source changed; regenerate output')

    @contextmanager
    def publication(self, directory, *, sources=True):
        with exclusive_file_lock(self.job_lock_path(self.job_id)):
            self.assert_current(sources=sources)
            with exclusive_file_lock(Path(directory)/'.publish.lock'):
                yield


def snapshot_operation(error_type):
    """Run service methods on a fresh request-local repository, never mutate self."""
    def decorate(method):
        @wraps(method)
        def execute(self, job_id, **kwargs):
            if not isinstance(self._jobs,OutputSnapshot):
                if not _OUTPUT_WORKERS.acquire(blocking=False):
                    raise error_type('OUTPUT_BUSY','Ya hay dos salidas en proceso. Espera y vuelve a intentarlo.',429)
            try:
                if isinstance(self._jobs, OutputSnapshot):
                    return method(self, job_id, **kwargs)
                # Validate request values before hashing or running preflight.
                face, dpi = kwargs.get('face','front'), kwargs.get('dpi',150)
                if not isinstance(face,str) or face not in {'front','back','both'}:
                    code = 'INVALID_PREVIEW_FACE' if error_type.__name__=='PreviewServiceError' else 'INVALID_PDF_FINAL_FACE'
                    raise OutputSnapshotError(code, 'face must be front, back or both',400)
                if isinstance(dpi,bool) or not isinstance(dpi,int) or not 36 <= dpi <= 300:
                    raise OutputSnapshotError('INVALID_OUTPUT_DPI', 'dpi must be an integer from 36 to 300',400)
                mirror = kwargs.get('allow_mirror_bleed',False)
                if not isinstance(mirror,bool):
                    raise OutputSnapshotError('INVALID_OUTPUT_OPTION', 'allow_mirror_bleed must be boolean',400)
                snapshot = OutputSnapshot(self._jobs,job_id, {'face':face,'dpi':dpi,'allow_mirror_bleed':mirror})
                expected = kwargs.pop('expected_revision',None)
                if expected is not None:
                    if isinstance(expected,bool) or not isinstance(expected,int) or expected<1:
                        raise OutputSnapshotError('INVALID_OUTPUT_REVISION','expected_revision must be a positive integer',400)
                    if snapshot.read_layout(job_id)['job']['revision']!=expected:
                        raise OutputSnapshotError('PREFLIGHT_STALE','The requested revision is no longer current')
                return method(type(self)(snapshot),job_id,**kwargs)
            except OutputSnapshotError as exc:
                raise error_type(exc.code,exc.message,exc.status_code) from exc
            except JobRepositoryError as exc:
                raise error_type(exc.code,exc.message,404 if exc.code=='JOB_NOT_FOUND' else 400 if exc.code=='INVALID_JOB_ID' else 500) from exc
            finally:
                if not isinstance(self._jobs,OutputSnapshot): _OUTPUT_WORKERS.release()
        return execute
    return decorate
