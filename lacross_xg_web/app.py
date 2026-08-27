"""Flask web app with game sessions, goalie tracking, and PDF reports."""

import csv
import io
import json
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response, abort

from xg_logic import (
    XGModel, PLACEMENT_OPTIONS, HAND_OPTIONS,
    GOALIE_TIERS, goalie_xg_multiplier, goalie_tier_label,
)

app = Flask(__name__)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SHOTS_FILE = DATA_DIR / "shots_web.json"
PLAYERS_FILE = DATA_DIR / "players.json"
GOALIES_FILE = DATA_DIR / "goalies.json"
GAMES_FILE = DATA_DIR / "games.json"

xg_model = XGModel("chart")


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_shots() -> list:
    return load_json(SHOTS_FILE, [])


def save_shots(shots: list) -> None:
    save_json(SHOTS_FILE, shots)


def load_players() -> dict:
    return load_json(PLAYERS_FILE, {})


def save_players(players: dict) -> None:
    save_json(PLAYERS_FILE, players)


def load_goalies() -> dict:
    return load_json(GOALIES_FILE, {})


def save_goalies(goalies: dict) -> None:
    save_json(GOALIES_FILE, goalies)


def load_games() -> list:
    return load_json(GAMES_FILE, [])


def save_games(games: list) -> None:
    save_json(GAMES_FILE, games)


@app.route("/")
def index():
    return render_template(
        "index.html",
        placements=PLACEMENT_OPTIONS,
        hands=HAND_OPTIONS,
        goalie_tiers=GOALIE_TIERS,
    )


@app.route("/api/games", methods=["GET"])
def get_games():
    return jsonify(load_games())


@app.route("/api/games", methods=["POST"])
def create_game():
    data = request.get_json()
    opponent = (data.get("opponent") or "").strip()
    date_str = (data.get("date") or "").strip()
    game_id = f"G{uuid.uuid4().hex[:8].upper()}"
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    games = load_games()
    new_game = {
        "game_id": game_id,
        "opponent": opponent,
        "date": date_str,
        "status": "active",
        "goalies": {},
        "team_score": data.get("team_score"),
        "opponent_score": data.get("opponent_score"),
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }
    games.append(new_game)
    save_games(games)
    return jsonify(new_game), 201


@app.route("/api/games/<game_id>", methods=["GET"])
def get_game(game_id: str):
    games = load_games()
    game = next((g for g in games if g["game_id"] == game_id), None)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    return jsonify(game)


@app.route("/api/games/<game_id>", methods=["PUT"])
def update_game(game_id: str):
    updates = request.get_json()
    games = load_games()
    game = next((g for g in games if g["game_id"] == game_id), None)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    game.update(updates)
    save_games(games)
    return jsonify(game)


@app.route("/api/games/<game_id>/complete", methods=["POST"])
def complete_game(game_id: str):
    games = load_games()
    game = next((g for g in games if g["game_id"] == game_id), None)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    game["status"] = "completed"
    game["completed_at"] = datetime.now().isoformat()
    save_games(games)
    return jsonify(game)


@app.route("/api/games/<game_id>/reactivate", methods=["POST"])
def reactivate_game(game_id: str):
    games = load_games()
    game = next((g for g in games if g["game_id"] == game_id), None)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    game["status"] = "active"
    game["completed_at"] = None
    save_games(games)
    return jsonify(game)


@app.route("/api/games/<game_id>", methods=["DELETE"])
def delete_game(game_id: str):
    games = load_games()
    games = [g for g in games if g["game_id"] != game_id]
    save_games(games)
    shots = [s for s in load_shots() if s.get("game_id") != game_id]
    save_shots(shots)
    return jsonify({"ok": True})


@app.route("/api/shots", methods=["GET"])
def get_shots():
    game_id = request.args.get("game_id")
    shots = load_shots()
    if game_id:
        shots = [s for s in shots if s.get("game_id") == game_id]
    return jsonify(shots)


