"""Blueprint routes for the ClauseEase admin dashboard."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, date
from io import BytesIO
from typing import Dict, List

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

admin_bp = Blueprint('admin_portal', __name__)

_User = None
_Document = None
_get_db = None


def configure_admin(get_db_callable, user_model, document_model) -> None:
    """Inject dependencies from the main application."""
    global _get_db, _User, _Document
    _get_db = get_db_callable
    _User = user_model
    _Document = document_model


def _encode_plot(fig: plt.Figure) -> str:
    """Convert a Matplotlib figure to a base64 data URI."""
    buffer = BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=120)
    buffer.seek(0)
    image_b64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{image_b64}"


def _registrations_last_week(db_session) -> Dict[str, int]:
    """Return registration counts keyed by ISO date string for the last 7 days."""
    today = date.today()
    start_date = today - timedelta(days=6)

    rows = (
        db_session.query(func.date(_User.created_at), func.count(_User.id))
        .filter(_User.created_at >= datetime.combine(start_date, datetime.min.time()))
        .group_by(func.date(_User.created_at))
        .all()
    )

    counts = {str(day): total for day, total in rows}
    result: Dict[str, int] = {}
    for offset in range(7):
        current = start_date + timedelta(days=offset)
        key = current.isoformat()
        result[key] = counts.get(key, 0)
    return result


def _documents_last_weeks(db_session) -> Dict[str, int]:
    """Return document counts keyed by week label for the last 4 calendar weeks."""
    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    four_weeks_ago_start = current_week_start - timedelta(weeks=3)

    rows = (
        db_session.query(func.strftime('%Y-%W', _Document.uploaded_at), func.count(_Document.id))
        .filter(_Document.uploaded_at >= datetime.combine(four_weeks_ago_start, datetime.min.time()))
        .group_by(func.strftime('%Y-%W', _Document.uploaded_at))
        .all()
    )

    counts = {week: total for week, total in rows}

    result: Dict[str, int] = {}
    for weeks_back in reversed(range(4)):
        week_start = current_week_start - timedelta(weeks=weeks_back)
        week_end = week_start + timedelta(days=6)
        week_key = week_start.strftime('%Y-%W')
        label = f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}"
        result[label] = counts.get(week_key, 0)
    return result


def _build_line_chart(labels: List[str], values: List[int], title: str) -> str:
    sns.set_theme(style='whitegrid')
    fig, ax = plt.subplots(figsize=(7, 3.6))
    sns.lineplot(x=labels, y=values, marker='o', linewidth=2, color='#2563EB', ax=ax)
    ax.set_xlabel('')
    ax.set_ylabel('Count', fontweight='bold')
    ax.set_ylim(bottom=0)
    for tick in ax.get_xticklabels():
        tick.set_rotation(25)
    fig.tight_layout()
    return _encode_plot(fig)


def _build_bar_chart(labels: List[str], values: List[int], title: str) -> str:
    sns.set_theme(style='whitegrid')
    fig, ax = plt.subplots(figsize=(7, 3.6))
    palette = sns.color_palette('Blues', len(values))
    sns.barplot(x=labels, y=values, palette=palette, ax=ax)
    ax.set_xlabel('')
    ax.set_ylabel('Count', fontweight='bold')
    ax.set_ylim(bottom=0)
    for index, value in enumerate(values):
        ax.text(index, value + 0.05, str(value), ha='center', va='bottom', fontweight='bold')
    for tick in ax.get_xticklabels():
        tick.set_rotation(15)
    fig.tight_layout()
    return _encode_plot(fig)


@admin_bp.route('/admin')
@login_required
def admin_dashboard():
    if not all((_get_db, _User, _Document)):
        abort(500)
    if current_user.username.lower() != 'admin':
        abort(403)

    with _get_db() as db:
        total_users = db.query(_User).count()
        total_documents = db.query(_Document).count()
        today = datetime.now().date()
        active_users_today = (
            db.query(func.count(func.distinct(_Document.user_id)))
            .filter(func.date(_Document.uploaded_at) == today.isoformat())
            .scalar() or 0
        )

        registration_trend = _registrations_last_week(db)
        registration_labels = [
            datetime.fromisoformat(key).strftime('%d %b') for key in registration_trend.keys()
        ]
        registration_values = list(registration_trend.values())
        registrations_chart = _build_line_chart(
            registration_labels,
            registration_values,
            'User Registrations Per Day (Last 7 Days)'
        )

        documents_trend = _documents_last_weeks(db)
        documents_labels = list(documents_trend.keys())
        documents_values = list(documents_trend.values())
        documents_chart = _build_bar_chart(
            documents_labels,
            documents_values,
            'Documents Processed Per Week (Last 4 Weeks)'
        )

        active_users_rows = (
            db.query(_User.username, func.count(_Document.id).label('doc_count'))
            .outerjoin(_Document, _Document.user_id == _User.id)
            .group_by(_User.id)
            .order_by(func.count(_Document.id).desc())
            .limit(5)
            .all()
        )

    active_users_data = []
    for username, doc_count in active_users_rows:
        if doc_count >= 4:
            level = 'High'
        elif doc_count >= 2:
            level = 'Medium'
        else:
            level = 'Low'
        active_users_data.append({
            'username': username,
            'documents': doc_count,
            'activity_level': level
        })

    context = {
        'total_users': total_users,
        'total_documents': total_documents,
        'active_users_today': active_users_today,
        'registrations_chart': registrations_chart,
        'documents_chart': documents_chart,
        'active_users_data': active_users_data,
        'registration_labels': registration_labels,
        'documents_labels': documents_labels,
        'generated_at': datetime.utcnow(),
    }

    return render_template('admin.html', **context)
