"""
Implementation of `Sentinel Hub Process API interface <https://docs.sentinel-hub.com/api/latest/api/process/>`__.
"""
from typing import Any, Dict, List, Optional, Tuple, Union

from ..constants import MimeType
from ..download import SentinelHubDownloadClient
from ..geometry import BBox, Geometry
from ..types import JsonDict
from .base_request import InputDataDict, SentinelHubBaseApiRequest
from .utils import AccessSpecification, _update_other_args, remove_undefined, s3_specification


class SentinelHubRequest(SentinelHubBaseApiRequest):
    """Sentinel Hub Process API interface

    For more information check
    `Process API documentation <https://docs.sentinel-hub.com/api/latest/api/process/>`__.
    """

    _SERVICE_ENDPOINT = "process"

    def __init__(
        self,
        evalscript: str,
        input_data: List[Union[JsonDict, InputDataDict]],
        responses: List[JsonDict],
        bbox: Optional[BBox] = None,
        geometry: Optional[Geometry] = None,
        size: Optional[Tuple[int, int]] = None,
        resolution: Optional[Tuple[float, float]] = None,
        **kwargs: Any
    ):
        """
        For details of certain parameters check the
        `Process API reference <https://docs.sentinel-hub.com/api/latest/reference/#operation/process>`_.

        :param evalscript: `Evalscript <https://docs.sentinel-hub.com/api/latest/#/Evalscript/>`__.
        :param input_data: A list of input dictionary objects as described in the API reference. It can be generated
            with the helper method `SentinelHubRequest.input_data`
        :param responses: A list of `output.responses` objects as described in the API reference. It can be generated
            with the helper function `SentinelHubRequest.output_response`
        :param bbox: Bounding box describing the area of interest.
        :param geometry: Geometry describing the area of interest.
        :param size: Size of the image.
        :param resolution: Resolution of the image. It has to be in units compatible with the given CRS.
        :param data_folder: location of the directory where the fetched data will be saved.
        :param config: A custom instance of config class to override parameters from the saved configuration.
        """
        if not isinstance(evalscript, str):
            raise ValueError("'evalscript' should be a string")

        parsed_mime_type = MimeType.from_string(responses[0]["format"]["type"])
        self._mime_type = MimeType.TAR if len(responses) > 1 else parsed_mime_type

        self.payload = self.body(
            request_bounds=self.bounds(bbox=bbox, geometry=geometry),
            request_data=input_data,
            request_output=self.output(size=size, resolution=resolution, responses=responses),
            evalscript=evalscript,
        )

        super().__init__(SentinelHubDownloadClient, **kwargs)

    @property
    def mime_type(self) -> MimeType:
        return self._mime_type

    @staticmethod
    def body(
        request_bounds: JsonDict,
        request_data: List[JsonDict],
        evalscript: str,
        request_output: Optional[JsonDict] = None,
        other_args: Optional[JsonDict] = None,
    ) -> JsonDict:
        """Generate the Process API request body

        :param request_bounds: A dictionary as generated by `SentinelHubRequest.bounds` helper method.
        :param request_data: A list of dictionaries as generated by `SentinelHubRequest.input_data` helper method.
        :param evalscript: `Evalscript <https://docs.sentinel-hub.com/api/latest/#/Evalscript/>`__.
        :param request_output: A dictionary as generated by `SentinelHubRequest.output` helper method.
        :param other_args: Additional dictionary of arguments. If provided, the resulting dictionary will get updated
            by it.
        """
        request_body = {"input": {"bounds": request_bounds, "data": request_data}, "evalscript": evalscript}

        if request_output is not None:
            request_body["output"] = request_output

        if other_args:
            _update_other_args(request_body, other_args)

        return request_body

    @staticmethod
    def output_response(
        identifier: str, response_format: Union[str, MimeType], other_args: Optional[JsonDict] = None
    ) -> JsonDict:
        """Generate an element of `output.responses` as described in the Process API reference.

        :param identifier: Identifier of the output response.
        :param response_format: A mime type of one of 'png', 'json', 'jpeg', 'tiff'.
        :param other_args: Additional dictionary of arguments. If provided, the resulting dictionary will get updated
            by it.
        """
        output_response = {"identifier": identifier, "format": {"type": MimeType(response_format).get_string()}}

        if other_args:
            _update_other_args(output_response, other_args)

        return output_response

    @staticmethod
    def output(
        responses: List[JsonDict],
        size: Optional[Tuple[int, int]] = None,
        resolution: Optional[Tuple[float, float]] = None,
        other_args: Optional[Dict] = None,
    ) -> JsonDict:
        """Generate an `output` part of the request as described in the Process API reference

        :param responses: A list of objects in `output.responses` as generated by `SentinelHubRequest.output_response`.
        :param size: Size of the image.
        :param resolution: Resolution of the image. It has to be in units compatible with the given CRS.
        :param other_args: Additional dictionary of arguments. If provided, the resulting dictionary will get updated
            by it.
        """
        if size and resolution:
            raise ValueError("Either size or resolution argument should be given, not both.")

        request_output: JsonDict = {"responses": responses}

        if size:
            request_output["width"], request_output["height"] = size
        if resolution:
            request_output["resx"], request_output["resy"] = resolution

        if other_args:
            _update_other_args(request_output, other_args)

        return request_output