@app.route("/api/shots", methods=["POST"])
def add_shot():
    shot = request.get_json()
    shot["shot_id"] = f"S{uuid.uuid4().hex[:8].upper()}"
    shot["timestamp"] = datetime.now().isoformat()
    shot.setdefault("placement", "off_target")
    shot.setdefault("shooting_hand", "unknown")
    shot.setdefault("shooter_id", "unknown")
    shot.setdefault("jersey_number", "")
    shot.setdefault("player_name", "")
    shot.setdefault("goalie_name", "")
    shot.setdefault("goalie_save_pct", None)
    shot.setdefault("game_id", "")

    game_id = shot.get("game_id", "")
    if game_id:
        games = load_games()
        game = next((g for g in games if g["game_id"] == game_id), None)
        if game and shot.get("goalie_name"):
            goalies = game.get("goalies", {})
            if shot["goalie_name"] in goalies and not shot.get("goalie_save_pct"):
                shot["goalie_save_pct"] = goalies[shot["goalie_name"]]

    if shot.get("goalie_save_pct") in (None, "", 0, "0"):
        shot["goalie_save_pct"] = None
    else:
        try:
            shot["goalie_save_pct"] = float(shot["goalie_save_pct"])
        except (ValueError, TypeError):
            shot["goalie_save_pct"] = None

    xg = xg_model.calculate_xg(shot)
    shot["xg"] = round(xg, 4)
    shots = load_shots()
    shots.append(shot)
    save_shots(shots)

    jersey = str(shot.get("jersey_number", "")).strip()
    name = str(shot.get("player_name", "")).strip()
    shooter = shot["shooter_id"]
    if jersey or name:
        players = load_players()
        key = jersey or shooter
        if key not in players:
            players[key] = {"jersey_number": jersey, "player_name": name, "shooter_id": shooter}
        else:
            if name: players[key]["player_name"] = name
            if jersey: players[key]["jersey_number"] = jersey
        save_players(players)

    return jsonify(shot), 201


@app.route("/api/shots/<shot_id>", methods=["DELETE"])
def delete_shot(shot_id: str):
    shots = load_shots()
    shots = [s for s in shots if s.get("shot_id") != shot_id]
    save_shots(shots)
    return jsonify({"ok": True})


@app.route("/api/shots/<shot_id>", methods=["PUT"])
def update_shot(shot_id: str):
    updates = request.get_json()
    shots = load_shots()
    for shot in shots:
        if shot.get("shot_id") == shot_id:
            shot.update(updates)
            shot["xg"] = round(xg_model.calculate_xg(shot), 4)
            break
    save_shots(shots)
    return jsonify({"ok": True})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    game_id = request.args.get("game_id")
    shots = load_shots()
    if game_id:
        shots = [s for s in shots if s.get("game_id") == game_id]
    return jsonify(xg_model.evaluate(shots))


@app.route("/api/shooters", methods=["GET"])
def get_shooters():
    game_id = request.args.get("game_id")
    shots = load_shots()
    if game_id:
        shots = [s for s in shots if s.get("game_id") == game_id]
    return jsonify(xg_model.evaluate_by_shooter(shots))


@app.route("/api/shooter/<shooter_id>", methods=["GET"])
def get_shooter(shooter_id: str):
    game_id = request.args.get("game_id")
    shots = load_shots()
    if game_id:
        shots = [s for s in shots if s.get("game_id") == game_id]
    report = xg_model.get_shooter_report(shooter_id, shots)
    if report is None:
        return jsonify({"error": "Shooter not found"}), 404
    return jsonify(report)


@app.route("/api/players", methods=["GET"])
def get_players():
    return jsonify(load_players())


@app.route("/api/players", methods=["POST"])
def upsert_player():
    data = request.get_json()
    jersey = str(data.get("jersey_number", "")).strip()
    name = str(data.get("player_name", "")).strip()
    shooter = str(data.get("shooter_id", "")).strip()
    if not (jersey or shooter):
        return jsonify({"error": "Need jersey_number or shooter_id"}), 400
    players = load_players()
    key = jersey or shooter
    players[key] = {"jersey_number": jersey, "player_name": name, "shooter_id": shooter}
    save_players(players)
    return jsonify(players[key]), 201


