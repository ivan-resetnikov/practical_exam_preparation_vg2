"""
Praksisk eksamen forberedelse Copyright (c) 2026 ved Reshetnikov Ivan - alle rettigheter forbeholdt.
"""

import logging
import vendor.moeserver.server as server


# NOTE(vanya): Enable logging from the server and for us
logging.basicConfig(level=logging.DEBUG)
server.logger.setLevel(logging.INFO)


app = server.App()


@app.route("/")
def route_index(p_renderpass_params: dict, _p_catchall_params: dict) -> bytes:
    return app.render_html_file("./pages/statistics.html", p_renderpass_params,
        {
            "pie_total_problems": str(0),
            "pie_not_started": str(0),
            "pie_dealing_with": str(0),
            "pie_solved_problems": str(0),
            "pie_avg_response_time": str(0),
            "pie_avg_solution_time": str(0),
        }
    ).encode("utf-8")


app.enable_translation("./translation.json", "nb")
app.register_components_from_dir("./components/")
app.set_public_dir("./public/", "/public/", server.PublicAccessPolicy.SERVE_ALL)
app.serve_until_KeyboardInterrupt("localhost", 8001)
