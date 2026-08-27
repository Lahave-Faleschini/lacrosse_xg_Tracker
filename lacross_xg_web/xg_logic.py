"""xg_logic.py - Chart-based xG model with game sessions."""

import math
from typing import List, Dict, Any


CHART_BASELINE = {
    (-5, 0): 1.00, (-4, 0): 0.28, (-2, 0): 0.47, (4, 0): 1.00,
    (-9, 1): 1.00, (-6, 1): 0.10, (-5, 1): 0.22, (-4, 1): 0.33,
    (-3, 1): 0.45, (3, 1): 0.49, (4, 1): 0.31, (5, 1): 0.14,
    (-9, 2): 0.17, (-8, 2): 0.40, (-7, 2): 0.25, (-6, 2): 0.21,
    (-5, 2): 0.33, (-4, 2): 0.67, (3, 2): 0.62, (4, 2): 0.50,
    (5, 2): 0.33, (6, 2): 0.30, (7, 2): 0.10, (8, 2): 0.36,
    (9, 2): 0.17,
    (-12, 3): 0.0, (-10, 3): 0.11, (-9, 3): 0.27, (-8, 3): 0.30,
    (-7, 3): 0.36, (-6, 3): 0.59, (-5, 3): 0.44, (-4, 3): 0.55,
    (-3, 3): 0.72, (-2, 3): 0.77, (-1, 3): 0.60, (1, 3): 0.39,
    (2, 3): 0.29, (3, 3): 0.24, (4, 3): 0.26, (5, 3): 0.16,
    (6, 3): 0.20, (7, 3): 0.20, (8, 3): 0.50, (9, 3): 0.50,
    (-13, 4): 0.25, (-12, 4): 0.14, (-11, 4): 0.17, (-10, 4): 0.41,
    (-9, 4): 0.26, (-8, 4): 0.43, (-7, 4): 0.27, (-6, 4): 0.35,
    (-5, 4): 0.54, (-4, 4): 0.44, (-3, 4): 0.50, (-2, 4): 0.62,
    (-1, 4): 0.64, (1, 4): 0.30, (2, 4): 0.82, (3, 4): 0.20,
    (4, 4): 0.22, (5, 4): 0.18, (6, 4): 0.33, (7, 4): 0.33,
    (8, 4): 0.29, (15, 4): 0.0,
    (-14, 5): 0.0, (-13, 5): 0.0, (-12, 5): 0.10, (-11, 5): 0.20,
    (-10, 5): 0.20, (-9, 5): 0.31, (-8, 5): 0.50, (-7, 5): 0.60,
    (-6, 5): 0.47, (-5, 5): 0.50, (-4, 5): 0.64, (-3, 5): 0.50,
    (-2, 5): 0.77, (-1, 5): 0.43, (1, 5): 0.39, (2, 5): 0.37,
    (3, 5): 0.32, (4, 5): 0.20, (5, 5): 0.35, (6, 5): 0.21,
    (7, 5): 0.0, (8, 5): 0.0, (15, 5): 0.0,
    (-15, 6): 0.0, (-14, 6): 0.33, (-13, 6): 0.14, (-12, 6): 0.07,
    (-11, 6): 0.22, (-10, 6): 0.20, (-9, 6): 0.22, (-8, 6): 0.33,
    (-7, 6): 0.67, (-6, 6): 0.29, (-5, 6): 0.42, (-4, 6): 0.67,
    (-3, 6): 0.80, (-2, 6): 0.17, (-1, 6): 0.50, (1, 6): 0.43,
    (2, 6): 0.30, (3, 6): 0.35, (4, 6): 0.29, (5, 6): 0.13,
    (6, 6): 0.17, (7, 6): 0.43, (8, 6): 0.20, (14, 6): 0.0,
    (-15, 7): 0.0, (-14, 7): 0.0, (-13, 7): 0.25, (-12, 7): 0.27,
    (-11, 7): 0.29, (-10, 7): 0.19, (-9, 7): 0.24, (-8, 7): 0.31,
    (-7, 7): 0.83, (-6, 7): 0.14, (-5, 7): 0.31, (-4, 7): 0.46,
    (-3, 7): 0.57, (-2, 7): 0.40, (-1, 7): 0.38, (1, 7): 0.33,
    (2, 7): 0.57, (3, 7): 0.25, (4, 7): 0.33, (5, 7): 0.0,
    (6, 7): 0.25, (7, 7): 0.07, (12, 7): 0.0,
    (-15, 8): 0.0, (-14, 8): 0.50, (-13, 8): 0.14, (-12, 8): 0.25,
    (-11, 8): 0.27, (-10, 8): 0.23, (-9, 8): 0.28, (-8, 8): 0.06,
    (-7, 8): 0.13, (-6, 8): 0.42, (-5, 8): 0.0, (-4, 8): 0.20,
    (-3, 8): 0.29, (-2, 8): 0.56, (-1, 8): 0.33, (1, 8): 0.44,
    (2, 8): 0.20, (3, 8): 0.37, (4, 8): 0.25, (5, 8): 0.23,
    (6, 8): 0.48, (7, 8): 0.39, (8, 8): 0.15, (9, 8): 0.27,
    (-15, 9): 0.0, (-14, 9): 0.0, (-13, 9): 0.38, (-12, 9): 0.29,
    (-11, 9): 0.22, (-10, 9): 0.24, (-9, 9): 0.15, (-8, 9): 0.30,
    (-7, 9): 0.63, (-6, 9): 0.25, (-5, 9): 0.25, (-4, 9): 0.56,
    (-3, 9): 0.47, (-2, 9): 0.33, (-1, 9): 0.42, (1, 9): 0.25,
    (2, 9): 0.33, (3, 9): 0.14, (4, 9): 0.38, (5, 9): 0.18,
    (6, 9): 0.05, (7, 9): 0.38, (8, 9): 0.17, (14, 9): 0.0,
    (-14, 10): 0.0, (-13, 10): 0.0, (-12, 10): 0.13, (-11, 10): 0.33,
    (-10, 10): 0.33, (-9, 10): 0.22, (-8, 10): 0.17, (-7, 10): 0.42,
    (-6, 10): 0.27, (-5, 10): 0.27, (-4, 10): 0.27, (-3, 10): 0.27,
    (-2, 10): 0.27, (-1, 10): 0.45, (1, 10): 0.17, (2, 10): 0.20,
    (3, 10): 0.50, (4, 10): 0.30, (5, 10): 0.29, (6, 10): 0.07,
    (7, 10): 0.18, (8, 10): 0.0, (9, 10): 0.50, (14, 10): 0.0,
    (-13, 11): 0.0, (-12, 11): 0.14, (-11, 11): 0.13, (-10, 11): 0.05,
    (-9, 11): 0.22, (-8, 11): 0.33, (-7, 11): 0.20, (-6, 11): 0.36,
    (-5, 11): 0.30, (-4, 11): 0.33, (-3, 11): 0.30, (-2, 11): 0.07,
    (-1, 11): 0.30, (1, 11): 0.18, (2, 11): 0.36, (3, 11): 0.31,
    (4, 11): 0.13, (5, 11): 0.13, (6, 11): 0.17, (7, 11): 0.20,
    (14, 11): 0.0,
    (-13, 12): 0.0, (-12, 12): 0.50, (-11, 12): 0.0, (-10, 12): 0.14,
    (-9, 12): 0.29, (-8, 12): 0.17, (-7, 12): 0.13, (-6, 12): 0.08,
    (-5, 12): 0.33, (-4, 12): 0.17, (-3, 12): 0.35, (-2, 12): 0.22,
    (-1, 12): 0.21, (1, 12): 0.14, (2, 12): 0.27, (3, 12): 0.22,
    (4, 12): 0.17, (5, 12): 0.17, (6, 12): 0.25, (7, 12): 0.57,
    (8, 12): 0.50, (14, 12): 0.0,
    (-12, 13): 0.0, (-11, 13): 0.67, (-10, 13): 0.20, (-9, 13): 0.17,
    (-8, 13): 0.47, (-7, 13): 0.25, (-6, 13): 0.13, (-5, 13): 0.26,
    (-4, 13): 0.41, (-3, 13): 0.23, (-2, 13): 0.42, (-1, 13): 0.26,
    (1, 13): 0.12, (2, 13): 0.20, (3, 13): 0.18, (4, 13): 0.0,
    (5, 13): 0.50, (6, 13): 0.33, (7, 13): 0.67,
    (-10, 14): 0.0, (-9, 14): 0.14, (-8, 14): 0.20, (-7, 14): 0.14,
    (-6, 14): 0.29, (-5, 14): 0.14, (-4, 14): 0.45, (-3, 14): 0.26,
    (-2, 14): 0.42, (-1, 14): 0.33, (1, 14): 0.27, (2, 14): 0.27,
    (3, 14): 0.50, (4, 14): 0.36, (5, 14): 0.0, (6, 14): 0.0,
    (-10, 15): 0.0, (-9, 15): 0.0, (-8, 15): 0.0, (-7, 15): 0.29,
    (-6, 15): 0.17, (-5, 15): 0.25, (-4, 15): 0.30, (-3, 15): 0.33,
    (-2, 15): 0.40, (-1, 15): 0.25, (1, 15): 0.0, (2, 15): 0.20,
    (3, 15): 0.33, (4, 15): 0.67, (5, 15): 0.0, (6, 15): 0.0,
    (-10, 16): 0.0, (-8, 16): 0.0, (-7, 16): 0.0, (-6, 16): 0.0,
    (-5, 16): 0.33, (-4, 16): 0.33, (-3, 16): 0.50, (-2, 16): 0.33,
    (-1, 16): 0.0, (1, 16): 0.0, (2, 16): 0.50, (3, 16): 0.0,
    (9, 16): 0.0,
    (-5, 17): 0.0, (-4, 17): 0.0, (-3, 17): 0.0, (-2, 17): 0.0,
    (-1, 17): 0.0,
    (-5, 18): 0.0, (3, 18): 0.0, (9, 18): 0.0,
    (-1, 19): 0.0,
    (-10, 20): 0.0, (-1, 20): 0.0,
}


