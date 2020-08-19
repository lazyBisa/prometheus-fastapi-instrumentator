from typing import Callable, Tuple

from prometheus_client import Counter, Histogram, Summary
from starlette.requests import Request
from starlette.responses import Response


class Info:
    def __init__(
        self,
        request: Request,
        response: Response or None,
        method: str,
        modified_handler: str,
        modified_status: str,
        modified_duration: float,
    ):
        """Creates Info object that is used for instrumentation functions.

        This is the only argument that is passed to the instrumentation functions.

        Args:
            request: Python Requests request object.
            response Python Requests response object.
            method: Unmodified method of the request.
            modified_handler: Handler representation after processing by 
                instrumentator. For example grouped to `none` if not templated.
            modified_status: Status code representation after processing by
                instrumentator. For example grouping into `2xx`, `3xx` and so on.
            modified_duration: Latency representation after processing by 
                instrumentator. For example rounding of decimals. Seconds.
        """

        self.request = request
        self.response = response
        self.method = method
        self.modified_handler = modified_handler
        self.modified_status = modified_status
        self.modified_duration = modified_duration


def _build_label_attribute_names(
    should_include_handler: bool,
    should_include_method: bool,
    should_include_status: bool,
) -> Tuple[list, list]:
    """Builds up tuple with to be used label and attribute names.

    Args:
        should_include_handler: Should the `handler` label be part of the metric?
        should_include_method: Should the `method` label be part of the metric?
        should_include_status: Should the `status` label be part of the metric?

    Returns:
        Tuple with two list elements.

        First element: List with all labels to be used.
        Second element: List with all attribute names to be used from the 
            `Info` object. Done like this to enable dynamic on / off of labels.
    """

    label_names = []
    info_attribute_names = []

    if should_include_handler:
        label_names.append("handler")
        info_attribute_names.append("modified_handler")

    if should_include_method:
        label_names.append("method")
        info_attribute_names.append("method")

    if should_include_status:
        label_names.append("status")
        info_attribute_names.append("modified_status")

    return label_names, info_attribute_names


# Metrics ======================================================================


def latency(
    metric_name: str = "http_request_duration_seconds",
    metric_doc: str = "Duration of HTTP requests in seconds",
    metric_namespace: str = "",
    metric_subsystem: str = "",
    should_include_handler: bool = True,
    should_include_method: bool = True,
    should_include_status: bool = True,
    buckets: tuple = Histogram.DEFAULT_BUCKETS,
) -> Callable[[Info], None]:
    """Default metric for the Prometheus FastAPI Instrumentator.

    Args:
        metric_name: Name of the metric to be created. Must be unique.
        metric_doc: Documentation of the metric.
        metric_namespace: Namespace of all  metrics in this metric function.
        metric_subsystem: Subsystem of all  metrics in this metric function.
        should_include_handler: Should the `handler` label be part of the metric?
        should_include_method: Should the `method` label be part of the metric?
        should_include_status: Should the `status` label be part of the metric?
        buckets: Buckets for the histogram. Defaults to Prometheus default.

    Returns:
        Function that takes a single parameter `Info`.
    """

    if buckets[-1] != float("inf"):
        buckets = buckets + (float("inf"),)

    label_names, info_attribute_names = _build_label_attribute_names(
        should_include_handler, should_include_method, should_include_status
    )

    if label_names:
        METRIC = Histogram(
            metric_name,
            metric_doc,
            labelnames=label_names,
            buckets=buckets,
            namespace=metric_namespace,
            subsystem=metric_subsystem,
        )
    else:
        METRIC = Histogram(
            metric_name,
            metric_doc,
            buckets=buckets,
            namespace=metric_namespace,
            subsystem=metric_subsystem,
        )

    def instrumentation(info: Info) -> None:
        if label_names:
            label_values = []
            for attribute_name in info_attribute_names:
                label_values.append(getattr(info, attribute_name))
            METRIC.labels(*label_values).observe(info.modified_duration)
        else:
            METRIC.observe(info.modified_duration)

    return instrumentation


