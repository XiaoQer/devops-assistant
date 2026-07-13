import base64
import ipaddress
import json
import re
import socket
import ssl
from urllib.parse import parse_qsl, urlencode, urlparse

import urllib3
from urllib3.exceptions import (
    ConnectTimeoutError,
    HTTPError,
    NewConnectionError,
    ReadTimeoutError,
    SSLError as Urllib3SSLError,
)


class UnsafeRegistryTarget(ValueError):
    pass


class OCIRegistryClient:
    MAX_TOKEN_RESPONSE_BYTES = 64 * 1024
    CHALLENGE_PARAMETER = re.compile(r'([A-Za-z][A-Za-z0-9_-]*)="([^"\r\n]*)"')

    def __init__(self, requester=None, resolver=None):
        self._requester = requester or self._urllib3_request
        self._resolver = resolver or socket.getaddrinfo

    def test(self, server, username, token, skip_tls_verify=False):
        tls_verified = not skip_tls_verify
        try:
            registry_url = self._registry_url(server)
            basic_header = self._basic_authorization(username, token)
            response = self._request(
                "GET",
                registry_url,
                headers={"Authorization": basic_header},
                skip_tls_verify=skip_tls_verify,
            )
            status = response.status
            challenge = self._header(response.headers, "www-authenticate")
            self._discard_response(response)
            if 200 <= status < 300:
                return self._success("basic", tls_verified)
            if status == 403:
                return self._failure("authentication_failed", tls_verified)
            if status == 401:
                return self._authenticate_challenge(
                    challenge,
                    registry_url,
                    basic_header,
                    skip_tls_verify,
                    tls_verified,
                )
            return self._failure("protocol_error", tls_verified)
        except UnsafeRegistryTarget:
            return self._failure("protocol_error", tls_verified)
        except (ssl.SSLError, Urllib3SSLError):
            return self._failure("tls_failed", tls_verified)
        except NewConnectionError:
            return self._failure("unreachable", tls_verified)
        except (TimeoutError, ConnectTimeoutError, ReadTimeoutError):
            return self._failure("timeout", tls_verified)
        except OSError:
            return self._failure("unreachable", tls_verified)
        except (HTTPError, ValueError, TypeError, json.JSONDecodeError):
            return self._failure("protocol_error", tls_verified)

    def _authenticate_challenge(
        self,
        challenge,
        registry_url,
        basic_header,
        skip_tls_verify,
        tls_verified,
    ):
        if not challenge:
            return self._failure("protocol_error", tls_verified)
        scheme, _, parameters = challenge.partition(" ")
        if scheme.lower() == "basic":
            return self._failure("authentication_failed", tls_verified)
        if scheme.lower() != "bearer":
            return self._failure("protocol_error", tls_verified)

        values = {
            key.lower(): value
            for key, value in self.CHALLENGE_PARAMETER.findall(parameters)
        }
        realm = values.get("realm")
        if not realm:
            return self._failure("protocol_error", tls_verified)
        fields = {
            key: values[key]
            for key in ("service", "scope")
            if values.get(key)
        }
        token_response = self._request(
            "GET",
            realm,
            headers={"Authorization": basic_header},
            fields=fields,
            skip_tls_verify=skip_tls_verify,
        )
        if token_response.status in {401, 403}:
            self._discard_response(token_response)
            return self._failure("authentication_failed", tls_verified)
        if not self._successful(token_response):
            self._discard_response(token_response)
            return self._failure("protocol_error", tls_verified)
        token_data = self._read_limited(token_response)
        if token_data is None:
            return self._failure("protocol_error", tls_verified)
        document = json.loads(token_data.decode("utf-8"))
        if not isinstance(document, dict):
            return self._failure("protocol_error", tls_verified)
        bearer_token = document.get("token") or document.get("access_token")
        if not isinstance(bearer_token, str) or not bearer_token:
            return self._failure("protocol_error", tls_verified)

        authenticated = self._request(
            "GET",
            registry_url,
            headers={"Authorization": f"Bearer {bearer_token}"},
            skip_tls_verify=skip_tls_verify,
        )
        authenticated_status = authenticated.status
        self._discard_response(authenticated)
        if 200 <= authenticated_status < 300:
            return self._success("bearer", tls_verified)
        if authenticated_status in {401, 403}:
            return self._failure("authentication_failed", tls_verified)
        return self._failure("protocol_error", tls_verified)

    def _request(self, method, url, headers, skip_tls_verify, fields=None):
        parsed, resolved_ip = self._validated_target(url)
        return self._requester(
            method,
            url,
            headers=headers,
            fields=fields or {},
            skip_tls_verify=skip_tls_verify,
            resolved_ip=resolved_ip,
            server_hostname=parsed.hostname,
        )

    @staticmethod
    def _urllib3_request(
        method,
        url,
        headers,
        fields,
        skip_tls_verify,
        resolved_ip,
        server_hostname,
    ):
        parsed = urlparse(url)
        port = parsed.port or 443
        pool = urllib3.HTTPSConnectionPool(
            resolved_ip,
            port,
            cert_reqs="CERT_NONE" if skip_tls_verify else "CERT_REQUIRED",
            assert_hostname=False if skip_tls_verify else server_hostname,
            server_hostname=server_hostname,
        )
        query = parse_qsl(parsed.query, keep_blank_values=True)
        query.extend((key, value) for key, value in fields.items())
        target = parsed.path or "/"
        if query:
            target = f"{target}?{urlencode(query)}"
        request_headers = {**headers, "Host": parsed.netloc}
        return pool.request(
            method,
            target,
            headers=request_headers,
            timeout=urllib3.Timeout(connect=5.0, read=10.0),
            retries=False,
            redirect=False,
            preload_content=False,
        )

    @staticmethod
    def _registry_url(server):
        value = str(server or "").strip().rstrip("/")
        if "://" in value:
            parsed_input = urlparse(value)
            if parsed_input.scheme.lower() != "https":
                raise UnsafeRegistryTarget()
            if parsed_input.path or parsed_input.query or parsed_input.fragment:
                raise UnsafeRegistryTarget()
            base_url = value
        else:
            base_url = f"https://{value}"
        return f"{base_url}/v2/"

    def _validated_target(self, url):
        parsed = urlparse(url)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.hostname.lower() == "localhost"
        ):
            raise UnsafeRegistryTarget()
        port = parsed.port or 443
        try:
            literal = ipaddress.ip_address(parsed.hostname)
            addresses = [literal]
        except ValueError:
            resolved = self._resolver(
                parsed.hostname,
                port,
                type=socket.SOCK_STREAM,
            )
            addresses = [ipaddress.ip_address(item[4][0]) for item in resolved]
        if not addresses or any(self._unsafe_address(address) for address in addresses):
            raise UnsafeRegistryTarget()
        return parsed, str(addresses[0])

    def _read_limited(self, response):
        content_length = self._header(response.headers, "content-length")
        if content_length:
            try:
                if int(content_length) > self.MAX_TOKEN_RESPONSE_BYTES:
                    self._discard_response(response)
                    return None
            except ValueError:
                pass
        try:
            reader = getattr(response, "read", None)
            if callable(reader):
                data = reader(self.MAX_TOKEN_RESPONSE_BYTES + 1)
            else:
                data = response.data or b""
        finally:
            self._discard_response(response)
        if len(data) > self.MAX_TOKEN_RESPONSE_BYTES:
            return None
        return data

    @staticmethod
    def _discard_response(response):
        closer = getattr(response, "close", None)
        if callable(closer):
            closer()
        releaser = getattr(response, "release_conn", None)
        if callable(releaser):
            releaser()

    @staticmethod
    def _unsafe_address(address):
        return (
            address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_unspecified
        )

    @staticmethod
    def _basic_authorization(username, token):
        encoded = base64.b64encode(
            f"{str(username)}:{str(token)}".encode("utf-8")
        ).decode("ascii")
        return f"Basic {encoded}"

    @staticmethod
    def _header(headers, name):
        for key, value in (headers or {}).items():
            if str(key).lower() == name:
                return str(value)
        return None

    @staticmethod
    def _successful(response):
        return 200 <= response.status < 300

    @staticmethod
    def _success(auth_method, tls_verified):
        message = "Registry 连接与认证成功"
        if not tls_verified:
            message = "Registry 连接与认证成功，但 TLS 证书未验证"
        return {
            "connected": True,
            "message": message,
            "tls_verified": tls_verified,
            "auth_method": auth_method,
        }

    @staticmethod
    def _failure(reason, tls_verified):
        messages = {
            "authentication_failed": "Registry 用户名或 Token 无效",
            "tls_failed": "Registry TLS 证书校验失败",
            "timeout": "Registry 连接超时",
            "unreachable": "Registry 网络不可达",
            "protocol_error": "Registry 响应不符合 OCI 协议或目标不安全",
        }
        return {
            "connected": False,
            "message": messages[reason],
            "tls_verified": tls_verified,
            "failure_reason": reason,
        }
