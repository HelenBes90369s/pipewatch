"""Alert dispatcher that filters delivery by tag."""
from __future__ import annotations

from pipewatch.alerting.tagging import TagFilter
from pipewatch.monitor import JobResult


class TaggedAlertDispatcher:
    """Wraps an inner dispatcher and only forwards results that match *filter*.

    Parameters
    ----------
    inner:
        The downstream dispatcher to delegate to when the filter passes.
    tag_filter:
        A :class:`TagFilter` instance describing which tags are required or
        excluded.  Defaults to an empty filter that matches everything.
    """

    def __init__(self, inner, tag_filter: TagFilter | None = None) -> None:
        self._inner = inner
        self._filter = tag_filter or TagFilter()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def dispatch(self, result: JobResult) -> None:
        """Forward *result* to the inner dispatcher if the tag filter matches."""
        if self._filter.matches(result):
            self._inner.dispatch(result)

    @property
    def filter(self) -> TagFilter:
        """The :class:`TagFilter` used by this dispatcher."""
        return self._filter

    @property
    def inner(self):
        """The wrapped downstream dispatcher."""
        return self._inner