def request_size(
    metric_name: str = "http_request_size_bytes",
    metric_doc: str = "Content bytes of requests.",
    metric_namespace: str = "",
    metric_subsystem: str = "",
    should_include_handler: bool = True,
    should_include_method: bool = True,
    should_include_status: bool = True,
) -> Callable[[Info], None]:
    """Record the content length of incoming requests.

    Requests / Responses with missing `Content-Length` will be skipped.

    Args:
        metric_name: Name of the metric to be created. Must be unique.
        metric_doc: Documentation of the metric.
        metric_namespace: Namespace of all  metrics in this metric function.
        metric_subsystem: Subsystem of all  metrics in this metric function.
        should_include_handler: Should the `handler` label be part of the metric?
        should_include_method: Should the `method` label be part of the metric?
        should_include_status: Should the `status` label be part of the metric?

    Returns:
        Function that takes a single parameter `Info`.
    """

    label_names, info_attribute_names = _build_label_attribute_names(
        should_include_handler, should_include_method, should_include_status
    )

    if label_names:
        METRIC = Summary(
            metric_name,
            metric_doc,
            labelnames=label_names,
            namespace=metric_namespace,
            subsystem=metric_subsystem,
        )
    else:
        METRIC = Summary(
            metric_name,
            metric_doc,
            namespace=metric_namespace,
            subsystem=metric_subsystem,
        )

    def instrumentation(info: Info) -> None:
        content_length = info.request.headers.get("Content-Length", None)
        if content_length is not None:
            if label_names:
                label_values = []
                for attribute_name in info_attribute_names:
                    label_values.append(getattr(info, attribute_name))
                METRIC.labels(*label_values).observe(int(content_length))
            else:
                METRIC.observe(int(content_length))

    return instrumentation


def response_size(
    metric_name: str = "http_response_size_bytes",
    metric_doc: str = "Content bytes of responses.",
    metric_namespace: str = "",
    metric_subsystem: str = "",
    should_include_handler: bool = True,
    should_include_method: bool = True,
    should_include_status: bool = True,
) -> Callable[[Info], None]:
    """Record the content length of outgoing responses.

    Responses with missing `Content-Length` will be skipped.

    Args:
        metric_name: Name of the metric to be created. Must be unique.
        metric_doc: Documentation of the metric.
        metric_namespace: Namespace of all  metrics in this metric function.
        metric_subsystem: Subsystem of all  metrics in this metric function.
        should_include_handler: Should the `handler` label be part of the metric?
        should_include_method: Should the `method` label be part of the metric?
        should_include_status: Should the `status` label be part of the metric?

    Returns:
        Function that takes a single parameter `Info`.
    """

    label_names, info_attribute_names = _build_label_attribute_names(
        should_include_handler, should_include_method, should_include_status
    )

    if label_names:
        METRIC = Summary(
            metric_name,
            metric_doc,
            labelnames=label_names,
            namespace=metric_namespace,
            subsystem=metric_subsystem,
        )
    else:
        METRIC = Summary(
            metric_name,
            metric_doc,
            namespace=metric_namespace,
            subsystem=metric_subsystem,
        )

    def instrumentation(info: Info) -> None:
        content_length = info.response.headers.get("Content-Length", None)
        if content_length is not None:
            if label_names:
                label_values = []
                for attribute_name in info_attribute_names:
                    label_values.append(getattr(info, attribute_name))
                METRIC.labels(*label_values).observe(int(content_length))
            else:
                METRIC.observe(int(content_length))

    return instrumentation


def combined_size(
    metric_name: str = "http_combined_size_bytes",
    metric_doc: str = "Content bytes of requests and responses.",
    metric_namespace: str = "",
    metric_subsystem: str = "",
    should_include_handler: bool = True,
    should_include_method: bool = True,
    should_include_status: bool = True,
) -> Callable[[Info], None]:
    """Record the combined content length of requests and responses.

    Requests / Responses with missing `Content-Length` will be skipped.

    Args:
        metric_name: Name of the metric to be created. Must be unique.
        metric_doc: Documentation of the metric.
        metric_namespace: Namespace of all  metrics in this metric function.
        metric_subsystem: Subsystem of all  metrics in this metric function.
        should_include_handler: Should the `handler` label be part of the metric?
        should_include_method: Should the `method` label be part of the metric?
        should_include_status: Should the `status` label be part of the metric?

    Returns:
        Function that takes a single parameter `Info`.
    """

    label_names, info_attribute_names = _build_label_attribute_names(
        should_include_handler, should_include_method, should_include_status
    )

    if label_names:
        METRIC = Summary(
            metric_name,
            metric_doc,
            labelnames=label_names,
            namespace=metric_namespace,
            subsystem=metric_subsystem,
        )
    else:
        METRIC = Summary(
            metric_name,
            metric_doc,
            namespace=metric_namespace,
            subsystem=metric_subsystem,
        )

    def instrumentation(info: Info) -> None:
        request_cl = info.request.headers.get("Content-Length", None)
        response_cl = info.response.headers.get("Content-Length", None)

        if request_cl and response_cl:
            content_length = int(request_cl) + int(response_cl)
        elif request_cl:
            content_length = int(request_cl)
        elif response_cl:
            content_length = int(response_cl)
        else:
            content_length = None

        if content_length is not None:
            if label_names:
                label_values = []
                for attribute_name in info_attribute_names:
                    label_values.append(getattr(info, attribute_name))
                METRIC.labels(*label_values).observe(int(content_length))
            else:
                METRIC.observe(int(content_length))

    return instrumentation


