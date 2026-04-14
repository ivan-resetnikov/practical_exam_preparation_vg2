"""
Praksisk eksamen forberedelse Copyright (c) 2026 ved Reshetnikov Ivan - alle rettigheter forbeholdt.
"""

import logging

import vendor.moeserver.server as server
import vendor.moeserver.html_factory as html_factory

import db


# NOTE(vanya): Enable logging from the server and for us
logging.basicConfig(level=logging.DEBUG)
server.logger.setLevel(logging.INFO)


app = server.App()


@app.route("/")
def route_index(p_renderpass_params: dict, _p_catchall_params: dict) -> bytes:
    def weights_to_pie_chart_angles(p_values: list[int]) -> list[int]:
        total: float = float(sum(p_values))

        output_angles: list[float] = []
        last_angle: float = 0.0

        for value in p_values:
            value_fraction_or_0: float = (value / total) if value > 0.0 else 0.0

            output_angles.append(last_angle + value_fraction_or_0 * 360.0)
            last_angle = output_angles[-1]
        
        return output_angles

    def render_tickers_feed() -> str:
        root = html_factory.HTMLFactory()

        table = root.push_element(None, "table")
        tr = root.push_element(table, "tr")
        root.push_element(tr, "td", "Reporter")
        root.push_element(tr, "td", "Summary")
        root.push_element(tr, "td", "Time passed")
        root.push_element(tr, "td", "")

        # for tickets in db.load_unsolved_ticket_range(0, 20):
        #     root.push_element(tr, "td", "Reporter")
        #     root.push_element(tr, "td", "Summary")
        #     root.push_element(tr, "td", "Time passed")
        #     root.push_element(tr, "td", "")
        
        return root.render_html()

        

    pie_chart_angles: list[float] = weights_to_pie_chart_angles([0, 0, 0])

    return app.render_html_file("../pages/statistics.html", p_renderpass_params,
        {
            "pie_total": str(0),
            "pie_not_started": str(0),
            "pie_dealing_with": str(0),
            "pie_solved": str(0),
            "pie_avg_response_time": str(0),
            "pie_avg_solution_time": str(0),

            "pie_angle_not_started": pie_chart_angles[0],
            "pie_angle_dealing_with": pie_chart_angles[1],
            "pie_angle_solved": pie_chart_angles[2],

            "tickets_feed": render_tickers_feed(),
        }
    ).encode("utf-8")


if db.create_database_sql_file() != db.Error.SUCCESS:
    raise AssertionError("Failed to start the database module, exitting.")

app.enable_translation("./translation.json", "nb")
app.register_components_from_dir("../components/")
app.set_public_dir("../public/", "/public/", server.PublicAccessPolicy.SERVE_ALL)

if app.serve_until_KeyboardInterrupt("localhost", 8001) != server.Error.SUCCESS:
    raise AssertionError("Critical error in the server runtime, exitting.")