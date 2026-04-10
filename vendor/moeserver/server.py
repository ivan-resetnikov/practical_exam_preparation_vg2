"""
moeserver Copyright (c) 2026 ved Reshetnikov Ivan - alle rettigheter forbeholdt.

server.py - HTTP server and request handling
"""

import socket
import errno
import logging
import selectors
import os
import importlib
import re
import inspect
import json

from collections.abc import Callable



LIB_NAME: str = "moeserver"


logger = logging.getLogger(LIB_NAME)
logger.setLevel(logging.WARNING)

selector = selectors.DefaultSelector()



# NOTE(vanya): Experimenting with Result type pattern from Rust
class Error:
    SUCCESS: int = 0
    UNKNOWN: int = 1

    SERVER_BIND_FAIL: int = 2
    CLIENT_CONNECTION_BROKEN: int = 3

    NOT_FOUND: int = 4
    REJECTED: int = 5



class PublicAccessPolicy:
    SERVE_NONE: int = 0
    SERVE_ALL: int = 1
    SERVE_CALLBACK: int = 2



class Route:
    path: str = ""
    render_callback: Callable = None



class Component:
    name: str = ""
    render_callback: Callable = None



class App:
    def __init__(self):
        self.serving: bool = False
        self.routes: list[Route] = []
        self.components: list[Component] = []
        self.public_dir_path: str = ""
        self.public_dir_route: str = ""
        self.default_language: str = ""


    def route(self, p_route_path: str) -> Callable:
        if not p_route_path:
            logger.error("Route path cannot be empty!")
            return lambda f: f

        def decorator(p_user_page_render_function: Callable) -> Callable:
            logger.info(f"Registering new route `{p_route_path}`")

            new_route = Route()
            new_route.path = p_route_path
            new_route.render_callback = p_user_page_render_function

            self.routes.append(new_route)

            return p_user_page_render_function

        return decorator
    

    def component(self, p_component_name: str) -> Callable:
        if not p_component_name:
            logger.error("Component name cannot be empty!")
            return lambda f: f

        def decorator(p_user_component_render_function: Callable) -> Callable:
            self.register_component(p_component_name, p_user_component_render_function)

            return p_user_component_render_function

        return decorator
    

    def register_component(self, p_name: str, p_render_callback: Callable) -> Error:
        logger.info(f"Registering new component `{p_name}`")

        new_component = Component()
        new_component.name = p_name
        new_component.render_callback = p_render_callback

        self.components.append(new_component)

        # TODO(vanya): Check for colliding component names

        return Error.SUCCESS


    def render_html(self, p_html_source: str, p_renderpass_params: dict, p_paste_keys: dict) -> str:
        rendered_source: str = p_html_source

        # NOTE(vanya): Replace all component syntax with registered components until none are lefr
        while True:
            # NOTE(vanya): Match component syntax
            component_regex_match = re.search(r"\{\{.*?\}\}", rendered_source)
            
            if component_regex_match == None:
                # NOTE(vanya): No components left to replace
                break
            
            replace_str: str = ""

            # NOTE(vanya): Parse component syntax
            component_syntax: str = component_regex_match.group(0)
            component_inner_syntax: str = component_syntax.removeprefix("{{").removesuffix("}}").strip()
            component_inner_tokens: list[str] = component_inner_syntax.split(" ")

            key_value_pairs = dict(re.findall(r'(\w+)="([^"]*)"', component_inner_syntax))

            requested_component_name: str = component_inner_syntax.split(None, 1)[0]

            if not requested_component_name:
                logger.warning(f"Component syntax without a component name! `{component_syntax}` `{requested_component_name}`")

            # NOTE(vanya): Search for a component to render the replacement
            found_requested_component: bool = False
            for component in self.components:
                if component.name == requested_component_name:
                    # NOTE(vanya): Call component rendering function with argments and renderpass parameters
                    replace_str = component.render_callback(key_value_pairs, p_renderpass_params)

                    found_requested_component = True
                    break
            
            if not found_requested_component:
                if requested_component_name in p_paste_keys:
                    replace_str = p_paste_keys[requested_component_name]
                else:
                    logger.error(f"Could not find a requested component `{requested_component_name}`.")

            # NOTE(vanya): Replace HTML source
            rendered_source = rendered_source[:component_regex_match.start()] + replace_str + rendered_source[component_regex_match.end():]

        return rendered_source


    def render_html_file(self, p_html_file_path: str, p_renderpass_params: dict={}, p_paste_keys: dict={}) -> str:
        with open(p_html_file_path, "r", encoding="utf-8") as f:
            return self.render_html(f.read(), p_renderpass_params, p_paste_keys)
    

    def load_file_bytes(self, p_file_path: str) -> bytes:
        with open(p_file_path, "rb") as f:
            return f.read()
    

    def enable_translation(self, p_translation_file_path: str, p_default_language: str) -> Error:
        self.default_language = p_default_language
        self.translation_file_path = p_translation_file_path

        @self.component("translate")
        def translate(p_args: dict, p_renderpass_params: dict) -> str:
            text_to_translate: str = p_args.get("text", "")
            requested_language: str = p_renderpass_params.get("requested_language", self.default_language)

            if self.default_language == requested_language:
                return text_to_translate

            with open(self.translation_file_path, "r", encoding="utf-8") as f:
                translation_lut: dict = json.load(f)
            
            if requested_language in translation_lut:
                language_translation_lut: dict = translation_lut[requested_language]
                if text_to_translate in language_translation_lut:
                    return language_translation_lut[text_to_translate]
                else:
                    logger.warning(f"Requested language for translation `{requested_language}` does not have the key to replace `{text_to_translate}` with.")
                    logger.info("Returning translation key.")
                    return text_to_translate
            else:
                logger.warning(f"Requested language for translation `{requested_language}` was not found in the translation file.")
                logger.info("Returning translation key.")
                return text_to_translate
        

    def set_public_dir(self, p_path: str, p_route_prefix: str, p_access_policy: PublicAccessPolicy, p_serve_callback: Callable=None) -> Error:
        self.public_dir_path = p_path
        self.public_dir_route = p_route_prefix
        self.public_access_policy = p_access_policy
        self.public_access_serve_callback = p_serve_callback

        match self.public_access_policy:
            case PublicAccessPolicy.SERVE_NONE:
                pass

            case PublicAccessPolicy.SERVE_ALL:
                pass
            
            case PublicAccessPolicy.SERVE_CALLBACK:
                pass
        
        return Error.SUCCESS
    

    def register_components_from_dir(self, p_path: str) -> Error:
        logger.debug(f"Scanning directory `{p_path}` to register components.")

        for entry_name in os.listdir(p_path):
            entry_path: str = os.path.join(p_path, entry_name)

            if os.path.isfile(entry_path):
                if entry_name.endswith(".py"):
                    logger.debug(f"Found {entry_path} - Attempting to import and call `register_components(app)`")
                    
                    project_root_path: str = os.path.abspath(os.getcwd())

                    if not os.path.abspath(entry_path).startswith(project_root_path):
                        logger.warning(f"{entry_path} is not in the same directory (or any of its children directories) and the project root - cannot import the module.")
                        continue
                    
                    module_path: str = \
                        os.path.relpath(entry_path, project_root_path) \
                        .replace(os.sep, ".") \
                        .removesuffix(".py")
                    
                    module_path_has_illegal_characters: bool = False
                    for module_path_part in module_path.split("."):
                        if not self.is_valid_python_module_name(module_path_part):
                            module_path_has_illegal_characters = True
                            break
                    
                    if module_path_has_illegal_characters:
                        logger.warning(f"Module path `{module_path}` has illegal characters. (Each part can only have A-Z, 0-9, and underscores. And must not begin with a number)")
                        continue

                    component_registrar_module = importlib.import_module(module_path)
                    
                    if hasattr(component_registrar_module, "register_components_for_app"):
                        component_registrar_module.register_components_for_app(self)
                    else:
                        logger.error(f"Module `{module_path}` has no function `register_components_for_app` which usually registers the components.")
                
                elif entry_name.endswith(".html"):
                    def simple_html_render_callback(p_html_file_path=entry_path) -> bytes:
                        return self.render_html_file(p_html_file_path)
                    
                    self.register_component(entry_name, simple_html_render_callback)
        
        return Error.SUCCESS
    

    def serve_until_KeyboardInterrupt(self, p_ip: str, p_port: int) -> Error:
        # NOTE(vanya): Gotta support IPv6 with AF_INET6 one day
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # NOTE(vanya): Ignore TCP socket in TIME_WAIT for quick developement iterating
        # Otherwise every time the app goes down it can't restart on the same port for 30 seconds ~ 2 minutes
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # NOTE(vanya): We'll need to support these
            # * 127.0.0.1 - local only
            # * 0.0.0.0 - all interfaces
            # * :: - all interfaces (IPv6)
            server.bind((p_ip, p_port))
        except OSError as error:
            match error.errno:
                case errno.EADDRINUSE:
                    logger.critical(f"OSError .errno=EADDRINUSE ({e.errno}) - Port already in use.")
                case errno.EACCES:
                    logger.critical(f"OSError .errno=EACCES ({e.errno}) - Permission denied by the OS.")
                case errno.EINVAL:
                    logger.critical(f"OSError .errno=EINVAL ({e.errno}) - Invalid address.")
                case errno.EAFNOSUPPORT:
                    logger.critical(f"OSError .errno=EAFNOSUPPORT ({e.errno}) - Correct address info but not supported. (Trying to use IPv6? {LIB_NAME} only implements IPv4)")
                case errno.EADDRNOTAVAIL:
                    logger.critical(f"OSError .errno=EADDRNOTAVAIL ({e.errno}) - Trying to bind to an IP not assigned to your machine.")
                case errno.EOPNOTSUPP:
                    logger.critical(f"OSError .errno=EADDRNOTAVAIL ({e.errno}) - Binding not supported by the OS.")
                case _:
                    logger.critical(f"OSError .errno={e.errno} - Unhandled by {LIB_NAME} error!")
            return Error.SERVER_BIND_FAIL
        
        server.listen()
        server.setblocking(False)

        logger.info(f"App up at `http://{p_ip}:{p_port}`")

        self.serving = True
        try:
            # NOTE(vanya): Create a Python selector - An abstraction over event APIs for syscalls.
            # Backends:
            # * epoll - Linux and Android
            # * kqueue - MacOS and BSD
            # * IOCP - Windows
            selector.register(server, selectors.EVENT_READ, data={"type": "server"})

            while self.serving:
                events = selector.select()

                for key, mask in events:
                    event_sender_type: str = key.data.get("type", "")

                    if event_sender_type == "server":
                        client_socket, client_address = server.accept()
                        client_socket.setblocking(False)

                        logger.debug(f"New client socket at `{client_address[0]}:{client_address[1]}`")

                        selector.register(
                            client_socket,
                            selectors.EVENT_READ,
                            data={
                                "type": "client",
                                "address": client_address,
                                "outgoing_bytes": b""
                            }
                        )
                    
                    elif event_sender_type == "client":
                        client_socket = key.fileobj

                        if mask & selectors.EVENT_READ:
                            match self.recieve_and_handle_http(key):
                                case Error.CLIENT_CONNECTION_BROKEN:
                                    selector.unregister(client_socket)
                                    client_socket.close()

                        if mask & selectors.EVENT_WRITE:
                            # NOTE(vanya): Send the outgoing buffer

                            outgoing_bytes_left: bytes = key.data["outgoing_bytes"]

                            if outgoing_bytes_left:
                                try:
                                    transfered_bytes: int = client_socket.send(outgoing_bytes_left)
                                    key.data["outgoing_bytes"] = outgoing_bytes_left[transfered_bytes:]

                                    logger.debug(f"Sending data until response finished. {transfered_bytes} sent, {len(key.data["outgoing_bytes"])} bytes left")
                                
                                except ConnectionError:
                                    logger.debug(f"Client `{key.data['address'][0]}:{key.data['address'][1]}` disconnected.")
                                    selector.unregister(client_socket)
                                    client_socket.close()
                                
                                except BlockingIOError:
                                    pass

                            elif len(key.data["outgoing_bytes"]) == 0:
                                logger.debug("Finished sending response.")
                                selector.unregister(client_socket)
                                client_socket.close()
                            
            
            logger.info(f"App down, because App.serving == False")
            
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt from Python, closing server.")
            self.serving = False
        
        server.close()

        return Error.SUCCESS
    

    def recieve_and_handle_http(self, p_client_key) -> Error:
        client_socket: socket.socket = p_client_key.fileobj
        client_address: tuple[str, int] = p_client_key.data["address"]

        try:
            # NOTE(vanya): Receive full request
            data: bytes = b""

            logger.debug(f"Recieving data from `{client_address[0]}:{client_address[1]}`")

            while b"\r\n\r\n" not in data:
                chunk = client_socket.recv(4096)

                if not chunk:
                    break

                data += chunk

            if len(data) == 0:
                return Error.CLIENT_CONNECTION_BROKEN

            # NOTE(vanya): Parse request
            request_and_header_bytes, body_bytes = data.split(b"\r\n\r\n", 1)

            request_and_header: str = request_and_header_bytes.decode()
            request_and_header_lines: list[str] = request_and_header.split("\r\n")

            request_line: str = request_and_header_lines[0]
            header_lines: list[str] = request_and_header_lines[1:]

            # NOTE(vanya): Debug-print request info
            logger.debug("\tRequest:")
            logger.debug(f"\t\t{request_line}")

            logger.debug("\tHeader:")
            for header_line in header_lines:
                logger.debug(f"\t\t{header_line}")
            
            logger.debug(f"\t+{len(body_bytes)} bytes of body")

            # NOTE(vanya): Handle request
            header_dict: dict = {}
            for header_line in header_lines:
                key, value = tuple(header_line.split(": "))
                header_dict[key] = value

            request_method, request_path, request_protocol_version = tuple(request_line.split(" ", 2))

            response_bytes: bytes = self.get_request_response(
                request_method,
                request_path,
                request_protocol_version,
                header_dict,
                body_bytes
            )

            # NOTE(vanya): Queue response bytes
            logger.debug(f"Sending response {len(response_bytes)} bytes")

            p_client_key.data["outgoing_bytes"] = response_bytes

            selector.modify(
                client_socket,
                selectors.EVENT_READ | selectors.EVENT_WRITE,
                p_client_key.data
            )

            return Error.SUCCESS

        except ConnectionError:
            return Error.CLIENT_CONNECTION_BROKEN


    def get_request_response(self, p_method: str, p_path: str, p_protocol_version: str, p_header_data: dict, p_data: bytes) -> bytes:
        match p_method:
            case "GET":
                return self.handle_GET_response(p_path, p_protocol_version, p_header_data, p_data)
            
            case "POST":
                # TODO(vanya)
                return b"HTTP/1.1 405 Method Not Allowed\r\n\r\n"
            
            case "PUT":
                # TODO(vanya)
                return b"HTTP/1.1 405 Method Not Allowed\r\n\r\n"
            
            case "PATCH":
                # TODO(vanya)
                return b"HTTP/1.1 405 Method Not Allowed\r\n\r\n"
            
            case "DELETE":
                # TODO(vanya)
                return b"HTTP/1.1 405 Method Not Allowed\r\n\r\n"
            
            case "HEAD":
                # TODO(vanya)
                return b"HTTP/1.1 405 Method Not Allowed\r\n\r\n"
            
            case "OPTIONS":
                # TODO(vanya)
                return b"HTTP/1.1 405 Method Not Allowed\r\n\r\n"

            case _:
                return b"HTTP/1.1 405 Method Not Allowed\r\n\r\n"
    

    def handle_GET_response(self, p_path: str, _p_protocol_version: str, p_header_data: dict, p_extra_data: bytes) -> bytes:
        status_line, header_lines, body = self.get_route_response(p_path, p_header_data, p_extra_data)

        # NOTE(vanya): Debug-print response
        logger.debug("Response:")
        logger.debug("\tStatus:")
        logger.debug(f"\t\t{status_line}")

        logger.debug("\tHeader:")
        for header_line in header_lines:
            logger.debug(f"\t\t{header_line}")

            header_key, header_value = tuple(header_line.split(": "))

            match header_key:
                case _:
                    pass
        
        logger.debug(f"\t+{len(body)} bytes of body")
        
        # NOTE(vanya): Combine response header lines, content delimeter, and content
        return (
            (
                status_line + "\r\n"
                + "\r\n".join(header_lines)
                + "\r\n\r\n"
            ).encode("utf-8")
            + body
        )
    

    def get_route_response(self, p_path: str, p_header_data: dict, p_extra_data: bytes) -> tuple[str, list[str], bytes]:
        status_line: str = ""
        header_lines: list[str] = []
        body: bytes = b""

        route_data, error = self.get_route_bytes_or_404(p_path, p_header_data, p_extra_data)

        match error:
            case Error.SUCCESS:
                status_line = "HTTP/1.1 200 OK"

                header_lines.append(f"Content-Length: {len(route_data)}")
                
                body = route_data
            
            case Error.NOT_FOUND:
                status_line = "HTTP/1.1 404 Not Found"
            
            case Error.REJECTED:
                status_line = "HTTP/1.1 403 Rejected"
        
        return status_line, header_lines, body
    

    def get_route_bytes_or_404(self, p_path: str, p_header_data: dict, p_request_data: bytes) -> tuple[bytes, Error]:
        # NOTE(vanya): Serve hard-coded routes
        requested_route_bytes, error = self.get_route(p_path, p_header_data, p_request_data)
        if error == Error.SUCCESS:
            logger.debug(f"Serving route `{p_path}`")
            return (requested_route_bytes, Error.SUCCESS)
    
        is_in_public_dir: bool = self.public_dir_route and p_path.startswith(self.public_dir_route)
        
        if is_in_public_dir:
            # NOTE(vanya): Serve 404 asset

            rel_path: str = os.path.join(self.public_dir_path, p_path.removeprefix(self.public_dir_route))
            if os.path.exists(rel_path):
                match self.public_access_policy:
                    case PublicAccessPolicy.SERVE_NONE:
                        return (b"", Error.REJECTED)

                    case PublicAccessPolicy.SERVE_ALL:
                        return (self.load_file_bytes(rel_path), Error.SUCCESS)
                    
                    case PublicAccessPolicy.SERVE_CALLBACK:
                        return self.public_access_serve_callback(p_path, p_header_data, p_request_data)
            else:
                # TODO(vanya): Custom 404 for public assets
                logger.warning(f"Asset route not found `{p_path}`.")
                return (b"404 - Route not found", Error.NOT_FOUND)

        else:
            # NOTE(vanya): Serve 404 page (not asset)

            route_404_bytes, error = self.get_route("404", p_header_data, p_request_data)
            if error == Error.SUCCESS:
                logger.info(f"Serving route `404` for requested path `{p_path}`")
                return (route_404_bytes, Error.SUCCESS)
        
            logger.warning(f"Route not found `{p_path}`, and no custom 404 page (Searched for route `404`), serving {LIB_NAME}'s default 404 page.")

        # NOTE(vanya): Complete 404
        return (b"404 - Route not found", Error.SUCCESS)
    

    def get_route(self, p_path: str, p_header_data: dict, p_request_data: bytes) -> tuple[bytes, Error]:
        logger.debug(f"Matching registered routes for requested path `{p_path}`")

        requested_language: str = p_header_data.get("Accept-Language", self.default_language).split(",", 1)[0]

        renderpass_params: dict = {
            "requested_language": requested_language
        }

        for route in self.routes:
            catchall_params: dict = {}

            route_path_parts: list[str] = route.path.split("/")
            requested_path_parts: list[str] = p_path.split("/")

            if len(route_path_parts) != len(requested_path_parts):
                continue

            part_index_to_check: int = 0
            while part_index_to_check < len(route_path_parts):
                route_path_part: str = route_path_parts[part_index_to_check]
                requested_path_part: str = requested_path_parts[part_index_to_check]
                
                part_matched: bool = False

                if route_path_part.startswith("[") and route_path_part.endswith("]"):
                    # NOTE(vanya): Catchall key
                    catchall_key: str = route_path_part[1:-1]

                    catchall_params[catchall_key] = requested_path_part
                    part_matched = True

                else:
                    part_matched = (route_path_part == requested_path_part)
                
                if part_matched:
                    # NOTE(vanya): Check if matched the entire path
                    if part_index_to_check + 1 == len(route_path_parts):
                        # NOTE(vanya): Render route
                        return (route.render_callback(renderpass_params, catchall_params), Error.SUCCESS)
                else:
                    # NOTE(vanya): Route didn't match
                    break
                
                part_index_to_check += 1
        
        return (b"404", Error.NOT_FOUND)
    

    def is_valid_python_module_name(self, p_name: str) -> bool:
        return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", p_name) != None
