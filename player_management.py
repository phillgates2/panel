"""
Player Management and Community System

Comprehensive player tracking, moderation, community features, and
social systems for ET:Legacy game servers.
"""

import json
from datetime import datetime, timedelta, timezone

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import desc, func, or_

from app import db

player_bp = Blueprint("players", __name__)


class Player(db.Model):
    """Unified player identity across servers."""

    __tablename__ = "player"

    id = db.Column(db.Integer, primary_key=True)

    # Identity
    name = db.Column(db.String(128), nullable=False)
    guid = db.Column(db.String(64), nullable=False, unique=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 support

    # Status
    status = db.Column(
        db.String(32), default="active"
    )  # active, banned, suspended, vip
    registration_date = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_seen = db.Column(db.DateTime, nullable=True)
    last_server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=True)

    # Statistics
    total_playtime = db.Column(db.Integer, default=0)  # minutes
    total_sessions = db.Column(db.Integer, default=0)
    total_kills = db.Column(db.Integer, default=0)
    total_deaths = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)

    # Reputation system
    reputation_score = db.Column(db.Integer, default=0)
    commendations = db.Column(db.Integer, default=0)
    reports = db.Column(db.Integer, default=0)

    # Profile
    country = db.Column(db.String(8), nullable=True)  # Country code
    preferred_team = db.Column(db.String(16), nullable=True)  # axis, allies
    skill_level = db.Column(db.Integer, default=0)  # 0-10 skill rating

    # Community features
    is_verified = db.Column(db.Boolean, default=False)
    is_vip = db.Column(db.Boolean, default=False)
    badges = db.Column(db.Text, nullable=True)  # JSON array of badges

    last_server = db.relationship("Server", foreign_keys=[last_server_id])


class PlayerBan(db.Model):
    """Player bans and suspensions."""

    __tablename__ = "player_ban"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False)
    server_id = db.Column(
        db.Integer, db.ForeignKey("server.id"), nullable=True
    )  # NULL for global ban

    # Ban details
    ban_type = db.Column(
        db.String(32), nullable=False
    )  # temporary, permanent, ip, guid
    reason = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.Text, nullable=True)  # Screenshots, logs, etc.

    # Timing
    banned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=True)  # NULL for permanent
    lifted_at = db.Column(db.DateTime, nullable=True)

    # Staff
    banned_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    lifted_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    is_active = db.Column(db.Boolean, default=True)

    player = db.relationship("Player", backref=db.backref("bans", lazy="dynamic"))
    server = db.relationship("Server")
    banner = db.relationship("User", foreign_keys=[banned_by])
    lifter = db.relationship("User", foreign_keys=[lifted_by])


class PlayerReport(db.Model):
    """Player reports and moderation tickets."""

    __tablename__ = "player_report"

    id = db.Column(db.Integer, primary_key=True)
    reported_player_id = db.Column(
        db.Integer, db.ForeignKey("player.id"), nullable=False
    )
    server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=False)

    # Report details
    report_type = db.Column(
        db.String(32), nullable=False
    )  # cheating, griefing, spam, etc.
    description = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.Text, nullable=True)  # JSON array of evidence

    # Reporter (can be anonymous)
    reporter_name = db.Column(db.String(128), nullable=True)
    reporter_guid = db.Column(db.String(64), nullable=True)
    reporter_ip = db.Column(db.String(45), nullable=True)

    # Status
    status = db.Column(
        db.String(32), default="pending"
    )  # pending, investigating, resolved, dismissed
    priority = db.Column(db.String(16), default="normal")  # low, normal, high, urgent

    # Timestamps
    reported_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)

    # Staff handling
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    reported_player = db.relationship(
        "Player", backref=db.backref("reports_against", lazy="dynamic")
    )
    server = db.relationship("Server")
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    resolver = db.relationship("User", foreign_keys=[resolved_by])


class PlayerAchievement(db.Model):
    """Player achievements and milestones."""

    __tablename__ = "player_achievement"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False)

    achievement_type = db.Column(db.String(64), nullable=False)
    achievement_data = db.Column(db.Text, nullable=True)  # JSON data

    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=True)

    player = db.relationship(
        "Player", backref=db.backref("achievements", lazy="dynamic")
    )
    server = db.relationship("Server")


