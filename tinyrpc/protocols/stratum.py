__author__ = 'laudney'


#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import RPCBatchProtocol, RPCRequest, RPCResponse, RPCErrorResponse, \
    InvalidRequestError, MethodNotFoundError, ServerError, \
    InvalidReplyError, RPCError, RPCBatchRequest, RPCBatchResponse


from .jsonrpc import FixedErrorMessageMixin, JSONRPCInvalidRequestError, \
    JSONRPCMethodNotFoundError, JSONRPCServerError, JSONRPCParseError, JSONRPCInvalidParamsError


import ujson as json


class StratumUnknownError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = 20
    message = 'Other/Unknown'


class StratumJobNotFoundError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = 21
    message = 'Job not found (=stale)'


class StratumDuplicateShareError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = 22
    message = 'Duplicate share'


class StratumLowDifficultyShareError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = 23
    message = 'Low difficulty share'


class StratumUnauthorizedError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = 24
    message = 'Unauthorized worker'


class StratumNotSubscribedError(FixedErrorMessageMixin, InvalidRequestError):
    jsonrpc_error_code = 25
    message = 'Not subscribed'


class StratumRPCSuccessResponse(RPCResponse):
    def _to_dict(self):
        return {
            'id': self.unique_id,
            'result': self.result,
            'error': None
        }

    def serialize(self):
        return json.dumps(self._to_dict())


# hardcode traceback to be null for now
class StratumRPCErrorResponse(RPCErrorResponse):
    def _to_dict(self):
        return {
            'id': self.unique_id,
            'result': None,
            'error': (self._jsonrpc_error_code, str(self.error), None)
        }

    def serialize(self):
        return json.dumps(self._to_dict())


def _get_code_and_message(error):
    assert isinstance(error, (Exception, basestring))
    if isinstance(error, Exception):
        if hasattr(error, 'jsonrpc_error_code'):
            code = error.jsonrpc_error_code
            msg = str(error)
        elif isinstance(error, InvalidRequestError):
            code = JSONRPCInvalidRequestError.jsonrpc_error_code
            msg = JSONRPCInvalidRequestError.message
        elif isinstance(error, MethodNotFoundError):
            code = JSONRPCMethodNotFoundError.jsonrpc_error_code
            msg = JSONRPCMethodNotFoundError.message
        else:
            # allow exception message to propagate
            code = JSONRPCServerError.jsonrpc_error_code
            msg = str(error)
    else:
        code = -32000
        msg = error

    return code, msg


class StratumRPCRequest(RPCRequest):
    def error_respond(self, error):
        if not self.unique_id:
            return None

        response = StratumRPCErrorResponse()

        code, msg = _get_code_and_message(error)

        response.error = msg
        response.unique_id = self.unique_id
        response._jsonrpc_error_code = code
        return response

    def respond(self, result):
        response = StratumRPCSuccessResponse()

        if not self.unique_id:
            return None

        response.result = result
        response.unique_id = self.unique_id

        return response

    def _to_dict(self):
        jdata = {'method': self.method}
        if self.args:
            jdata['params'] = self.args
        if self.kwargs:
            jdata['params'] = self.kwargs
        if self.unique_id is not None:
            jdata['id'] = self.unique_id
        return jdata

    def serialize(self):
        return json.dumps(self._to_dict())


class StratumRPCProtocol(RPCBatchProtocol):
    """Stratum JSONRPC protocol implementation."""

    _ALLOWED_REPLY_KEYS = sorted(['id', 'result', 'error'])
    _ALLOWED_REQUEST_KEYS = sorted(['id', 'method', 'params'])

    def __init__(self, *args, **kwargs):
        super(StratumRPCProtocol, self).__init__(*args, **kwargs)
        self._id_counter = 0

    def _get_unique_id(self):
        self._id_counter += 1
        return self._id_counter

    def create_request(self, method, args=None, kwargs=None, one_way=False):
        if args and kwargs:
            raise InvalidRequestError('Does not support args and kwargs at the same time')

        request = StratumRPCRequest()

        if not one_way:
            request.unique_id = self._get_unique_id()

        request.method = method
        request.args = args
        request.kwargs = kwargs

        return request

    def parse_reply(self, data):
        try:
            rep = json.loads(data)
        except Exception as e:
            raise InvalidReplyError(e)

        for k in rep.iterkeys():
            if not k in self._ALLOWED_REPLY_KEYS:
                raise InvalidReplyError('Key not allowed: %s' % k)

        if rep.get('id', None) is None:
            raise InvalidReplyError('Missing id in response')

        # if ('error' in rep) == ('result' in rep):
        #     raise InvalidReplyError('Reply must contain exactly one of result and error.')

        if rep.get('error', None) is not None:
            response = StratumRPCErrorResponse()
            error = rep['error']
            response._jsonrpc_error_code = error[0]
            response.error = error[1]
        else:
            response = StratumRPCSuccessResponse()
            response.result = rep.get('result', None)

        response.unique_id = rep['id']

        return response

    def parse_request(self, data):
        try:
            req = json.loads(data)
        except Exception as e:
            raise JSONRPCParseError()

        if isinstance(req, list):
            raise InvalidRequestError('Batch request is not supported by Stratum.')
        else:
            return self._parse_subrequest(req)

    def _parse_subrequest(self, req):
        for k in req.iterkeys():
            if not k in self._ALLOWED_REQUEST_KEYS:
                raise JSONRPCInvalidRequestError()

        if not isinstance(req['method'], basestring):
            raise JSONRPCInvalidRequestError()

        request = StratumRPCRequest()
        request.method = req['method']
        request.unique_id = req.get('id', None)

        params = req.get('params', None)
        if params is not None:
            if isinstance(params, list):
                request.args = req['params']
            elif isinstance(params, dict):
                request.kwargs = req['params']
            else:
                raise JSONRPCInvalidParamsError()

        return request