PLACEMENT_OPTIONS = [
    "goalie_stick_high",
    "goalie_off_stick_high",
    "goalie_stick_hip",
    "goalie_off_stick_hip",
    "five_hole",
    "goalie_stick_low",
    "goalie_off_stick_low",
    "off_target",
]

HAND_OPTIONS = ["right", "left", "ambidextrous", "unknown"]


GOALIE_TIERS = [
    ("Average / Below Average", 45.0, 49.9, 1.05),
    ("Solid Starter",           50.0, 55.9, 0.90),
    ("All-Conference / Elite",  56.0, 70.0, 0.70),
]

AVERAGE_SAVE_PCT = 50.0


def goalie_xg_multiplier(save_pct: float) -> float:
    if save_pct is None or save_pct <= 0:
        return 1.0
    diff = save_pct - AVERAGE_SAVE_PCT
    if diff >= 0:
        return max(0.2, 1.0 - (diff / 100.0) * 2.0)
    return 1.0 + (abs(diff) / 100.0) * 2.0


def goalie_tier_label(save_pct: float) -> str:
    if save_pct is None or save_pct <= 0:
        return "Unknown"
    if save_pct < 45:
        return "Below Average"
    if save_pct < 50:
        return "Average / Below Average"
    if save_pct < 56:
        return "Solid Starter"
    return "All-Conference / Elite"