class PlayerSession(db.Model):
    """Detailed player session tracking."""

    __tablename__ = "player_session"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=False)

    # Session timing
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)

    # Session stats
    kills = db.Column(db.Integer, default=0)
    deaths = db.Column(db.Integer, default=0)
    score = db.Column(db.Integer, default=0)
    team = db.Column(db.String(16), nullable=True)

    # Maps played (JSON array)
    maps_played = db.Column(db.Text, nullable=True)

    # Connection info
    connection_ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(256), nullable=True)

    player = db.relationship("Player", backref=db.backref("sessions", lazy="dynamic"))
    server = db.relationship("Server")


class CommunityEvent(db.Model):
    """Community events and tournaments."""

    __tablename__ = "community_event"

    id = db.Column(db.Integer, primary_key=True)

    # Event details
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_type = db.Column(db.String(32), nullable=False)  # tournament, match, training

    # Scheduling
    scheduled_start = db.Column(db.DateTime, nullable=False)
    scheduled_end = db.Column(db.DateTime, nullable=True)
    actual_start = db.Column(db.DateTime, nullable=True)
    actual_end = db.Column(db.DateTime, nullable=True)

    # Configuration
    server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=True)
    max_participants = db.Column(db.Integer, nullable=True)
    entry_requirements = db.Column(db.Text, nullable=True)  # JSON

    # Status
    status = db.Column(
        db.String(32), default="planned"
    )  # planned, active, completed, cancelled

    # Organization
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    server = db.relationship("Server")
    organizer = db.relationship("User")