def default(
    metric_namespace: str = "",
    metric_subsystem: str = "",
    latency_highr_buckets: tuple = (
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1,
        1.5,
        2,
        2.5,
        3,
        3.5,
        4,
        4.5,
        5,
        7.5,
        10,
        30,
        60,
    ),
    latency_lowr_buckets: tuple = (0.1, 0.5, 1),
) -> Callable[[Info], None]:
    """Contains multiple metrics to cover multiple things.

    Combines several metrics into a single function. Also more efficient than 
    multiple separate instrumentation functions that do more or less the same.
    
    You get the following:

    * `http_requests_total` (`handler`, `status`, `method`): Total number of 
        requests by handler, status and method. 
    * `http_request_size_bytes` (`handler`): Total number of incoming 
        content length bytes by handler.
    * `http_response_size_bytes` (`handler`): Total number of outgoing 
        content length bytes by handler.
    * `http_request_duration_highr_seconds` (no labels): High number of buckets 
        leading to more accurate calculation of percentiles.
    * `http_request_duration_seconds` (`handler`): 
        Kepp the bucket count very low. Only put in SLIs.

    Args:
        metric_namespace: Namespace of all  metrics in this metric function.
        metric_subsystem: Subsystem of all  metrics in this metric function.
        latency_highr_buckets: Buckets tuple for high res histogram. Can be 
            large because no labels are used.
        latency_lowr_buckets: Buckets tuple for low res histogram. Should be 
            very small as all possible labels are included.

    Returns:
        Function that takes a single parameter `Info`.
    """

    if latency_highr_buckets[-1] != float("inf"):
        latency_highr_buckets = latency_highr_buckets + (float("inf"),)

    if latency_lowr_buckets[-1] != float("inf"):
        latency_lowr_buckets = latency_lowr_buckets + (float("inf"),)

    TOTAL = Counter(
        name="http_requests_total",
        documentation="Total number of requests by method, status and handler.",
        labelnames=("method", "status", "handler",),
        namespace=metric_namespace,
        subsystem=metric_subsystem,
    )

    IN_SIZE = Summary(
        name="http_request_size_bytes",
        documentation=(
            "Content length of incoming requests by handler. "
            "Only value of header is respected. Otherwise ignored. "
            "No percentile calculated. "
        ),
        labelnames=("handler",),
        namespace=metric_namespace,
        subsystem=metric_subsystem,
    )

    OUT_SIZE = Summary(
        name="http_response_size_bytes",
        documentation=(
            "Content length of outgoing responses by handler. "
            "Only value of header is respected. Otherwise ignored. "
            "No percentile calculated. "
        ),
        labelnames=("handler",),
        namespace=metric_namespace,
        subsystem=metric_subsystem,
    )

    LATENCY_HIGHR = Histogram(
        name="http_request_duration_highr_seconds",
        documentation=(
            "Latency with many buckets but no API specific labels. "
            "Made for more accurate percentile calculations. "
        ),
        buckets=latency_highr_buckets,
        namespace=metric_namespace,
        subsystem=metric_subsystem,
    )

    LATENCY_LOWR = Histogram(
        name="http_request_duration_seconds",
        documentation=(
            "Latency with only few buckets by handler. "
            "Made to be only used if aggregation by handler is important. "
        ),
        buckets=latency_lowr_buckets,
        labelnames=("handler",),
        namespace=metric_namespace,
        subsystem=metric_subsystem,
    )

    def instrumentation(info: Info) -> None:
        TOTAL.labels(info.method, info.modified_status, info.modified_handler).inc()
        IN_SIZE.labels(info.modified_handler).observe(
            int(info.request.headers.get("Content-Length", 0))
        )
        OUT_SIZE.labels(info.modified_handler).observe(
            int(info.response.headers.get("Content-Length", 0))
        )
        LATENCY_HIGHR.observe(info.modified_duration)
        LATENCY_LOWR.labels(info.modified_handler).observe(info.modified_duration)

    return instrumentation