class XGModel:
    def __init__(self, model_type: str = "chart"):
        if model_type not in {"chart", "heuristic"}:
            raise ValueError(f"Unknown model_type: {model_type}")
        self.model_type = model_type

    def calculate_xg(self, shot: Dict[str, Any]) -> float:
        if self.model_type == "chart":
            return self._chart_xg(shot)
        return self._heuristic_xg(shot)

    def _chart_xg(self, shot: Dict[str, Any]) -> float:
        x = float(shot["x"])
        y = float(shot["y"])
        cell_x = round(x)
        cell_y = round(y)
        base_xg = CHART_BASELINE.get((cell_x, cell_y), 0.0)

        if base_xg == 0.0:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    neighbor = CHART_BASELINE.get((cell_x + dx, cell_y + dy), 0.0)
                    if neighbor > 0.0:
                        base_xg = neighbor
                        break
                if base_xg > 0.0:
                    break

        if shot.get("shot_quality") == "high":
            base_xg *= 1.20
        elif shot.get("shot_quality") == "low":
            base_xg *= 0.75

        if shot.get("rebound"):
            base_xg *= 1.15

        if shot.get("defender_distance", 5.0) < 2.0:
            base_xg *= 0.60
        elif shot.get("defender_distance", 5.0) < 5.0:
            base_xg *= 0.85

        hand = shot.get("shooting_hand", "unknown")
        if hand == "ambidextrous":
            base_xg *= 1.05

        situation = shot.get("game_situation", "even")
        situation_mult = {
            "even": 1.0,
            "power_play": 1.10,
            "short_handed": 0.85,
            "empty_net": 1.40,
        }
        base_xg *= situation_mult.get(situation, 1.0)

        goalie_save_pct = shot.get("goalie_save_pct")
        if goalie_save_pct is not None and goalie_save_pct > 0:
            base_xg *= goalie_xg_multiplier(goalie_save_pct)

        return max(0.0, min(1.0, base_xg))

    def _heuristic_xg(self, shot: Dict[str, Any]) -> float:
        distance = math.hypot(shot["x"], shot["y"])
        xg = math.exp(-0.045 * distance)
        if shot.get("defender_distance", 5.0) < 2.0:
            xg *= 0.60
        if shot.get("rebound"):
            xg *= 1.15
        return max(0.0, min(1.0, xg))

    def evaluate(self, shots: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not shots:
            return {
                "total_xg": 0, "actual_goals": 0, "xdiff": 0,
                "brier_score": 0, "calibration": [],
                "placement_breakdown": {},
                "goalie_breakdown": {},
            }

        xgs = [self.calculate_xg(s) for s in shots]
        goals = [1.0 if s.get("is_goal") else 0.0 for s in shots]

        total_xg = float(sum(xgs))
        actual_goals = float(sum(goals))
        brier = float(
            sum((xg - g) ** 2 for xg, g in zip(xgs, goals)) / len(shots)
        )

        placement_counts = {p: 0 for p in PLACEMENT_OPTIONS}
        placement_goals = {p: 0 for p in PLACEMENT_OPTIONS}
        for shot, g in zip(shots, goals):
            placement = shot.get("placement", "off_target")
            if placement in placement_counts:
                placement_counts[placement] += 1
                placement_goals[placement] += int(g)

        placement_breakdown = {
 p: {
                "shots": placement_counts[p],
                "goals": placement_goals[p],
                "rate": (placement_goals[p] / placement_counts[p]
                         if placement_counts[p] else 0.0),
            }
            for p in PLACEMENT_OPTIONS
        }

        goalie_breakdown: Dict[str, Dict[str, Any]] = {}
        for shot, xg, g in zip(shots, xgs, goals):
            goalie = shot.get("goalie_name") or "unknown"
            if goalie not in goalie_breakdown:
                goalie_breakdown[goalie] = {
                    "shots": 0, "goals": 0, "total_xg": 0.0,
                    "save_pct": shot.get("goalie_save_pct"),
                    "tier": goalie_tier_label(shot.get("goalie_save_pct")),
 }
            goalie_breakdown[goalie]["shots"] += 1
            goalie_breakdown[goalie]["goals"] += int(g)
            goalie_breakdown[goalie]["total_xg"] += xg

        for g_name, g_stats in goalie_breakdown.items():
            n = g_stats["shots"]
            g_stats["shooting_pct"] = (g_stats["goals"] / n) if n else 0.0
            g_stats["xdiff"] = g_stats["goals"] - g_stats["total_xg"]

        return {
            "total_xg": total_xg,
            "actual_goals": actual_goals,
            "xdiff": total_xg - actual_goals,
            "brier_score": brier,
            "calibration": [],
            "placement_breakdown": placement_breakdown,
            "goalie_breakdown": goalie_breakdown,
        }

    def evaluate_by_shooter(self, shots: List[Dict[str, Any]]) -> Dict[str, Any]:
        by_s = {}
        for shot in shots:
            shooter = shot.get("shooter_id") or "unknown"
            if shooter not in by_s:
                by_s[shooter] = {
                    "shots": 0, "goals": 0, "total_xg": 0.0,
                    "placements": {p: 0 for p in PLACEMENT_OPTIONS},
                    "hands": {h: 0 for h in HAND_OPTIONS},
                    "jersey_number": shot.get("jersey_number", ""),
                    "player_name": shot.get("player_name", ""),
                }
            xg = self.calculate_xg(shot)
            is_goal = 1.0 if shot.get("is_goal") else 0.0
            by_s[shooter]["shots"] += 1
            by_s[shooter]["goals"] += int(is_goal)
            by_s[shooter]["total_xg"] += xg
            placement = shot.get("placement", "off_target")
            if placement in by_s[shooter]["placements"]:
                by_s[shooter]["placements"][placement] += 1
            hand = shot.get("shooting_hand", "unknown")
            if hand in by_s[shooter]["hands"]:
                by_s[shooter]["hands"][hand] += 1
            if shot.get("jersey_number") and not by_s[shooter]["jersey_number"]:
                by_s[shooter]["jersey_number"] = shot["jersey_number"]
            if shot.get("player_name") and not by_s[shooter]["player_name"]:
                by_s[shooter]["player_name"] = shot["player_name"]

        for shooter, stats in by_s.items():
            shots_count = stats["shots"]
            stats["shooting_pct"] = (
                stats["goals"] / shots_count if shots_count else 0.0
            )
            stats["xdiff"] = stats["goals"] - stats["total_xg"]
            stats["xG_per_shot"] = (
                stats["total_xg"] / shots_count if shots_count else 0.0
            )
            if stats["total_xg"] > 0:
                stats["conversion_rate"] = stats["goals"] / stats["total_xg"]
            else:
                stats["conversion_rate"] = 0.0
        return by_s

    def get_shooter_report(self, shooter_id: str, shots: List[Dict[str, Any]]) -> Dict[str, Any]:
        shooter_shots = [s for s in shots if s.get("shooter_id") == shooter_id]
        if not shooter_shots:
            return None
        overall = self.evaluate(shooter_shots)
        by_s = self.evaluate_by_shooter(shooter_shots)
        return {
            "shooter_id": shooter_id,
            "shots": shooter_shots,
            "stats": overall,
            "shooter_summary": by_s.get(shooter_id, {}),
        }