class PlayerManager:
    """Centralized player management system."""

    def __init__(self):
        pass

    def find_or_create_player(self, name, guid, ip_address=None):
        """Find existing player or create new one."""
        try:
            player = Player.query.filter_by(guid=guid).first()

            if not player:
                player = Player(
                    name=name,
                    guid=guid,
                    ip_address=ip_address,
                    last_seen=datetime.now(timezone.utc),
                )
                db.session.add(player)
            else:
                # Update player info
                player.name = name  # Update name in case it changed
                player.ip_address = ip_address  # Update IP
                player.last_seen = datetime.now(timezone.utc)

            db.session.commit()
            return player

        except Exception as e:
            db.session.rollback()
            raise e

    def start_session(self, player_id, server_id, connection_ip=None):
        """Start a new player session."""
        try:
            # End any existing active sessions for this player
            active_sessions = PlayerSession.query.filter(
                PlayerSession.player_id == player_id, PlayerSession.ended_at.is_(None)
            ).all()

            for session in active_sessions:
                self.end_session(session.id)

            # Create new session
            session = PlayerSession(
                player_id=player_id, server_id=server_id, connection_ip=connection_ip
            )

            db.session.add(session)
            db.session.commit()

            # Update player statistics
            player = Player.query.get(player_id)
            player.total_sessions += 1
            player.last_server_id = server_id
            db.session.commit()

            return session

        except Exception as e:
            db.session.rollback()
            raise e

    def end_session(self, session_id, stats=None):
        """End a player session and update statistics."""
        try:
            session = PlayerSession.query.get(session_id)
            if not session or session.ended_at:
                return None

            session.ended_at = datetime.now(timezone.utc)

            # Calculate duration
            duration = session.ended_at - session.started_at
            session.duration_minutes = int(duration.total_seconds() / 60)

            # Update session stats if provided
            if stats:
                session.kills = stats.get("kills", 0)
                session.deaths = stats.get("deaths", 0)
                session.score = stats.get("score", 0)
                session.team = stats.get("team")
                session.maps_played = json.dumps(stats.get("maps", []))

            # Update player totals
            player = session.player
            player.total_playtime += session.duration_minutes
            player.total_kills += session.kills
            player.total_deaths += session.deaths
            player.total_score += session.score

            db.session.commit()

            # Check for achievements
            self._check_achievements(session.player_id)

            return session

        except Exception as e:
            db.session.rollback()
            raise e

    def _check_achievements(self, player_id):
        """Check and award achievements for player."""
        try:
            player = Player.query.get(player_id)
            if not player:
                return

            achievements_to_award = []

            # Define achievement criteria
            achievement_criteria = {
                "first_session": {"total_sessions": 1},
                "veteran_10h": {"total_playtime": 600},  # 10 hours
                "veteran_100h": {"total_playtime": 6000},  # 100 hours
                "killer_1000": {"total_kills": 1000},
                "survivor": {
                    "deaths_ratio": lambda p: p.total_deaths < p.total_kills * 0.5
                },
                "regular": {"total_sessions": 50},
            }

            for achievement_type, criteria in achievement_criteria.items():
                # Check if already earned
                existing = PlayerAchievement.query.filter_by(
                    player_id=player_id, achievement_type=achievement_type
                ).first()

                if existing:
                    continue

                # Check criteria
                earned = True
                for field, threshold in criteria.items():
                    if callable(threshold):
                        if not threshold(player):
                            earned = False
                            break
                    else:
                        if getattr(player, field, 0) < threshold:
                            earned = False
                            break

                if earned:
                    achievements_to_award.append(achievement_type)

            # Award achievements
            for achievement_type in achievements_to_award:
                achievement = PlayerAchievement(
                    player_id=player_id, achievement_type=achievement_type
                )
                db.session.add(achievement)

            if achievements_to_award:
                db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"Achievement checking error: {e}")

    def ban_player(
        self,
        player_id,
        server_id,
        ban_type,
        reason,
        duration_hours=None,
        banned_by_user_id=None,
        evidence=None,
    ):
        """Ban a player."""
        try:
            expires_at = None
            if duration_hours:
                expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=duration_hours
                )

            ban = PlayerBan(
                player_id=player_id,
                server_id=server_id,
                ban_type=ban_type,
                reason=reason,
                evidence=evidence,
                expires_at=expires_at,
                banned_by=banned_by_user_id,
            )

            db.session.add(ban)

            # Update player status
            player = Player.query.get(player_id)
            player.status = "banned"

            db.session.commit()

            return ban

        except Exception as e:
            db.session.rollback()
            raise e

    def lift_ban(self, ban_id, lifted_by_user_id, reason=None):
        """Lift a player ban."""
        try:
            ban = PlayerBan.query.get(ban_id)
            if not ban or not ban.is_active:
                return None

            ban.is_active = False
            ban.lifted_at = datetime.now(timezone.utc)
            ban.lifted_by = lifted_by_user_id

            if reason:
                ban.resolution_notes = reason

            # Check if player has other active bans
            other_bans = PlayerBan.query.filter(
                PlayerBan.player_id == ban.player_id,
                PlayerBan.is_active,
                PlayerBan.id != ban_id,
            ).first()

            if not other_bans:
                # No other active bans, restore player status
                player = ban.player
                player.status = "active"

            db.session.commit()

            return ban

        except Exception as e:
            db.session.rollback()
            raise e

    def create_report(
        self,
        reported_player_id,
        server_id,
        report_type,
        description,
        reporter_name=None,
        reporter_guid=None,
        reporter_ip=None,
        evidence=None,
    ):
        """Create a player report."""
        try:
            report = PlayerReport(
                reported_player_id=reported_player_id,
                server_id=server_id,
                report_type=report_type,
                description=description,
                reporter_name=reporter_name,
                reporter_guid=reporter_guid,
                reporter_ip=reporter_ip,
                evidence=json.dumps(evidence) if evidence else None,
            )

            db.session.add(report)
            db.session.commit()

            return report

        except Exception as e:
            db.session.rollback()
            raise e

    def get_player_statistics(self, player_id):
        """Get comprehensive player statistics."""
        player = Player.query.get(player_id)
        if not player:
            return None

        # Recent sessions
        recent_sessions = (
            PlayerSession.query.filter_by(player_id=player_id)
            .order_by(desc(PlayerSession.started_at))
            .limit(10)
            .all()
        )

        # Achievements
        achievements = (
            PlayerAchievement.query.filter_by(player_id=player_id)
            .order_by(desc(PlayerAchievement.earned_at))
            .all()
        )

        # Active bans
        active_bans = PlayerBan.query.filter(
            PlayerBan.player_id == player_id, PlayerBan.is_active
        ).all()

        # Server distribution
        server_stats = (
            db.session.query(
                PlayerSession.server_id,
                func.count(PlayerSession.id).label("session_count"),
                func.sum(PlayerSession.duration_minutes).label("total_time"),
            )
            .filter(PlayerSession.player_id == player_id)
            .group_by(PlayerSession.server_id)
            .all()
        )

        return {
            "player": player,
            "recent_sessions": recent_sessions,
            "achievements": achievements,
            "active_bans": active_bans,
            "server_stats": server_stats,
            "kd_ratio": player.total_kills / max(player.total_deaths, 1),
            "average_score": player.total_score / max(player.total_sessions, 1),
        }