class AsyncProcessRequest(SentinelHubBaseApiRequest):
    """Sentinel Hub Async Process API interface

    For more information check
    `Async Process API documentation <https://docs.sentinel-hub.com/api/latest/api/async-process/>`__.
    """

    _SERVICE_ENDPOINT = "async/process"

    def __init__(
        self,
        *,
        evalscript: Optional[str] = None,
        evalscript_reference: Optional[AccessSpecification] = None,
        input_data: List[Union[JsonDict, InputDataDict]],
        responses: List[JsonDict],
        delivery: AccessSpecification,
        bbox: Optional[BBox] = None,
        geometry: Optional[Geometry] = None,
        size: Optional[Tuple[int, int]] = None,
        resolution: Optional[Tuple[float, float]] = None,
        **kwargs: Any
    ):
        """
        For details of certain parameters check the
        `Async Process API reference <https://docs.sentinel-hub.com/api/latest/reference/#tag/async_process>`_.

        :param evalscript: `Evalscript <https://docs.sentinel-hub.com/api/latest/#/Evalscript/>`__.
        :param evalscript_reference:
            `Evalscript specification <https://docs.sentinel-hub.com/api/latest/reference/#tag/async_process>`__.
        :param input_data: A list of input dictionary objects as described in the API reference. It can be generated
            with the helper method `SentinelHubRequest.input_data`
        :param responses: A list of `output.responses` objects as described in the API reference. It can be generated
            with the helper function `SentinelHubRequest.output_response`
        :param delivery: S3 specification for dumping the request data.
        :param bbox: Bounding box describing the area of interest.
        :param geometry: Geometry describing the area of interest.
        :param size: Size of the image.
        :param resolution: Resolution of the image. It has to be in units compatible with the given CRS.
        :param data_folder: location of the directory where the fetched data will be saved.
        :param config: A custom instance of config class to override parameters from the saved configuration.
        """

        self._mime_type = MimeType.JSON

        self.payload = self.body(
            request_bounds=self.bounds(bbox=bbox, geometry=geometry),
            request_data=input_data,
            request_output=self.output(size=size, resolution=resolution, responses=responses, delivery=delivery),
            evalscript=evalscript,
            evalscript_reference=evalscript_reference,
        )

        super().__init__(SentinelHubDownloadClient, **kwargs)

    s3_specification = s3_specification

    @property
    def mime_type(self) -> MimeType:
        return self._mime_type

    @staticmethod
    def body(
        request_bounds: JsonDict,
        request_data: List[JsonDict],
        evalscript: Optional[str],
        evalscript_reference: Optional[AccessSpecification],
        request_output: Optional[JsonDict] = None,
        other_args: Optional[JsonDict] = None,
    ) -> JsonDict:
        """Generate the Async Process API request body

        :param request_bounds: A dictionary as generated by `SentinelHubRequest.bounds` helper method.
        :param request_data: A list of dictionaries as generated by `SentinelHubRequest.input_data` helper method.
        :param evalscript: `Evalscript <https://docs.sentinel-hub.com/api/latest/#/Evalscript/>`__.
        :param request_output: A dictionary as generated by `SentinelHubRequest.output` helper method.
        :param other_args: Additional dictionary of arguments. If provided, the resulting dictionary will get updated
            by it.
        """
        request_body = {
            "input": {"bounds": request_bounds, "data": request_data},
            "evalscript": evalscript,
            "evalscriptReference": evalscript_reference,
        }

        if request_output is not None:
            request_body["output"] = request_output

        if other_args:
            _update_other_args(request_body, other_args)

        return remove_undefined(request_body)

    @staticmethod
    def output_response(
        identifier: str, response_format: Union[str, MimeType], other_args: Optional[JsonDict] = None
    ) -> JsonDict:
        """Generate an element of `output.responses` as described in the Async Process API reference.

        :param identifier: Identifier of the output response.
        :param response_format: A mime type of one of 'png', 'json', 'jpeg', 'tiff'.
        :param other_args: Additional dictionary of arguments. If provided, the resulting dictionary will get updated
            by it.
        """
        output_response = {"identifier": identifier, "format": {"type": MimeType(response_format).get_string()}}

        if other_args:
            _update_other_args(output_response, other_args)

        return output_response

    @staticmethod
    def output(
        responses: List[JsonDict],
        delivery: AccessSpecification,
        size: Optional[Tuple[int, int]] = None,
        resolution: Optional[Tuple[float, float]] = None,
        other_args: Optional[Dict] = None,
    ) -> JsonDict:
        """Generate an `output` part of the request as described in the Async Process API reference

        :param responses: A list of objects in `output.responses` as generated by `AsyncProcessRequest.output_response`.
        :param size: Size of the image.
        :param resolution: Resolution of the image. It has to be in units compatible with the given CRS.
        :param other_args: Additional dictionary of arguments. If provided, the resulting dictionary will get updated
            by it.
        """
        if size and resolution:
            raise ValueError("Either size or resolution argument should be given, not both.")

        request_output: JsonDict = {"responses": responses, "delivery": delivery}

        if size:
            request_output["width"], request_output["height"] = size
        if resolution:
            request_output["resx"], request_output["resy"] = resolution

        if other_args:
            _update_other_args(request_output, other_args)

        return request_output