@app.route("/api/goalies", methods=["GET"])
def get_goalies():
    game_id = request.args.get("game_id")
    if game_id:
        games = load_games()
        game = next((g for g in games if g["game_id"] == game_id), None)
        if game:
            return jsonify(game.get("goalies", {}))
        return jsonify({})
    return jsonify(load_goalies())


@app.route("/api/goalies", methods=["POST"])
def upsert_goalie():
    data = request.get_json()
    name = str(data.get("name", "")).strip()
    save_pct = data.get("save_pct")
    game_id = data.get("game_id")

    if game_id:
        games = load_games()
        game = next((g for g in games if g["game_id"] == game_id), None)
        if not game:
            return jsonify({"error": "Game not found"}), 404
        if "goalies" not in game:
            game["goalies"] = {}
        if save_pct is None or save_pct == "":
            game["goalies"].pop(name, None)
        else:
            try:
                save_pct = float(save_pct)
                game["goalies"][name] = save_pct
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid save_pct"}), 400
        save_games(games)
        return jsonify({"name": name, "save_pct": game["goalies"].get(name)}), 201

    if not name:
        return jsonify({"error": "Need goalie name"}), 400
    try:
        save_pct = float(save_pct) if save_pct else None
    except (ValueError, TypeError):
        save_pct = None
    goalies = load_goalies()
    goalies[name] = {"save_pct": save_pct, "tier": goalie_tier_label(save_pct)}
    save_goalies(goalies)
    return jsonify(goalies[name]), 201