# Global player manager instance
player_manager = PlayerManager()


@player_bp.route("/admin/players")
@login_required
def players_dashboard():
    """Main players management dashboard."""
    if not current_user.is_system_admin:
        return redirect(url_for("dashboard"))

    # Get player statistics
    total_players = Player.query.count()
    active_players = Player.query.filter_by(status="active").count()
    banned_players = Player.query.filter_by(status="banned").count()
    vip_players = Player.query.filter_by(is_vip=True).count()

    # Recent players
    recent_players = Player.query.order_by(desc(Player.last_seen)).limit(20).all()

    # Top players by playtime
    top_players = Player.query.order_by(desc(Player.total_playtime)).limit(10).all()

    # Pending reports
    pending_reports = PlayerReport.query.filter_by(status="pending").count()

    return render_template(
        "admin_players_dashboard.html",
        total_players=total_players,
        active_players=active_players,
        banned_players=banned_players,
        vip_players=vip_players,
        recent_players=recent_players,
        top_players=top_players,
        pending_reports=pending_reports,
    )


@player_bp.route("/admin/players/<int:player_id>")
@login_required
def player_profile(player_id):
    """Detailed player profile."""
    if not current_user.is_system_admin:
        return redirect(url_for("dashboard"))

    stats = player_manager.get_player_statistics(player_id)
    if not stats:
        flash("Player not found", "error")
        return redirect(url_for("players.players_dashboard"))

    return render_template("admin_player_profile.html", **stats)


@player_bp.route("/admin/reports")
@login_required
def reports_dashboard():
    """Player reports management."""
    if not current_user.is_system_admin:
        return redirect(url_for("dashboard"))

    status_filter = request.args.get("status", "pending")

    reports = (
        PlayerReport.query.filter_by(status=status_filter)
        .order_by(desc(PlayerReport.reported_at))
        .limit(100)
        .all()
    )

    return render_template(
        "admin_player_reports.html", reports=reports, current_status=status_filter
    )


@player_bp.route("/admin/players/<int:player_id>/ban", methods=["POST"])
@login_required
def ban_player(player_id):
    """Ban a player."""
    if not current_user.is_system_admin:
        return jsonify({"success": False, "error": "Access denied"}), 403

    try:
        data = request.get_json()

        ban = player_manager.ban_player(
            player_id=player_id,
            server_id=data.get("server_id"),
            ban_type=data["ban_type"],
            reason=data["reason"],
            duration_hours=data.get("duration_hours"),
            banned_by_user_id=current_user.id,
            evidence=data.get("evidence"),
        )

        return jsonify(
            {"success": True, "ban_id": ban.id, "message": "Player banned successfully"}
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@player_bp.route("/api/players/search")
@login_required
def search_players():
    """Search players API."""
    if not current_user.is_system_admin:
        return jsonify({"error": "Access denied"}), 403

    query_text = request.args.get("q", "")
    status_filter = request.args.get("status")
    limit = min(request.args.get("limit", 50, type=int), 200)

    query = Player.query

    if query_text:
        query = query.filter(
            or_(Player.name.contains(query_text), Player.guid.contains(query_text))
        )

    if status_filter:
        query = query.filter(Player.status == status_filter)

    players = query.limit(limit).all()

    results = []
    for player in players:
        results.append(
            {
                "id": player.id,
                "name": player.name,
                "guid": player.guid,
                "status": player.status,
                "total_playtime": player.total_playtime,
                "last_seen": player.last_seen.isoformat() if player.last_seen else None,
                "is_vip": player.is_vip,
            }
        )

    return jsonify({"success": True, "players": results, "total": len(results)})
