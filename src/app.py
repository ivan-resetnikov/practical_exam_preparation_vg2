"""
Praktisk eksamen forberedelse Copyright (c) 2026 ved Reshetnikov Ivan - alle rettigheter forbeholdt.
"""

import logging

import vendor.moeserver.server as server
import vendor.moeserver.html_factory as html_factory

import db
import sessions
import urllib



# NOTE(vanya): Configure logging
logging.basicConfig(level=logging.DEBUG)
server.logger.setLevel(logging.INFO)
db.logger.setLevel(logging.INFO)


if db.init() != db.Error.SUCCESS:
    raise AssertionError("Failed to initialize the database module, exitting.")


app = server.App()



def check_session_vailidity(p_header_data: dict) -> sessions.SessionValidity:
    cookies: dict = app.parse_cookies_from_header(p_header_data)
    
    session_id: str = cookies.get("session_id", "")

    return sessions.check_session_id_validity(session_id)


def check_session_get_login_redirect_if_needed(p_header_data: dict) -> bytes|None:
    session_validity: sessions.SessionValidity = check_session_vailidity(p_header_data)

    match session_validity:
        case sessions.SessionValidity.OK:
            # NOTE(vanya): If we aleady have a session we don't need to log in again

            return None
        
        case sessions.SessionValidity.EXPIRED | sessions.SessionValidity.INCORRECT | sessions.SessionValidity.NOT_FOUND | _:
            # NOTE(vanya): No active session - gotta re-login

            return app.response_redirect("/login")


@app.route_GET("/")
def route_index(p_renderpass_params: dict, p_catchall_params: dict, p_header_data: dict, _p_request_data: bytes) -> bytes:
    return check_session_get_login_redirect_if_needed(p_header_data) or app.response_redirect("/statistics")


@app.route_GET("/login")
def route_get_login(p_renderpass_params: dict, p_catchall_params: dict, p_header_data: dict, p_request_data: bytes) -> bytes:
    return app.response_ok(
        app.render_html_file("../pages/login.html", p_renderpass_params, {}).encode("utf-8")
    )


@app.route_POST("/login")
def route_post_login(p_renderpass_params: dict, p_catchall_params: dict, p_header_data: dict, p_request_data: bytes) -> bytes:
    form_params: dict = urllib.parse.parse_qs(p_request_data.decode("utf-8"))

    email: str = form_params.get("email", [""])[0]
    password: str = form_params.get("password", [""])[0]

    user, login_status = db.attempt_login(email, password)

    match login_status:
        case db.UserLoginStatus.OK:
            new_session: sessions.Session = sessions.begin_session(user, p_duration_minutes=1)

            return app.response_redirect(
                "/statistics",
                p_headers=[
                    f"Set-Cookie: session_id={new_session.id}; Path=/; HttpOnly; SameSite=Lax",
                ]
            )
        
        case db.UserLoginStatus.EMAIL_NOT_FOUND:
            return app.response_reject("Email not found".encode("utf-8"))
        
        case db.UserLoginStatus.INCORRECT_PASSWORD:
            return app.response_reject("Incorrect password".encode("utf-8"))


@app.route_POST("/ticket")
def route_post_ticket(p_renderpass_params: dict, p_catchall_params: dict, p_header_data: dict, p_request_data: bytes) -> bytes:
    form_params: dict = urllib.parse.parse_qs(p_request_data.decode("utf-8"))

    print(form_params)

    return app.response_ok()


