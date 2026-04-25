"""
Praktisk eksamen forberedelse Copyright (c) 2026 ved Reshetnikov Ivan - alle rettigheter forbeholdt.
"""

import logging
import datetime

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


db.User.create("kjell@gvs.no", "123")
db.User.create("me@ivan-reshetnikov.dev", "123")
for _ in range(20):
    db.Ticket.create("John Doe", "My computer exploded")


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
def route_index(p_request_params: server.RequestParams) -> bytes:
    return check_session_get_login_redirect_if_needed(p_request_params.header_dict) or app.response_redirect("/statistics")


@app.route_GET("/login")
def route_get_login(p_request_params: server.RequestParams) -> bytes:
    return app.response_ok(
        app.render_html_file("../pages/login.html", p_request_params.renderpass_params, {}).encode("utf-8")
    )


@app.route_POST("/login")
def route_post_login(p_request_params: server.RequestParams) -> bytes:
    form_params: dict = urllib.parse.parse_qs(p_request_params.data.decode("utf-8"))

    email: str = form_params.get("email", [""])[0]
    password: str = form_params.get("password", [""])[0]

    user, login_status = db.attempt_login(email, password)

    match login_status:
        case db.UserLoginStatus.OK:
            new_session: sessions.Session = sessions.begin_session(user, p_duration_minutes=15)

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


@app.route_GET("/ticket")
def route_get_ticket(p_request_params: server.RequestParams) -> bytes:
    login_redirect: bytes = check_session_get_login_redirect_if_needed(p_request_params.header_dict)
    if login_redirect:
        return login_redirect
    
    ticket_id: int = int(p_request_params.query.get("id", ["0"])[0])
    
    ticket: db.Ticket = db.load_all_tickets()[ticket_id]

    return app.response_ok(app.render_html_file("../pages/ticket.html", p_request_params.renderpass_params, {
        "ticket_id": str(ticket_id),
        "reporter_name": ticket.reporter_name,
        "reporter_summary": ticket.reporter_summary,
        "selected_NOT_STARTED": "selected" if ticket.state == db.TicketState.NOT_STARTED else "",
        "selected_DEALING_WITH": "selected" if ticket.state == db.TicketState.DEALING_WITH else "",
        "selected_SOLVED": "selected" if ticket.state == db.TicketState.SOLVED else "",
        "selected_FAILED": "selected" if ticket.state == db.TicketState.FAILED else "",
    }).encode("utf-8"))


@app.route_POST("/ticket")
def route_post_ticket(p_request_params: server.RequestParams) -> bytes:
    login_redirect: bytes = check_session_get_login_redirect_if_needed(p_request_params.header_dict)
    if login_redirect:
        return login_redirect
    
    form_params: dict = urllib.parse.parse_qs(p_request_params.data.decode("utf-8"))

    ticket_id: int = int(p_request_params.query.get("id", ["0"])[0])

    ticket: db.Ticket = db.load_all_tickets()[ticket_id]

    ticket.reporter_name = form_params.get("reporter_name", ["No reporter name"])[0]
    ticket.reporter_summary = form_params.get("reporter_summary", ["No summary"])[0]
    ticket.state = db.TicketState[form_params.get("state", ["0"])[0]]

    logging.debug("Updated ticket info:")
    logging.debug(f"\tticket.reporter_name = {ticket.reporter_name}")
    logging.debug(f"\tticket.reporter_summary = {ticket.reporter_summary}")
    logging.debug(f"\tticket.state = {ticket.state.name}")

    ticket.flush_to_database()

    return app.response_redirect("/statistics")


