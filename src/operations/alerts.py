"""
alerts.py — Operational Alert Engine for Namma Pulse OCC.

Generates real-time operational alerts based on emergent simulation state,
train delays, headway bunching lifecycles, platform crowding, ML forecasts, and active incidents.

Alert Priorities:
- INFO (1)
- WARNING (2)
- HIGH (3)
- CRITICAL (4)
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class AlertSeverity(str, Enum):
    INFO = "INFO"          # 🟢 Info / Normal
    WARNING = "WARNING"      # 🟡 Minor delay (+1:20)
    HIGH = "HIGH"          # 🟠 Train bunching / Platform crowding (75%+)
    CRITICAL = "CRITICAL"    # 🔴 Severe delay (+5:40) / Block closure / Incident


@dataclass
class Alert:
    id: str
    timestamp_formatted: str
    severity: AlertSeverity
    title: str
    message: str
    source: str = "SIMULATED OPERATIONS"

    @property
    def priority(self) -> int:
        p_map = {
            AlertSeverity.INFO: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4,
        }
        return p_map.get(self.severity, 1)

    def to_dict(self) -> Dict:
        icon_map = {
            AlertSeverity.INFO: "🟢",
            AlertSeverity.WARNING: "🟡",
            AlertSeverity.HIGH: "🟠",
            AlertSeverity.CRITICAL: "🔴",
        }
        return {
            "id": self.id,
            "timestamp": self.timestamp_formatted,
            "severity": self.severity.value,
            "priority": self.priority,
            "icon": icon_map.get(self.severity, "ℹ️"),
            "title": self.title,
            "message": self.message,
            "source": self.source,
        }


class AlertEngine:
    """
    Evaluates simulation state and generates dynamic OCC alert feed.
    Deduplicates active alert messages across simulation ticks.
    """

    def __init__(self):
        self.alerts: List[Alert] = []

    def generate_alerts(
        self,
        formatted_time: str,
        active_scenario_name: Optional[str] = None,
        trains: Optional[List[Dict]] = None,
        bunching_lifecycle_events: Optional[List[Dict]] = None,
        station_crowding_list: Optional[List[Dict]] = None,
        high_congestion_edges: Optional[List[str]] = None,
        forecast_alerts: Optional[List[Dict]] = None,
    ) -> List[Alert]:
        new_alerts: List[Alert] = []

        # 1. External Disruption Incident Alerts (CRITICAL)
        if active_scenario_name:
            new_alerts.append(
                Alert(
                    id=f"alert-scenario-{formatted_time}",
                    timestamp_formatted=formatted_time,
                    severity=AlertSeverity.CRITICAL,
                    title="ACTIVE DISRUPTION INCIDENT",
                    message=f"Disruption scenario '{active_scenario_name}' active on network state.",
                    source="SIMULATED SCENARIO",
                )
            )

        # 2. Train Delay & Wait Alerts (WARNING / CRITICAL)
        if trains:
            for t in trains:
                delay = t.get("delay_seconds", 0)
                status = t.get("status")
                t_id = t.get("train_id")
                is_held = t.get("is_held", False)
                wait_reason = t.get("wait_reason")

                if is_held or wait_reason == "OPERATOR_HOLD":
                    new_alerts.append(
                        Alert(
                            id=f"alert-held-{t_id}",
                            timestamp_formatted=formatted_time,
                            severity=AlertSeverity.CRITICAL,
                            title=f"Train {t_id} HELD by Operator",
                            message=f"Train {t_id} held at {t.get('current_station')} ({t.get('hold_reason', 'Operator Command')}).",
                        )
                    )
                elif wait_reason == "INSUFFICIENT_SEPARATION":
                    new_alerts.append(
                        Alert(
                            id=f"alert-sep-{t_id}",
                            timestamp_formatted=formatted_time,
                            severity=AlertSeverity.HIGH,
                            title=f"Train {t_id} Safe Separation Wait",
                            message=f"Train {t_id} holding behind leader {t.get('leader_train_id')} due to section occupancy.",
                        )
                    )
                elif wait_reason == "STATION_OCCUPIED":
                    new_alerts.append(
                        Alert(
                            id=f"alert-st-occ-{t_id}",
                            timestamp_formatted=formatted_time,
                            severity=AlertSeverity.HIGH,
                            title=f"Train {t_id} Station Platform Wait",
                            message=f"Train {t_id} waiting outside {t.get('next_station')} (platform occupied).",
                        )
                    )
                elif status == "CRITICAL_DELAY" or delay > 300:
                    new_alerts.append(
                        Alert(
                            id=f"alert-crit-delay-{t_id}",
                            timestamp_formatted=formatted_time,
                            severity=AlertSeverity.CRITICAL,
                            title=f"Train {t_id} +{delay // 60}:{delay % 60:02d}",
                            message=f"Severe operational delay on Train {t_id} ({t.get('line')} Line).",
                        )
                    )
                elif status in ("MINOR_DELAY", "DELAYED") or 60 < delay <= 300:
                    new_alerts.append(
                        Alert(
                            id=f"alert-warn-delay-{t_id}",
                            timestamp_formatted=formatted_time,
                            severity=AlertSeverity.WARNING,
                            title=f"Train {t_id} +{delay // 60}:{delay % 60:02d}",
                            message=f"Minor delay on Train {t_id} at {t.get('current_station')}.",
                        )
                    )

        # 3. Train Bunching Lifecycle Alerts (HIGH)
        if bunching_lifecycle_events:
            for b in bunching_lifecycle_events:
                ev = b.get("event")
                line = b.get("line")
                if ev == "DETECTED":
                    new_alerts.append(
                        Alert(
                            id=f"alert-bunch-det-{line}",
                            timestamp_formatted=formatted_time,
                            severity=AlertSeverity.HIGH,
                            title=f"Train Bunching Detected ({line} Line)",
                            message=f"Headway disturbance on {line} Line. Trains operating below separation threshold.",
                        )
                    )
                elif ev == "PERSISTING":
                    new_alerts.append(
                        Alert(
                            id=f"alert-bunch-pers-{line}",
                            timestamp_formatted=formatted_time,
                            severity=AlertSeverity.HIGH,
                            title=f"Train Bunching Persisting ({line} Line)",
                            message=f"Headway bunching continues on {line} Line.",
                        )
                    )

        # 4. Station Crowding Alerts (HIGH / CRITICAL)
        if station_crowding_list:
            for c in station_crowding_list:
                pct = c.get("crowding_pct", 0)
                st_name = c.get("station_name")
                if pct >= 75.0:
                    severity = AlertSeverity.CRITICAL if pct >= 88.0 else AlertSeverity.HIGH
                    new_alerts.append(
                        Alert(
                            id=f"alert-crowd-{st_name}",
                            timestamp_formatted=formatted_time,
                            severity=severity,
                            title=f"High Platform Occupancy: {st_name}",
                            message=f"{st_name} platform occupancy at {pct:.1f}% ({c.get('crowding_band')} crowding).",
                        )
                    )

        # 5. ML Forecast Alerts (HIGH / CRITICAL)
        if forecast_alerts:
            for f in forecast_alerts:
                new_alerts.append(
                    Alert(
                        id=f"alert-forecast-{f.get('target')}",
                        timestamp_formatted=formatted_time,
                        severity=AlertSeverity.CRITICAL if f.get("predicted_val", 0) >= 80 else AlertSeverity.HIGH,
                        title=f"High Congestion Forecast (+{f.get('horizon_min', 15)} min)",
                        message=f"Predicted {f.get('predicted_val')}% congestion at {f.get('target')}.",
                        source="SYNTHETIC MODEL OUTPUT",
                    )
                )

        # 6. Default Normal Operational Status
        if not new_alerts:
            new_alerts.append(
                Alert(
                    id=f"alert-normal-{formatted_time}",
                    timestamp_formatted=formatted_time,
                    severity=AlertSeverity.INFO,
                    title="Network Operating Normally",
                    message="All active train services operating within standard section and headway tolerances.",
                )
            )

        # Sort by priority descending (CRITICAL -> HIGH -> WARNING -> INFO)
        new_alerts.sort(key=lambda a: a.priority, reverse=True)
        self.alerts = new_alerts
        return self.alerts