@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    game_id = request.args.get("game_id")
    shots = load_shots()
    if game_id:
        shots = [s for s in shots if s.get("game_id") == game_id]
    output = io.StringIO()
    fieldnames = [
        "shot_id", "game_id", "shooter_id", "jersey_number", "player_name",
        "shooting_hand", "x", "y", "placement", "is_goal", "xg",
        "shot_quality", "game_situation", "defender_distance",
        "rebound", "goalie_name", "goalie_save_pct",
        "timestamp",
 ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for shot in shots:
        writer.writerow({k: shot.get(k, "") for k in fieldnames})
    csv_data = output.getvalue()
    suffix = f"_{game_id}" if game_id else ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lacrosse_shots{suffix}_{timestamp}.csv"
    return Response(
        csv_data, mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/api/export/json", methods=["GET"])
def export_json():
    game_id = request.args.get("game_id")
    shots = load_shots()
    games = load_games()
    if game_id:
        shots = [s for s in shots if s.get("game_id") == game_id]
        game = next((g for g in games if g["game_id"] == game_id), None)
    else:
        game = None
    stats = xg_model.evaluate(shots)
    shooters = xg_model.evaluate_by_shooter(shots)
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "shot_count": len(shots),
        "game": game,
        "players": load_players(),
        "statistics": stats,
        "shooters": shooters,
        "shots": shots,
    }
    suffix = f"_{game_id}" if game_id else ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lacrosse_export{suffix}_{timestamp}.json"
    return Response(
        json.dumps(export_data, indent=2), mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/api/export/report", methods=["GET"])
def export_report():
    game_id = request.args.get("game_id")
    shots = load_shots()
    games = load_games()
    if game_id:
        shots = [s for s in shots if s.get("game_id") == game_id]
        game = next((g for g in games if g["game_id"] == game_id), None)
    else:
        game = None
    stats = xg_model.evaluate(shots)

    lines = []
    lines = ["=" * 60]
    lines.append("   LACROSSE EXPECTED GOALS REPORT")
    lines.append("=" * 60)
    if game:
        lines.append(f"Game vs {game.get('opponent', '?')} on {game.get('date', '?')}")
        lines.append(f"Status: {game.get('status', '?')}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("OVERALL STATISTICS")
    lines.append("-" * 60)
    lines.append(f"Total shots:        {len(shots)}")
    lines.append(f"Total goals:        {stats['actual_goals']:.0f}")
    lines.append(f"Total xG:           {stats['total_xg']:.2f}")
    lines.append(f"xDiff:              {stats['xdiff']:+.2f}")
    lines.append("")
    lines.append("GOALIE BREAKDOWN")
    lines.append("-" * 60)
    lines.append(f"{'Goalie':<20} {'Save%':>6} {'Tier':<25} {'Shots':>6} {'Goals':>6} {'xG':>7}")
    for g_name, g_stats in stats.get("goalie_breakdown", {}).items():
        save_pct = g_stats.get("save_pct") or 0
        tier = g_stats.get("tier", "-")
        lines.append(
            f"{g_name:<20} {save_pct:>5.1f}% {tier:<25} "
            f"{g_stats['shots']:>6} {g_stats['goals']:>6} {g_stats['total_xg']:>7.2f}"
        )
    lines.append("")
    lines.append("=" * 60)
    report_text = "\n".join(lines)
    suffix = f"_{game_id}" if game_id else ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lacrosse_report{suffix}_{timestamp}.txt"
    return Response(
        report_text, mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def build_shot_map_drawing(shots, width=480, height=440):
    from reportlab.graphics.shapes import (
        Drawing, Rect, Circle, Line, String, PolyLine,
 )
    from reportlab.lib.colors import HexColor
    import math as m

    SVG_X_MIN, SVG_X_MAX = -15, 15
    SVG_Y_MIN, SVG_Y_MAX = 0, 30
    SVG_W = SVG_X_MAX - SVG_X_MIN
    SVG_H = SVG_Y_MAX - SVG_Y_MIN
    GOAL_HEIGHT_YARDS = 4
    PADDING_TOP = 8
    PADDING_BOTTOM = 4
    PADDING_LEFT = 4
    PADDING_RIGHT = 4

    world_w = SVG_W + PADDING_LEFT + PADDING_RIGHT
    world_h = SVG_H + PADDING_TOP + PADDING_BOTTOM
    scale = min(width / world_w, height / world_h)
    draw_w = world_w * scale
    draw_h = world_h * scale

    def to_pdf(x_yards, y_yards):
        dx = (x_yards - SVG_X_MIN) * scale + PADDING_LEFT * scale
        dy = (PADDING_TOP + GOAL_HEIGHT_YARDS + y_yards) * scale
        return dx, dy

    d = Drawing(draw_w, draw_h)
    field_top_y = (PADDING_TOP + GOAL_HEIGHT_YARDS) * scale
    d.add(Rect(0, field_top_y, draw_w, draw_h - field_top_y,
               fillColor=HexColor("#2f855a"), strokeColor=None))
    d.add(Rect(0, 0, draw_w, field_top_y,
               fillColor=HexColor("#1a4d2e"), strokeColor=None))

    cx_pdf, _ = to_pdf(0, 0)
    d.add(Line(cx_pdf, field_top_y, cx_pdf, draw_h,
               strokeColor=HexColor("#ffffff"),
               strokeWidth=0.5, strokeDashArray=[3, 3]))

    crease_radius_yards = 3
    crease_path = []
    for angle_deg in range(0, 181, 5):
        a = m.radians(180 - angle_deg)
        cx_yards = 0 + crease_radius_yards * m.cos(a)
        cy_yards = 0 + crease_radius_yards * m.sin(a)
        crease_path.append(to_pdf(cx_yards, cy_yards))
    if len(crease_path) >= 2:
        d.add(PolyLine(crease_path,
                       strokeColor=HexColor("#3182ce"),
                       strokeWidth=1.5,
                       fillColor=HexColor("#bee3f8"),
                       fillOpacity=0.6))

    x_left_pdf, y_goal_pdf = to_pdf(SVG_X_MIN, 0)
    x_right_pdf, _ = to_pdf(SVG_X_MAX, 0)
    d.add(Line(x_left_pdf, y_goal_pdf, x_right_pdf, y_goal_pdf,
               strokeColor=HexColor("#ffffff"), strokeWidth=1.5))

    goal_backing_y = field_top_y - 1.5 * scale
    d.add(Rect(x_left_pdf + draw_w * 0.3, goal_backing_y,
               draw_w * 0.4, 1.5 * scale,
               fillColor=HexColor("#2d3748"), strokeColor=None))

    goal_half_width = 2.45
    post_left_x_pdf, _ = to_pdf(-goal_half_width, 0)
    post_right_x_pdf, _ = to_pdf(goal_half_width, 0)
    post_thickness = 1.5 * scale
    d.add(Rect(post_left_x_pdf - post_thickness / 2, 0,
               post_thickness, field_top_y,
               fillColor=HexColor("#d32f2f"),
               strokeColor=HexColor("#ffffff"),
               strokeWidth=0.5))
    d.add(Rect(post_right_x_pdf - post_thickness / 2, 0,
               post_thickness, field_top_y,
               fillColor=HexColor("#d32f2f"),
               strokeColor=HexColor("#ffffff"),
               strokeWidth=0.5))
    d.add(Rect(post_left_x_pdf - post_thickness / 2,
               field_top_y - post_thickness,
               (post_right_x_pdf - post_left_x_pdf) + post_thickness,
               post_thickness,
               fillColor=HexColor("#d32f2f"),
               strokeColor=HexColor("#ffffff"),
               strokeWidth=0.5))

    d.add(String(draw_w / 2, field_top_y + 1.5 * scale, "GOAL",
                 fontName="Helvetica-Bold", fontSize=8,
                 fillColor=HexColor("#ffffff"), textAnchor="middle"))

    rl_x_left, rl_y = to_pdf(SVG_X_MIN, 20)
    rl_x_right, _ = to_pdf(SVG_X_MAX, 20)
    d.add(Line(rl_x_left, rl_y, rl_x_right, rl_y,
               strokeColor=HexColor("#cbd5e0"),
               strokeWidth=0.8, strokeDashArray=[4, 3]))
    d.add(String(draw_w - 4, rl_y - 4, "20 yd",
                 fontName="Helvetica", fontSize=6,
                 fillColor=HexColor("#cbd5e0"), textAnchor="end"))

    for shot in shots:
        x_yards = shot.get("x", 0)
        y_yards = shot.get("y", 0)
        if x_yards < SVG_X_MIN or x_yards > SVG_X_MAX:
            x_yards = max(SVG_X_MIN, min(SVG_X_MAX, x_yards))
        if y_yards < SVG_Y_MIN or y_yards > SVG_Y_MAX:
            y_yards = max(SVG_Y_MIN, min(SVG_Y_MAX, y_yards))

        px, py = to_pdf(x_yards, y_yards)
        xg = shot.get("xg", 0)
        radius = (3 + xg * 6) * (scale / 10)
        is_goal = shot.get("is_goal", False)
        color = HexColor("#48bb78") if is_goal else HexColor("#f56565")
        d.add(Circle(px, py, max(2, radius),
                     fillColor=color,
                     strokeColor=HexColor("#ffffff"),
                     strokeWidth=0.7,
                     fillOpacity=0.85))

    legend_y = 4
    d.add(Circle(15, draw_h - legend_y, 3,
                 fillColor=HexColor("#48bb78"),
                 strokeColor=HexColor("#ffffff"), strokeWidth=0.5))
    d.add(String(22, draw_h - legend_y - 1.5, "Goal",
                 fontName="Helvetica", fontSize=7,
                 fillColor=HexColor("#ffffff")))
    d.add(Circle(60, draw_h - legend_y, 3,
                 fillColor=HexColor("#f56565"),
                 strokeColor=HexColor("#ffffff"), strokeWidth=0.5))
    d.add(String(67, draw_h - legend_y - 1.5, "Miss",
                 fontName="Helvetica", fontSize=7,
                 fillColor=HexColor("#ffffff")))

    return d


@app.route("/api/export/shooter-pdf/<shooter_id>", methods=["GET"])
def export_shooter_pdf(shooter_id: str):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        )
    except ImportError:
        return jsonify({"error": "reportlab not installed"}), 500

    game_id = request.args.get("game_id")
    shots = load_shots()
    if game_id:
        shots = [s for s in shots if s.get("game_id") == game_id]
    report = xg_model.get_shooter_report(shooter_id, shots)
    if report is None:
        abort(404)

    summary = report["shooter_summary"]
    stats = report["stats"]
    placement_labels = {
        "goalie_stick_high":     "Stick Side · High",
        "goalie_off_stick_high": "Off-Stick · High",
        "goalie_stick_hip":      "Stick Side · Hip",
        "goalie_off_stick_hip":  "Off-Stick · Hip",
        "five_hole":             "Five Hole",
        "goalie_stick_low":      "Stick Side · Low",
        "goalie_off_stick_low":  "Off-Stick · Low",
        "off_target":            "Off Target",
    }

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=40, rightMargin=40,
                            topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"], fontSize=22,
        textColor=colors.HexColor("#1a365d"), spaceAfter=10,
    )

    name = summary.get("player_name") or shooter_id
    jersey = summary.get("jersey_number") or "?"
    story.append(Paragraph(name, title_style))
    story.append(Paragraph(
        f"Jersey #{jersey} · ID: {shooter_id}", styles["Normal"]))
    story.append(Paragraph(
        f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles["Italic"]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Overall Statistics", styles["Heading2"]))
    stats_data = [
        ["Shots", "Goals", "xG", "xDiff", "SH%", "xG/Shot"],
        [
            str(summary["shots"]), str(summary["goals"]),
            f"{summary['total_xg']:.2f}", f"{summary['xdiff']:+.2f}",
            f"{summary['shooting_pct']*100:.1f}%",
            f"{summary['xG_per_shot']:.3f}",
        ],
    ]
    t = Table(stats_data, colWidths=[60, 60, 60, 70, 60, 80])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f7fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    if summary["xdiff"] > 0.5:
        interp = "Overperforming expected goals - clutch finisher."
    elif summary["xdiff"] < -0.5:
        interp = "Underperforming expected goals - shooting luck is poor."
    else:
        interp = "Performing roughly as expected."
    story.append(Paragraph(f"<b>Analysis:</b> {interp}", styles["Normal"]))
    story.append(Spacer(1, 14))

    placement_breakdown = stats.get("placement_breakdown", {})
    used_placements = [(p, d) for p, d in placement_breakdown.items() if d["shots"] > 0]
    if used_placements:
        story.append(Paragraph("Shot Placement", styles["Heading2"]))
        placement_data = [["Placement", "Shots", "Goals", "%"]]
        for p in PLACEMENT_OPTIONS:
            d = placement_breakdown.get(p)
            if not d or d["shots"] == 0:
                continue
            pct = d["goals"] / d["shots"] * 100 if d["shots"] else 0
            placement_data.append([
                placement_labels.get(p, p), str(d["shots"]), str(d["goals"]), f"{pct:.1f}%",
            ])
        pt = Table(placement_data, colWidths=[150, 60, 60, 60])
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        story.append(pt)
        story.append(Spacer(1, 14))

    hands = summary.get("hands", {})
    used_hands = [(h, c) for h in HAND_OPTIONS if (c := hands.get(h, 0)) > 0]
    if used_hands:
        story.append(Paragraph("Shooting Hand", styles["Heading2"]))
        hand_data = [["Hand", "Shots"]] + [[h.capitalize(), str(c)] for h, c in used_hands]
        ht = Table(hand_data, colWidths=[100, 60])
        ht.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        story.append(ht)
        story.append(Spacer(1, 14))

    # Start the shot map on its own page - it needs the full page height,
    # and letting it flow naturally leaves the heading orphaned on the
    # previous page while the drawing spills onto the next one.
    story.append(PageBreak())
    story.append(Paragraph("Shot Map", styles["Heading2"]))
    shot_map = build_shot_map_drawing(report["shots"], width=480, height=400)
    story.append(shot_map)
    story.append(Spacer(1, 14))

    story.append(PageBreak())
    story.append(Paragraph("Recent Shot Log (last 20)", styles["Heading2"]))
    if report["shots"]:
        recent_shots = sorted(report["shots"],
                              key=lambda s: s.get("timestamp", ""), reverse=True)[:20]
        shot_data = [["Date", "Pos", "Place", "Hand", "xG", "Goal"]]
        for shot in recent_shots:
            ts = shot.get("timestamp", "")[:16].replace("T", " ")
            shot_data.append([
                ts,
                f"({shot.get('x', 0):.1f}, {shot.get('y', 0):.1f})",
                placement_labels.get(shot.get("placement", ""), shot.get("placement", "")),
                (shot.get("shooting_hand") or "?")[:1].upper(),
                f"{shot.get('xg', 0):.2f}",
                "Y" if shot.get("is_goal") else "N",
            ])
        st = Table(shot_data, colWidths=[95, 70, 120, 40, 40, 40])
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(st)
    else:
        story.append(Paragraph("No shots logged for this player.", styles["Normal"]))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    safe_id = "".join(c for c in shooter_id if c.isalnum() or c in "-_")
    suffix = f"_{game_id}" if game_id else ""
    filename = f"lacrosse_{safe_id}{suffix}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        pdf_data, mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/api/export/all-pdf", methods=["GET"])
def export_all_pdf():
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        )
    except ImportError:
        return jsonify({"error": "reportlab not installed"}), 500

    shots = load_shots()
    shooters = xg_model.evaluate_by_shooter(shots)
    if not shooters:
        return jsonify({"error": "No shots logged yet"}), 400

    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=40, rightMargin=40,
                            topMargin=40, bottomMargin=40)
    story = []
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"], fontSize=24,
        textColor=colors.HexColor("#1a365d"), spaceAfter=10,
    )
    story.append(Paragraph("Team xG Report", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles["Italic"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        f"Total shots: {len(shots)} &nbsp; Shooters: {len(shooters)}",
        styles["Normal"]))
    story.append(Spacer(1, 20))

    sorted_shooters = sorted(shooters.items(),
                             key=lambda kv: kv[1]["xdiff"], reverse=True)

    story.append(Paragraph("Leaderboard (ranked by xDiff)", styles["Heading2"]))
    story.append(Spacer(1, 8))
    leaderboard_data = [["Rank", "Shooter", "Jersey", "Name", "Shots", "Goals", "xG", "xDiff", "SH%"]]
    for rank, (sid, s) in enumerate(sorted_shooters, 1):
        leaderboard_data.append([
            str(rank), sid, s.get("jersey_number") or "-", s.get("player_name") or "-",
            str(s["shots"]), str(s["goals"]), f"{s['total_xg']:.2f}",
            f"{s['xdiff']:+.2f}", f"{s['shooting_pct']*100:.1f}%",
        ])
    lt = Table(leaderboard_data, colWidths=[35, 55, 45, 105, 45, 45, 45, 55, 50])
    lt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ]))
    story.append(lt)

    for sid, s in sorted_shooters:
        story.append(PageBreak())
        story.append(Paragraph(
            f"#{s.get('jersey_number', '?')} {s.get('player_name') or sid}",
            styles["Heading1"]))
        story.append(Spacer(1, 10))
        stats_data = [["Shots", "Goals", "xG", "xDiff", "SH%"]]
        stats_data.append([
            str(s["shots"]), str(s["goals"]),
            f"{s['total_xg']:.2f}", f"{s['xdiff']:+.2f}",
            f"{s['shooting_pct']*100:.1f}%",
        ])
        st = Table(stats_data, colWidths=[60, 60, 60, 70, 60])
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("FONTSIZE", (0, 1), (-1, 1), 14),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f7fafc")),
        ]))
        story.append(st)
        story.append(Spacer(1, 14))
        shooter_shots = [sh for sh in shots if sh.get("shooter_id") == sid]
        story.append(Paragraph("Shot Map", styles["Heading3"]))
        story.append(build_shot_map_drawing(shooter_shots, width=480, height=400))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    filename = f"team_xg_report_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        pdf_data, mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    print(f"Lacrosse xG Web App running at http://localhost:5000")
    print(f"📁 Data dir: {DATA_DIR}")
    app.run(debug=True, port=5000)