@app.route_GET("/statistics")
def route_statistics(p_request_params: server.RequestParams) -> bytes:
    login_redirect: bytes = check_session_get_login_redirect_if_needed(p_request_params.header_dict)
    if login_redirect:
        return login_redirect


    def format_time_delta_as_human_readable(delta: datetime.timedelta) -> str:
        # NOTE(vanya): Normalize to total seconds
        total_seconds = int(delta.total_seconds())

        if total_seconds <= 0:
            return "Just now"

        # Convert to components
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        parts: list[str] = []

        if days > 0:
            years = days // 365
            days = days % 365
            months = days // 30
            days = days % 30

            if years > 0:
                parts.append(f"{years} year{'s' if years != 1 else ''}")
            if months > 0:
                parts.append(f"{months} month{'s' if months != 1 else ''}")
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")

        else:
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        if len(parts) == 1:
            return parts[0]
        elif len(parts) > 1:
            return " ".join(parts[:-1]) + " and " + parts[-1]
        else:
            return "Just now"


    def weights_to_pie_chart_angles(p_values: list[int]) -> list[int]:
        total: float = float(sum(p_values))

        output_angles: list[float] = []
        last_angle: float = 0.0

        for value in p_values:
            value_fraction_or_0: float = (value / total) if value > 0.0 else 0.0

            output_angles.append(last_angle + value_fraction_or_0 * 360.0)
            last_angle = output_angles[-1]
        
        return output_angles


    def render_ticket_feed(p_tickets: list[db.Ticket]) -> str:
        root = html_factory.HTMLFactory()

        table = root.push_element(None, "table", class_="tickets-feed-table")

        table_head = root.push_element(table, "thead")
        table_head_row = root.push_element(table_head, "tr")

        root.push_element(table_head_row, "td", "Reporter", class_="column-reporter")
        root.push_element(table_head_row, "td", "Summary", class_="column-summary")
        root.push_element(table_head_row, "td", "Time passed", class_="column-registraction-time")
        root.push_element(table_head_row, "td", "Manage", class_="column-manage-button")

        table_body = root.push_element(table, "tbody")

        for ticket in p_tickets:
            table_body_row = root.push_element(table_body, "tr")

            reporter_column = root.push_element(table_body_row, "td", ticket.reporter_name, class_="column-reporter")
            summary_column = root.push_element(table_body_row, "td", ticket.reporter_summary, class_="column-summary")
            registraction_time_column = root.push_element(table_body_row, "td", format_time_delta_as_human_readable(datetime.datetime.now() - ticket.registration_time), class_="column-registraction-time")
            manage_button_column = root.push_element(table_body_row, "td", class_="column-manage-button")

            root.push_element(manage_button_column, "a", "Manage", href=f"/ticket?id={ticket.primary_key - 1}")
        
        return root.render_html()


    all_tickets: list[db.Ticket] = db.load_all_tickets()

    ticket_states: dict[db.TicketState, int] = {
        db.TicketState.NOT_STARTED: 0,
        db.TicketState.DEALING_WITH: 0,
        db.TicketState.SOLVED: 0,
        db.TicketState.FAILED: 0,
    }

    avg_response_time: datetime.timedelta = datetime.timedelta()
    avg_solution_time: datetime.timedelta = datetime.timedelta()
    
    response_time_tickets: list[datetime.timedelta] = []
    solution_time_tickets: list[datetime.timedelta] = []
    
    for ticket in all_tickets:
        ticket_states[ticket.state] += 1
        
        # Calculate response time (from registration to when work started)
        if ticket.state in (db.TicketState.DEALING_WITH, db.TicketState.SOLVED, db.TicketState.FAILED):
            response_time_tickets.append(datetime.datetime.now() - ticket.registration_time)
        
        # Calculate solution time (from registration to when ticket was solved)
        if ticket.state == db.TicketState.SOLVED:
            solution_time_tickets.append(datetime.datetime.now() - ticket.registration_time)
    
    if response_time_tickets:
        avg_response_time = sum(response_time_tickets, datetime.timedelta()) / len(response_time_tickets)
    
    if solution_time_tickets:
        avg_solution_time = sum(solution_time_tickets, datetime.timedelta()) / len(solution_time_tickets)

    pie_chart_angles: list[float] = weights_to_pie_chart_angles(list(ticket_states.values()))

    return app.response_ok(
        app.render_html_file("../pages/statistics.html", p_request_params.renderpass_params,
            {
                "pie_total": str(len(all_tickets)),

                "pie_not_started": ticket_states[db.TicketState.NOT_STARTED],
                "pie_dealing_with": ticket_states[db.TicketState.DEALING_WITH],
                "pie_solved": ticket_states[db.TicketState.SOLVED],
                "pie_failed": ticket_states[db.TicketState.FAILED],

                "pie_avg_response_time": format_time_delta_as_human_readable(avg_response_time),
                "pie_avg_solution_time": format_time_delta_as_human_readable(avg_solution_time),

                "pie_angle_not_started": pie_chart_angles[db.TicketState.NOT_STARTED.value],
                "pie_angle_dealing_with": pie_chart_angles[db.TicketState.DEALING_WITH.value],
                "pie_angle_solved": pie_chart_angles[db.TicketState.SOLVED.value],
                "pie_angle_failed": pie_chart_angles[db.TicketState.FAILED.value],

                "tickets_feed": render_ticket_feed(db.load_not_started_ticket_range(0, 20)),
                "assigned_tickets": render_ticket_feed(db.load_all_assigned_tickets()),
                "all_tickets": render_ticket_feed(db.load_all_tickets()),
            }
        ).encode("utf-8")
    )


app.enable_translation("./translation.json", "nb")
app.register_components_from_dir("../components/")
app.set_public_dir("../public/", "/public/", server.PublicAccessPolicy.SERVE_ALL)

if app.serve_until_KeyboardInterrupt("localhost", 8001) != server.Error.SUCCESS:
    raise AssertionError("Critical error in the server runtime, exitting.")