from dataclasses import dataclass


@dataclass
class StatusCode:
    CodeErrAccessTokenExpired = 4012
    CodeErrAccessTokenInvalid = 4013


TRACE_ID_KEY = "trace_id"
SPAN_ID_KEY = "span_id"
REQUEST_ID_KEY = "request_id"
EXTRA_LOG_FIELDS_KEY = "extra"
FILE_KEY = "file"
ERROR_KEY = "error"
TRACEBACK_KEY = "traceback"

HTTP_METHOD_KEY = "http.request.method"
HTTP_STATUS_KEY = "http.response.status_code"
HTTP_ROUTE_KEY = "http.route"
HTTP_REQUEST_DURATION_KEY = "http.server.request.duration"

TELEGRAM_USERBOT_USER_ID_KEY = "organization.userbot.user_id"
TELEGRAM_UPDATE_TYPE_KEY = "organization.update.type"
TELEGRAM_CHAT_ID_KEY = "organization.chat.id"
TELEGRAM_USER_USERNAME_KEY = "organization.user.username"
TELEGRAM_USER_MESSAGE_KEY = "organization.user.message"
TELEGRAM_MESSAGE_ID_KEY = "organization.message.id"
TELEGRAM_MESSAGE_DURATION_KEY = "organization.message.duration"
TELEGRAM_MESSAGE_DIRECTION_KEY = "organization.message.direction"
TELEGRAM_CHAT_TYPE_KEY = "organization.chat.type"

REQUEST_DURATION_METRIC = "http.server.request.duration"
ACTIVE_REQUESTS_METRIC = "http.server.active_requests"
REQUEST_BODY_SIZE_METRIC = "http.server.request.body.size"
RESPONSE_BODY_SIZE_METRIC = "http.server.response.body.size"
OK_REQUEST_TOTAL_METRIC = "http.server.ok.request.total"
ERROR_REQUEST_TOTAL_METRIC = "http.server.error.request.total"

OK_MESSAGE_TOTAL_METRIC = "organization.server.ok.message.total"
ERROR_MESSAGE_TOTAL_METRIC = "organization.server.error.message.total"
OK_JOIN_CHAT_TOTAL_METRIC = "organization.server.ok.join_chat.total"
ERROR_JOIN_CHAT_TOTAL_METRIC = "organization.server.error.join_chat.total"
MESSAGE_DURATION_METRIC = "organization.server.message.duration"
ACTIVE_MESSAGES_METRIC = "organization.server.active_messages"

TRACE_ID_HEADER = "X-Trace-ID"
SPAN_ID_HEADER = "X-Span-ID"