@app.route_GET("/statistics")
def route_statistics(p_renderpass_params: dict, _p_catchall_params: dict, p_header_data: dict, _p_request_data: bytes) -> bytes:
    login_redirect: bytes = check_session_get_login_redirect_if_needed(p_header_data)
    if login_redirect:
        return login_redirect

    def weights_to_pie_chart_angles(p_values: list[int]) -> list[int]:
        total: float = float(sum(p_values))

        output_angles: list[float] = []
        last_angle: float = 0.0

        for value in p_values:
            value_fraction_or_0: float = (value / total) if value > 0.0 else 0.0

            output_angles.append(last_angle + value_fraction_or_0 * 360.0)
            last_angle = output_angles[-1]
        
        return output_angles


    def render_tickets_feed() -> str:
        root = html_factory.HTMLFactory()

        table = root.push_element(None, "table", class_="tickets-feed-table")

        table_head = root.push_element(table, "thead")
        table_head_row = root.push_element(table_head, "tr")

        root.push_element(table_head_row, "td", "Reporter", class_="column-reporter")
        root.push_element(table_head_row, "td", "Summary", class_="column-summary")
        root.push_element(table_head_row, "td", "Time passed")
        root.push_element(table_head_row, "td", "")

        table_body = root.push_element(table, "tbody")

        for ticket in db.load_not_started_ticket_range(0, 20):
            table_body_row = root.push_element(table_body, "tr")

            reporter_column = root.push_element(table_body_row, "td", ticket.reporter_name, class_="column-reporter")
            summary_column = root.push_element(table_body_row, "td", ticket.reporter_summary, class_="column-summary")
            registraction_time_column = root.push_element(table_body_row, "td", ticket.registration_time, class_="column-registraction-time")
            button_column = root.push_element(table_body_row, "td", class_="column-assign-button")

            root.push_element(button_column, "button", "I'll help, assign to me")
        
        return root.render_html()


    def render_assigned_tickets() -> str:
        root = html_factory.HTMLFactory()

        table = root.push_element(None, "table", class_="tickets-feed-table")

        table_head = root.push_element(table, "thead")
        table_head_row = root.push_element(table_head, "tr")

        root.push_element(table_head_row, "td", "Reporter", class_="column-reporter")
        root.push_element(table_head_row, "td", "Summary", class_="column-summary")
        root.push_element(table_head_row, "td", "Time passed", class_="column-registraction-time")
        root.push_element(table_head_row, "td", "Manage", class_="column-manage-button")

        table_body = root.push_element(table, "tbody")

        for ticket in db.load_all_assigned_tickets():
            table_body_row = root.push_element(table_body, "tr")

            reporter_column = root.push_element(table_body_row, "td", ticket.reporter_name, class_="column-reporter")
            summary_column = root.push_element(table_body_row, "td", ticket.reporter_summary, class_="column-summary")
            registraction_time_column = root.push_element(table_body_row, "td", ticket.registraction_time, class_="column-registraction-time")
            manage_button_column = root.push_element(table_body_row, "td", class_="column-manage-button")

            root.push_element(manage_button_column, "button", "Manage")
        
        return root.render_html()


    all_tickets: list[Tickets] = db.load_all_tickets()

    ticket_states: dict[db.TicketState, int] = {
        db.TicketState.NOT_STARTED: 0,
        db.TicketState.DEALING_WITH: 0,
        db.TicketState.SOLVED: 0,
        db.TicketState.FAILED: 0,
    }
    for ticket in all_tickets:
        ticket_states[ticket.state] += 1

    pie_chart_angles: list[float] = weights_to_pie_chart_angles(list(ticket_states.values()))

    return app.response_ok(
        app.render_html_file("../pages/statistics.html", p_renderpass_params,
            {
                "pie_total": str(len(all_tickets)),

                "pie_not_started": ticket_states[db.TicketState.NOT_STARTED],
                "pie_dealing_with": ticket_states[db.TicketState.DEALING_WITH],
                "pie_solved": ticket_states[db.TicketState.SOLVED],
                "pie_failed": ticket_states[db.TicketState.FAILED],

                "pie_avg_response_time": 0,
                "pie_avg_solution_time": 0,

                "pie_angle_not_started": pie_chart_angles[db.TicketState.NOT_STARTED.value],
                "pie_angle_dealing_with": pie_chart_angles[db.TicketState.DEALING_WITH.value],
                "pie_angle_solved": pie_chart_angles[db.TicketState.SOLVED.value],
                "pie_angle_failed": pie_chart_angles[db.TicketState.FAILED.value],

                "tickets_feed": render_tickets_feed(),
                "assigned_tickets": render_assigned_tickets(),
            }
        ).encode("utf-8")
    )


app.enable_translation("./translation.json", "nb")
app.register_components_from_dir("../components/")
app.set_public_dir("../public/", "/public/", server.PublicAccessPolicy.SERVE_ALL)

if app.serve_until_KeyboardInterrupt("localhost", 8001) != server.Error.SUCCESS:
    raise AssertionError("Critical error in the server runtime, exitting.")