from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class FrontendHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        path = urlsplit(self.path).path.lower()

        is_html = (
            path.endswith(".html")
            or path.endswith("/")
            or "." not in path.rsplit("/", 1)[-1]
        )

        if is_html:
            self.send_header(
                "Cache-Control",
                "no-store, no-cache, must-revalidate, max-age=0",
            )
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")

        super().end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        ("0.0.0.0", 8080),
        FrontendHandler,
    )

    server.serve_forever()
